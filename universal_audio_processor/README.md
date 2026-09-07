# Universal Audio Processor 🎙️⚡

`universal_audio_processor` is a modular, stateful Python framework designed for real-time and batch digital signal processing (DSP) and machine learning (ML) audio enhancement.

It provides zero-latency-oriented frame buffering, dynamic noise estimation, spectral filtering, multi-runtime neural network inference (PyTorch, ONNX, TFLite), and automated edge hardware optimization.

---

## 📐 Architecture & Modules Overview

```text
universal_audio_processor/
├── config.py                   # Default pipeline configuration & YAML loader
├── core/                       # Stream chunking, ring buffering & hardware adapters
│   ├── audio_buffer.py         # RingBuffer & STFT AudioFrameBuffer
│   ├── chunk_manager.py        # Variable to fixed sample chunk streaming
│   ├── io_factory.py           # I/O creation & auto-detection factory
│   └── universal_interface.py  # FileIO & MicrophoneIO audio streaming adapters
├── dsp/                        # Digital Signal Processing routines
│   ├── spectral.py             # Wiener Filter, Spectral Subtraction, MMSE-STSA
│   └── transforms.py           # Real-time RFFT/iRFFT, STFT, Wavelet Denoising
├── ml/                         # Neural Network Inference & Features
│   ├── feature_extractor.py    # Log-Mel, MFCC, Spectral Centroid, Rolloff, ZCR
│   └── model_wrapper.py        # Universal PyTorch / ONNX / TFLite wrapper & quantization
├── pipelines/                  # Stateful Audio Execution Pipelines
│   ├── pipeline_state.py       # State Machine (INIT -> CALIBRATION -> PROCESSING)
│   ├── production_pipeline.py  # Production pipeline with post-processing & metrics
│   ├── realtime_pipeline.py    # Callback-driven streaming pipeline
│   └── hybrid_pipeline.py      # Combined DSP + Deep Learning pipeline
├── deployment/                 # Model registry & activation management
│   └── model_registry.py       # Thread-safe JSON model registry
└── utils/                      # Utilities & Hardware Profiling
    ├── audio_io.py             # Resampled float32 WAV loading and saving
    ├── latency_profiler.py     # Micro-second stage profiling tool
    └── platform_detector.py    # Auto-detects ARM/RPi4/RPi5, CUDA GPU, MPS & CPU
```

---

## ⚙️ How It Works

### 1. Frame Buffering & Stream Chunking (`core/`)
- **`ChunkManager`**: Converts incoming arbitrary-sized audio stream chunks into fixed sample blocks (`chunk_size=1024`).
- **`AudioFrameBuffer`**: Maintains circular sample history to preserve exact hop overlap (`hop_size=512`, `frame_size=2048`) required for Short-Time Fourier Transform (STFT) signal reconstruction without boundary click artifacts.

### 2. Spectral DSP & Noise Reduction (`dsp/`)
- **`NoiseEstimator`**: Dynamically estimates ambient noise Power Spectral Density (PSD) using initial frame calibration and continuous minimum statistics tracking.
- **`SpectralProcessor`**:
  - **Wiener Filter**: Computes spectral gain based on speech vs. noise PSD estimation.
  - **Spectral Subtraction**: Over-subtraction method with configurable spectral floor ($\alpha$, $\beta$).
  - **MMSE-STSA**: Minimum Mean-Square Error Short-Time Spectral Amplitude estimator.
  - **Wavelet Transform**: Discrete Wavelet Transform (`db4`) detail coefficient soft-thresholding.

### 3. Deep Learning Integration (`ml/`)
- **`UniversalModelWrapper`**: Auto-detects and loads model files (`.pt`, `.onnx`, `.tflite`). Unified `.predict()` interface abstracts away engine-specific input/output tensor conversions.
- **`ModelOptimizer`**: Utilities to convert PyTorch models to ONNX and apply INT8 dynamic quantization for edge deployment.

