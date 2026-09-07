# ml/feature_extractor.py
import numpy as np

try:
    import librosa
except ImportError:
    librosa = None

class FeatureExtractor:
    """Extract features for ML models"""

    @staticmethod
    def _require_librosa():
        if librosa is None:
            raise ImportError("librosa is required for feature extraction")
    
    def __init__(self, sr=16000, n_fft=512, hop_length=256, n_mels=80):
        self.sr = sr
        self.n_fft = n_fft
        self.hop_length = hop_length
        self.n_mels = n_mels
    
    def extract_magnitude_spectrum(self, audio):
        """Extract magnitude spectrum"""
        self._require_librosa()
        stft = librosa.stft(audio, n_fft=self.n_fft, hop_length=self.hop_length)
        magnitude = np.abs(stft)
        return magnitude
    
    def extract_log_magnitude(self, audio, eps=1e-10):
        """Extract log magnitude spectrum"""
        magnitude = self.extract_magnitude_spectrum(audio)
        log_magnitude = np.log(magnitude + eps)
        return log_magnitude
    
    def extract_mel_spectrogram(self, audio):
        """Extract mel spectrogram"""
        self._require_librosa()
        mel_spec = librosa.feature.melspectrogram(
            y=audio,
            sr=self.sr,
            n_fft=self.n_fft,
            hop_length=self.hop_length,
            n_mels=self.n_mels
        )
        return mel_spec
    
    def extract_log_mel_spectrogram(self, audio, eps=1e-10):
        """Extract log mel spectrogram"""
        mel_spec = self.extract_mel_spectrogram(audio)
        log_mel_spec = np.log(mel_spec + eps)
        return log_mel_spec
    
    def extract_mfcc(self, audio, n_mfcc=13):
        """Extract MFCCs"""
        self._require_librosa()
        mfcc = librosa.feature.mfcc(
            y=audio,
            sr=self.sr,
            n_fft=self.n_fft,
            hop_length=self.hop_length,
            n_mfcc=n_mfcc
        )
        return mfcc
    
    def extract_spectral_features(self, audio):
        """Extract comprehensive spectral features"""
        self._require_librosa()
        # Spectral centroid
        centroid = librosa.feature.spectral_centroid(
            y=audio, sr=self.sr, n_fft=self.n_fft, hop_length=self.hop_length
        )
        
        # Spectral rolloff
        rolloff = librosa.feature.spectral_rolloff(
            y=audio, sr=self.sr, n_fft=self.n_fft, hop_length=self.hop_length
        )
        
        # Zero crossing rate
        zcr = librosa.feature.zero_crossing_rate(
            audio, frame_length=self.n_fft, hop_length=self.hop_length
        )
        
        # Spectral flatness
        flatness = librosa.feature.spectral_flatness(
            y=audio, n_fft=self.n_fft, hop_length=self.hop_length
        )
        
        return {
            'centroid': centroid,
            'rolloff': rolloff,
            'zcr': zcr,
            'flatness': flatness
        }
    
    def normalize_features(self, features, mean=None, std=None):
        """Normalize features (z-score)"""
        if mean is None:
            mean = np.mean(features, axis=-1, keepdims=True)
        if std is None:
            std = np.std(features, axis=-1, keepdims=True)
        
        normalized = (features - mean) / (std + 1e-10)
        
        return normalized, mean, std