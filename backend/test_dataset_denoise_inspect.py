"""
Diagnostic Test: DeepFilterNet Input/Output Audio Statistics & Waveform Data Inspection
"""
import sys
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent
if str(BASE_DIR) not in sys.path:
    sys.path.insert(0, str(BASE_DIR))

import numpy as np
import librosa
from services.deepfilter_service import process_audio
from services.audio_comparison import get_audio_comparison

def inspect():
    uploads_dir = BASE_DIR / "uploads"
    wav_files = [f for f in uploads_dir.glob("*.wav") if not f.name.startswith("processed_") and not f.name.startswith("live_")]
    if not wav_files:
        print("No dataset WAV files found in uploads/. Using default 1b39b497598d.wav or live WAV...")
        wav_files = list(uploads_dir.glob("*.wav"))

    target_wav = wav_files[0]
    file_id = target_wav.stem
    print(f"============================================================")
    print(f"Target Input WAV: {target_wav.name} (file_id: {file_id})")
    print(f"============================================================")

    # 1. Inspect input WAV with librosa
    y_in, sr_in = librosa.load(str(target_wav), sr=None, mono=False)
    rms_in = float(np.sqrt(np.mean(np.square(y_in))))
    peak_in = float(np.max(np.abs(y_in)))
    print(f"INPUT AUDIO STATS:")
    print(f"  Sample Rate: {sr_in} Hz")
    print(f"  Shape:       {y_in.shape}")
    print(f"  RMS:         {rms_in:.6f}")
    print(f"  Peak:        {peak_in:.6f}")
    print(f"  Min/Max:     [{np.min(y_in):.6f}, {np.max(y_in):.6f}]")

    # 2. Run DeepFilterNet process_audio
    print("\nRunning DeepFilterNet process_audio()...")
    res = process_audio(target_wav, file_id)
    print("Process Result:")
    print(res)

    # 3. Inspect generated output WAV
    proc_wav = uploads_dir / f"processed_{file_id}.wav"
    if not proc_wav.exists():
        print(f"ERROR: Generated output WAV does not exist: {proc_wav}")
        return

    y_out, sr_out = librosa.load(str(proc_wav), sr=None, mono=False)
    rms_out = float(np.sqrt(np.mean(np.square(y_out))))
    peak_out = float(np.max(np.abs(y_out)))
    print(f"\nOUTPUT DEEPFILTERNET AUDIO STATS:")
    print(f"  Sample Rate: {sr_out} Hz")
    print(f"  Shape:       {y_out.shape}")
    print(f"  RMS:         {rms_out:.6f}")
    print(f"  Peak:        {peak_out:.6f}")
    print(f"  Min/Max:     [{np.min(y_out):.6f}, {np.max(y_out):.6f}]")

    if rms_out == 0 or peak_out == 0:
        print("CRITICAL WARNING: DeepFilterNet output file is SILENT (all zeros)!")
    else:
        print("DeepFilterNet output file has REAL NON-ZERO AUDIO SAMPLES! PASS.")

    # 4. Inspect get_audio_comparison output for frontend waveform chart
    print("\nTesting get_audio_comparison(file_id)...")
    comp = get_audio_comparison(file_id)
    proc_wf = comp.get("processed", {}).get("waveform", {})
    amps = proc_wf.get("amplitude", [])
    print(f"Processed Waveform Points Count: {len(amps)}")
    if amps:
        max_amp = max(abs(a) for a in amps)
        print(f"Max Waveform Amplitude in JSON: {max_amp:.6f}")
        if max_amp > 0:
            print("Waveform JSON contains VISIBLE NON-ZERO AUDIO DATA! PASS.")
        else:
            print("WARNING: Waveform JSON amplitude values are ALL ZERO!")

if __name__ == "__main__":
    inspect()
