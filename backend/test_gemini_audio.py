import os
import sys
import json
from pathlib import Path
from dotenv import load_dotenv

# Load environment variables
backend_dir = Path(__file__).resolve().parent
dotenv_path = backend_dir.parent / ".env"
load_dotenv(dotenv_path)

api_key = os.getenv("GEMINI_API_KEY")
model_name = os.getenv("GEMINI_MODEL", "gemini-3.6-flash").strip() or "gemini-3.6-flash"

print(f"API key loaded: {bool(api_key)}")
print(f"Model: {model_name}")

if not api_key:
    print("ERROR: GEMINI_API_KEY not found in environment.")
    sys.exit(1)

uploads_dir = backend_dir / "uploads"
if not uploads_dir.exists():
    print("ERROR: uploads directory does not exist.")
    sys.exit(1)

# Find an existing original uploaded audio file (ignore processed_*.wav)
matched_files = [f for f in uploads_dir.glob("*.wav") if not f.name.startswith("processed_")]
if not matched_files:
    print("ERROR: No valid original uploaded WAV files found in backend/uploads for testing.")
    sys.exit(1)

test_audio_file = matched_files[0]
file_id = test_audio_file.stem
print(f"Found test audio file: {test_audio_file.name} (file_id: {file_id})")

from services.audio_analysis import analyze_audio
from services.gemini_analysis import analyze_audio_with_gemini

print("Running Phase 3 DSP feature extraction...")
dsp_result = analyze_audio(test_audio_file, file_id)
print("DSP analysis complete. Duration:", dsp_result.get("metadata", {}).get("duration"), "sec")

print(f"Triggering Gemini audio analysis pipeline using '{model_name}'...")
ai_result = analyze_audio_with_gemini(test_audio_file, file_id, dsp_result)

print("\n--- GEMINI AI ANALYSIS RESULT ---")
print(json.dumps(ai_result, indent=2))

if ai_result.get("status") == "success":
    print("\nSUCCESS: Real audio + DSP + Gemini pipeline completed successfully!")
else:
    print(f"\nFAILURE/UNAVAILABLE: {ai_result.get('error_code')} - {ai_result.get('error')}")
    sys.exit(1)