### 4. Stateful Execution (`pipelines/`)
- **`ProductionAudioPipeline`**: Manages state transitions:
  1. `INIT` $\rightarrow$ `CALIBRATION`: Collects initial background noise profile.
  2. `PROCESSING`: Runs real-time STFT, noise estimation, spectral enhancement, optional ML model pass, high-pass filtering ($80\text{ Hz}$ cutoff), and dynamic range compression.
  3. **Metrics Tracking**: Captures latency statistics (`avg_latency_ms`, `p50`, `p95`, `p99`, `max_latency_ms`).

---

## 🛠️ Configuration Options

Parameters can be loaded from standard dictionary configs or YAML files via `load_config("config.yaml")`:

| Parameter | Type | Default | Description |
| :--- | :--- | :--- | :--- |
| `sample_rate` | int | `16000` | Target audio sample rate (Hz) |
| `n_fft` | int | `512` | FFT window length |
| `hop_length` | int | `256` | STFT hop size |
| `frame_size` | int | `2048` | Analysis frame size |
| `hop_size` | int | `512` | Processing hop step size |
| `chunk_size` | int | `1024` | Input stream chunk block size |
| `spectral_method`| str | `'wiener'` | Enhancement method: `'wiener'`, `'spectral_sub'`, `'mmse'` |
| `alpha` | float | `2.0` | Over-subtraction factor for spectral subtraction |
| `beta` | float | `0.02` | Spectral floor threshold |
| `noise_smoothing`| float| `0.98` | Minimum tracking noise smoothing coefficient |
| `use_ml` | bool | `False` | Enable neural network inference layer |
| `model_path` | str | `None` | File path to `.onnx`, `.pth`, or `.tflite` weights |
| `model_type` | str | `'auto'` | Engine type: `'pytorch'`, `'onnx'`, `'tflite'`, `'auto'` |

---

## 💻 Usage Examples

### Example 1: Enhancing a Audio WAV File

```python
from universal_audio_processor.config import DEFAULT_CONFIG
from universal_audio_processor.pipelines.production_pipeline import ProductionAudioPipeline
from universal_audio_processor.utils.audio_io import load_audio, save_audio

# 1. Load noisy audio file
audio_data, sr = load_audio("input_noisy.wav", sr=16000)

# 2. Configure & initialize pipeline
config = DEFAULT_CONFIG.copy()
config["spectral_method"] = "wiener"
pipeline = ProductionAudioPipeline(config)

# 3. Process complete audio stream
enhanced_audio = pipeline.process_complete_audio(audio_data)

# 4. Save enhanced audio result
save_audio("output_clean.wav", enhanced_audio, sr=16000)

# 5. Output processing latency stats
metrics = pipeline.get_metrics()
print(f"Avg Latency: {metrics['avg_latency_ms']:.2f} ms | P95: {metrics['p95_latency_ms']:.2f} ms")
```

---

### Example 2: Real-time Streaming Processing (Microphone / Callback)

```python
import numpy as np
from universal_audio_processor.config import DEFAULT_CONFIG
from universal_audio_processor.pipelines.realtime_pipeline import RealtimeAudioPipeline

# Define audio chunk callback
def on_audio_ready(enhanced_chunk):
    print(f"Processed audio chunk size: {len(enhanced_chunk)} samples")

# Initialize streaming pipeline
config = DEFAULT_CONFIG.copy()
stream_pipeline = RealtimeAudioPipeline(config, callback=on_audio_ready)

# Simulate incoming hardware stream
raw_mic_chunk = np.random.randn(1024).astype(np.float32)
stream_pipeline.process_chunk(raw_mic_chunk)
```

---

### Example 3: Edge Hardware Auto-Detection & Config Tuning

```python
from universal_audio_processor.utils.platform_detector import PlatformDetector

# Detect current host platform capabilities (RPi, GPU, CPU cores)
platform_info = PlatformDetector.detect()
print("System info:", platform_info)

# Get recommended configuration settings
optimal_config = PlatformDetector.get_optimal_config(platform_info)
print("Recommended config:", optimal_config)
```

---

## 🧪 Testing & Validation

Run unit tests to verify spectral processing, transforms, and pipeline state execution:

```bash
pytest universal_audio_processor/tests/
```
