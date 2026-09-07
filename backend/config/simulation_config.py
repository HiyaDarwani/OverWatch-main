"""
Centralized Strategy & Simulation Configuration for OverWatch Pipeline.
Contains strategy characteristics, simulation latency bounds, complexity levels,
and noise suitability mapping.
"""

STRATEGY_CONFIGS = {
    "WIENER_FILTER": {
        "label": "Wiener Filter",
        "suitable_noises": ["stationary"],
        "base_latency_ms": 8.5,
        "latency_jitter_ms": 2.1,
        "complexity": "low",
        "estimated_enhancement_pct": 68,
        "dsp_weight": 0.85,
        "ai_weight": 0.15,
        "attenuation_db": -12.0,
        "cutoff_freq_hz": 1200
    },
    "SPECTRAL_SUBTRACTION": {
        "label": "Spectral Subtraction",
        "suitable_noises": ["stationary"],
        "base_latency_ms": 6.2,
        "latency_jitter_ms": 1.8,
        "complexity": "low",
        "estimated_enhancement_pct": 60,
        "dsp_weight": 0.90,
        "ai_weight": 0.10,
        "attenuation_db": -10.0,
        "cutoff_freq_hz": 1500
    },
    "LMS_NLMS": {
        "label": "LMS / NLMS Adaptive",
        "suitable_noises": ["non_stationary"],
        "base_latency_ms": 14.2,
        "latency_jitter_ms": 3.4,
        "complexity": "medium",
        "estimated_enhancement_pct": 74,
        "dsp_weight": 0.65,
        "ai_weight": 0.35,
        "attenuation_db": -15.0,
        "cutoff_freq_hz": 2000
    },
    "MMSE_STSA": {
        "label": "MMSE-STSA",
        "suitable_noises": ["non_stationary", "stationary"],
        "base_latency_ms": 18.0,
        "latency_jitter_ms": 4.0,
        "complexity": "medium",
        "estimated_enhancement_pct": 78,
        "dsp_weight": 0.70,
        "ai_weight": 0.30,
        "attenuation_db": -16.0,
        "cutoff_freq_hz": 1800
    },
    "WAVELET_DENOISING": {
        "label": "Wavelet Denoising",
        "suitable_noises": ["impulsive"],
        "base_latency_ms": 22.5,
        "latency_jitter_ms": 5.2,
        "complexity": "high",
        "estimated_enhancement_pct": 82,
        "dsp_weight": 0.50,
        "ai_weight": 0.50,
        "attenuation_db": -18.0,
        "cutoff_freq_hz": 2500
    },
    "HYBRID": {
        "label": "Hybrid DSP + AI Fusion",
        "suitable_noises": ["non_stationary", "impulsive"],
        "base_latency_ms": 25.8,
        "latency_jitter_ms": 6.1,
        "complexity": "high",
        "estimated_enhancement_pct": 88,
        "dsp_weight": 0.45,
        "ai_weight": 0.55,
        "attenuation_db": -22.0,
        "cutoff_freq_hz": 3000
    }
}

PIPELINE_STAGE_ORDER = [
    {"id": "input", "label": "Input"},
    {"id": "preprocessing", "label": "Preprocessing"},
    {"id": "noise-analysis", "label": "Noise Analysis"},
    {"id": "classification", "label": "Classification"},
    {"id": "adaptive-filter", "label": "Adaptive Filter"},
    {"id": "ai-enhancement", "label": "AI Enhancement"},
    {"id": "fusion", "label": "Fusion"},
    {"id": "output", "label": "Output"}
]
