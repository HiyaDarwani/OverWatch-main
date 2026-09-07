# dsp/spectral.py
import numpy as np
from scipy import signal

class SpectralProcessor:
    """Spectral-domain processing operations"""
    
    def __init__(self, n_fft=512):
        self.n_fft = n_fft
        self.freq_bins = n_fft // 2 + 1
    
    def spectral_subtraction(self, noisy_spectrum, noise_spectrum, 
                            alpha=2.0, beta=0.02):
        """
        Power-domain over-subtraction spectral subtraction.
        
        Args:
            noisy_spectrum: Noisy complex spectrum
            noise_spectrum: Noise spectrum (magnitude or complex)
            alpha: Over-subtraction factor (typically 1.0 - 2.5)
            beta: Spectral floor parameter (typically 0.01 - 0.05)
        """
        noisy_mag = np.abs(noisy_spectrum)
        noise_mag = np.abs(noise_spectrum)
        phase = np.angle(noisy_spectrum)
        
        # Operate in power domain (|X|^2)
        noisy_power = noisy_mag ** 2
        noise_power = noise_mag ** 2
        
        # Over-subtraction in power domain
        clean_power = noisy_power - alpha * noise_power
        
        # Apply spectral floor relative to noisy power
        clean_power = np.maximum(clean_power, beta * noisy_power)
        
        # Convert back to magnitude and reconstruct complex spectrum
        clean_mag = np.sqrt(np.maximum(clean_power, 1e-12))
        return clean_mag * np.exp(1j * phase)
    
    def wiener_filter(self, noisy_spectrum, noise_psd, a_priori_snr=None, g_min=0.05):
        """
        Wiener filtering with spectral gain floor to eliminate musical noise.
        
        Args:
            noisy_spectrum: Noisy complex spectrum
            noise_psd: Noise power spectral density (|N|^2)
            a_priori_snr: Optional a priori SNR estimate
            g_min: Minimum spectral gain floor (-26 dB default)
        """
        noisy_psd = np.abs(noisy_spectrum) ** 2
        
        if a_priori_snr is None:
            # Power spectral density estimation
            speech_psd = np.maximum(noisy_psd - noise_psd, 0.0)
            wiener_gain = speech_psd / (speech_psd + noise_psd + 1e-10)
        else:
            # MMSE with a priori SNR
            wiener_gain = a_priori_snr / (1.0 + a_priori_snr)
        
        # Apply gain floor to prevent musical noise
        wiener_gain = np.clip(wiener_gain, g_min, 1.0)
        return wiener_gain * noisy_spectrum
    
    def mmse_stsa(self, noisy_spectrum, noise_psd, a_priori_snr=None):
        """
        MMSE Short-Time Spectral Amplitude estimator
        
        Args:
            noisy_spectrum: Noisy speech spectrum
            noise_psd: Noise PSD
            a_priori_snr: A priori SNR
        """
        from scipy.special import i0, i1
        
        noisy_mag = np.abs(noisy_spectrum)
        phase = np.angle(noisy_spectrum)
        
        # A posteriori SNR
        gamma = noisy_mag ** 2 / (noise_psd + 1e-10)
        
        # A priori SNR (decision-directed)
        if a_priori_snr is None:
            a_priori_snr = np.maximum(gamma - 1, 0)
        
        # MMSE gain
        nu = a_priori_snr * gamma / (1 + a_priori_snr)
        
        # Gain function
        gain = (np.sqrt(np.pi * nu) / (2 * np.maximum(gamma, 1e-10))) * \
               np.exp(-nu / 2) * \
               ((1 + nu) * i0(nu / 2) +
            nu * i1(nu / 2))
        
        # Clamp gain
        gain = np.clip(gain, 0, 1)
        
        clean_mag = gain * noisy_mag
        
        return clean_mag * np.exp(1j * phase)
    
    def power_subtraction(self, noisy_psd, noise_psd, alpha=1.0):
        """Power subtraction"""
        clean_psd = noisy_psd - alpha * noise_psd
        clean_psd = np.maximum(clean_psd, 0.1 * noisy_psd)
        return clean_psd
    
    def spectral_gating(self, spectrum, threshold_db=-40):
        """Spectral gating (noise gate)"""
        magnitude = np.abs(spectrum)
        phase = np.angle(spectrum)
        
        # Convert to dB
        magnitude_db = 20 * np.log10(magnitude + 1e-10)
        
        # Create gate
        gate = (magnitude_db > threshold_db).astype(float)
        
        # Apply gate
        gated_magnitude = magnitude * gate
        
        return gated_magnitude * np.exp(1j * phase)
    
    def harmonic_percussive_separation(self, spectrum, kernel_size=31):
        """
        Separate harmonic and percussive components
        
        Args:
            spectrum: Input spectrum
            kernel_size: Median filter kernel size
        """
        magnitude = np.abs(spectrum)
        phase = np.angle(spectrum)
        
        # Median filtering
        from scipy.ndimage import median_filter
        
        # Harmonic (median along time)
        harmonic_mag = median_filter(magnitude, size=(1, kernel_size))
        
        # Percussive (median along frequency)
        percussive_mag = median_filter(magnitude, size=(kernel_size, 1))
        
        # Soft masking
        mask_harmonic = harmonic_mag / (harmonic_mag + percussive_mag + 1e-10)
        mask_percussive = percussive_mag / (harmonic_mag + percussive_mag + 1e-10)
        
        harmonic_spectrum = mask_harmonic * magnitude * np.exp(1j * phase)
        percussive_spectrum = mask_percussive * magnitude * np.exp(1j * phase)
        
        return harmonic_spectrum, percussive_spectrum


