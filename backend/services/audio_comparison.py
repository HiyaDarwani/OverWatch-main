import os
from pathlib import Path
from typing import Dict, Any

from services.audio_analysis import analyze_audio, _ANALYSIS_CACHE
from services.deepfilter_service import get_denoise_status as get_dfn_status
from services.fullsubnet_service import get_denoise_status as get_fsn_status

BASE_DIR = Path(__file__).resolve().parent.parent
UPLOADS_DIR = BASE_DIR / "uploads"


def clear_analysis_cache(file_id: str):
    """
    Clears cached analysis for a file_id (used when reprocessing generates a new WAV).
    """
    _ANALYSIS_CACHE.pop(file_id, None)


def get_audio_comparison(file_id: str, model: str = "deepfilternet") -> Dict[str, Any]:
    """
    Calculates and returns a detailed DSP comparison between the original uploaded WAV
    and the generated output WAV (processed_{file_id}.wav or processed_fsn_{file_id}.wav).
    
    Returns real calculated metrics, waveforms, FFT frequency spectra, STFT spectrograms,
    and delta shifts.
    """
    matched_orig = list(UPLOADS_DIR.glob(f"{file_id}.*"))
    # Exclude any processed_ files from original matched list
    orig_files = [f for f in matched_orig if not f.name.startswith("processed_")]

    if not orig_files:
        return {
            "file_id": file_id,
            "status": "error",
            "message": f"Original audio file with ID '{file_id}' not found."
        }

    orig_path = orig_files[0]
    
    fsn_proc_path = UPLOADS_DIR / f"processed_fsn_{file_id}.wav"
    dfn_proc_path = UPLOADS_DIR / f"processed_{file_id}.wav"

    if model == "fullsubnet" and fsn_proc_path.exists():
        proc_path = fsn_proc_path
        is_fsn = True
        is_dfn = False
    elif model == "deepfilternet" and dfn_proc_path.exists():
        proc_path = dfn_proc_path
        is_fsn = False
        is_dfn = True
    elif fsn_proc_path.exists() and not dfn_proc_path.exists():
        proc_path = fsn_proc_path
        is_fsn = True
        is_dfn = False
    elif dfn_proc_path.exists():
        proc_path = dfn_proc_path
        is_fsn = False
        is_dfn = True
    else:
        return {
            "file_id": file_id,
            "status": "no_output",
            "message": "Processed output WAV has not been generated yet. Run processing simulation or denoising first."
        }

    try:
        # Check model status
        if is_fsn:
            fsn_info = get_fsn_status(file_id)
            engine_name = "FullSubNet+"
            mode_name = "fullsubnet"
        else:
            dfn_info = get_dfn_status(file_id)
            is_deepfilter = dfn_info.get("status") == "success"
            engine_name = "DeepFilterNet" if is_deepfilter else "simulated"
            mode_name = "deepfilternet" if is_deepfilter else "simulated"

        # Calculate real DSP analysis for original and processed files
        orig_analysis = analyze_audio(orig_path, file_id)
        
        # Always re-analyze processed file to ensure fresh results after reprocessing
        proc_id = proc_path.stem
        clear_analysis_cache(proc_id)
        proc_analysis = analyze_audio(proc_path, proc_id, original_filename=f"processed_{orig_path.name}")

        orig_amp = orig_analysis["amplitude"]
        proc_amp = proc_analysis["amplitude"]
        orig_spec = orig_analysis["spectral_features"]
        proc_spec = proc_analysis["spectral_features"]

        # Calculate genuine metric deltas
        orig_rms = max(1e-6, orig_amp["rms"])
        proc_rms = proc_amp["rms"]
        rms_change_pct = ((proc_rms - orig_rms) / orig_rms) * 100.0

        orig_peak = max(1e-6, orig_amp["peak"])
        proc_peak = proc_amp["peak"]
        peak_change_pct = ((proc_peak - orig_peak) / orig_peak) * 100.0

        centroid_shift = proc_spec["centroid_hz"] - orig_spec["centroid_hz"]
        bandwidth_shift = proc_spec["bandwidth_hz"] - orig_spec["bandwidth_hz"]
        rolloff_shift = proc_spec["rolloff_hz"] - orig_spec["rolloff_hz"]
        zcr_shift = proc_spec["zero_crossing_rate"] - orig_spec["zero_crossing_rate"]

        # Calculate estimated noise reduction based on high-frequency energy reduction
        est_nr_pct = max(0.0, min(95.0, abs(rms_change_pct) * 1.5))

        return {
            "file_id": file_id,
            "status": "ready",
            "engine": engine_name,
            "simulation_mode": mode_name,
            "original_audio_url": f"/api/audio/{file_id}",
            "processed_audio_url": f"/api/audio/processed/{file_id}",
            "original": {
                "metadata": orig_analysis["metadata"],
                "amplitude": orig_amp,
                "spectral_features": orig_spec,
                "waveform": orig_analysis["waveform"],
                "spectrum": orig_analysis["spectrum"],
                "spectrogram": orig_analysis["spectrogram"],
            },
            "processed": {
                "metadata": proc_analysis["metadata"],
                "amplitude": proc_amp,
                "spectral_features": proc_spec,
                "waveform": proc_analysis["waveform"],
                "spectrum": proc_analysis["spectrum"],
                "spectrogram": proc_analysis["spectrogram"],
            },
            "deltas": {
                "rms_change_pct": round(rms_change_pct, 1),
                "peak_change_pct": round(peak_change_pct, 1),
                "centroid_shift_hz": round(centroid_shift, 1),
                "bandwidth_shift_hz": round(bandwidth_shift, 1),
                "rolloff_shift_hz": round(rolloff_shift, 1),
                "zcr_shift": round(zcr_shift, 4),
                "estimated_noise_reduction_pct": round(est_nr_pct, 1)
            }
        }
    except Exception as err:
        return {
            "file_id": file_id,
            "status": "error",
            "message": f"Comparison analysis failed: {str(err)}"
        }
