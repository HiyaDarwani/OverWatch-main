#!/bin/bash
# ============================================================
# OverWatch Real-Time Audio Processor - Single Command Launcher
# ============================================================
# Usage: ./run_realtime.sh [options]
# Options passed through to Python script:
#   --model deepfilternet|fullsubnet|none   (default: none)
#   --sr 16000|48000                        (default: 16000)
#   --chunk 1024                            (default: 1024)
#   --method wiener|spectral_sub|mmse       (default: wiener)
#   --list-devices                          (list audio devices)
# ============================================================

set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$SCRIPT_DIR"

echo
echo "============================================================"
echo "  OVERWATCH REAL-TIME AUDIO PROCESSOR"
echo "============================================================"
echo

# Check if Python is available
if ! command -v python3 &> /dev/null; then
    echo "ERROR: Python 3 not found"
    echo "Please install Python 3.9+ from your package manager"
    exit 1
fi

# Check if virtual environment exists, create if not
if [ ! -d ".venv" ]; then
    echo "Creating virtual environment..."
    python3 -m venv .venv
fi

# Activate virtual environment and install dependencies
echo "Activating environment and installing dependencies..."
source .venv/bin/activate
pip install -q -r requirements.txt

# Run the real-time CLI with all passed arguments
echo
echo "Starting OverWatch Real-Time Processor..."
echo "Press Ctrl+C to stop"
echo "============================================================"
echo

python realtime_cli.py "$@"