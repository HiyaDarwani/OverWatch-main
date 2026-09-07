"""
Diagnostic test script for DeepFilterNet audio enhancement engine.

Tests:
1. Locate an existing uploaded WAV file.
2. Run real DeepFilterNet inference via deepfilter_service.
3. Verify processed output WAV exists.
4. Verify audio integrity using librosa.
5. Print structured diagnostic details.
"""
import sys
import os
import time
from pathlib import Path

# Add backend directory to sys.path
BASE_DIR = Path(__file__).resolve().parent
if str(BASE_DIR) not in sys.path:
    sys.path.insert(0, str(BASE_DIR))

import librosa
from services.deepfilter_service import process_audio, get_engine_status

def main():
    print("=" * 60)
    print("  OVERWATCH DEEPFILTERNET DIAGNOSTIC TEST")
    print("=" * 60)
    
    # 1. Check Engine Status
    status_info = get_engine_status()
    print(f"Engine: {status_info['engine']}")
    print(f"Available: {status_info['available']}")
    print(f"Mode: {status_info['mode']}")
    print(f"Venv Path: {status_info['venv_path']}")
    print("-" * 60)
    
    if not status_info['available']:
        print("DEEPFILTERNET_NOT_INSTALLED")
        print("\nPlease run backend/setup_deepfilter.ps1 to install DeepFilterNet in .venv-dfn.")
        sys.exit(1)
        
    # 2. Locate an existing uploaded WAV file
    uploads_dir = BASE_DIR / "uploads"
    wav_files = [f for f in uploads_dir.glob("*.wav") if not f.name.startswith("processed_")]
    
    if not wav_files:
        print("No sample WAV file found in backend/uploads/.")
        print("Creating dummy noisy 48kHz WAV file for test...")
        import numpy as np
        import scipy.io.wavfile as wavfile
        
        test_file = uploads_dir / "test_sample.wav"
        sr = 48000
        duration = 2.0
        t = np.linspace(0, duration, int(sr * duration), endpoint=False)
        signal = 0.5 * np.sin(2 * np.pi * 440 * t)  # 440Hz tone
        noise = 0.1 * np.random.normal(size=len(t)) # White noise
        noisy_signal = (signal + noise).astype(np.float32)
        pcm = (noisy_signal * 32767.0).astype(np.int16)
        wavfile.write(str(test_file), sr, pcm)
        input_path = test_file
        file_id = "test_sample"
    else:
        input_path = wav_files[0]
        file_id = input_path.stem

    print(f"Input WAV: {input_path.name}")
    print(f"File ID: {file_id}")
    
    # 3. Run DeepFilterNet Inference
    start_time = time.perf_counter()
    res = process_audio(input_path, file_id)
    elapsed_ms = round((time.perf_counter() - start_time) * 1000, 1)
    
    print("-" * 60)
    print("Process Result:")
    for k, v in res.items():
        print(f"  {k}: {v}")
    print("-" * 60)
    
    if res.get("status") != "success":
        print(f"TEST FAILED: {res.get('error_code', 'UNKNOWN')} - {res.get('error')}")
        sys.exit(1)
        
    # 4. Verify Output File
    output_path = uploads_dir / f"processed_{file_id}.wav"
    output_exists = output_path.exists()
    print(f"DeepFilterNet loaded: True")
    print(f"Input: {input_path}")
    print(f"Output: {output_path}")
    print(f"Processing time: {res.get('processing_time_ms', elapsed_ms)} ms")
    print(f"Output exists: {output_exists}")
    
    if not output_exists:
        print("TEST FAILED: Output file does not exist on disk!")
        sys.exit(1)

    # 5. Load and Verify Output Audio with Librosa
    try:
        y, sr = librosa.load(str(output_path), sr=None)
        duration = round(len(y) / float(sr), 3)
        print(f"Output sample rate: {sr}")
        print(f"Output duration: {duration} s")
        print("Audio verification: PASS")
    except Exception as e:
        print(f"Audio verification FAILED: {e}")
        sys.exit(1)

    print("=" * 60)
    print("  DEEPFILTERNET DIAGNOSTIC TEST PASSED  ")
    print("=" * 60)

if __name__ == "__main__":
    main()
