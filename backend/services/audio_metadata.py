import os
import wave
from pathlib import Path
from typing import Dict, Any

try:
    import soundfile as sf
except ImportError:
    sf = None

try:
    import mutagen
except ImportError:
    mutagen = None


def extract_audio_metadata(file_path: Path, original_filename: str) -> Dict[str, Any]:
    """
    Extract basic metadata from an audio file.
    Supports WAV natively via stdlib wave module or soundfile, and MP3/FLAC via mutagen/soundfile.

    Returns:
        Dict with keys: duration (float), sample_rate (int), channels (int), format (str)
    Raises:
        ValueError if the file is invalid, corrupted, or unsupported.
    """
    if not file_path.exists():
        raise ValueError("File does not exist on disk.")

    file_size = file_path.stat().st_size
    if file_size == 0:
        raise ValueError("Uploaded audio file is empty (0 bytes).")

    ext = file_path.suffix.lower().lstrip('.')
    if not ext:
        ext = Path(original_filename).suffix.lower().lstrip('.') or "wav"

    # 1. Primary path: try soundfile for WAV and other uncompressed formats
    if sf is not None:
        try:
            info = sf.info(str(file_path))
            if info.samplerate > 0 and info.frames >= 0:
                duration = round(info.frames / float(info.samplerate), 2)
                return {
                    "duration": duration,
                    "sample_rate": int(info.samplerate),
                    "channels": int(info.channels),
                    "format": ext if ext else "wav"
                }
        except Exception:
            pass  # Fallback to wave / mutagen

    # 2. Fallback path: try standard wave module for standard 16-bit PCM WAV files
    if ext == "wav":
        try:
            with wave.open(str(file_path), "rb") as wav_file:
                nchannels = wav_file.getnchannels()
                framerate = wav_file.getframerate()
                nframes = wav_file.getnframes()

                if framerate <= 0 or nframes < 0:
                    raise ValueError("Invalid WAV header values.")

                duration = round(nframes / float(framerate), 2)
                sample_rate = int(framerate)
                channels = int(nchannels)
                return {
                    "duration": duration,
                    "sample_rate": sample_rate,
                    "channels": channels,
                    "format": "wav"
                }
        except (wave.Error, EOFError, ValueError) as e:
            if not mutagen and sf is None:
                raise ValueError(f"Invalid or corrupted WAV audio file: {str(e)}")

    # 3. Fallback path: try mutagen for MP3, FLAC, or fallback WAV
    if mutagen:
        try:
            audio = mutagen.File(str(file_path))
            if audio is not None and audio.info is not None:
                duration = round(float(audio.info.length), 2)
                sample_rate = int(getattr(audio.info, "sample_rate", 44100))
                channels = int(getattr(audio.info, "channels", 1))
                return {
                    "duration": duration,
                    "sample_rate": sample_rate,
                    "channels": channels,
                    "format": ext
                }
        except Exception as e:
            raise ValueError(f"Could not parse audio file metadata: {str(e)}")

    raise ValueError(f"Invalid, corrupted, or unsupported audio file format (.{ext}).")

