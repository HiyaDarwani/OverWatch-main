import os
import sys
from pathlib import Path
from dotenv import load_dotenv

# Load environment variables
dotenv_path = Path(__file__).resolve().parent.parent / ".env"
load_dotenv(dotenv_path)

api_key = os.getenv("GEMINI_API_KEY")
model_name = os.getenv("GEMINI_MODEL", "gemini-3.6-flash").strip() or "gemini-3.6-flash"

print(f"API key loaded: {bool(api_key)}")
print(f"Model: {model_name}")

if not api_key:
    print("ERROR: GEMINI_API_KEY not found in environment.")
    sys.exit(1)

try:
    from google import genai
    from google.genai import types
    from services.gemini_analysis import classify_gemini_error
except ImportError as imp_err:
    print(f"SDK_ERROR: Failed to import google-genai SDK: {imp_err}")
    sys.exit(1)

print("Initializing Gemini client...")

try:
    client = genai.Client(api_key=api_key)
    config = types.GenerateContentConfig(
        http_options=types.HttpOptions(timeout=60000)
    )
    print(f"Sending request to Gemini ({model_name}, timeout: 60s)...")
    response = client.models.generate_content(
        model=model_name,
        contents="Say exactly GEMINI_WORKS",
        config=config
    )
    
    response_text = response.text.strip() if response and response.text else ""
    print(f"Response: {response_text}")

except Exception as err:
    error_code, error_msg = classify_gemini_error(err)
    print(f"Error Code: {error_code}")
    print(f"Error Message: {error_msg}")
    print(f"Raw Technical Details: {type(err).__name__} - {err}")
    sys.exit(1)