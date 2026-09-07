"""
DeepFilterNet Worker Script — Runs inside the .venv-dfn environment.

This script is invoked as a subprocess by deepfilter_service.py.
It performs REAL DeepFilterNet inference on an input audio file.

Usage:
    .venv-dfn/Scripts/python.exe services/deepfilter_worker.py <input_path> <output_path>

Outputs JSON to stdout. Exits with code 0 on success, 1 on failure.
"""
import sys
import os
import json
import time
import traceback

def main():
    if len(sys.argv) < 3:
        result = {
            "status": "error",
            "error_code": "INVALID_ARGUMENTS",
            "error": "Usage: deepfilter_worker.py <input_path> <output_path>"
        }
        print(json.dumps(result))
        sys.exit(1)

    input_path = sys.argv[1]
    output_path = sys.argv[2]

    # Validate input file exists
    if not os.path.isfile(input_path):
        result = {
            "status": "error",
            "error_code": "INVALID_AUDIO",
            "error": f"Input file does not exist: {input_path}"
        }
        print(json.dumps(result))
        sys.exit(1)

    # Step 1: Import DeepFilterNet
    try:
        from df.enhance import init_df, enhance, load_audio, save_audio
    except ImportError as e:
        result = {
            "status": "error",
            "error_code": "DEEPFILTERNET_NOT_INSTALLED",
            "error": f"DeepFilterNet is not installed in this environment: {e}"
        }
        print(json.dumps(result))
        sys.exit(1)

    # Step 2: Initialize model
    try:
        model, df_state, _ = init_df()
        model_sr = df_state.sr()
    except Exception as e:
        result = {
            "status": "error",
            "error_code": "DEEPFILTERNET_MODEL_LOAD_FAILED",
            "error": f"Failed to initialize DeepFilterNet model: {e}"
        }
        print(json.dumps(result))
        sys.exit(1)

    # Step 3: Load audio
    try:
        audio, audio_info = load_audio(input_path, sr=model_sr)
    except Exception as e:
        result = {
            "status": "error",
            "error_code": "UNSUPPORTED_AUDIO_FORMAT",
            "error": f"Failed to load audio file: {e}"
        }
        print(json.dumps(result))
        sys.exit(1)

    # Step 4: Enhance audio
    try:
        start_time = time.perf_counter()
        enhanced_audio = enhance(model, df_state, audio)
        processing_time_ms = round((time.perf_counter() - start_time) * 1000, 1)
    except Exception as e:
        result = {
            "status": "error",
            "error_code": "DEEPFILTERNET_INFERENCE_FAILED",
            "error": f"DeepFilterNet inference failed: {e}"
        }
        print(json.dumps(result))
        sys.exit(1)

    # Step 5: Save enhanced audio
    try:
        save_audio(output_path, enhanced_audio, model_sr)
    except Exception as e:
        result = {
            "status": "error",
            "error_code": "OUTPUT_WRITE_FAILED",
            "error": f"Failed to save enhanced audio: {e}"
        }
        print(json.dumps(result))
        sys.exit(1)

    # Step 6: Calculate output duration
    try:
        import torch
        if isinstance(enhanced_audio, torch.Tensor):
            num_samples = enhanced_audio.shape[-1]
        else:
            import numpy as np
            num_samples = len(enhanced_audio) if hasattr(enhanced_audio, '__len__') else 0
        duration = round(num_samples / model_sr, 3) if model_sr > 0 else 0.0
    except Exception:
        duration = 0.0

    # Success result
    result = {
        "status": "success",
        "engine": "DeepFilterNet",
        "model_version": "DeepFilterNet3",
        "input_file": os.path.basename(input_path),
        "output_file": os.path.basename(output_path),
        "processing_time_ms": processing_time_ms,
        "sample_rate": int(model_sr),
        "duration": duration
    }
    print(json.dumps(result))
    sys.exit(0)


if __name__ == "__main__":
    main()
