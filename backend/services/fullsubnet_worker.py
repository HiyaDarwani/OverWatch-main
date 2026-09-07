"""
FullSubNet+ Worker Script — Runs inside the .venv-fsn environment.

This script is invoked as a subprocess by fullsubnet_service.py.
It performs REAL FullSubNet+ inference on an input audio file.

Usage:
    .venv-fsn/Scripts/python.exe services/fullsubnet_worker.py <input_path> <output_path>

Outputs JSON to stdout. Exits with code 0 on success, 1 on failure.
"""
import sys
import os
import json
import time
import traceback
import argparse

# ---------------------------------------------------------------------------
# Path setup — dynamically resolve FullSubNet+ repo before importing speech_enhance
# ---------------------------------------------------------------------------
parser = argparse.ArgumentParser(description="FullSubNet+ Worker")
parser.add_argument("input_path", nargs="?", default=None, help="Input audio WAV path")
parser.add_argument("output_path", nargs="?", default=None, help="Output enhanced audio WAV path")
parser.add_argument("--repo", default=None, help="Path to FullSubNet-plus repository")
parser.add_argument("--checkpoint", default=None, help="Path to best_model.tar checkpoint")
cli_args, _ = parser.parse_known_args()

FSN_REPO = cli_args.repo or os.environ.get("FULLSUBNET_REPO")
if not FSN_REPO:
    # Auto-discover sibling directory: ../FullSubNet-plus relative to OverWatch root
    # __file__ is in backend/services/, so 3 levels up is the parent workspace folder
    candidate_sibling = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..", "..", "FullSubNet-plus"))
    candidate_internal = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "external", "FullSubNet-plus"))
    if os.path.isdir(candidate_sibling):
        FSN_REPO = candidate_sibling
    elif os.path.isdir(candidate_internal):
        FSN_REPO = candidate_internal
    else:
        FSN_REPO = candidate_sibling

FSN_SPEECH_ENHANCE = os.path.join(FSN_REPO, "speech_enhance") if FSN_REPO else ""

# Prepend paths for audio_zen and fullsubnet_plus imports
for _p in [FSN_SPEECH_ENHANCE, FSN_REPO]:
    if _p and os.path.isdir(_p) and _p not in sys.path:
        sys.path.insert(0, _p)

# Silence loggers that write to stdout and break JSON parsing
import logging
logging.disable(logging.CRITICAL)


def _emit(obj: dict) -> None:
    """Print a single-line JSON dict to stdout (the only JSON line the service reads)."""
    print(json.dumps(obj), flush=True)


