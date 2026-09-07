"""
Real-Time Audio Ingestion & DSP Service for OverWatch.

Handles live microphone audio streaming over WebSockets:
- Accepts raw PCM binary audio chunks (Float32 or Int16)
- Performs lightweight streaming DSP analysis (RMS, Peak, dB, ZCR, FFT, Spectral Centroid, Bandwidth, Rolloff, Dominant Frequency)
- Maintains a fixed-capacity rolling audio buffer (default 5-10 seconds)
- Exports rolling buffer snapshots to WAV for Gemini AI classification and DeepFilterNet denoising
- Manages live session lifecycle with thread-safe cleanup
"""
import os
import time
import uuid
import wave
import logging
import threading
from pathlib import Path
from typing import Dict, Any, List, Optional, Tuple

import numpy as np
import scipy.signal
import librosa

logger = logging.getLogger("overwatch.realtime")

BASE_DIR = Path(__file__).resolve().parent.parent
UPLOADS_DIR = BASE_DIR / "uploads"
UPLOADS_DIR.mkdir(parents=True, exist_ok=True)


class LiveAudioSession:
    """
    Manages a single live microphone audio session.
    Maintains a rolling audio buffer and calculates streaming DSP telemetry.
    """

    def __init__(
        self,
        session_id: str,
        sample_rate: int = 48000,
        channels: int = 1,
        max_buffer_seconds: float = 10.0,
    ):
        self.session_id = session_id
        self.sample_rate = max(8000, min(192000, sample_rate))
        self.channels = max(1, min(2, channels))
        self.max_buffer_seconds = max(2.0, min(30.0, max_buffer_seconds))

        # Max samples capacity
        self.max_samples = int(self.sample_rate * self.max_buffer_seconds)

        # Thread-safe rolling audio buffer (float32, normalized -1.0 to 1.0)
        self.lock = threading.Lock()
        self.buffer = np.zeros(0, dtype=np.float32)

        self.start_time = time.time()
        self.last_activity = time.time()
        self.total_samples_received = 0
        self.frame_count = 0

        # Latest DSP metrics cache
        self.latest_telemetry: Dict[str, Any] = {
            "session_id": session_id,
            "timestamp": time.time(),
            "rms": 0.0,
            "peak": 0.0,
            "db": -100.0,
            "zero_crossing_rate": 0.0,
            "spectral_centroid": 0.0,
            "spectral_bandwidth": 0.0,
            "spectral_rolloff": 0.0,
            "spectral_flatness": 0.0,
            "dominant_frequency": 0.0,
            "sample_rate": self.sample_rate,
            "buffer_duration_sec": 0.0,
        }

    def process_chunk(self, raw_bytes: bytes, dtype: str = "float32") -> Dict[str, Any]:
        """
        Ingests a binary PCM chunk from the browser, appends to the rolling buffer,
        and computes real-time streaming DSP telemetry.
        """
        self.last_activity = time.time()

        # 1. Decode binary PCM bytes to float32 normalized array
        try:
            if dtype == "int16":
                pcm16 = np.frombuffer(raw_bytes, dtype=np.int16)
                if len(pcm16) == 0:
                    return self.latest_telemetry
                chunk = (pcm16.astype(np.float32) / 32768.0)
            else:
                chunk = np.frombuffer(raw_bytes, dtype=np.float32)
                if len(chunk) == 0:
                    return self.latest_telemetry
        except Exception as e:
            logger.warning(f"[LiveSession {self.session_id}] Error decoding PCM chunk: {e}")
            return self.latest_telemetry

        # Handle multi-channel (average to mono)
        if self.channels > 1 and len(chunk) % self.channels == 0:
            chunk = chunk.reshape(-1, self.channels).mean(axis=1)

        # Clip values to prevent overflow
        chunk = np.clip(chunk, -1.0, 1.0)
        num_chunk_samples = len(chunk)

        with self.lock:
            # Append chunk to rolling buffer and maintain max capacity
            self.buffer = np.concatenate([self.buffer, chunk])
            if len(self.buffer) > self.max_samples:
                self.buffer = self.buffer[-self.max_samples:]

            self.total_samples_received += num_chunk_samples
            self.frame_count += 1
            current_buffer_len = len(self.buffer)

        # 2. Compute Real-Time DSP Telemetry on current chunk / window
        analysis_window = chunk if len(chunk) >= 128 else self.buffer[-min(2048, current_buffer_len):]
        telemetry = self._calculate_dsp(analysis_window, current_buffer_len)
        self.latest_telemetry = telemetry
        return telemetry

    def _calculate_dsp(self, signal: np.ndarray, current_buffer_len: int) -> Dict[str, Any]:
        """
        Calculates genuine physical DSP measurements from audio signal.
        NO fake or simulated values.
        """
        if len(signal) == 0:
            return self.latest_telemetry

        # Amplitude metrics
        rms_val = float(np.sqrt(np.mean(np.square(signal))))
        peak_val = float(np.max(np.abs(signal)))

        db_val = float(20.0 * np.log10(max(rms_val, 1e-6)))
        if rms_val < 1e-6:
            db_val = -100.0

        # Zero crossing rate
        zcr = float(np.mean(np.abs(np.diff(np.signbit(signal)))))

        # FFT Spectrum
        windowed = signal * np.hanning(len(signal))
        fft_raw = np.abs(np.fft.rfft(windowed))
        freqs_raw = np.fft.rfftfreq(len(signal), d=1.0 / self.sample_rate)

        # Dominant frequency
        if len(fft_raw) > 1:
            dom_idx = np.argmax(fft_raw[1:]) + 1
            dominant_freq = float(freqs_raw[dom_idx])
        else:
            dominant_freq = 0.0

        # Spectral Centroid & Bandwidth calculation
        sum_fft = float(np.sum(fft_raw))
        if sum_fft > 1e-9:
            spectral_centroid = float(np.sum(freqs_raw * fft_raw) / sum_fft)
            spectral_bandwidth = float(np.sqrt(np.sum(((freqs_raw - spectral_centroid) ** 2) * fft_raw) / sum_fft))

            # Spectral Rolloff (85% energy threshold)
            cum_energy = np.cumsum(fft_raw)
            rolloff_idx = np.searchsorted(cum_energy, 0.85 * sum_fft)
            spectral_rolloff = float(freqs_raw[min(rolloff_idx, len(freqs_raw) - 1)])

            # Spectral Flatness (Geometric mean / Arithmetic mean)
            geom_mean = np.exp(np.mean(np.log(np.maximum(fft_raw, 1e-9))))
            arith_mean = np.mean(fft_raw)
            spectral_flatness = float(geom_mean / max(arith_mean, 1e-9))
        else:
            spectral_centroid = 0.0
            spectral_bandwidth = 0.0
            spectral_rolloff = 0.0
            spectral_flatness = 0.0

        # Estimated SNR calculation for live microphone (Speech Peak 90th percentile vs Noise Floor 10th percentile)
        if len(signal) >= 128:
            mags = np.abs(signal)
            speech_est = float(np.percentile(mags, 90) ** 2)
            noise_est = float(np.percentile(mags, 10) ** 2)
            if noise_est > 1e-9 and speech_est > noise_est:
                est_snr_val = float(10.0 * np.log10(speech_est / noise_est))
                estimated_snr_db = round(min(60.0, max(0.0, est_snr_val)), 1)
            else:
                estimated_snr_db = 0.0
        else:
            estimated_snr_db = 0.0

        # Bounded FFT Spectrum Data for Client Chart (~80 frequency bins)
        target_bins = 80
        max_mag = float(np.max(fft_raw)) if len(fft_raw) > 0 else 1.0
        if max_mag > 1e-9:
            fft_db = 20.0 * np.log10(np.maximum(fft_raw / max_mag, 1e-4))
        else:
            fft_db = np.full_like(fft_raw, -100.0)

        if len(freqs_raw) > target_bins:
            bin_edges = np.linspace(0, len(freqs_raw), target_bins + 1, dtype=int)
            freq_list = []
            mag_db_list = []
            for i in range(target_bins):
                b_start, b_end = bin_edges[i], bin_edges[i + 1]
                if b_start == b_end:
                    b_end = b_start + 1
                freq_list.append(float(np.mean(freqs_raw[b_start:b_end])))
                mag_db_list.append(float(np.max(fft_db[b_start:b_end])))
        else:
            freq_list = [float(f) for f in freqs_raw]
            mag_db_list = [float(m) for m in fft_db]

        # Bounded Waveform Subsample for Client (~150 points)
        target_wf_points = min(150, len(signal))
        indices = np.linspace(0, len(signal) - 1, target_wf_points, dtype=int)
        wf_samples = [round(float(s), 4) for s in signal[indices]]

        buffer_dur = round(float(current_buffer_len) / float(self.sample_rate), 2)

        return {
            "session_id": self.session_id,
            "timestamp": round(time.time(), 3),
            "rms": round(rms_val, 4),
            "peak": round(peak_val, 4),
            "db": round(db_val, 1),
            "estimated_snr_db": estimated_snr_db,
            "zero_crossing_rate": round(zcr, 4),
            "spectral_centroid": round(spectral_centroid, 1),
            "spectral_bandwidth": round(spectral_bandwidth, 1),
            "spectral_rolloff": round(spectral_rolloff, 1),
            "spectral_flatness": round(spectral_flatness, 4),
            "dominant_frequency": round(dominant_freq, 1),
            "sample_rate": self.sample_rate,
            "buffer_duration_sec": buffer_dur,
            "spectrum": {
                "frequencies": [round(f, 1) for f in freq_list],
                "magnitudes": [round(m, 1) for m in mag_db_list],
            },
            "waveform": {
                "samples": wf_samples,
            },
        }

    def export_snapshot_wav(self, duration_sec: float = 5.0) -> Tuple[Path, str]:
        """
        Exports recent rolling audio buffer to a standard 16-bit WAV file on disk.
        Returns (file_path, file_id).
        """
        with self.lock:
            if len(self.buffer) == 0:
                # Fallback silent buffer
                audio_data = np.zeros(self.sample_rate * 2, dtype=np.float32)
            else:
                num_target = int(self.sample_rate * duration_sec)
                if len(self.buffer) > num_target:
                    audio_data = self.buffer[-num_target:].copy()
                else:
                    audio_data = self.buffer.copy()

        # Generate unique file_id
        file_id = f"live_{uuid.uuid4().hex[:10]}"
        wav_filename = f"{file_id}.wav"
        wav_path = UPLOADS_DIR / wav_filename

        pcm16 = (audio_data * 32767.0).astype(np.int16)

        with wave.open(str(wav_path), "wb") as wf:
            wf.setnchannels(1)
            wf.setsampwidth(2)
            wf.setframerate(self.sample_rate)
            wf.writeframes(pcm16.tobytes())

        logger.info(f"[LiveSession {self.session_id}] Exported snapshot WAV: {wav_filename} ({len(pcm16)} samples)")
        return wav_path, file_id


