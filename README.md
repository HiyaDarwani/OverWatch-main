# OverWatch 🎯

**OverWatch** is an enterprise-grade, high-performance real-time audio processing and telemetry system. It combines modular Digital Signal Processing (DSP), flexible Machine Learning (ML) inference acceleration, and a web-based monitoring dashboard for streaming audio enhancement, noise reduction, and signal profiling.

For loading data and for data purposes loading modifying creating dataset all such stuff to be used hdf5 file format to compress all data into one file.
---

## 🏛️ Project Architecture

```text
OverWatch/
├── universal_audio_processor/   # Python DSP & ML core engine
│   ├── core/                   # Audio buffering, frame & I/O management
│   ├── dsp/                    # Spectral transforms, noise estimation, filtering
│   ├── ml/                     # Model inference wrappers (PyTorch, ONNX, TFLite)
│   ├── pipelines/              # Stateful production, real-time & hybrid pipelines
│   ├── deployment/             # Model registry & activation management
│   └── utils/                  # Hardware auto-detection, profiling & WAV I/O
└── Dashboard/                  # Full-stack monitoring dashboard
|_ Visuals/
```

### Key Modules

1. **`universal_audio_processor/`**:
   - High-throughput, frame-based and chunk-based streaming pipeline.
   - Dual-engine approach: Classical STFT/spectral DSP paired with deep learning model support (ONNX Runtime, PyTorch, TFLite).
   - Dynamic platform detection optimizing thread counts and engine selection for hardware ranging from Raspberry Pi 4/5 to CUDA/MPS GPUs.

2. **`Dashboard/`**:
   - `frontend/`: Web interface designed for live spectrum/waveform display, latency histograms, and configuration tweaking.
   - `backend/`: REST/WebSocket service interfacing live telemetry with client dashboards.

---

## ✨ Features

- ⚡ **Low-Latency Streaming**: Real-time STFT with circular frame buffering and overlap-add reconstruction.
- 🎛️ **Advanced DSP Algorithms**: Wiener Filtering, Spectral Subtraction, MMSE-STSA, Wavelet Denoising, and Noise Minima Tracking.
- 🤖 **Universal ML Inference**: Unified model wrapper for PyTorch (`.pt`/`.pth`), ONNX (`.onnx`), and TFLite (`.tflite`) runtime engines.
- 🖥️ **Hardware Adaptation**: Automatic detection of Raspberry Pi (RPi4/RPi5), CUDA GPUs, and Apple Silicon MPS.
- 📊 **Telemetry & Metrics**: Sub-millisecond stage-by-stage latency profiling (`p50`, `p95`, `p99`, max latency) and frame tracking.

---

## 🚀 Getting Started

### 1. Prerequisites

- Python 3.9+
- Node.js 18+ (for Dashboard frontend/backend)
- Virtual Environment (recommended)

### 2. Environment Setup

```bash
# Clone the repository
git clone https://github.com/your-username/OverWatch.git
cd OverWatch

# Create and activate main backend environment
cd backend
python -m venv .venv
# Windows:
.venv\Scripts\activate
# Linux/macOS:
source .venv/bin/activate

# Install main backend dependencies
pip install -r requirements.txt
```

### 3. Speech Enhancement Engine Setup

OverWatch supports two neural speech enhancement engines operating in isolated Python virtual environments:

#### DeepFilterNet3 (48 kHz Default Engine)
```powershell
# Run the automated setup script from the backend directory:
powershell -ExecutionPolicy Bypass -File backend/setup_deepfilter.ps1
```
This script creates `backend/.venv-dfn` (Python 3.10/3.11) with PyTorch CPU wheels and downloads pretrained DeepFilterNet3 weights automatically upon initial run.

#### FullSubNet+ (16 kHz Secondary Engine)
FullSubNet+ is an external research dependency. The setup script automatically clones the official repository as a sibling directory (`../FullSubNet-plus`), creates a dedicated `.venv-fsn` environment, installs dependencies, and verifies the pretrained checkpoint:
```powershell
# Run the automated setup script from the backend directory:
powershell -ExecutionPolicy Bypass -File backend/setup_fullsubnet.ps1
```

*Note on Checkpoint (`best_model.tar`)*:
If the automated Google Drive download is blocked or rate-limited, download `best_model.tar` manually from the [official repository checkpoint link](https://drive.google.com/file/d/1UJSt1G0P_aXry-u79LLU_l9tCnNa2u7C/view) and place it into `FullSubNet-plus/checkpoints/best_model.tar`. OverWatch will automatically discover it.

### 4. Running OverWatch (Dashboard Mode)

```bash
# Start FastAPI backend (Port 8000)
cd backend
python -m uvicorn main:app --port 8000

# In a separate terminal, start Next.js dashboard (Port 3000)
npm run dev
```

---

## ⚡ Real-Time CLI Mode (Single Command)

**New!** Run the entire OverWatch pipeline in one command — captures microphone, processes audio in real-time, plays enhanced output to speakers, and prints live telemetry.

### Windows (One-Command Launch)
```cmd
run_realtime.bat
```

### Linux/macOS (One-Command Launch)
```bash
./run_realtime.sh
```

### Manual Python Launch
```bash
# Classical DSP only (Wiener Filter) - no models needed
python realtime_cli.py

# With DeepFilterNet3 (48kHz) - requires model download
python realtime_cli.py --model deepfilternet --sr 48000

# With FullSubNet+ (16kHz) - requires model download
python realtime_cli.py --model fullsubnet --sr 16000

# Spectral subtraction method
python realtime_cli.py --method spectral_sub

# List audio devices
python realtime_cli.py --list-devices
```

### Real-Time CLI Options

| Option | Values | Default | Description |
|--------|--------|---------|-------------|
| `--model` | `none`, `deepfilternet`, `fullsubnet` | `none` | Enhancement model |
| `--sr` | `16000`, `48000` | `16000` | Sample rate (Hz) |
| `--chunk` | integer | `1024` | Chunk size (samples) |
| `--method` | `wiener`, `spectral_sub`, `mmse` | `wiener` | Classical DSP method |
| `--list-devices` | flag | - | List audio devices |

### What It Does

1. **🎙️ Captures** microphone input in real-time chunks
2. **⚡ Processes** through DSP pipeline (Wiener/Spectral Sub/MMSE) + optional ML model
3. **🔊 Outputs** enhanced audio to speakers/headphones with near-zero latency
4. **📊 Prints** live telemetry: latency, chunks processed, stage timings
5. **⏹️** Press `Ctrl+C` to stop and see session summary

### Model Setup for ML Enhancement

```powershell
# For DeepFilterNet3 (run from backend folder)
powershell -ExecutionPolicy Bypass -File setup_deepfilter.ps1

# For FullSubNet+ (run from backend folder)
powershell -ExecutionPolicy Bypass -File setup_fullsubnet.ps1
```

Models will be downloaded to `models/` directory. The CLI auto-discovers them.

---

## 🔒 Security & Sensitivity

This project includes a strict `.gitignore` configuration excluding:
- Sensitive credentials (`.env*`, `*.pem`, `*.key`)
- Build outputs, virtual environments, and `__pycache__` directories
- Binary ML model weights (`*.onnx`, `*.pth`, `*.tflite`)

Always verify secrets are kept out of source control by copying `.env.example` to `.env` for local configuration.

---

## 📄 License

Distributed under the MIT License. See `LICENSE` for more information.
