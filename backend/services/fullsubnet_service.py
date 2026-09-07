"""
FullSubNet+ Service — Real audio denoising engine for OverWatch.

Mirrors deepfilter_service.py architecture exactly.
Invokes fullsubnet_worker.py inside .venv-fsn (separate Python venv).

Output filename: processed_fsn_<file_id>.wav  (separate from DFN3's processed_<file_id>.wav)
"""
import json
import logging
import subprocess
import threading
from pathlib import Path
from typing import Any, Dict

import os
from typing import Any, Dict, Optional, Tuple

logger = logging.getLogger("overwatch.fullsubnet")

BASE_DIR = Path(__file__).resolve().parent.parent
UPLOADS_DIR = BASE_DIR / "uploads"
WORKER_SCRIPT = Path(__file__).resolve().parent / "fullsubnet_worker.py"

# Thread-safe state
_FSN_LOCK = threading.Lock()
_FSN_ACTIVE: Dict[str, str] = {}           # file_id -> "processing" | "success" | "error"
_FSN_RESULTS: Dict[str, Dict[str, Any]] = {}  # file_id -> result dict


def _resolve_paths() -> Tuple[Optional[Path], Optional[Path], Optional[Path]]:
    """
    Dynamically discovers:
      (fsn_repo_path, fsn_python_exe, checkpoint_path)
    using environment variables, sibling repo (../FullSubNet-plus), and standard virtualenvs.
    """
    # 1. Resolve FullSubNet-plus repository root
    fsn_repo: Optional[Path] = None
    env_repo = os.environ.get("FULLSUBNET_PATH") or os.environ.get("FULLSUBNET_REPO")
    if env_repo and Path(env_repo).is_dir():
        fsn_repo = Path(env_repo).resolve()
    else:
        # Sibling directory: ../FullSubNet-plus relative to OverWatch root
        # BASE_DIR is OverWatch/backend, so BASE_DIR.parent.parent is the workspace folder
        sibling = BASE_DIR.parent.parent / "FullSubNet-plus"
        if sibling.is_dir():
            fsn_repo = sibling.resolve()
        else:
            # Internal directory: backend/external/FullSubNet-plus
            internal = BASE_DIR / "external" / "FullSubNet-plus"
            if internal.is_dir():
                fsn_repo = internal.resolve()

    # 2. Resolve Python executable inside .venv-fsn (or .venv)
    fsn_python: Optional[Path] = None
    env_python = os.environ.get("FULLSUBNET_PYTHON")
    if env_python and Path(env_python).is_file():
        fsn_python = Path(env_python).resolve()
    elif fsn_repo:
        for rel_py in [
            Path(".venv-fsn/Scripts/python.exe"),
            Path(".venv-fsn/bin/python"),
            Path(".venv/Scripts/python.exe"),
            Path(".venv/bin/python"),
        ]:
            candidate = fsn_repo / rel_py
            if candidate.is_file():
                fsn_python = candidate.resolve()
                break

    # Also check backend/.venv-fsn as fallback
    if not fsn_python:
        for rel_py in [
            BASE_DIR / ".venv-fsn" / "Scripts" / "python.exe",
            BASE_DIR / ".venv-fsn" / "bin" / "python",
        ]:
            if rel_py.is_file():
                fsn_python = rel_py.resolve()
                break

    # 3. Resolve Checkpoint
    checkpoint_path: Optional[Path] = None
    env_ckpt = os.environ.get("FULLSUBNET_CHECKPOINT")
    if env_ckpt and Path(env_ckpt).is_file():
        checkpoint_path = Path(env_ckpt).resolve()
    elif fsn_repo:
        candidate_ckpt = fsn_repo / "checkpoints" / "best_model.tar"
        if candidate_ckpt.is_file():
            checkpoint_path = candidate_ckpt.resolve()

    return fsn_repo, fsn_python, checkpoint_path


def _check_availability() -> bool:
    """Check if the FullSubNet+ python executable and checkpoint exist."""
    _, fsn_python, checkpoint_path = _resolve_paths()
    return bool(fsn_python and fsn_python.is_file() and checkpoint_path and checkpoint_path.is_file())


def _run_subprocess(input_path: Path, output_path: Path) -> Dict[str, Any]:
    """
    Run FullSubNet+ inference via subprocess using the discovered environment.
    """
    fsn_repo, fsn_python, checkpoint_path = _resolve_paths()

    if not fsn_python or not fsn_python.is_file():
        return {
            "status": "error",
            "error_code": "FULLSUBNET_NOT_INSTALLED",
            "error": (
                "FullSubNet+ Python environment (.venv-fsn) not found. "
                "Run 'backend/setup_fullsubnet.ps1' or configure FULLSUBNET_PATH."
            ),
        }

    if not checkpoint_path or not checkpoint_path.is_file():
        return {
            "status": "error",
            "error_code": "FULLSUBNET_NOT_INSTALLED",
            "error": (
                "FullSubNet+ checkpoint (best_model.tar) not found. "
                "Run 'backend/setup_fullsubnet.ps1' or place best_model.tar in checkpoints/."
            ),
        }

    if not WORKER_SCRIPT.is_file():
        return {
            "status": "error",
            "error_code": "FULLSUBNET_NOT_INSTALLED",
            "error": f"Worker script not found at {WORKER_SCRIPT}.",
        }

    cmd = [
        str(fsn_python),
        str(WORKER_SCRIPT),
        str(input_path),
        str(output_path),
    ]
    if fsn_repo:
        cmd.extend(["--repo", str(fsn_repo)])
    if checkpoint_path:
        cmd.extend(["--checkpoint", str(checkpoint_path)])

    logger.info(f"[FullSubNet+] Running subprocess: {' '.join(cmd)}")

    try:
        proc = subprocess.run(
            cmd,
            capture_output=True,
            text=True,
            timeout=600,  # 10 minute timeout (CPU inference can be slow)
            cwd=str(BASE_DIR),
        )
    except subprocess.TimeoutExpired:
        return {
            "status": "error",
            "error_code": "FULLSUBNET_INFERENCE_FAILED",
            "error": "FullSubNet+ processing timed out (>10 minutes).",
        }
    except Exception as e:
        return {
            "status": "error",
            "error_code": "FULLSUBNET_INFERENCE_FAILED",
            "error": f"Failed to run FullSubNet+ subprocess: {e}",
        }

    # Parse stdout for JSON line (worker emits exactly one JSON line)
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
        stderr_snippet = proc.stderr.strip()[-500:] if proc.stderr else ""
        return {
            "status": "error",
            "error_code": "FULLSUBNET_INFERENCE_FAILED",
            "error": (
                f"FullSubNet+ subprocess exited with code {proc.returncode}. "
                f"stderr: {stderr_snippet}"
            ),
        }

    if not json_obj:
        return {
            "status": "error",
            "error_code": "FULLSUBNET_INFERENCE_FAILED",
            "error": "FullSubNet+ subprocess returned invalid or missing JSON output.",
        }

    return json_obj


