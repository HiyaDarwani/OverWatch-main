import numpy as np

from dsp.spectral import NoiseEstimator, SpectralProcessor
from dsp.transforms import AudioTransforms


class HybridAudioPipeline:
	"""Combine frame-based DSP enhancement with an optional ML enhancer."""

	def __init__(self, config):
		self.config = config
		self.transforms = AudioTransforms(
			n_fft=config.get('n_fft', 512),
			hop_length=config.get('hop_length', 256),
			window=config.get('window', 'hann'),
		)
		self.spectral = SpectralProcessor(config.get('n_fft', 512))
		self.noise_estimator = NoiseEstimator(
			config.get('n_fft', 512), config.get('noise_smoothing', 0.98)
		)
		self.ml_model = None

		if config.get('use_ml'):
			model_path = config.get('model_path')
			if not model_path:
				raise ValueError("model_path is required when use_ml is enabled")
			from ml.model_wrapper import UniversalModelWrapper
			self.ml_model = UniversalModelWrapper(
				model_path, config.get('model_type', 'auto')
			)

	def process_frame(self, frame):
		"""Enhance one time-domain frame and return one hop of audio."""
		frame = np.asarray(frame, dtype=np.float32).reshape(-1)
		spectrum = self.transforms.stft_realtime(frame)
		noise_psd = self.noise_estimator.update_minima_tracking(spectrum)
		method = self.config.get('spectral_method', 'wiener')

		if method == 'spectral_sub':
			noise_spectrum = np.sqrt(noise_psd).astype(np.complex128)
			enhanced = self.spectral.spectral_subtraction(
				spectrum,
				noise_spectrum,
				self.config.get('alpha', 2.0),
				self.config.get('beta', 0.02),
			)
		elif method == 'mmse':
			enhanced = self.spectral.mmse_stsa(spectrum, noise_psd)
		elif method == 'wiener':
			enhanced = self.spectral.wiener_filter(spectrum, noise_psd)
		else:
			raise ValueError(f"Unsupported spectral_method: {method}")

		return self.transforms.istft_realtime(enhanced)

	def reset(self):
		"""Reset state held between streaming frames."""
		self.noise_estimator.reset()
