import os
import json
import logging
import threading
import socket
from pathlib import Path
from typing import Dict, Any, List, Literal, Tuple, Optional

from dotenv import load_dotenv
from pydantic import BaseModel, Field

# Load environment variables
load_dotenv(override=True)
load_dotenv(Path(__file__).resolve().parent.parent.parent / ".env", override=True)

logger = logging.getLogger("overwatch.gemini")

try:
    import httpx
    from google import genai
    from google.genai import types, errors
    HAS_GENAI_SDK = True
except ImportError:
    HAS_GENAI_SDK = False

from prompts.audio_analysis_prompt import SYSTEM_INSTRUCTION, build_analysis_prompt

# Thread-safe in-memory cache for Gemini analysis results (file_id -> analysis_dict)
_GEMINI_CACHE: Dict[str, Dict[str, Any]] = {}
_GEMINI_LOCK = threading.Lock()

# Default Gemini model (must be gemini-3.6-flash unless overridden by GEMINI_MODEL env var)
DEFAULT_GEMINI_MODEL = "gemini-3.6-flash"

ALLOWED_NOISE_TYPES = {"stationary", "non_stationary", "impulsive"}
ALLOWED_STRATEGIES = {
    "SPECTRAL_SUBTRACTION",
    "WIENER_FILTER",
    "LMS_NLMS",
    "MMSE_STSA",
    "WAVELET_DENOISING",
    "HYBRID"
}
ALLOWED_PRIORITIES = {"low", "medium", "high"}


if HAS_GENAI_SDK:
    class GeminiAudioAnalysisSchema(BaseModel):
        noise_type: Literal["stationary", "non_stationary", "impulsive"]
        confidence: float = Field(..., ge=0.0, le=1.0)
        severity: float = Field(..., ge=0.0, le=1.0)
        characteristics: List[str]
        recommended_strategy: Literal[
            "SPECTRAL_SUBTRACTION",
            "WIENER_FILTER",
            "LMS_NLMS",
            "MMSE_STSA",
            "WAVELET_DENOISING",
            "HYBRID"
        ]
        processing_priority: Literal["low", "medium", "high"]
        reasoning: str


def classify_gemini_error(err: Exception) -> Tuple[str, str]:
    """
    Classifies a Gemini API exception into structured error codes:
      AUTHENTICATION_ERROR, QUOTA_EXCEEDED, RATE_LIMITED, MODEL_NOT_FOUND,
      TIMEOUT, NETWORK_ERROR, INVALID_RESPONSE, API_ERROR, SDK_ERROR.
    Ensures technical error messages never expose secret keys.
    """
    logger.error(f"[Gemini AI Exception]: type={type(err).__name__}, err={err}")
    err_str = str(err).lower()

    # 1. Authentication failures (401, 403)
    if HAS_GENAI_SDK and isinstance(err, errors.APIError) and err.code in (401, 403):
        return "AUTHENTICATION_ERROR", "Gemini API authentication failed."
    if any(k in err_str for k in ("unauthorized", "invalid api key", "api_key_invalid", "permission_denied")):
        return "AUTHENTICATION_ERROR", "Gemini API authentication failed."

    # 2. Quota & Rate Limits (429)
    if HAS_GENAI_SDK and isinstance(err, errors.APIError) and err.code == 429:
        if "quota" in err_str or "resource_exhausted" in err_str:
            return "QUOTA_EXCEEDED", "Gemini API quota exceeded."
        return "RATE_LIMITED", "Gemini API rate limit exceeded."
    if "resource_exhausted" in err_str or "quota" in err_str:
        return "QUOTA_EXCEEDED", "Gemini API quota exceeded."
    if "429" in err_str or "rate limit" in err_str:
        return "RATE_LIMITED", "Gemini API rate limit exceeded."

    # 3. Model Not Found (404)
    if HAS_GENAI_SDK and isinstance(err, errors.APIError) and err.code == 404:
        return "MODEL_NOT_FOUND", "Requested Gemini model is not available."
    if any(k in err_str for k in ("404", "not found", "no longer available")):
        return "MODEL_NOT_FOUND", "Requested Gemini model is not available."

    # 4. Timeout
    if isinstance(err, TimeoutError) or (HAS_GENAI_SDK and isinstance(err, httpx.TimeoutException)):
        return "TIMEOUT", "Gemini API request timed out."
    if HAS_GENAI_SDK and isinstance(err, errors.APIError) and err.code in (504, 408):
        return "TIMEOUT", "Gemini API request timed out."
    if any(k in err_str for k in ("deadline_exceeded", "timed out", "timeout")):
        return "TIMEOUT", "Gemini API request timed out."

    # 5. Network / Socket Connection Failures
    if isinstance(err, socket.error) or (HAS_GENAI_SDK and isinstance(err, (httpx.NetworkError, httpx.ConnectError))):
        return "NETWORK_ERROR", "Network error communicating with Gemini API."
    if any(k in err_str for k in ("connection error", "name resolution", "failed to connect")):
        return "NETWORK_ERROR", "Network error communicating with Gemini API."

    # 6. Malformed JSON / Schema / Invalid Response
    if isinstance(err, (json.JSONDecodeError, KeyError, TypeError, ValueError)):
        return "INVALID_RESPONSE", "Invalid structured response from Gemini API."

    # 7. Generic API error
    if HAS_GENAI_SDK and isinstance(err, errors.APIError):
        return "API_ERROR", "Gemini API request failed."

    # 8. SDK / General exception fallback
    return "SDK_ERROR", "Gemini SDK error occurred."


