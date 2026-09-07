import os
import re
import uuid
import shutil
import asyncio
from pathlib import Path
from typing import List

from fastapi import APIRouter, File, UploadFile, HTTPException, status, WebSocket, WebSocketDisconnect
from fastapi.responses import FileResponse

from services.audio_metadata import extract_audio_metadata
from services.audio_analysis import analyze_audio
from services.gemini_analysis import analyze_audio_with_gemini
from services.rule_classifier import classify_audio_rule_based
from services.processing_simulator import (
    start_processing_simulation,
    get_processing_status,
    stop_processing_simulation,
)
from services.audio_comparison import get_audio_comparison
from services.deepfilter_service import (
    process_audio as run_deepfilter_process,
    get_denoise_status as get_deepfilter_status,
)
from services.fullsubnet_service import (
    process_audio as run_fullsubnet_process,
    get_denoise_status as get_fullsubnet_status,
)
from services.stream_simulator import (
    get_or_create_stream_simulator,
    get_stream_status,
    _ACTIVE_WEBSOCKETS,
    _ANALYSIS_CACHE,
)

router = APIRouter(tags=["Audio"])

# Allowed extensions (primary is .wav)
ALLOWED_EXTENSIONS = {".wav", ".mp3", ".flac"}
MAX_FILE_SIZE_BYTES = 50 * 1024 * 1024  # 50 MB

# Base upload directory
BASE_DIR = Path(__file__).resolve().parent.parent
UPLOADS_DIR = BASE_DIR / "uploads"
UPLOADS_DIR.mkdir(parents=True, exist_ok=True)


@router.post("/upload", status_code=status.HTTP_201_CREATED)
async def upload_audio(file: UploadFile = File(...)):
    """
    Accepts an audio file (primarily .wav), validates it, saves it to disk with a unique ID,
    and returns extracted audio metadata.
    """
    if not file or not file.filename:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="No file provided in the upload request."
        )

    original_filename = Path(file.filename).name  # Strips any directory info
    ext = Path(original_filename).suffix.lower()

    if ext not in ALLOWED_EXTENSIONS:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Unsupported file format '{ext}'. Allowed formats: {', '.join(sorted(ALLOWED_EXTENSIONS))}."
        )

    # Generate short unique file_id
    file_id = uuid.uuid4().hex[:12]
    stored_filename = f"{file_id}{ext}"
    target_path = UPLOADS_DIR / stored_filename

    # Prevent overwriting & path traversal
    try:
        resolved_target = target_path.resolve()
        if not str(resolved_target).startswith(str(UPLOADS_DIR.resolve())):
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Invalid file path detected."
            )
    except Exception:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid filename."
        )

    # Save file and calculate size
    bytes_written = 0
    try:
        with open(target_path, "wb") as buffer:
            while chunk := await file.read(1024 * 1024):  # 1MB chunks
                bytes_written += len(chunk)
                if bytes_written > MAX_FILE_SIZE_BYTES:
                    buffer.close()
                    if target_path.exists():
                        target_path.unlink()
                    raise HTTPException(
                        status_code=status.HTTP_413_REQUEST_ENTITY_TOO_LARGE,
                        detail=f"File size exceeds the maximum allowed limit of {MAX_FILE_SIZE_BYTES // (1024*1024)}MB."
                    )
                buffer.write(chunk)
    except HTTPException:
        raise
    except Exception as e:
        if target_path.exists():
            target_path.unlink()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to save file to disk: {str(e)}"
        )

    # Extract metadata
    try:
        metadata = extract_audio_metadata(target_path, original_filename)
    except ValueError as val_err:
        # Cleanup invalid/corrupted file
        if target_path.exists():
            target_path.unlink()
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Audio validation failed: {str(val_err)}"
        )
    except Exception as err:
        if target_path.exists():
            target_path.unlink()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Metadata extraction error: {str(err)}"
        )

    return {
        "success": True,
        "file_id": file_id,
        "filename": original_filename,
        "duration": metadata["duration"],
        "sample_rate": metadata["sample_rate"],
        "channels": metadata["channels"],
        "format": metadata["format"]
    }


