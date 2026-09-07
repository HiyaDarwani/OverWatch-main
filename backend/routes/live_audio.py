"""
FastAPI Routes for Live Microphone Audio Streaming & Snapshot Processing.

Endpoints:
  WS /api/live/audio            — Binary WebSocket endpoint for live microphone PCM streaming
  POST /api/live/snapshot/analyze — Runs Gemini AI acoustic intelligence on live rolling buffer snapshot
  POST /api/live/snapshot/denoise — Runs DeepFilterNet speech enhancement on live rolling buffer snapshot
"""
import re
import uuid
import asyncio
import logging
from pathlib import Path
from typing import Dict, Any, Optional

from fastapi import APIRouter, WebSocket, WebSocketDisconnect, HTTPException, status, Query
from pydantic import BaseModel

from services.realtime_audio import live_session_manager, LiveAudioSession
from services.audio_analysis import analyze_audio
from services.gemini_analysis import analyze_audio_with_gemini
from services.deepfilter_service import process_audio as run_deepfilter_process, get_denoise_status

logger = logging.getLogger("overwatch.live_routes")

router = APIRouter(tags=["Live Audio"])

BASE_DIR = Path(__file__).resolve().parent.parent
UPLOADS_DIR = BASE_DIR / "uploads"


class SnapshotRequest(BaseModel):
    session_id: str
    duration_sec: float = 5.0


@router.websocket("/live/audio")
async def live_audio_websocket(websocket: WebSocket):
    """
    WebSocket endpoint for real-time microphone audio capture.

    Accepts:
      - Text JSON control messages: {"action": "start", "sample_rate": 48000, "channels": 1}
      - Binary PCM audio chunks: Raw Float32 or Int16 audio data from browser Web Audio API

    Emits:
      - {"type": "session_started", "session_id": "...", "sample_rate": 48000}
      - {"type": "telemetry", "rms": ..., "peak": ..., "db": ..., "spectrum": ..., "waveform": ...}
    """
    await websocket.accept()

    session_id = f"live_sess_{uuid.uuid4().hex[:8]}"
    session: Optional[LiveAudioSession] = None
    sample_rate = 48000
    channels = 1
    pcm_dtype = "float32"

    logger.info(f"[LiveWS] Connected client session: {session_id}")

    try:
        # Send initial handshake message
        await websocket.send_json({
            "type": "session_started",
            "session_id": session_id,
            "status": "ready",
            "message": "Send audio chunks or control message to start live capture."
        })

        session = live_session_manager.get_or_create_session(
            session_id=session_id, sample_rate=sample_rate, channels=channels
        )

        last_emit_time = 0.0
        emit_interval = 0.05  # Max ~20 FPS telemetry emission
        chunk_count = 0
        total_bytes_received = 0

        while True:
            # Receive either text control frame or binary PCM frame
            message = await websocket.receive()
            msg_type = message.get("type", "")

            if msg_type == "websocket.disconnect":
                logger.info(f"[LiveWS {session_id}] Clean disconnect signal received.")
                break

            if "text" in message and message["text"]:
                try:
                    import json
                    data = json.loads(message["text"])
                    action = data.get("action")

                    if action == "start":
                        sample_rate = int(data.get("sample_rate", 48000))
                        channels = int(data.get("channels", 1))
                        pcm_dtype = str(data.get("dtype", "float32")).lower()
                        session = live_session_manager.get_or_create_session(
                            session_id=session_id, sample_rate=sample_rate, channels=channels
                        )
                        await websocket.send_json({
                            "type": "status",
                            "status": "capturing",
                            "session_id": session_id,
                            "sample_rate": sample_rate,
                            "channels": channels,
                        })
                    elif action == "stop":
                        await websocket.send_json({
                            "type": "status",
                            "status": "stopped",
                            "session_id": session_id,
                        })
                    elif action == "ping":
                        await websocket.send_json({"type": "pong", "timestamp": asyncio.get_event_loop().time()})
                except Exception as text_err:
                    logger.warning(f"[LiveWS {session_id}] Text frame parse error: {text_err}")

            elif "bytes" in message and message["bytes"]:
                raw_bytes = message["bytes"]
                chunk_count += 1
                total_bytes_received += len(raw_bytes)

                if chunk_count == 1 or chunk_count % 100 == 0:
                    logger.info(f"[LiveWS {session_id}] Received PCM chunk #{chunk_count}: {len(raw_bytes)} bytes | Total: {total_bytes_received} bytes")

                if not session:
                    session = live_session_manager.get_or_create_session(
                        session_id=session_id, sample_rate=sample_rate, channels=channels
                    )

                # Process chunk in worker thread to prevent event loop blocking
                telemetry = await asyncio.to_thread(session.process_chunk, raw_bytes, pcm_dtype)

                now = asyncio.get_event_loop().time()
                if (now - last_emit_time) >= emit_interval:
                    last_emit_time = now
                    payload = {"type": "telemetry", **telemetry}
                    await websocket.send_json(payload)

    except WebSocketDisconnect:
        logger.info(f"[LiveWS] Client disconnected: {session_id}")
    except Exception as e:
        logger.error(f"[LiveWS] Error in live session {session_id}: {e}")
    finally:
        if session:
            session.last_activity = asyncio.get_event_loop().time()
            logger.info(f"[LiveWS] Session {session_id} marked idle (will be cleaned up after 60s idle).")