class LiveSessionManager:
    """
    Singleton manager tracking active live audio sessions.
    Thread-safe session registration and automatic cleanup of stale sessions (>60s idle).
    """

    def __init__(self):
        self._sessions: Dict[str, LiveAudioSession] = {}
        self._lock = threading.Lock()

    def get_or_create_session(
        self, session_id: str, sample_rate: int = 48000, channels: int = 1
    ) -> LiveAudioSession:
        with self._lock:
            self._cleanup_stale_sessions()
            if session_id not in self._sessions:
                self._sessions[session_id] = LiveAudioSession(
                    session_id=session_id, sample_rate=sample_rate, channels=channels
                )
                logger.info(f"[LiveSessionManager] Created session: {session_id} ({sample_rate}Hz)")
            else:
                sess = self._sessions[session_id]
                sess.sample_rate = max(8000, min(192000, sample_rate))
                sess.channels = max(1, min(2, channels))
                sess.max_samples = int(sess.sample_rate * sess.max_buffer_seconds)
            return self._sessions[session_id]

    def get_session(self, session_id: str) -> Optional[LiveAudioSession]:
        with self._lock:
            return self._sessions.get(session_id)

    def close_session(self, session_id: str):
        with self._lock:
            if session_id in self._sessions:
                del self._sessions[session_id]
                logger.info(f"[LiveSessionManager] Closed session: {session_id}")

    def _cleanup_stale_sessions(self, max_idle_sec: float = 60.0):
        now = time.time()
        stale = [
            sid
            for sid, sess in self._sessions.items()
            if (now - sess.last_activity) > max_idle_sec
        ]
        for sid in stale:
            del self._sessions[sid]
            logger.info(f"[LiveSessionManager] Cleaned up stale session: {sid}")


# Singleton instance
live_session_manager = LiveSessionManager()