@router.get("/audio/{file_id}")
async def get_audio(file_id: str):
    """
    Retrieves and streams the stored audio file by file_id.
    """
    # Strict validation of file_id to prevent path traversal
    if not re.match(r"^[a-zA-Z0-9_-]+$", file_id):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid file_id format."
        )

    # Find matching file in uploads directory
    matched_files = list(UPLOADS_DIR.glob(f"{file_id}.*"))
    if not matched_files:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Audio file with ID '{file_id}' was not found."
        )

    target_file = matched_files[0]

    # Verify security constraints (must be inside UPLOADS_DIR)
    try:
        resolved_file = target_file.resolve()
        if not str(resolved_file).startswith(str(UPLOADS_DIR.resolve())):
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Access denied."
            )
    except Exception:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="File resolution failed."
        )

    ext = target_file.suffix.lower()
    media_type = "audio/wav"
    if ext == ".mp3":
        media_type = "audio/mpeg"
    elif ext == ".flac":
        media_type = "audio/flac"

    return FileResponse(
        path=target_file,
        media_type=media_type,
        filename=target_file.name,
        headers={"Accept-Ranges": "bytes"}
    )


@router.get("/audio/{file_id}/analysis")
async def get_audio_analysis(file_id: str):
    """
    Performs real audio feature extraction and DSP analysis (FFT, STFT, spectral metrics)
    on the stored audio file and returns visualization-friendly data.
    """
    if not re.match(r"^[a-zA-Z0-9_-]+$", file_id):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid file_id format."
        )

    matched_files = list(UPLOADS_DIR.glob(f"{file_id}.*"))
    if not matched_files:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Audio file with ID '{file_id}' was not found."
        )

    target_file = matched_files[0]

    try:
        resolved_file = target_file.resolve()
        if not str(resolved_file).startswith(str(UPLOADS_DIR.resolve())):
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Access denied."
            )
    except Exception:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="File resolution failed."
        )

    try:
        result = await asyncio.to_thread(analyze_audio, target_file, file_id)
        # Populate analysis cache so the WS simulator can skip re-analysis
        if file_id not in _ANALYSIS_CACHE:
            _ANALYSIS_CACHE[file_id] = {}
        _ANALYSIS_CACHE[file_id]["analysis"] = result
        return result
    except ValueError as val_err:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Analysis failed: {str(val_err)}"
        )
    except Exception as err:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Audio processing error: {str(err)}"
        )


@router.post("/audio/{file_id}/analyze")
async def analyze_audio_with_ai(file_id: str):
    """
    Integrates Gemini API as the AI Audio Analysis / Intelligence layer.
    Extracts Phase 3 DSP features, sends audio and feature context to Gemini,
    validates the structured response, and returns AI acoustic intelligence.
    """
    if not re.match(r"^[a-zA-Z0-9_-]+$", file_id):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid file_id format."
        )

    matched_files = list(UPLOADS_DIR.glob(f"{file_id}.*"))
    if not matched_files:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Audio file with ID '{file_id}' was not found."
        )

    target_file = matched_files[0]

    try:
        resolved_file = target_file.resolve()
        if not str(resolved_file).startswith(str(UPLOADS_DIR.resolve())):
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Access denied."
            )
    except Exception:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="File resolution failed."
        )

    # 1. Obtain Phase 3 DSP analysis first
    try:
        phase3_result = await asyncio.to_thread(analyze_audio, target_file, file_id)
    except Exception as dsp_err:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"DSP pre-analysis failed: {str(dsp_err)}"
        )

    # 2. Perform Gemini AI analysis in worker thread (prevents event loop blocking)
    ai_result = await asyncio.to_thread(analyze_audio_with_gemini, target_file, file_id, phase3_result)

    # Populate analysis cache so the WS simulator can start immediately without re-running Gemini
    _ANALYSIS_CACHE[file_id] = {"analysis": phase3_result, "gemini": ai_result}

    return ai_result


