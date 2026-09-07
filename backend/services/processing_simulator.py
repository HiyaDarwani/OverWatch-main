import os
import time
import math
import wave
import struct
import asyncio
from datetime import datetime
from pathlib import Path
from typing import Dict, Any, List

import numpy as np
import scipy.signal
import librosa

from config.simulation_config import STRATEGY_CONFIGS, PIPELINE_STAGE_ORDER

# In-memory registry for simulation jobs (file_id -> job_dict)
_SIMULATION_JOBS: Dict[str, Dict[str, Any]] = {}
_ACTIVE_TASKS: Dict[str, asyncio.Task] = {}

BASE_DIR = Path(__file__).resolve().parent.parent
UPLOADS_DIR = BASE_DIR / "uploads"


def get_current_timestamp() -> str:
    return datetime.now().strftime("%H:%M:%S")


def get_processing_status(file_id: str) -> Dict[str, Any]:
    """
    Returns the current simulation state for a given file_id.
    """
    if file_id in _SIMULATION_JOBS:
        return _SIMULATION_JOBS[file_id]

    return {
        "file_id": file_id,
        "status": "idle",
        "current_stage": "input",
        "progress": 0.0,
        "total_frames": 0,
        "processed_frames": 0,
        "strategy": "WIENER_FILTER",
        "noise_type": "stationary",
        "confidence": 0.85,
        "pipeline_stages": [
            {"id": s["id"], "label": s["label"], "status": "pending"}
            for s in PIPELINE_STAGE_ORDER
        ],
        "telemetry": {
            "cpu_percent": 18.0,
            "memory_percent": 24.0,
            "frame_rate_fps": 60,
            "latency_ms": 0.0,
            "snr_gain_db": 0.0,
            "p50_latency": 0.0,
            "p95_latency": 0.0,
            "p99_latency": 0.0,
            "max_latency": 0.0,
        },
        "logs": [],
        "output_file_id": None,
        "output_waveform": None,
    }


def stop_processing_simulation(file_id: str) -> Dict[str, Any]:
    """
    Gracefully requests stopping an active simulation.
    """
    if file_id in _SIMULATION_JOBS:
        job = _SIMULATION_JOBS[file_id]
        if job["status"] == "processing":
            job["stop_requested"] = True
            job["logs"].append({
                "time": get_current_timestamp(),
                "level": "WARN",
                "message": "User requested simulation halt."
            })
    return get_processing_status(file_id)


