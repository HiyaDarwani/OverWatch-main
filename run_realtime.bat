@echo off
REM ============================================================
REM OverWatch Real-Time Audio Processor - Single Command Launcher
REM ============================================================
REM Usage: run_realtime.bat [options]
REM Options passed through to Python script:
REM   --model deepfilternet|fullsubnet|none   (default: none)
REM   --sr 16000|48000                        (default: 16000)
REM   --chunk 1024                            (default: 1024)
REM   --method wiener|spectral_sub|mmse       (default: wiener)
REM   --list-devices                          (list audio devices)
REM ============================================================

cd /d "%~dp0"

echo.
echo ============================================================
echo   OVERWATCH REAL-TIME AUDIO PROCESSOR
echo ============================================================
echo.

REM Check if Python is available
where python >nul 2>nul
if %errorlevel% neq 0 (
    echo ERROR: Python not found in PATH
    echo Please install Python 3.9+ from https://python.org
    echo Or add it to your system PATH during installation
    pause
    exit /b 1
)

REM Check if virtual environment exists, create if not
if not exist ".venv" (
    echo Creating virtual environment...
    python -m venv .venv
    if %errorlevel% neq 0 (
        echo ERROR: Failed to create virtual environment
        pause
        exit /b 1
    )
)

REM Activate virtual environment and install dependencies
echo Activating environment and installing dependencies...
call .venv\Scripts\activate.bat
pip install -q -r requirements.txt
if %errorlevel% neq 0 (
    echo WARNING: Some dependencies may have failed to install
)

REM Run the real-time CLI with all passed arguments
echo.
echo Starting OverWatch Real-Time Processor...
echo Press Ctrl+C to stop
echo ============================================================
echo.

python realtime_cli.py %*

REM Pause on error so user can see the message
if %errorlevel% neq 0 (
    echo.
    echo Process exited with code %errorlevel%
    pause
)