class NoiseEstimator:
    """Noise spectrum estimation with recursive tracking and VAD support"""
    
    def __init__(self, n_fft=512, smoothing_factor=0.98):
        self.n_fft = n_fft
        self.smoothing_factor = smoothing_factor
        self.noise_psd = None
        self.smooth_psd = None
        self.frame_count = 0
    
    def estimate_initial(self, initial_frames):
        """Estimate noise from initial frames (assumed to be noise-only)"""
        if not initial_frames:
            raise ValueError("initial_frames must contain at least one frame")
        noise_sum = np.zeros(self.n_fft // 2 + 1)
        
        for frame_spectrum in initial_frames:
            noise_sum += np.abs(frame_spectrum) ** 2
        
        self.noise_psd = noise_sum / len(initial_frames)
        self.smooth_psd = self.noise_psd.copy()
        return self.noise_psd
    
    def update_vad(self, spectrum, is_speech):
        """
        Update noise estimate using VAD
        
        Args:
            spectrum: Current frame spectrum
            is_speech: Boolean indicating if speech is present
        """
        current_psd = np.abs(spectrum) ** 2
        
        if self.noise_psd is None:
            self.noise_psd = current_psd
            self.smooth_psd = current_psd.copy()
        elif not is_speech:
            # Update only during non-speech
            self.noise_psd = (self.smoothing_factor * self.noise_psd + 
                             (1 - self.smoothing_factor) * current_psd)
        
        return self.noise_psd
    
    def update_minima_tracking(self, spectrum, window_size=100):
        """
        Update noise PSD estimate using smoothed continuous minima tracking.
        Prevents decay-to-zero bugs and avoids speech frame contamination.
        """
        current_psd = np.abs(spectrum) ** 2
        
        if self.noise_psd is None:
            self.noise_psd = current_psd.copy()
            self.smooth_psd = current_psd.copy()
            self.frame_count = 1
            return self.noise_psd
        
        # Smooth frame power
        if self.smooth_psd is None:
            self.smooth_psd = current_psd.copy()
        else:
            self.smooth_psd = 0.85 * self.smooth_psd + 0.15 * current_psd
            
        # Recursive minima tracking:
        # Fast descent when signal power drops (noise floor lowers)
        # Very slow ascent when signal power rises (preserves speech bursts)
        self.noise_psd = np.where(
            self.smooth_psd < self.noise_psd,
            0.80 * self.noise_psd + 0.20 * self.smooth_psd,
            0.995 * self.noise_psd + 0.005 * self.smooth_psd
        )
        
        self.frame_count += 1
        return self.noise_psd
    
    def reset(self):
        """Reset estimator"""
        self.noise_psd = None
        self.smooth_psd = None
        self.frame_count = 0