def analyze_audio_with_gemini(
    file_path: Path,
    file_id: str,
    phase3_analysis: Dict[str, Any]
) -> Dict[str, Any]:
    """
    Integrates Google Gemini API as the AI Audio Analysis / Intelligence layer.
    Uploads audio file to Gemini API along with Phase 3 feature context,
    requests structured JSON analysis, validates response schema, and caches result.

    Model: gemini-3.6-flash (Primary default model, configurable via GEMINI_MODEL).
    Performs exactly ONE request per attempt with a 60-second HTTP timeout.
    Guarded by a thread lock against concurrent duplicate requests for the same file_id.
    """
    # 1. Fast cache check (lock-free read)
    if file_id in _GEMINI_CACHE:
        return _GEMINI_CACHE[file_id]

    api_key = os.getenv("GEMINI_API_KEY")
    model_name = os.getenv("GEMINI_MODEL", DEFAULT_GEMINI_MODEL).strip() or DEFAULT_GEMINI_MODEL

    # Handle unconfigured or default placeholder API key
    if not api_key or api_key == "your_gemini_api_key_here":
        logger.warning("[Gemini AI] GEMINI_API_KEY is not configured on server. AI analysis disabled.")
        return {
            "file_id": file_id,
            "status": "unavailable",
            "error_code": "AUTHENTICATION_ERROR",
            "error": "GEMINI_API_KEY is not configured on backend server.",
            "analysis": None
        }

    if not HAS_GENAI_SDK:
        logger.warning("[Gemini AI] google-genai SDK is not installed. AI analysis disabled.")
        return {
            "file_id": file_id,
            "status": "unavailable",
            "error_code": "SDK_ERROR",
            "error": "google-genai SDK is not installed.",
            "analysis": None
        }

    if not file_path.exists():
        raise ValueError("Audio file does not exist on disk.")

    metadata = phase3_analysis.get("metadata", {})
    amplitude = phase3_analysis.get("amplitude", {})
    spectral_features = phase3_analysis.get("spectral_features", {})

    prompt_text = build_analysis_prompt(metadata, amplitude, spectral_features)

    # 2. Acquire thread lock for file_id execution
    with _GEMINI_LOCK:
        # Double-check cache inside lock
        if file_id in _GEMINI_CACHE:
            return _GEMINI_CACHE[file_id]

        # Initialize Gemini client
        try:
            client = genai.Client(api_key=api_key)
        except Exception as init_err:
            error_code, error_msg = classify_gemini_error(init_err)
            logger.error(f"[Gemini AI] Client initialization failed: {init_err}")
            return {
                "file_id": file_id,
                "status": "unavailable",
                "error_code": error_code,
                "error": error_msg,
                "analysis": None
            }

        uploaded_gemini_file = None
        try:
            # Step A: Upload audio file to Gemini API
            uploaded_gemini_file = client.files.upload(file=str(file_path))

            # Step B: Configure structured JSON output & 60-second HTTP timeout (60,000 ms)
            config = types.GenerateContentConfig(
                system_instruction=SYSTEM_INSTRUCTION,
                response_mime_type="application/json",
                response_schema=GeminiAudioAnalysisSchema,
                temperature=0.2,
                http_options=types.HttpOptions(timeout=60000)
            )

            # Step C: Single request using gemini-3.6-flash (or overridden GEMINI_MODEL)
            logger.info(f"[Gemini AI] Sending audio analysis request using model '{model_name}' (timeout: 60s)...")
            response = client.models.generate_content(
                model=model_name,
                contents=[uploaded_gemini_file, prompt_text],
                config=config
            )

            if not response or not response.text:
                raise ValueError("Received empty text response from Gemini API.")

            raw_text = response.text.strip()
            parsed_json = json.loads(raw_text)

            # Step D: Validate & Normalize JSON Schema
            raw_noise_type = str(parsed_json.get("noise_type", "stationary")).lower().replace("-", "_")
            if raw_noise_type not in ALLOWED_NOISE_TYPES:
                raw_noise_type = "stationary"

            confidence = float(parsed_json.get("confidence", 0.85))
            confidence = max(0.0, min(1.0, confidence))

            severity = float(parsed_json.get("severity", 0.5))
            severity = max(0.0, min(1.0, severity))

            raw_characteristics = parsed_json.get("characteristics", [])
            if not isinstance(raw_characteristics, list) or len(raw_characteristics) == 0:
                raw_characteristics = ["Continuous acoustic energy", "Measured spectral context"]
            characteristics = [str(c) for c in raw_characteristics[:4]]

            raw_strategy = str(parsed_json.get("recommended_strategy", "WIENER_FILTER")).upper().replace(" ", "_")
            if raw_strategy not in ALLOWED_STRATEGIES:
                raw_strategy = "WIENER_FILTER"

            raw_priority = str(parsed_json.get("processing_priority", "medium")).lower()
            if raw_priority not in ALLOWED_PRIORITIES:
                raw_priority = "medium"

            reasoning = str(parsed_json.get("reasoning", "Acoustic signal analyzed with measured spectral context."))

            structured_analysis = {
                "model_used": model_name,
                "noise_type": raw_noise_type,
                "confidence": round(confidence, 2),
                "severity": round(severity, 2),
                "characteristics": characteristics,
                "recommended_strategy": raw_strategy,
                "processing_priority": raw_priority,
                "reasoning": reasoning
            }

            result = {
                "file_id": file_id,
                "status": "success",
                "analysis": structured_analysis
            }

            # Cache successful result
            _GEMINI_CACHE[file_id] = result
            logger.info(f"[Gemini AI] Analysis succeeded for file_id '{file_id}' using model '{model_name}'.")
            return result

        except Exception as err:
            error_code, error_msg = classify_gemini_error(err)
            logger.error(f"[Gemini AI Error] Analysis failed for {file_id} [{error_code}]: {err}", exc_info=True)
            return {
                "file_id": file_id,
                "status": "unavailable",
                "error_code": error_code,
                "error": error_msg,
                "analysis": None
            }
        finally:
            # Step E: Always delete temporary uploaded audio file from Gemini server
            if uploaded_gemini_file:
                try:
                    client.files.delete(name=uploaded_gemini_file.name)
                    logger.debug(f"[Gemini AI] Successfully deleted temp file '{uploaded_gemini_file.name}' from Gemini server.")
                except Exception as del_err:
                    logger.warning(f"[Gemini AI] Temp file deletion failed for '{uploaded_gemini_file.name}': {del_err}")
