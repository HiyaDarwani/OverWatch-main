# DeepFilterNet Environment Setup Script for OverWatch
# This creates a separate Python 3.10 virtual environment for DeepFilterNet.
# The main backend .venv (Python 3.13) is NOT modified.

$ErrorActionPreference = "Stop"

Write-Host ""
Write-Host "============================================" -ForegroundColor Cyan
Write-Host "  OverWatch DeepFilterNet Setup" -ForegroundColor Cyan
Write-Host "============================================" -ForegroundColor Cyan
Write-Host ""

# Step 1: Locate a compatible Python (<= 3.11)
$pythonCmd = $null
$pythonVersion = $null

foreach ($ver in @("3.11", "3.10", "3.9", "3.8")) {
    try {
        $output = & py "-$ver" --version 2>&1
        if ($LASTEXITCODE -eq 0) {
            $pythonCmd = "py -$ver"
            $pythonVersion = $output.ToString().Trim()
            break
        }
    } catch {}
}

if (-not $pythonCmd) {
    Write-Host "ERROR: No compatible Python version found (3.8-3.11)." -ForegroundColor Red
    Write-Host ""
    Write-Host "DeepFilterNet requires Python <= 3.11." -ForegroundColor Yellow
    Write-Host "Your current backend uses Python 3.13 which is NOT compatible." -ForegroundColor Yellow
    Write-Host ""
    Write-Host "Please install Python 3.10 or 3.11 from:" -ForegroundColor Yellow
    Write-Host "  https://www.python.org/downloads/" -ForegroundColor White
    Write-Host ""
    Write-Host "After installing, re-run this script." -ForegroundColor Yellow
    exit 1
}

Write-Host "Found compatible Python: $pythonVersion" -ForegroundColor Green
Write-Host "Using: $pythonCmd" -ForegroundColor DarkGray

# Step 2: Create .venv-dfn
$venvDir = Join-Path $PSScriptRoot ".venv-dfn"

if (Test-Path $venvDir) {
    Write-Host ""
    Write-Host "Existing .venv-dfn found. Removing..." -ForegroundColor Yellow
    Remove-Item -Recurse -Force $venvDir
}

Write-Host ""
Write-Host "Creating virtual environment: .venv-dfn" -ForegroundColor Cyan
$parts = $pythonCmd -split " "
& $parts[0] $parts[1] -m venv $venvDir

if (-not (Test-Path (Join-Path $venvDir "Scripts\python.exe"))) {
    Write-Host "ERROR: Failed to create .venv-dfn" -ForegroundColor Red
    exit 1
}

Write-Host "Virtual environment created successfully." -ForegroundColor Green

# Step 3: Upgrade pip
$dfnPython = Join-Path $venvDir "Scripts\python.exe"

Write-Host ""
Write-Host "Upgrading pip..." -ForegroundColor Cyan
& $dfnPython -m pip install --upgrade pip --quiet

# Step 4: Install PyTorch (CPU only) and TorchAudio (pinned for DeepFilterNet compatibility)
Write-Host ""
Write-Host "Installing PyTorch (CPU) and TorchAudio..." -ForegroundColor Cyan
Write-Host "  (This may take a few minutes - ~170MB download)" -ForegroundColor DarkGray
& $dfnPython -m pip install torch==2.0.1 torchaudio==2.0.2 --index-url https://download.pytorch.org/whl/cpu --quiet

if ($LASTEXITCODE -ne 0) {
    Write-Host "ERROR: Failed to install PyTorch/TorchAudio." -ForegroundColor Red
    exit 1
}
Write-Host "PyTorch installed." -ForegroundColor Green

# Step 5: Install DeepFilterNet
Write-Host ""
Write-Host "Installing DeepFilterNet..." -ForegroundColor Cyan
& $dfnPython -m pip install deepfilternet --quiet

if ($LASTEXITCODE -ne 0) {
    Write-Host "ERROR: Failed to install DeepFilterNet." -ForegroundColor Red
    exit 1
}
Write-Host "DeepFilterNet installed." -ForegroundColor Green

# Step 6: Install numpy (required for worker)
Write-Host ""
Write-Host "Installing numpy..." -ForegroundColor Cyan
& $dfnPython -m pip install numpy --quiet
Write-Host "numpy installed." -ForegroundColor Green

# Step 7: Verify imports
Write-Host ""
Write-Host "Verifying DeepFilterNet installation..." -ForegroundColor Cyan

$verifyScript = @"
import sys
try:
    from df.enhance import init_df, enhance, load_audio, save_audio
    print('IMPORT_OK')
    model, df_state, _ = init_df()
    print(f'MODEL_OK sr={df_state.sr()}')
except Exception as e:
    print(f'IMPORT_FAILED: {e}')
    sys.exit(1)
"@

$result = & $dfnPython -c $verifyScript 2>&1
$resultStr = $result -join "`n"

if ($resultStr -match "IMPORT_OK" -and $resultStr -match "MODEL_OK") {
    Write-Host ""
    Write-Host "============================================" -ForegroundColor Green
    Write-Host "  DeepFilterNet environment ready!" -ForegroundColor Green
    Write-Host "============================================" -ForegroundColor Green
    Write-Host ""
    Write-Host "  Python:       $pythonVersion" -ForegroundColor White
    Write-Host "  Venv:         .venv-dfn" -ForegroundColor White
    Write-Host "  $resultStr" -ForegroundColor White
    Write-Host ""
    Write-Host "  The main backend .venv was NOT modified." -ForegroundColor DarkGray
    Write-Host ""
} else {
    Write-Host "ERROR: DeepFilterNet import verification failed:" -ForegroundColor Red
    Write-Host $resultStr -ForegroundColor Red
    exit 1
}