def main():
    input_path = cli_args.input_path
    output_path = cli_args.output_path

    if not input_path or not output_path:
        _emit({
            "status": "error",
            "error_code": "INVALID_ARGUMENTS",
            "error": "Usage: fullsubnet_worker.py <input_path> <output_path> [--repo <path>] [--checkpoint <path>]"
        })
        sys.exit(1)

    # ------------------------------------------------------------------
    # Validate input
    # ------------------------------------------------------------------
    if not os.path.isfile(input_path):
        _emit({
            "status": "error",
            "error_code": "INVALID_AUDIO",
            "error": f"Input file does not exist: {input_path}"
        })
        sys.exit(1)

    # ------------------------------------------------------------------
    # Step 1: Import dependencies
    # ------------------------------------------------------------------
    try:
        import torch
        import numpy as np
        import soundfile as sf
        import librosa
    except ImportError as e:
        _emit({
            "status": "error",
            "error_code": "FULLSUBNET_NOT_INSTALLED",
            "error": f"Required package not installed in .venv-fsn: {e}"
        })
        sys.exit(1)

    # ------------------------------------------------------------------
    # Step 2: Import FullSubNet+ model
    # ------------------------------------------------------------------
    try:
        from fullsubnet_plus.model.fullsubnet_plus import FullSubNet_Plus
        from audio_zen.acoustics.feature import stft, istft, mag_phase
        from audio_zen.acoustics.mask import decompress_cIRM
        from audio_zen.utils import prepare_device
    except ImportError as e:
        _emit({
            "status": "error",
            "error_code": "FULLSUBNET_NOT_INSTALLED",
            "error": f"Failed to import FullSubNet+ modules: {e}\n{traceback.format_exc()}"
        })
        sys.exit(1)

    CHECKPOINT_PATH = (
        cli_args.checkpoint
        or os.environ.get("FULLSUBNET_CHECKPOINT")
        or (os.path.join(FSN_REPO, "checkpoints", "best_model.tar") if FSN_REPO else "")
    )
    SR = 16000
    N_FFT = 512
    WIN_LENGTH = 512
    HOP_LENGTH = 256

    MODEL_ARGS = dict(
        num_freqs=257,
        look_ahead=2,
        sequence_model="LSTM",
        fb_num_neighbors=0,
        sb_num_neighbors=15,
        fb_output_activate_function="ReLU",
        sb_output_activate_function=False,
        fb_model_hidden_size=512,
        sb_model_hidden_size=384,
        channel_attention_model="TSSE",
        norm_type="offline_laplace_norm",
        num_groups_in_drop_band=2,
        kersize=[3, 5, 10],
        subband_num=1,
        weight_init=False,
    )

    if not os.path.isfile(CHECKPOINT_PATH):
        _emit({
            "status": "error",
            "error_code": "FULLSUBNET_NOT_INSTALLED",
            "error": f"Checkpoint not found at: {CHECKPOINT_PATH}"
        })
        sys.exit(1)

    # ------------------------------------------------------------------
    # Step 4: Load audio (resample to 16 kHz mono)
    # ------------------------------------------------------------------
    try:
        audio, orig_sr = librosa.load(input_path, sr=SR, mono=True)
        # audio is float32 numpy array, range roughly [-1, 1]
    except Exception as e:
        _emit({
            "status": "error",
            "error_code": "UNSUPPORTED_AUDIO_FORMAT",
            "error": f"Failed to load audio: {e}"
        })
        sys.exit(1)

    # ------------------------------------------------------------------
    # Step 5: Load model
    # ------------------------------------------------------------------
    try:
        device = prepare_device(0)  # 0 GPUs → cpu device

        model = FullSubNet_Plus(**MODEL_ARGS)

        ckpt = torch.load(CHECKPOINT_PATH, map_location="cpu", weights_only=False)
        model.load_state_dict(ckpt["model"])
        model.to(device)
        model.eval()

        epoch = ckpt.get("epoch", "?")
    except Exception as e:
        _emit({
            "status": "error",
            "error_code": "FULLSUBNET_MODEL_LOAD_FAILED",
            "error": f"Failed to load FullSubNet+ checkpoint: {e}\n{traceback.format_exc()}"
        })
        sys.exit(1)

    # ------------------------------------------------------------------
    # Step 6: Inference  (mag_complex_full_band_crm_mask)
    # ------------------------------------------------------------------
    try:
        from functools import partial

        torch_stft = partial(stft, n_fft=N_FFT, hop_length=HOP_LENGTH, win_length=WIN_LENGTH)
        torch_istft = partial(istft, n_fft=N_FFT, hop_length=HOP_LENGTH, win_length=WIN_LENGTH)

        noisy_tensor = torch.tensor(audio, dtype=torch.float32).unsqueeze(0).to(device)  # [1, T]

        start_time = time.perf_counter()

        with torch.no_grad():
            noisy_complex = torch_stft(noisy_tensor)          # [1, F, T] complex
            noisy_mag, _ = mag_phase(noisy_complex)            # [1, F, T] real

            noisy_mag_in   = noisy_mag.unsqueeze(1)            # [1, 1, F, T]
            noisy_real_in  = noisy_complex.real.unsqueeze(1)   # [1, 1, F, T]
            noisy_imag_in  = noisy_complex.imag.unsqueeze(1)   # [1, 1, F, T]

            pred_crm = model(noisy_mag_in, noisy_real_in, noisy_imag_in)  # [1, 2, F, T]
            pred_crm = pred_crm.permute(0, 2, 3, 1)                        # [1, F, T, 2]

            pred_crm = decompress_cIRM(pred_crm)

            enhanced_real = pred_crm[..., 0] * noisy_complex.real - pred_crm[..., 1] * noisy_complex.imag
            enhanced_imag = pred_crm[..., 1] * noisy_complex.real + pred_crm[..., 0] * noisy_complex.imag
            enhanced_complex = torch.stack((enhanced_real, enhanced_imag), dim=-1)

            enhanced = torch_istft(enhanced_complex, length=noisy_tensor.size(-1))  # [1, T]
            enhanced_np = enhanced.detach().squeeze(0).cpu().numpy()

        processing_time_ms = round((time.perf_counter() - start_time) * 1000, 1)

    except Exception as e:
        _emit({
            "status": "error",
            "error_code": "FULLSUBNET_INFERENCE_FAILED",
            "error": f"FullSubNet+ inference failed: {e}\n{traceback.format_exc()}"
        })
        sys.exit(1)

    # ------------------------------------------------------------------
    # Step 7: Normalise and save output WAV
    # ------------------------------------------------------------------
    try:
        # Clip to [-1, 1] without silent-clipping artefacts
        max_abs = np.max(np.abs(enhanced_np))
        if max_abs > 1e-6:
            enhanced_np = enhanced_np / max_abs * 0.95  # headroom to avoid hard clip

        sf.write(output_path, enhanced_np.astype(np.float32), samplerate=SR, subtype="PCM_16")
    except Exception as e:
        _emit({
            "status": "error",
            "error_code": "OUTPUT_WRITE_FAILED",
            "error": f"Failed to save enhanced audio: {e}"
        })
        sys.exit(1)

    # ------------------------------------------------------------------
    # Step 8: Emit success JSON
    # ------------------------------------------------------------------
    duration = round(len(enhanced_np) / SR, 3)

    result = {
        "status": "success",
        "engine": "FullSubNet+",
        "model_version": f"FullSubNet+ (epoch {epoch})",
        "input_file": os.path.basename(input_path),
        "output_file": os.path.basename(output_path),
        "processing_time_ms": processing_time_ms,
        "sample_rate": SR,
        "duration": duration,
    }
    _emit(result)
    sys.exit(0)


if __name__ == "__main__":
    main()
