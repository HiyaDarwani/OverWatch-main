"""
DeepFilterNet Service — Real audio denoising engine for OverWatch.

This service provides the actual DeepFilterNet speech enhancement / denoising
capability. It is separate from and complementary to the Gemini AI acoustic
intelligence layer.

Gemini answers: "What is this noise and what processing strategy is appropriate?"
DeepFilterNet answers: "Actually denoise/enhance the audio."

Execution modes:
  1. Direct: If DeepFilterNet is importable in the current Python environment.
  2. Subprocess: Invokes deepfilter_worker.py inside .venv-dfn (separate Python venv).
"""
import os
import json
import time
import logging
import threading
import subprocess
from pathlib import Path
from typing import Dict, Any, Optional

logger = logging.getLogger("overwatch.deepfilter")

BASE_DIR = Path(__file__).resolve().parent.parent
UPLOADS_DIR = BASE_DIR / "uploads"
WORKER_SCRIPT = Path(__file__).resolve().parent / "deepfilter_worker.py"

# .venv-dfn Python executable (created by setup_deepfilter.ps1)
DFN_VENV_PYTHON = BASE_DIR / ".venv-dfn" / "Scripts" / "python.exe"

# Thread-safe state
_DFN_LOCK = threading.Lock()
_DFN_ACTIVE: Dict[str, str] = {}  # file_id -> status ("processing" | "success" | "error")
_DFN_RESULTS: Dict[str, Dict[str, Any]] = {}  # file_id -> result dict

# Direct-mode model cache (only used if DeepFilterNet is importable in current env)
_DIRECT_MODEL = None
_DIRECT_DF_STATE = None
_DIRECT_AVAILABLE: Optional[bool] = None


def _check_direct_availability() -> bool:
    """Check if DeepFilterNet can be imported directly in the current Python environment."""
    global _DIRECT_AVAILABLE
    if _DIRECT_AVAILABLE is not None:
        return _DIRECT_AVAILABLE
    try:
        from df.enhance import init_df, enhance, load_audio, save_audio
        _DIRECT_AVAILABLE = True
        logger.info("[DeepFilterNet] Direct import available in current environment.")
    except ImportError:
        _DIRECT_AVAILABLE = False
        logger.info("[DeepFilterNet] Not available in current env; will use subprocess mode.")
    return _DIRECT_AVAILABLE


def _check_subprocess_availability() -> bool:
    """Check if the .venv-dfn Python executable exists."""
    exists = DFN_VENV_PYTHON.is_file()
    if exists:
        logger.info(f"[DeepFilterNet] Subprocess venv found: {DFN_VENV_PYTHON}")
    else:
        logger.warning(f"[DeepFilterNet] Subprocess venv NOT found at: {DFN_VENV_PYTHON}")
    return exists


def get_engine_status() -> Dict[str, Any]:
    """
    Returns the current DeepFilterNet engine availability status.
    """
    direct = _check_direct_availability()
    subprocess_ok = _check_subprocess_availability()

    if direct:
        mode = "direct"
        available = True
    elif subprocess_ok:
        mode = "subprocess"
        available = True
    else:
        mode = "none"
        available = False

    return {
        "engine": "DeepFilterNet",
        "available": available,
        "mode": mode,
        "venv_path": str(DFN_VENV_PYTHON) if subprocess_ok else None,
        "worker_script": str(WORKER_SCRIPT) if WORKER_SCRIPT.is_file() else None,
    }