@router.post("/live/snapshot/analyze")
async def analyze_live_snapshot(req: SnapshotRequest):
    """
    Exports recent rolling audio buffer snapshot to WAV, runs Phase 3 DSP analysis,
    and calls Gemini AI for acoustic intelligence classification.
    """
    session = live_session_manager.get_session(req.session_id)
    if not session:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Live session '{req.session_id}' not found or expired. Make sure live capture is active."
        )

    if session.total_samples_received == 0 or len(session.buffer) < 1024:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Insufficient live microphone audio received (need at least ~0.1s / 1024 samples). Speak into the microphone and try again."
        )

    # 1. Export rolling buffer to WAV file
    wav_path, file_id = session.export_snapshot_wav(duration_sec=req.duration_sec)

    # 2. Perform Phase 3 DSP analysis
    try:
        phase3_result = await asyncio.to_thread(analyze_audio, wav_path, file_id)
    except Exception as dsp_err:
        logger.error(f"[LiveSnapshot] DSP analysis failed for {file_id}: {dsp_err}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Live snapshot DSP analysis failed: {str(dsp_err)}"
        )

    # 3. Call Gemini AI acoustic intelligence in worker thread safely
    try:
        ai_result = await asyncio.to_thread(analyze_audio_with_gemini, wav_path, file_id, phase3_result)
    except Exception as gemini_err:
        logger.error(f"[LiveSnapshot] Gemini analysis exception for {file_id}: {gemini_err}", exc_info=True)
        ai_result = {
            "file_id": file_id,
            "status": "unavailable",
            "error_code": "GEMINI_ERROR",
            "error": str(gemini_err),
            "analysis": None
        }

    return {
        "session_id": req.session_id,
        "file_id": file_id,
        "snapshot_url": f"/api/audio/{file_id}",
        "dsp_analysis": phase3_result,
        "gemini_analysis": ai_result,
    }


@router.post("/live/snapshot/denoise")
async def denoise_live_snapshot(req: SnapshotRequest):
    """
    Exports recent rolling audio buffer snapshot to WAV and runs DeepFilterNet speech enhancement.
    Returns DeepFilterNet processing result + enhanced audio streaming URL.
    """
    session = live_session_manager.get_session(req.session_id)
    if not session:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Live session '{req.session_id}' not found or expired. Make sure live capture is active."
        )

    if session.total_samples_received == 0 or len(session.buffer) == 0:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="No live microphone audio has been received yet for this session. Speak into the microphone and try again."
        )

    # 1. Export rolling buffer to WAV file
    wav_path, file_id = session.export_snapshot_wav(duration_sec=req.duration_sec)

    # 2. Run real DeepFilterNet inference in worker thread
    dfn_result = await asyncio.to_thread(run_deepfilter_process, wav_path, file_id)

    if dfn_result.get("status") == "error":
        error_code = dfn_result.get("error_code", "DEEPFILTERNET_INFERENCE_FAILED")
        error_msg = dfn_result.get("error", "DeepFilterNet processing failed.")
        status_code = status.HTTP_500_INTERNAL_SERVER_ERROR
        if error_code == "DEEPFILTERNET_NOT_INSTALLED":
            status_code = status.HTTP_503_SERVICE_UNAVAILABLE

        raise HTTPException(
            status_code=status_code,
            detail=f"Live DeepFilterNet snapshot error [{error_code}]: {error_msg}"
        )

    return {
        "session_id": req.session_id,
        "file_id": file_id,
        "original_url": f"/api/audio/{file_id}",
        "processed_url": f"/api/audio/processed/{file_id}",
        "deepfilter_result": dfn_result,
    }
