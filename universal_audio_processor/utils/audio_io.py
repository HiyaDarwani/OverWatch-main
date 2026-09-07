"""Small, dependency-light helpers for reading and writing WAV audio."""

import numpy as np
from scipy.io import wavfile


def load_audio(path, sr=None):
	"""Load a WAV file as mono float32 audio and optionally resample it."""
	source_rate, audio = wavfile.read(path)
	audio = np.asarray(audio)

	if audio.ndim == 2:
		audio = np.mean(audio, axis=1)
	if np.issubdtype(audio.dtype, np.integer):
		info = np.iinfo(audio.dtype)
		scale = max(abs(info.min), info.max)
		audio = audio.astype(np.float32) / scale
	else:
		audio = audio.astype(np.float32)

	if sr is not None and sr != source_rate:
		from scipy.signal import resample_poly
		divisor = np.gcd(source_rate, sr)
		audio = resample_poly(
			audio,
			sr // divisor,
			source_rate // divisor,
		).astype(np.float32)
		source_rate = sr

	return audio, source_rate


def save_audio(path, audio, sr=16000):
	"""Write float audio to a 32-bit WAV file."""
	audio = np.asarray(audio, dtype=np.float32)
	wavfile.write(path, sr, np.clip(audio, -1.0, 1.0))