def get_denoise_status(file_id: str) -> Dict[str, Any]:
    """
    Returns the denoising status for a specific file_id.
    """
    if file_id in _DFN_RESULTS:
        return _DFN_RESULTS[file_id]

    if file_id in _DFN_ACTIVE:
        return {
            "file_id": file_id,
            "status": _DFN_ACTIVE[file_id],
            "engine": "DeepFilterNet",
        }

    # Check if a processed file already exists
    output_path = UPLOADS_DIR / f"processed_{file_id}.wav"
    if output_path.exists():
        return {
            "file_id": file_id,
            "status": "success",
            "engine": "DeepFilterNet",
            "output_file": f"processed_{file_id}.wav",
            "note": "Processed file exists (from previous run)."
        }

    engine_status = get_engine_status()
    if not engine_status["available"]:
        return {
            "file_id": file_id,
            "status": "not_installed",
            "engine": "DeepFilterNet",
            "error_code": "DEEPFILTERNET_NOT_INSTALLED",
            "error": "DeepFilterNet is not installed. Run setup_deepfilter.ps1 to set up the environment."
        }

    return {
        "file_id": file_id,
        "status": "not_started",
        "engine": "DeepFilterNet",
    }


def _run_direct(input_path: Path, output_path: Path) -> Dict[str, Any]:
    """
    Run DeepFilterNet inference directly in the current Python process.
    """
    global _DIRECT_MODEL, _DIRECT_DF_STATE

    from df.enhance import init_df, enhance, load_audio, save_audio

    # Lazy model initialization
    if _DIRECT_MODEL is None:
        logger.info("[DeepFilterNet] Loading model (direct mode)...")
        _DIRECT_MODEL, _DIRECT_DF_STATE, _ = init_df()
        logger.info(f"[DeepFilterNet] Model loaded. SR={_DIRECT_DF_STATE.sr()}")

    model = _DIRECT_MODEL
    df_state = _DIRECT_DF_STATE
    model_sr = df_state.sr()

    audio, _ = load_audio(str(input_path), sr=model_sr)

    start_time = time.perf_counter()
    enhanced = enhance(model, df_state, audio)
    processing_time_ms = round((time.perf_counter() - start_time) * 1000, 1)

    save_audio(str(output_path), enhanced, model_sr)

    # Calculate duration
    try:
        import torch
        if isinstance(enhanced, torch.Tensor):
            num_samples = enhanced.shape[-1]
        else:
            num_samples = len(enhanced)
        duration = round(num_samples / model_sr, 3)
    except Exception:
        duration = 0.0

    return {
        "status": "success",
        "engine": "DeepFilterNet",
        "model_version": "DeepFilterNet3",
        "input_file": input_path.name,
        "output_file": output_path.name,
        "processing_time_ms": processing_time_ms,
        "sample_rate": int(model_sr),
        "duration": duration,
    }


def _run_subprocess(input_path: Path, output_path: Path) -> Dict[str, Any]:
    """
    Run DeepFilterNet inference via subprocess using the .venv-dfn environment.
    """
    if not DFN_VENV_PYTHON.is_file():
        return {
            "status": "error",
            "error_code": "DEEPFILTERNET_NOT_INSTALLED",
            "error": f"DeepFilterNet venv not found at {DFN_VENV_PYTHON}. Run setup_deepfilter.ps1."
        }

    if not WORKER_SCRIPT.is_file():
        return {
            "status": "error",
            "error_code": "DEEPFILTERNET_NOT_INSTALLED",
            "error": f"Worker script not found at {WORKER_SCRIPT}."
        }

    cmd = [
        str(DFN_VENV_PYTHON),
        str(WORKER_SCRIPT),
        str(input_path),
        str(output_path),
    ]

    logger.info(f"[DeepFilterNet] Running subprocess: {' '.join(cmd)}")

    try:
        proc = subprocess.run(
            cmd,
            capture_output=True,
            text=True,
            timeout=300,  # 5 minute timeout for large files
            cwd=str(BASE_DIR),
        )
    except subprocess.TimeoutExpired:
        return {
            "status": "error",
            "error_code": "DEEPFILTERNET_INFERENCE_FAILED",
            "error": "DeepFilterNet processing timed out (>5 minutes)."
        }
    except Exception as e:
        return {
            "status": "error",
            "error_code": "DEEPFILTERNET_INFERENCE_FAILED",
            "error": f"Failed to run DeepFilterNet subprocess: {e}"
        }

    # Parse stdout for JSON line (worker outputs logs + JSON line)
    stdout = proc.stdout.strip()
    json_obj = None

    for line in stdout.splitlines():
        line_str = line.strip()
        if line_str.startswith("{") and line_str.endswith("}"):
            try:
                json_obj = json.loads(line_str)
                break
            except json.JSONDecodeError:
                continue

    if proc.returncode != 0:
        if json_obj and "error_code" in json_obj:
            return json_obj
        return {
            "status": "error",
            "error_code": "DEEPFILTERNET_INFERENCE_FAILED",
            "error": f"DeepFilterNet subprocess exited with code {proc.returncode}.",
        }

    if not json_obj:
        return {
            "status": "error",
            "error_code": "DEEPFILTERNET_INFERENCE_FAILED",
            "error": "DeepFilterNet subprocess returned invalid or missing JSON output.",
        }

    return json_obj


