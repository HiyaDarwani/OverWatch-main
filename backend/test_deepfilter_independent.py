import sys
from pathlib import Path
import numpy as np
import librosa

BASE_DIR = Path(__file__).resolve().parent
UPLOADS_DIR = BASE_DIR / "uploads"

input_files = list(UPLOADS_DIR.glob("1b39b497598d.wav"))
processed_files = list(UPLOADS_DIR.glob("processed_1b39b497598d.wav"))

if not input_files or not processed_files:
    print("ERROR: Input or Processed audio file not found for independent audit.")
    sys.exit(1)

input_path = input_files[0]
output_path = processed_files[0]

print("=== INDEPENDENT DEEPFILTERNET OUTPUT AUDIT ===")
print(f"Input File:     {input_path.name}")
print(f"Output File:    {output_path.name}")
print(f"Output Exists:  {output_path.exists()}")

# Load input audio
y_in, sr_in = librosa.load(input_path, sr=None, mono=False)
if y_in.ndim == 1:
    y_in = np.expand_dims(y_in, axis=0)

# Load output audio
y_out, sr_out = librosa.load(output_path, sr=None, mono=False)
if y_out.ndim == 1:
    y_out = np.expand_dims(y_out, axis=0)

dur_in = y_in.shape[-1] / sr_in
dur_out = y_out.shape[-1] / sr_out

print("\n--- INPUT AUDIO PROPERTIES ---")
print(f"  Sample Rate: {sr_in} Hz")
print(f"  Channels:    {y_in.shape[0]}")
print(f"  Duration:    {dur_in:.2f} s")
print(f"  RMS:         {np.sqrt(np.mean(y_in**2)):.6f}")
print(f"  Peak:        {np.max(np.abs(y_in)):.6f}")

print("\n--- OUTPUT DEEPFILTERNET AUDIO PROPERTIES ---")
print(f"  Sample Rate: {sr_out} Hz (Expected 48000 Hz)")
print(f"  Channels:    {y_out.shape[0]}")
print(f"  Duration:    {dur_out:.2f} s")
print(f"  RMS:         {np.sqrt(np.mean(y_out**2)):.6f}")
print(f"  Peak:        {np.max(np.abs(y_out)):.6f}")

is_not_identical = not np.array_equal(y_in, y_out)
has_nonzero = np.any(y_out != 0)
is_48k = sr_out == 48000

print("\n--- INDEPENDENT VERIFICATION CHECKS ---")
print(f"  1. File Exists & Readable:   {'PASS' if output_path.exists() else 'FAIL'}")
print(f"  2. Non-Identical to Input:   {'PASS' if is_not_identical else 'FAIL'}")
print(f"  3. Non-Zero Audio Samples:   {'PASS' if has_nonzero else 'FAIL'}")
print(f"  4. Target 48kHz Resampling:  {'PASS' if is_48k else 'FAIL'}")
print(f"  5. Reasonable Duration:     {'PASS' if dur_out > 0.5 else 'FAIL'}")

if output_path.exists() and is_not_identical and has_nonzero and is_48k:
    print("\nOVERALL DEEPFILTERNET INDEPENDENT AUDIT: PASS")
else:
    print("\nOVERALL DEEPFILTERNET INDEPENDENT AUDIT: FAIL")