def process_audio(file_path: Path, file_id: str) -> Dict[str, Any]:
    """
    Process audio through FullSubNet+ — the main entry point.

    Thread-safe: prevents duplicate concurrent processing of the same file_id.
    Output: uploads/processed_fsn_<file_id>.wav
    """
    # Prevent duplicate concurrent processing
    with _FSN_LOCK:
        if _FSN_ACTIVE.get(file_id) == "processing":
            return {
                "file_id": file_id,
                "status": "processing",
                "engine": "FullSubNet+",
                "error": "FullSubNet+ is already processing this file.",
            }
        _FSN_ACTIVE[file_id] = "processing"

    output_path = UPLOADS_DIR / f"processed_fsn_{file_id}.wav"

    try:
        # Validate input
        if not file_path.exists():
            result: Dict[str, Any] = {
                "file_id": file_id,
                "status": "error",
                "error_code": "INVALID_AUDIO",
                "error": "Input audio file does not exist.",
                "engine": "FullSubNet+",
            }
            with _FSN_LOCK:
                _FSN_ACTIVE[file_id] = "error"
                _FSN_RESULTS[file_id] = result
            return result

        if not _check_availability():
            fsn_repo, fsn_python, checkpoint_path = _resolve_paths()
            missing = []
            if not fsn_python or not fsn_python.is_file():
                missing.append("Python environment (.venv-fsn)")
            if not checkpoint_path or not checkpoint_path.is_file():
                missing.append("checkpoint (best_model.tar)")
            result = {
                "file_id": file_id,
                "status": "error",
                "error_code": "FULLSUBNET_NOT_INSTALLED",
                "error": (
                    f"FullSubNet+ is not ready ({', '.join(missing)} missing). "
                    "Run 'backend/setup_fullsubnet.ps1' to configure."
                ),
                "engine": "FullSubNet+",
            }
            with _FSN_LOCK:
                _FSN_ACTIVE[file_id] = "error"
                _FSN_RESULTS[file_id] = result
            return result

        logger.info(f"[FullSubNet+] Processing {file_id} via subprocess...")
        result = _run_subprocess(file_path, output_path)

        # Attach file_id and engine
        result["file_id"] = file_id
        if "engine" not in result:
            result["engine"] = "FullSubNet+"

        # Verify output was created on success
        if result.get("status") == "success" and not output_path.exists():
            result = {
                "file_id": file_id,
                "status": "error",
                "error_code": "OUTPUT_WRITE_FAILED",
                "error": "FullSubNet+ reported success but output file was not created.",
                "engine": "FullSubNet+",
            }

        # Cache result
        with _FSN_LOCK:
            _FSN_ACTIVE[file_id] = result.get("status", "error")
            _FSN_RESULTS[file_id] = result

        return result

    except Exception as e:
        logger.error(f"[FullSubNet+] Unexpected error processing {file_id}: {e}", exc_info=True)
        result = {
            "file_id": file_id,
            "status": "error",
            "error_code": "FULLSUBNET_INFERENCE_FAILED",
            "error": f"Unexpected error during FullSubNet+ processing: {type(e).__name__}",
            "engine": "FullSubNet+",
        }
        with _FSN_LOCK:
            _FSN_ACTIVE[file_id] = "error"
            _FSN_RESULTS[file_id] = result
        return result


def get_denoise_status(file_id: str) -> Dict[str, Any]:
    """
    Returns the current FullSubNet+ denoising status for file_id.
    """
    with _FSN_LOCK:
        if file_id in _FSN_RESULTS:
            return _FSN_RESULTS[file_id]
        if file_id in _FSN_ACTIVE:
            return {
                "file_id": file_id,
                "status": _FSN_ACTIVE[file_id],
                "engine": "FullSubNet+",
            }

    # Check if output file already exists from a previous run
    output_path = UPLOADS_DIR / f"processed_fsn_{file_id}.wav"
    if output_path.exists():
        return {
            "file_id": file_id,
            "status": "success",
            "engine": "FullSubNet+",
            "output_file": output_path.name,
        }

    return {
        "file_id": file_id,
        "status": "not_started",
        "engine": "FullSubNet+",
    }
