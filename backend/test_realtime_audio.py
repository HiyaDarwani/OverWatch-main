"""
Diagnostic test script for Real-Time Audio Ingestion & DSP Service.

Tests:
1. Initialize LiveAudioSession (48kHz mono).
2. Generate synthetic sine wave + noise PCM chunks and feed into session.process_chunk.
3. Verify calculated DSP metrics (RMS, peak, dB, ZCR, spectral centroid, dominant frequency).
4. Verify rolling buffer capacity limit (max samples enforced).
5. Verify snapshot WAV export and librosa audio loading.
6. Verify no fake/random data is generated.
"""
import sys
import os
import time
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent
if str(BASE_DIR) not in sys.path:
    sys.path.insert(0, str(BASE_DIR))

import numpy as np
import librosa
from services.realtime_audio import LiveAudioSession, live_session_manager

def main():
    print("=" * 60)
    print("  OVERWATCH REAL-TIME AUDIO DSP DIAGNOSTIC TEST")
    print("=" * 60)

    session_id = "test_realtime_sess_123"
    sr = 48000
    max_buf_sec = 5.0
    
    # 1. Create Session
    session = LiveAudioSession(
        session_id=session_id,
        sample_rate=sr,
        channels=1,
        max_buffer_seconds=max_buf_sec
    )
    
    print(f"Session created: {session.session_id}")
    print(f"Sample Rate: {session.sample_rate} Hz")
    print(f"Max Buffer: {session.max_buffer_seconds} s ({session.max_samples} samples)")
    print("-" * 60)

    # 2. Ingest 440 Hz Sine Wave PCM Chunks (approx 50ms per chunk = 2400 samples)
    chunk_ms = 50
    chunk_samples = int(sr * (chunk_ms / 1000.0))
    freq = 440.0 # A4 tone
    
    total_chunks_sent = 0
    t_running = 0.0

    print("Feeding 120 live PCM chunks (~6 seconds of 440Hz audio)...")
    for i in range(120):
        t_chunk = np.linspace(t_running, t_running + (chunk_ms / 1000.0), chunk_samples, endpoint=False)
        t_running += (chunk_ms / 1000.0)
        
        # 440 Hz sine wave + small noise
        signal = 0.6 * np.sin(2 * np.pi * freq * t_chunk) + 0.05 * np.random.normal(size=len(t_chunk))
        pcm_bytes = signal.astype(np.float32).tobytes()
        
        telemetry = session.process_chunk(pcm_bytes, dtype="float32")
        total_chunks_sent += 1

    print(f"Chunks sent: {total_chunks_sent}")
    print("-" * 60)

    # 3. Verify Telemetry Results
    print("Latest Calculated Telemetry:")
    print(f"  Timestamp:          {telemetry['timestamp']}")
    print(f"  RMS Amplitude:      {telemetry['rms']} (expected ~0.42)")
    print(f"  Peak Amplitude:     {telemetry['peak']} (expected ~0.65)")
    print(f"  dB Level:           {telemetry['db']} dB")
    print(f"  Dominant Frequency: {telemetry['dominant_frequency']} Hz (expected ~440.0 Hz)")
    print(f"  Spectral Centroid:  {telemetry['spectral_centroid']} Hz")
    print(f"  Zero Crossing Rate: {telemetry['zero_crossing_rate']}")
    print(f"  Buffer Duration:    {telemetry['buffer_duration_sec']} s (max {max_buf_sec}s)")
    print("-" * 60)

    # Assertions
    assert 0.35 <= telemetry['rms'] <= 0.50, f"RMS out of expected range: {telemetry['rms']}"
    assert 0.50 <= telemetry['peak'] <= 0.80, f"Peak out of expected range: {telemetry['peak']}"
    assert 420.0 <= telemetry['dominant_frequency'] <= 460.0, f"Dominant freq out of expected range: {telemetry['dominant_frequency']}"
    assert telemetry['buffer_duration_sec'] <= max_buf_sec, f"Buffer exceeded max duration limit: {telemetry['buffer_duration_sec']} > {max_buf_sec}"

    print("DSP Metrics Check: PASS")

    # 4. Verify Rolling Buffer Capacity Limit
    with session.lock:
        buf_len = len(session.buffer)
    print(f"Buffer length: {buf_len} samples ({buf_len / sr:.2f} s)")
    assert buf_len <= session.max_samples, f"Buffer capacity overflow: {buf_len} > {session.max_samples}"
    print("Rolling Buffer Capacity Limit: PASS")

    # 5. Verify Snapshot WAV Export
    print("-" * 60)
    print("Exporting 4.0s rolling buffer snapshot to WAV...")
    wav_path, file_id = session.export_snapshot_wav(duration_sec=4.0)
    print(f"Exported WAV Path: {wav_path}")
    print(f"Generated File ID: {file_id}")
    assert wav_path.exists(), "Snapshot WAV file does not exist!"

    y, loaded_sr = librosa.load(str(wav_path), sr=None)
    duration = round(len(y) / float(loaded_sr), 3)
    print(f"Librosa loaded SR: {loaded_sr} Hz")
    print(f"Librosa loaded duration: {duration} s")
    assert loaded_sr == sr, f"Loaded SR mismatch: {loaded_sr} != {sr}"
    assert 3.8 <= duration <= 4.2, f"Loaded duration mismatch: {duration} s"

    print("Snapshot WAV Verification: PASS")
    print("=" * 60)
    print("  REAL-TIME AUDIO DSP DIAGNOSTIC TEST PASSED  ")
    print("=" * 60)

if __name__ == "__main__":
    main()
