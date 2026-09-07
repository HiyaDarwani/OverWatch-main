# dsp/transforms.py
import numpy as np
from scipy import signal, fft

try:
    import librosa
except ImportError:
    librosa = None

class AudioTransforms:
    """Audio transform operations (STFT, FFT, etc.)"""
    
    def __init__(self, n_fft=512, hop_length=256, win_length=None, window='hann'):
        if n_fft <= 0 or hop_length <= 0:
            raise ValueError("n_fft and hop_length must be positive")
        self.n_fft = n_fft
        self.hop_length = hop_length
        self.win_length = win_length or n_fft
        if self.win_length <= 0 or self.win_length > n_fft:
            raise ValueError("win_length must be in the range 1..n_fft")
        self.window = window
        
        # Pre-compute window
        if window == 'hann':
            self.window_func = np.hanning(self.win_length)
        elif window == 'hamming':
            self.window_func = np.hamming(self.win_length)
        elif window == 'blackman':
            self.window_func = np.blackman(self.win_length)
        else:
            self.window_func = np.ones(self.win_length)
    
    def stft(self, audio):
        """Short-Time Fourier Transform"""
        if librosa is None:
            raise ImportError("librosa is required for batch STFT")
        return librosa.stft(
            audio,
            n_fft=self.n_fft,
            hop_length=self.hop_length,
            win_length=self.win_length,
            window=self.window
        )
    
    def istft(self, stft_matrix):
        """Inverse STFT"""
        if librosa is None:
            raise ImportError("librosa is required for batch inverse STFT")
        return librosa.istft(
            stft_matrix,
            hop_length=self.hop_length,
            win_length=self.win_length,
            window=self.window
        )
    
    def stft_realtime(self, frame):
        """STFT for single frame (real-time)"""
        frame = np.asarray(frame, dtype=np.float32).reshape(-1)
        windowed = frame[:self.win_length]
        if len(windowed) < self.win_length:
            windowed = np.pad(windowed, (0, self.win_length - len(windowed)))
        windowed = windowed * self.window_func
        
        # Zero-pad if needed
        if len(windowed) < self.n_fft:
            windowed = np.pad(windowed, (0, self.n_fft - len(windowed)))
        
        # FFT
        spectrum = fft.rfft(windowed, n=self.n_fft)
        
        return spectrum
    
    def istft_realtime(self, spectrum, prev_frame=None):
        """Inverse STFT for single frame with overlap-add"""
        # IFFT
        time_domain = fft.irfft(spectrum, n=self.n_fft)
        
        # Apply window
        time_domain = time_domain[:self.win_length] * self.window_func
        
        # Overlap-add if previous frame exists
        if prev_frame is not None and self.win_length > self.hop_length:
            overlap_size = self.win_length - self.hop_length
            previous = np.asarray(prev_frame).reshape(-1)
            time_domain[:overlap_size] += previous[-overlap_size:]
        
        # Return hop_length samples
        return time_domain[:self.hop_length]
    
    def magnitude_phase(self, stft_matrix):
        """Extract magnitude and phase"""
        magnitude = np.abs(stft_matrix)
        phase = np.angle(stft_matrix)
        return magnitude, phase
    
    def reconstruct_from_mag_phase(self, magnitude, phase):
        """Reconstruct complex STFT from magnitude and phase"""
        return magnitude * np.exp(1j * phase)
    
    def mel_spectrogram(self, audio, sr=16000, n_mels=80):
        """Compute mel spectrogram"""
        if librosa is None:
            raise ImportError("librosa is required for mel spectrograms")
        return librosa.feature.melspectrogram(
            y=audio,
            sr=sr,
            n_fft=self.n_fft,
            hop_length=self.hop_length,
            n_mels=n_mels
        )
    
    def mfcc(self, audio, sr=16000, n_mfcc=13):
        """Compute MFCCs"""
        if librosa is None:
            raise ImportError("librosa is required for MFCCs")
        return librosa.feature.mfcc(
            y=audio,
            sr=sr,
            n_fft=self.n_fft,
            hop_length=self.hop_length,
            n_mfcc=n_mfcc
        )


class WaveletTransform:
    """Wavelet transform for multi-resolution analysis"""
    
    def __init__(self, wavelet='db4', level=4):
        self.wavelet = wavelet
        self.level = level
    
    def decompose(self, signal):
        """Wavelet decomposition"""
        import pywt
        coeffs = pywt.wavedec(signal, self.wavelet, level=self.level)
        return coeffs
    
    def reconstruct(self, coeffs):
        """Wavelet reconstruction"""
        import pywt
        return pywt.waverec(coeffs, self.wavelet)
    
    def denoise(self, signal, threshold_scale=1.0):
        """Wavelet denoising"""
        import pywt
        
        # Decompose
        coeffs = self.decompose(signal)
        
        # Threshold detail coefficients
        threshold = threshold_scale * np.median(np.abs(coeffs[-1])) / 0.6745
        
        coeffs_thresh = [coeffs[0]]  # Keep approximation
        for detail in coeffs[1:]:
            coeffs_thresh.append(pywt.threshold(detail, threshold, mode='soft'))
        
        # Reconstruct
        return self.reconstruct(coeffs_thresh)