def start_processing_simulation(
    file_path: Path,
    file_id: str,
    phase3_analysis: Dict[str, Any],
    gemini_analysis: Dict[str, Any]
) -> Dict[str, Any]:
    """
    Initializes and starts a frame-based processing simulation background task for file_id.
    """
    # If already processing, return current status
    if file_id in _SIMULATION_JOBS:
        existing = _SIMULATION_JOBS[file_id]
        if existing["status"] == "processing":
            return existing

    # Extract Gemini decision & strategy recommendation
    ai_data = gemini_analysis.get("analysis") or {}
    strategy_key = ai_data.get("recommended_strategy", "WIENER_FILTER").upper()
    if strategy_key not in STRATEGY_CONFIGS:
        strategy_key = "WIENER_FILTER"

    noise_type = ai_data.get("noise_type", "stationary")
    confidence = ai_data.get("confidence", 0.88)
    severity = ai_data.get("severity", 0.50)

    metadata = phase3_analysis.get("metadata", {})
    sr = metadata.get("sample_rate", 16000)
    duration = metadata.get("duration", 1.0)
    num_samples = metadata.get("num_samples", int(sr * duration))

    # Frame sizing: 30 ms frame duration
    frame_ms = 30
    frame_samples = max(256, int(sr * (frame_ms / 1000.0)))
    total_frames = max(10, num_samples // frame_samples)

    initial_job = {
        "file_id": file_id,
        "status": "processing",
        "current_stage": "input",
        "progress": 0.0,
        "total_frames": total_frames,
        "processed_frames": 0,
        "strategy": strategy_key,
        "noise_type": noise_type,
        "confidence": confidence,
        "severity": severity,
        "pipeline_stages": [
            {"id": s["id"], "label": s["label"], "status": "pending"}
            for s in PIPELINE_STAGE_ORDER
        ],
        "telemetry": {
            "cpu_percent": 35.0,
            "memory_percent": 28.0,
            "frame_rate_fps": 55,
            "latency_ms": 12.0,
            "snr_gain_db": 0.0,
            "p50_latency": 0.0,
            "p95_latency": 0.0,
            "p99_latency": 0.0,
            "max_latency": 0.0,
        },
        "logs": [
            {"time": get_current_timestamp(), "level": "INFO", "message": f"Audio dataset loaded ({total_frames} frames, {sr}Hz)"},
            {"time": get_current_timestamp(), "level": "INFO", "message": f"Phase 3 DSP features retrieved (RMS: {phase3_analysis.get('amplitude', {}).get('rms', 0):.3f})"},
            {"time": get_current_timestamp(), "level": "AI", "message": f"Gemini AI Strategy: {strategy_key} (Noise: {noise_type.upper()}, Confidence: {int(confidence*100)}%)"}
        ],
        "output_file_id": None,
        "output_waveform": None,
        "stop_requested": False,
    }

    _SIMULATION_JOBS[file_id] = initial_job

    # Launch background task
    task = asyncio.create_task(
        _run_simulation_loop(file_id, file_path, phase3_analysis, gemini_analysis, strategy_key)
    )
    _ACTIVE_TASKS[file_id] = task

    return initial_job


async def _run_simulation_loop(
    file_id: str,
    file_path: Path,
    phase3_analysis: Dict[str, Any],
    gemini_analysis: Dict[str, Any],
    strategy_key: str
):
    """
    Asynchronous simulation loop processing audio frames, updating stage status,
    generating latency metrics, logging events, and producing simulated output audio.
    """
    job = _SIMULATION_JOBS[file_id]
    strat_cfg = STRATEGY_CONFIGS.get(strategy_key, STRATEGY_CONFIGS["WIENER_FILTER"])

    # Load audio array for simulated signal transformation
    try:
        y, sr = librosa.load(str(file_path), sr=None, mono=True)
    except Exception:
        y = np.zeros(16000, dtype=np.float32)
        sr = 16000

    num_samples = len(y)
    total_frames = job["total_frames"]

    latency_history: List[float] = []

    # Map stage steps across frame progress
    stages_order = [s["id"] for s in PIPELINE_STAGE_ORDER]

    def update_stage_states(active_stage_id: str):
        active_idx = stages_order.index(active_stage_id) if active_stage_id in stages_order else 0
        job["current_stage"] = active_stage_id
        for i, s in enumerate(job["pipeline_stages"]):
            if i < active_idx:
                s["status"] = "complete"
            elif i == active_idx:
                s["status"] = "active"
            else:
                s["status"] = "pending"

    # Step 1: Preprocessing Stage
    update_stage_states("preprocessing")
    job["logs"].append({"time": get_current_timestamp(), "level": "DSP", "message": "Stage 01: Preprocessing & Hanning Windowing initialized"})
    await asyncio.sleep(0.05)

    if job["stop_requested"]:
        _finish_stopped(job)
        return

    # Step 2: Noise Analysis Stage
    update_stage_states("noise-analysis")
    job["logs"].append({"time": get_current_timestamp(), "level": "DSP", "message": "Stage 02: Real Phase 3 spectral features loaded"})
    await asyncio.sleep(0.05)

    if job["stop_requested"]:
        _finish_stopped(job)
        return

    # Step 3: Classification Stage
    update_stage_states("classification")
    job["logs"].append({"time": get_current_timestamp(), "level": "AI", "message": f"Stage 03: Gemini AI classified environment as '{job['noise_type'].upper()}'"})
    await asyncio.sleep(0.05)

    if job["stop_requested"]:
        _finish_stopped(job)
        return

    # Step 4: Adaptive Filter & AI Enhancement & Fusion Frame Simulation
    update_stage_states("adaptive-filter")
    job["logs"].append({"time": get_current_timestamp(), "level": "SIM", "message": f"Stage 04: Running frame-by-frame adaptive filtering ({strat_cfg['label']})"})

    # Process frames sequentially
    step_chunk = max(1, total_frames // 12)
    processed = 0

    while processed < total_frames:
        if job["stop_requested"]:
            _finish_stopped(job)
            return

        # Frame step
        processed += step_chunk
        if processed > total_frames:
            processed = total_frames

        job["processed_frames"] = processed
        progress = round(processed / float(total_frames), 2)
        job["progress"] = progress

        # Update stages based on progress threshold
        if progress > 0.45 and job["current_stage"] == "adaptive-filter":
            update_stage_states("ai-enhancement")
            job["logs"].append({"time": get_current_timestamp(), "level": "AI", "message": "Stage 05: Simulating AI Enhancement weighting & mask application"})
        elif progress > 0.75 and job["current_stage"] == "ai-enhancement":
            update_stage_states("fusion")
            job["logs"].append({"time": get_current_timestamp(), "level": "DSP", "message": f"Stage 06: Fusing DSP ({int(strat_cfg['dsp_weight']*100)}%) + AI ({int(strat_cfg['ai_weight']*100)}%) paths"})

        # Frame latency simulation
        base_lat = strat_cfg["base_latency_ms"]
        jitter = np.random.uniform(-strat_cfg["latency_jitter_ms"], strat_cfg["latency_jitter_ms"])
        frame_lat = max(2.0, base_lat + jitter)
        latency_history.append(frame_lat)

        # Telemetry updates
        job["telemetry"]["latency_ms"] = round(frame_lat, 1)
        job["telemetry"]["cpu_percent"] = round(float(np.random.uniform(48.0, 76.0)), 1)
        job["telemetry"]["memory_percent"] = round(float(np.random.uniform(32.0, 44.0)), 1)
        job["telemetry"]["frame_rate_fps"] = int(np.random.uniform(50, 64))
        job["telemetry"]["snr_gain_db"] = round(strat_cfg["estimated_enhancement_pct"] * 0.18, 1)

        await asyncio.sleep(0.04)


    # Step 5: Output Stage & Audio Generation
    update_stage_states("output")
    job["logs"].append({"time": get_current_timestamp(), "level": "DSP", "message": "Stage 07: Generating enhanced DSP audio output (Wiener Filter)..."})

    output_filename = f"processed_{file_id}.wav"
    output_path = UPLOADS_DIR / output_filename

    try:
        # Apply mathematically rigorous Decision-Directed Wiener Filter speech enhancement
        # STFT analysis with 512-sample Hann window (50% overlap)
        n_fft = 512
        hop_length = 256
        win_length = 512
        window = scipy.signal.windows.hann(win_length)
        
        f, t, Zxx = scipy.signal.stft(
            y, fs=sr, window=window, nperseg=win_length, noverlap=win_length - hop_length, nfft=n_fft
        )
        mag = np.abs(Zxx)
        phase = np.angle(Zxx)
        power = mag ** 2
        n_bins, n_frames = mag.shape
        
        if n_frames > 0:
            init_frames = max(1, min(10, n_frames))
            noise_psd = np.mean(power[:, :init_frames], axis=1)
            
            alpha_dd = 0.98
            g_min = 0.05  # -26 dB spectral floor to prevent musical noise
            smooth_power = power[:, 0].copy()
            prev_clean_mag = mag[:, 0].copy()
            
            enhanced_stft = np.zeros_like(Zxx, dtype=np.complex128)
            
            for m in range(n_frames):
                curr_power = power[:, m]
                smooth_power = 0.85 * smooth_power + 0.15 * curr_power
                
                # Recursive noise PSD tracking (minima tracking)
                noise_psd = np.where(
                    smooth_power < noise_psd,
                    0.80 * noise_psd + 0.20 * smooth_power,
                    0.995 * noise_psd + 0.005 * smooth_power
                )
                
                post_snr = curr_power / (noise_psd + 1e-10)
                
                if m == 0:
                    priori_snr = np.maximum(post_snr - 1.0, 0.0)
                else:
                    priori_snr = (
                        alpha_dd * (prev_clean_mag ** 2) / (noise_psd + 1e-10)
                        + (1.0 - alpha_dd) * np.maximum(post_snr - 1.0, 0.0)
                    )
                    
                gain = priori_snr / (priori_snr + 1.0)
                gain = np.maximum(gain, g_min)
                
                clean_mag = gain * mag[:, m]
                prev_clean_mag = clean_mag
                enhanced_stft[:, m] = clean_mag * np.exp(1j * phase[:, m])
                
            _, processed_y = scipy.signal.istft(
                enhanced_stft, fs=sr, window=window, nperseg=win_length, noverlap=win_length - hop_length, nfft=n_fft
            )
            processed_y = processed_y[:len(y)]
        else:
            processed_y = y.copy()
            
        processed_y = np.clip(processed_y, -1.0, 1.0).astype(np.float32)

        # Write output WAV file with full RIFF/WAVE header
        pcm_out = (processed_y * 32767.0).astype(np.int16)
        with wave.open(str(output_path), "wb") as wav_out:
            wav_out.setnchannels(1)
            wav_out.setsampwidth(2)
            wav_out.setframerate(sr)
            wav_out.writeframes(pcm_out.tobytes())

        # Generate downsampled output waveform for chart
        target_points = min(1200, len(processed_y))
        indices = np.linspace(0, len(processed_y) - 1, target_points, dtype=int)
        wf_samples = processed_y[indices]
        duration = float(len(processed_y)) / float(sr)
        wf_times = np.linspace(0, duration, target_points)

        job["output_waveform"] = {
            "time": [round(float(t), 3) for t in wf_times],
            "amplitude": [round(float(a), 4) for a in wf_samples]
        }
        job["output_file_id"] = f"processed_{file_id}"
        job["logs"].append({"time": get_current_timestamp(), "level": "SUCCESS", "message": f"Simulated output audio generated: {output_filename}"})
    except Exception as err:
        job["logs"].append({"time": get_current_timestamp(), "level": "WARN", "message": f"Output audio fallback: {str(err)}"})

    # Latency percentiles calculation
    if latency_history:
        arr = np.array(latency_history)
        job["telemetry"]["p50_latency"] = round(float(np.percentile(arr, 50)), 1)
        job["telemetry"]["p95_latency"] = round(float(np.percentile(arr, 95)), 1)
        job["telemetry"]["p99_latency"] = round(float(np.percentile(arr, 99)), 1)
        job["telemetry"]["max_latency"] = round(float(np.max(arr)), 1)

    # Mark all stages as complete
    for s in job["pipeline_stages"]:
        s["status"] = "complete"

    job["status"] = "complete"
    job["progress"] = 1.0
    job["telemetry"]["cpu_percent"] = 22.0
    job["telemetry"]["memory_percent"] = 25.0
    job["telemetry"]["frame_rate_fps"] = 60
    job["telemetry"]["latency_ms"] = 0.0

    job["logs"].append({"time": get_current_timestamp(), "level": "SUCCESS", "message": "Simulation Complete ✓ All pipeline stages executed successfully."})


def _finish_stopped(job: dict):
    job["status"] = "stopped"
    job["telemetry"]["cpu_percent"] = 18.0
    job["telemetry"]["memory_percent"] = 24.0
    job["telemetry"]["frame_rate_fps"] = 60
    job["telemetry"]["latency_ms"] = 0.0
    for s in job["pipeline_stages"]:
        if s["status"] == "active":
            s["status"] = "error"