@router.post("/audio/{file_id}/denoise")
async def denoise_audio_endpoint(file_id: str, model: str = "deepfilternet"):
    """
    Triggers REAL audio enhancement / denoising on the uploaded WAV file using either DeepFilterNet3 or FullSubNet+.
    """
    if not re.match(r"^[a-zA-Z0-9_-]+$", file_id):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid file_id format."
        )

    matched_files = list(UPLOADS_DIR.glob(f"{file_id}.*"))
    orig_files = [f for f in matched_files if not f.name.startswith("processed_")]
    if not orig_files:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Audio file with ID '{file_id}' was not found."
        )

    target_file = orig_files[0]

    try:
        resolved_file = target_file.resolve()
        if not str(resolved_file).startswith(str(UPLOADS_DIR.resolve())):
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Access denied."
            )
    except Exception:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="File resolution failed."
        )

    model_clean = model.lower().strip()
    if model_clean not in ("deepfilternet", "fullsubnet", "fullsubnet_plus"):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Unsupported model '{model}'. Must be 'deepfilternet' or 'fullsubnet'."
        )

    if model_clean in ("fullsubnet", "fullsubnet_plus"):
        result = await asyncio.to_thread(run_fullsubnet_process, target_file, file_id)
    else:
        result = await asyncio.to_thread(run_deepfilter_process, target_file, file_id)

    if result.get("status") == "error":
        error_code = result.get("error_code", "INFERENCE_FAILED")
        error_msg = result.get("error", "Denoising processing failed.")
        status_code = status.HTTP_500_INTERNAL_SERVER_ERROR
        if "NOT_INSTALLED" in error_code:
            status_code = status.HTTP_503_SERVICE_UNAVAILABLE
        elif error_code in ("INVALID_AUDIO", "UNSUPPORTED_AUDIO_FORMAT"):
            status_code = status.HTTP_400_BAD_REQUEST

        raise HTTPException(
            status_code=status_code,
            detail=f"Denoising error [{error_code}]: {error_msg}"
        )

    return result


@router.get("/audio/{file_id}/denoise/status")
async def get_denoise_status_endpoint(file_id: str, model: str = "deepfilternet"):
    """
    Returns current denoising status for file_id and specified model.
    """
    if not re.match(r"^[a-zA-Z0-9_-]+$", file_id):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid file_id format."
        )

    if model.lower().strip() in ("fullsubnet", "fullsubnet_plus"):
        return get_fullsubnet_status(file_id)
    return get_deepfilter_status(file_id)


@router.post("/audio/{file_id}/process")
async def start_processing(file_id: str):
    """
    Starts the OverWatch frame-based processing simulation for file_id.
    Uses Phase 3 DSP features and Phase 4 Gemini AI recommendations.
    Also triggers real DeepFilterNet denoising in parallel if available.
    """
    if not re.match(r"^[a-zA-Z0-9_-]+$", file_id):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid file_id format."
        )

    matched_files = list(UPLOADS_DIR.glob(f"{file_id}.*"))
    orig_files = [f for f in matched_files if not f.name.startswith("processed_")]
    if not orig_files:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Audio file with ID '{file_id}' was not found."
        )

    target_file = orig_files[0]

    # Retrieve Phase 3 DSP analysis
    try:
        phase3_res = await asyncio.to_thread(analyze_audio, target_file, file_id)
        cached_gemini = _ANALYSIS_CACHE.get(file_id, {}).get("gemini")
        if cached_gemini:
            gemini_res = cached_gemini
        else:
            rule_analysis = classify_audio_rule_based(phase3_res)
            gemini_res = {"file_id": file_id, "status": "success", "analysis": rule_analysis}
    except Exception as err:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Pre-processing pipeline initialization failed: {str(err)}"
        )

    # Trigger real DeepFilterNet processing in background thread so processed WAV exists
    asyncio.create_task(asyncio.to_thread(run_deepfilter_process, target_file, file_id))

    job = start_processing_simulation(target_file, file_id, phase3_res, gemini_res)
    return job


