# config.py
DEFAULT_CONFIG = {
    # Audio parameters
    'sample_rate': 16000,
    'n_fft': 512,
    'hop_length': 256,
    'window': 'hann',
    'frame_size': 2048,
    'hop_size': 512,
    'chunk_size': 1024,
    
    # DSP parameters
    'use_adaptive_filter': True,
    'filter_length': 256,
    'mu': 0.5,  # NLMS step size
    'noise_smoothing': 0.98,
    
    # Spectral processing
    'spectral_method': 'wiener',  # 'wiener', 'spectral_sub', 'mmse'
    'alpha': 2.0,  # Over-subtraction factor
    'beta': 0.02,  # Spectral floor
    
    # ML parameters
    'model_path': None,
    'model_type': 'auto',  # 'pytorch', 'onnx', 'tflite', 'auto'
    'use_ml': False,
    
    # Feature extraction
    'n_mels': 80,
    'n_mfcc': 13,
    
    # Performance
    'num_threads': 4,
    'use_gpu': False,
}


def load_config(config_path=None):
    """Load configuration from file"""
    config = DEFAULT_CONFIG.copy()
    
    if config_path:
        import yaml
        with open(config_path, 'r') as f:
            user_config = yaml.safe_load(f)
            config.update(user_config)
    
    return config