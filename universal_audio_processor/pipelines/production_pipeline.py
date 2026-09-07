import logging
import time
from dataclasses import dataclass, field

import numpy as np
from scipy import signal

from core.audio_buffer import AudioFrameBuffer, ChunkManager
from dsp.spectral import NoiseEstimator, SpectralProcessor
from dsp.transforms import AudioTransforms
from pipelines.pipeline_state import StateMachine

logger = logging.getLogger(__name__)


@dataclass
class PipelineMetrics:
    total_frames_processed: int = 0
    total_processing_time: float = 0.0
    latency_samples: list = field(default_factory=list)
    dropped_frames: int = 0
    noise_classification_counts: dict = field(default_factory=dict)

    def add_latency(self, latency_ms):
        self.latency_samples.append(float(latency_ms))
        del self.latency_samples[:-1000]

    def get_stats(self):
        if not self.latency_samples:
            return {
                "avg_latency_ms": 0.0,
                "p50_latency_ms": 0.0,
                "p95_latency_ms": 0.0,
                "p99_latency_ms": 0.0,
                "max_latency_ms": 0.0,
                "total_frames": self.total_frames_processed,
                "dropped_frames": self.dropped_frames,
                "noise_distribution": dict(self.noise_classification_counts),
            }
        values = np.asarray(self.latency_samples)
        return {
            "avg_latency_ms": float(np.mean(values)),
            "p50_latency_ms": float(np.percentile(values, 50)),
            "p95_latency_ms": float(np.percentile(values, 95)),
            "p99_latency_ms": float(np.percentile(values, 99)),
            "max_latency_ms": float(np.max(values)),
            "total_frames": self.total_frames_processed,
            "dropped_frames": self.dropped_frames,
            "noise_distribution": dict(self.noise_classification_counts),
        }


class ProductionAudioPipeline:
    """Stateful DSP pipeline for real-time and batch audio enhancement."""

    def __init__(self, config):
        self.config = dict(config)
        sample_rate = self.config.get("sample_rate", 16000)
        n_fft = self.config.get("n_fft", 512)
        self.state_machine = StateMachine(
            self.config.get("calibration_duration", 0.5), sample_rate
        )
        self.metrics = PipelineMetrics()
        self.transforms = AudioTransforms(
            n_fft=n_fft,
            hop_length=self.config.get("hop_length", 256),
            window=self.config.get("window", "hann"),
        )
        self.spectral_processor = SpectralProcessor(n_fft)
        self.noise_estimator = NoiseEstimator(
            n_fft, self.config.get("noise_smoothing", 0.98)
        )
        self.frame_buffer = AudioFrameBuffer(
            self.config.get("frame_size", 2048),
            self.config.get("hop_size", 512),
        )
        self.chunk_manager = ChunkManager(
            self.config.get("chunk_size", 1024), sample_rate
        )
        self.noise_profile = None
        self.calibration_frames = []
        self.on_state_change = None
        self.on_noise_detected = None
        self.model = None
        self.use_ml = False
        model_path = self.config.get("model_path")
        if model_path:
            from ml.model_wrapper import UniversalModelWrapper
            self.model = UniversalModelWrapper(
                model_path, self.config.get("model_type", "auto")
            )
            self.use_ml = True

    def _transition(self, state):
        previous = self.state_machine.state
        self.state_machine.transition_to(state)
        if self.on_state_change and previous != state:
            self.on_state_change(previous, state)

    def classify_noise(self, spectrum):
        magnitude = np.abs(spectrum)
        geometric = np.exp(np.mean(np.log(magnitude + 1e-10)))
        arithmetic = np.mean(magnitude)
        flatness = geometric / (arithmetic + 1e-10)
        noise_type = "stationary" if flatness > 0.3 else "non_stationary"
        self.metrics.noise_classification_counts[noise_type] = (
            self.metrics.noise_classification_counts.get(noise_type, 0) + 1
        )
        return noise_type

    def _enhance(self, spectrum, noise_psd):
        method = self.config.get("spectral_method", "wiener")
        if method == "wiener":
            return self.spectral_processor.wiener_filter(spectrum, noise_psd)
        if method == "spectral_sub":
            return self.spectral_processor.spectral_subtraction(
                spectrum, np.sqrt(noise_psd), self.config.get("alpha", 2.0),
                self.config.get("beta", 0.02)
            )
        if method == "mmse":
            return self.spectral_processor.mmse_stsa(spectrum, noise_psd)
        raise ValueError(f"Unsupported spectral_method: {method}")

    def _post_process(self, audio):
        sample_rate = self.config.get("sample_rate", 16000)
        if self.config.get("apply_highpass", False):
            cutoff = self.config.get("highpass_cutoff", 80)
            sos = signal.butter(4, cutoff, "highpass", fs=sample_rate, output="sos")
            audio = signal.sosfilt(sos, audio)
        if self.config.get("apply_compression", False):
            threshold = self.config.get("compression_threshold", 0.8)
            ratio = self.config.get("compression_ratio", 4.0)
            magnitude = np.abs(audio)
            audio = np.where(
                magnitude > threshold,
                np.sign(audio) * (threshold + (magnitude - threshold) / ratio),
                audio,
            )
        return np.asarray(audio, dtype=np.float32)

    def process_frame(self, audio_frame):
        audio_frame = np.asarray(audio_frame, dtype=np.float32).reshape(-1)
        start = time.perf_counter()
        try:
            self.state_machine.update(len(audio_frame))
            spectrum = self.transforms.stft_realtime(audio_frame)
            if self.state_machine.is_calibrating():
                self.calibration_frames.append(spectrum)
                result = audio_frame.copy()
            elif self.state_machine.can_process():
                noise_psd = self.noise_estimator.update_minima_tracking(spectrum)
                self.noise_profile = noise_psd
                noise_type = self.classify_noise(spectrum)
                if self.on_noise_detected:
                    self.on_noise_detected(noise_type)
                result = self.transforms.istft_realtime(
                    self._enhance(spectrum, noise_psd)
                )
                result = self._post_process(result)
            else:
                result = audio_frame.copy()
            self.metrics.total_frames_processed += 1
            elapsed = (time.perf_counter() - start) * 1000
            self.metrics.total_processing_time += elapsed
            self.metrics.add_latency(elapsed)
            return result
        except Exception as error:
            self.metrics.dropped_frames += 1
            self.state_machine.handle_error(error)
            return audio_frame.copy()

    def process_stream_chunk(self, audio_chunk):
        outputs = []
        for chunk in self.chunk_manager.process_stream(audio_chunk):
            for frame in self.frame_buffer.write(chunk):
                outputs.append(self.process_frame(frame))
        return outputs

    def process_complete_audio(self, audio):
        audio = np.asarray(audio, dtype=np.float32).reshape(-1)
        self.reset()
        outputs = []
        for start in range(0, len(audio), self.config.get("chunk_size", 1024)):
            outputs.extend(self.process_stream_chunk(audio[start:start + self.config.get("chunk_size", 1024)]))
        remaining = self.frame_buffer.flush()
        if remaining is not None:
            outputs.append(self.process_frame(remaining))
        if not outputs:
            return audio.copy()
        return np.concatenate(outputs)[:len(audio)]

    def get_metrics(self):
        return self.metrics.get_stats()

    def reset(self):
        self.state_machine = StateMachine(
            self.config.get("calibration_duration", 0.5),
            self.config.get("sample_rate", 16000),
        )
        self.metrics = PipelineMetrics()
        self.noise_profile = None
        self.calibration_frames = []
        self.noise_estimator.reset()
        self.frame_buffer.reset()
        self.chunk_manager.reset()