@router.get("/audio/{file_id}/process/status")
async def get_simulation_status(file_id: str):
    """
    Retrieves the current simulation state, progress, telemetry, logs, and output waveform.
    """
    if not re.match(r"^[a-zA-Z0-9_-]+$", file_id):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid file_id format."
        )

    return get_processing_status(file_id)


@router.post("/audio/{file_id}/process/stop")
async def stop_simulation(file_id: str):
    """
    Gracefully halts the running simulation for file_id.
    """
    if not re.match(r"^[a-zA-Z0-9_-]+$", file_id):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid file_id format."
        )

    return stop_processing_simulation(file_id)


@router.get("/audio/processed/{file_id}")
async def get_processed_audio(file_id: str, model: str = "deepfilternet"):
    """
    Streams the generated simulated or denoised output audio file.
    """
    clean_id = file_id.replace("processed_fsn_", "").replace("processed_", "")
    if not re.match(r"^[a-zA-Z0-9_-]+$", clean_id):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid file_id format."
        )

    fsn_file = UPLOADS_DIR / f"processed_fsn_{clean_id}.wav"
    dfn_file = UPLOADS_DIR / f"processed_{clean_id}.wav"

    if (model.lower().strip() in ("fullsubnet", "fullsubnet_plus") or file_id.startswith("processed_fsn_")) and fsn_file.exists():
        target_file = fsn_file
    elif dfn_file.exists():
        target_file = dfn_file
    elif fsn_file.exists():
        target_file = fsn_file
    else:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Processed audio for ID '{clean_id}' not found."
        )

    try:
        resolved = target_file.resolve()
        if not str(resolved).startswith(str(UPLOADS_DIR.resolve())):
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Access denied."
            )
    except Exception:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="File resolution failed."
        )

    return FileResponse(
        path=target_file,
        media_type="audio/wav",
        filename=target_file.name,
        headers={"Accept-Ranges": "bytes"}
    )


@router.get("/audio/{file_id}/comparison")
async def get_comparison(file_id: str, model: str = "deepfilternet"):
    """
    Retrieves real calculated DSP metrics, waveforms, spectra, spectrograms,
    and delta comparisons between the original uploaded WAV and generated output WAV.
    """
    if not re.match(r"^[a-zA-Z0-9_-]+$", file_id):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid file_id format."
        )

    res = get_audio_comparison(file_id, model=model)
    if res.get("status") == "error":
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=res.get("message", "Comparison failed.")
        )
    return res


