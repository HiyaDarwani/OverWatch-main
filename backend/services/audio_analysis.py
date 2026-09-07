import os
import math
from pathlib import Path
from typing import Dict, Any, List

import numpy as np
import scipy.signal
import librosa

# In-memory cache for analysis results (file_id -> analysis_dict)
_ANALYSIS_CACHE: Dict[str, Dict[str, Any]] = {}


def analyze_audio(file_path: Path, file_id: str, original_filename: str = "") -> Dict[str, Any]:
    """
    Analyzes an uploaded audio file using librosa, scipy, and numpy.
    Calculates duration, sample rate, channels, sample count, RMS, peak amplitude,
    downsampled waveform, frequency spectrum (FFT), STFT spectrogram matrix,
    and spectral features (centroid, bandwidth, rolloff, zero crossing rate).
    
    Caches analysis result in memory by file_id.
    """
    if file_id in _ANALYSIS_CACHE:
        return _ANALYSIS_CACHE[file_id]

    if not file_path.exists():
        raise ValueError("Audio file does not exist on disk.")

    # 1. Load full audio signal with librosa (preserve native sample rate & channels)
    try:
        # sr=None preserves original sampling rate
        # mono=False preserves stereo/multi-channel array shape
        y, sr = librosa.load(str(file_path), sr=None, mono=False)
    except Exception as e:
        raise ValueError(f"Failed to decode audio file for analysis: {str(e)}")

    sr = int(sr)

    # 2. Channel & sample count handling
    if y.ndim == 1:
        channels = 1
        num_samples = len(y)
        y_mono = y.astype(np.float32)
    elif y.ndim == 2:
        channels = int(y.shape[0])
        num_samples = int(y.shape[1])
        # Average across channels for mono analysis signal
        y_mono = np.mean(y, axis=0).astype(np.float32)
    else:
        raise ValueError("Unsupported audio array shape.")

    if num_samples == 0:
        raise ValueError("Audio file contains 0 samples.")

    # Pad short audio signals to at least 2048 samples so librosa FFT/STFT operations never crash
    if num_samples < 2048:
        y_mono = np.pad(y_mono, (0, 2048 - num_samples), mode="constant")
        num_samples = len(y_mono)

    duration = round(float(num_samples) / float(sr), 2)

    # 3. RMS & Peak Amplitude calculations (with numerical stability for silence)
    rms_val = float(np.sqrt(np.mean(np.square(y_mono))))
    peak_val = float(np.max(np.abs(y_mono)))

    rms_db = round(float(20.0 * np.log10(max(rms_val, 1e-9))), 2)
    if rms_val < 1e-9:
        rms_db = -100.0

    peak_dbfs = round(float(20.0 * np.log10(max(peak_val, 1e-9))), 2)
    if peak_val < 1e-9:
        peak_dbfs = -100.0

    # 4. Waveform Downsampling (Bounded visualization: ~1200 points)
    target_waveform_points = min(1200, num_samples)
    if num_samples <= target_waveform_points:
        wf_samples = y_mono
        wf_times = np.linspace(0, duration, num_samples, endpoint=False)
    else:
        indices = np.linspace(0, num_samples - 1, target_waveform_points, dtype=int)
        wf_samples = y_mono[indices]
        wf_times = np.linspace(0, duration, target_waveform_points)

    waveform_data = {
        "time": [round(float(t), 3) for t in wf_times],
        "amplitude": [round(float(a), 4) for a in wf_samples]
    }

    # 5. FFT / Frequency Spectrum (Bounded visualization: ~300 frequency bins)
    n_fft_spectrum = min(8192, num_samples)
    if num_samples > n_fft_spectrum:
        start_idx = (num_samples - n_fft_spectrum) // 2
        chunk = y_mono[start_idx : start_idx + n_fft_spectrum]
    else:
        chunk = y_mono

    windowed = chunk * np.hanning(len(chunk))
    fft_raw = np.abs(np.fft.rfft(windowed))
    freqs_raw = np.fft.rfftfreq(len(chunk), d=1.0 / sr)

    max_mag = float(np.max(fft_raw)) if len(fft_raw) > 0 else 1.0
    if max_mag > 1e-9:
        fft_db = 20.0 * np.log10(np.maximum(fft_raw / max_mag, 1e-5))
    else:
        fft_db = np.full_like(fft_raw, -100.0)

    target_freq_bins = 300
    if len(freqs_raw) > target_freq_bins:
        bin_edges = np.linspace(0, len(freqs_raw), target_freq_bins + 1, dtype=int)
        freq_list = []
        mag_db_list = []
        for i in range(target_freq_bins):
            b_start, b_end = bin_edges[i], bin_edges[i + 1]
            if b_start == b_end:
                b_end = b_start + 1
            freq_list.append(float(np.mean(freqs_raw[b_start:b_end])))
            mag_db_list.append(float(np.max(fft_db[b_start:b_end])))
    else:
        freq_list = [float(f) for f in freqs_raw]
        mag_db_list = [float(m) for m in fft_db]

    spectrum_data = {
        "frequency": [round(f, 1) for f in freq_list],
        "magnitude_db": [round(m, 2) for m in mag_db_list]
    }

    # 6. STFT / Spectrogram (Bounded 2D matrix for visualization: ~50 freq bins x ~80 time steps)
    n_fft_stft = 1024
    hop_length_stft = max(256, num_samples // 100)
    stft_matrix = np.abs(librosa.stft(y_mono, n_fft=n_fft_stft, hop_length=hop_length_stft))
    stft_db = librosa.amplitude_to_db(stft_matrix, ref=np.max)

    num_stft_freqs, num_stft_times = stft_db.shape
    target_spec_freqs = min(50, num_stft_freqs)
    target_spec_times = min(80, num_stft_times)

    freq_indices = np.linspace(0, num_stft_freqs - 1, target_spec_freqs, dtype=int)
    time_indices = np.linspace(0, num_stft_times - 1, target_spec_times, dtype=int)

    spec_freq_axis = (freq_indices / max(1, num_stft_freqs - 1)) * (sr / 2.0)
    spec_time_axis = (time_indices / max(1, num_stft_times - 1)) * duration
    reduced_stft_db = stft_db[np.ix_(freq_indices, time_indices)]

    spectrogram_data = {
        "time": [round(float(t), 2) for t in spec_time_axis],
        "frequency": [round(float(f), 1) for f in spec_freq_axis],
        "magnitude_db": [[round(float(val), 1) for val in row] for row in reduced_stft_db]
    }

    # 7. Spectral Features (Summary metrics across frames)
    centroid_arr = librosa.feature.spectral_centroid(y=y_mono, sr=sr)
    bandwidth_arr = librosa.feature.spectral_bandwidth(y=y_mono, sr=sr)
    rolloff_arr = librosa.feature.spectral_rolloff(y=y_mono, sr=sr)
    zcr_arr = librosa.feature.zero_crossing_rate(y_mono)

    centroid_hz = round(float(np.mean(centroid_arr)), 1)
    bandwidth_hz = round(float(np.mean(bandwidth_arr)), 1)
    rolloff_hz = round(float(np.mean(rolloff_arr)), 1)
    zcr_val = round(float(np.mean(zcr_arr)), 4)

    analysis_result = {
        "file_id": file_id,
        "metadata": {
            "filename": original_filename or file_path.name,
            "duration": duration,
            "sample_rate": sr,
            "channels": channels,
            "num_samples": num_samples
        },
        "amplitude": {
            "rms": round(rms_val, 4),
            "peak": round(peak_val, 4),
            "rms_db": rms_db,
            "peak_dbfs": peak_dbfs
        },
        "waveform": waveform_data,
        "spectrum": spectrum_data,
        "spectrogram": spectrogram_data,
        "spectral_features": {
            "centroid_hz": centroid_hz,
            "bandwidth_hz": bandwidth_hz,
            "rolloff_hz": rolloff_hz,
            "zero_crossing_rate": zcr_val
        }
    }

    _ANALYSIS_CACHE[file_id] = analysis_result
    return analysis_result