def process_audio(file_path: Path, file_id: str) -> Dict[str, Any]:
    """
    Process audio through DeepFilterNet — the main entry point.

    Uses direct import if available, otherwise subprocess via .venv-dfn.
    Thread-safe: prevents duplicate concurrent processing of the same file_id.
    """
    # Prevent duplicate concurrent processing
    with _DFN_LOCK:
        if _DFN_ACTIVE.get(file_id) == "processing":
            return {
                "file_id": file_id,
                "status": "processing",
                "engine": "DeepFilterNet",
                "error": "DeepFilterNet is already processing this file."
            }
        _DFN_ACTIVE[file_id] = "processing"

    output_path = UPLOADS_DIR / f"processed_{file_id}.wav"

    try:
        # Validate input
        if not file_path.exists():
            result = {
                "file_id": file_id,
                "status": "error",
                "error_code": "INVALID_AUDIO",
                "error": "Input audio file does not exist.",
                "engine": "DeepFilterNet",
            }
            with _DFN_LOCK:
                _DFN_ACTIVE[file_id] = "error"
                _DFN_RESULTS[file_id] = result
            return result

        # Choose execution mode
        if _check_direct_availability():
            logger.info(f"[DeepFilterNet] Processing {file_id} (direct mode)...")
            result = _run_direct(file_path, output_path)
        elif _check_subprocess_availability():
            logger.info(f"[DeepFilterNet] Processing {file_id} (subprocess mode)...")
            result = _run_subprocess(file_path, output_path)
        else:
            result = {
                "status": "error",
                "error_code": "DEEPFILTERNET_NOT_INSTALLED",
                "error": "DeepFilterNet is not available. Run setup_deepfilter.ps1 to install."
            }

        # Add file_id and engine to result
        result["file_id"] = file_id
        if "engine" not in result:
            result["engine"] = "DeepFilterNet"

        # Verify output was actually created on success
        if result.get("status") == "success":
            if not output_path.exists():
                result = {
                    "file_id": file_id,
                    "status": "error",
                    "error_code": "OUTPUT_WRITE_FAILED",
                    "error": "DeepFilterNet reported success but output file was not created.",
                    "engine": "DeepFilterNet",
                }

        # Cache result
        with _DFN_LOCK:
            _DFN_ACTIVE[file_id] = result.get("status", "error")
            _DFN_RESULTS[file_id] = result

        return result

    except Exception as e:
        logger.error(f"[DeepFilterNet] Unexpected error processing {file_id}: {e}", exc_info=True)
        result = {
            "file_id": file_id,
            "status": "error",
            "error_code": "DEEPFILTERNET_INFERENCE_FAILED",
            "error": f"Unexpected error during DeepFilterNet processing: {type(e).__name__}",
            "engine": "DeepFilterNet",
        }
        with _DFN_LOCK:
            _DFN_ACTIVE[file_id] = "error"
            _DFN_RESULTS[file_id] = result
        return result