@router.websocket("/audio/{file_id}/stream")
async def websocket_stream_endpoint(websocket: WebSocket, file_id: str):
    """
    WebSocket endpoint for real-time audio stream simulation events.
    Pushes frame updates, live FFT, telemetry, stage events, and handles client control messages.
    """
    await websocket.accept()

    if file_id not in _ACTIVE_WEBSOCKETS:
        _ACTIVE_WEBSOCKETS[file_id] = set()
    _ACTIVE_WEBSOCKETS[file_id].add(websocket)

    matched_files = list(UPLOADS_DIR.glob(f"{file_id}.*"))
    orig_files = [f for f in matched_files if not f.name.startswith("processed_")]

    if not orig_files:
        await websocket.send_json({"type": "error", "message": "Audio file not found."})
        await websocket.close()
        return

    sim = get_or_create_stream_simulator(file_id, orig_files[0])

    # Run async initialization (loads AI analysis if not already cached) — non-blocking
    await sim.initialize_async()

    try:
        # Send initial status & metadata so the frontend knows frames/duration immediately
        await websocket.send_json({
            "type": "init",
            "session_id": sim.session_id,
            "status": sim.status,
            "speed": sim.speed,
            "frame_index": sim.frame_index,
            "total_frames": sim.total_frames,
            "duration": sim.duration,
            "strategy": sim.strategy,
            "noise_type": sim.noise_type,
            "confidence": sim.confidence,
        })

        while True:
            data = await websocket.receive_json()
            action = data.get("action")
            if action == "start":
                sim.start(speed=float(data.get("speed", 1.0)))
            elif action == "pause":
                sim.pause()
            elif action == "resume":
                sim.resume()
            elif action == "stop":
                sim.stop()
            elif action == "reset":
                sim.reset()
            elif action == "set_speed":
                sim.set_speed(speed=float(data.get("speed", 1.0)))
    except WebSocketDisconnect:
        if file_id in _ACTIVE_WEBSOCKETS:
            _ACTIVE_WEBSOCKETS[file_id].discard(websocket)
    except Exception:
        if file_id in _ACTIVE_WEBSOCKETS:
            _ACTIVE_WEBSOCKETS[file_id].discard(websocket)



@router.post("/audio/{file_id}/stream/start")
async def start_stream_api(file_id: str, speed: float = 1.0):
    matched_files = list(UPLOADS_DIR.glob(f"{file_id}.*"))
    orig_files = [f for f in matched_files if not f.name.startswith("processed_")]
    if not orig_files:
        raise HTTPException(status_code=404, detail="Audio file not found.")
    sim = get_or_create_stream_simulator(file_id, orig_files[0])
    sim.start(speed=speed)
    return get_stream_status(file_id)


@router.post("/audio/{file_id}/stream/pause")
async def pause_stream_api(file_id: str):
    matched_files = list(UPLOADS_DIR.glob(f"{file_id}.*"))
    orig_files = [f for f in matched_files if not f.name.startswith("processed_")]
    if orig_files:
        sim = get_or_create_stream_simulator(file_id, orig_files[0])
        sim.pause()
    return get_stream_status(file_id)


@router.post("/audio/{file_id}/stream/resume")
async def resume_stream_api(file_id: str):
    matched_files = list(UPLOADS_DIR.glob(f"{file_id}.*"))
    orig_files = [f for f in matched_files if not f.name.startswith("processed_")]
    if orig_files:
        sim = get_or_create_stream_simulator(file_id, orig_files[0])
        sim.resume()
    return get_stream_status(file_id)


@router.post("/audio/{file_id}/stream/stop")
async def stop_stream_api(file_id: str):
    matched_files = list(UPLOADS_DIR.glob(f"{file_id}.*"))
    orig_files = [f for f in matched_files if not f.name.startswith("processed_")]
    if orig_files:
        sim = get_or_create_stream_simulator(file_id, orig_files[0])
        sim.stop()
    return get_stream_status(file_id)


@router.post("/audio/{file_id}/stream/reset")
async def reset_stream_api(file_id: str):
    matched_files = list(UPLOADS_DIR.glob(f"{file_id}.*"))
    orig_files = [f for f in matched_files if not f.name.startswith("processed_")]
    if orig_files:
        sim = get_or_create_stream_simulator(file_id, orig_files[0])
        sim.reset()
    return get_stream_status(file_id)


@router.post("/audio/{file_id}/stream/speed")
async def speed_stream_api(file_id: str, speed: float = 1.0):
    matched_files = list(UPLOADS_DIR.glob(f"{file_id}.*"))
    orig_files = [f for f in matched_files if not f.name.startswith("processed_")]
    if orig_files:
        sim = get_or_create_stream_simulator(file_id, orig_files[0])
        sim.set_speed(speed)
    return get_stream_status(file_id)


@router.get("/audio/{file_id}/stream/status")
async def status_stream_api(file_id: str):
    return get_stream_status(file_id)







