# FullSubNet+ Environment & Repository Setup Script for OverWatch
# Sets up the external FullSubNet+ repository and its dedicated .venv-fsn virtual environment.
# DeepFilterNet (.venv-dfn) and the main backend (.venv) are NOT modified.

$ErrorActionPreference = "Stop"

Write-Host ""
Write-Host "============================================" -ForegroundColor Cyan
Write-Host "  OverWatch FullSubNet+ Setup" -ForegroundColor Cyan
Write-Host "============================================" -ForegroundColor Cyan
Write-Host ""

# ---------------------------------------------------------------------------
# Step 1: Locate a compatible Python version (Python 3.8 - 3.11)
# ---------------------------------------------------------------------------
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
    # Check default python on PATH
    try {
        $output = & python --version 2>&1
        if ($LASTEXITCODE -eq 0 -and $output -match "Python 3\.(8|9|10|11)\.") {
            $pythonCmd = "python"
            $pythonVersion = $output.ToString().Trim()
        }
    } catch {}
}

if (-not $pythonCmd) {
    Write-Host "ERROR: No compatible Python version found (3.8-3.11)." -ForegroundColor Red
    Write-Host ""
    Write-Host "FullSubNet+ (PyTorch 2.1) requires Python <= 3.11." -ForegroundColor Yellow
    Write-Host "Please install Python 3.10 or 3.11 from:" -ForegroundColor Yellow
    Write-Host "  https://www.python.org/downloads/" -ForegroundColor White
    Write-Host ""
    Write-Host "After installing, re-run this script." -ForegroundColor Yellow
    exit 1
}

Write-Host "Found compatible Python: $pythonVersion" -ForegroundColor Green
Write-Host "Using launcher: $pythonCmd" -ForegroundColor DarkGray

# ---------------------------------------------------------------------------
# Step 2: Locate or Clone FullSubNet-plus Repository
# ---------------------------------------------------------------------------
# Target default location: sibling directory ../FullSubNet-plus
$overwatchRoot = (Get-Item $PSScriptRoot).Parent.FullName
$defaultRepoPath = Join-Path (Split-Path $overwatchRoot -Parent) "FullSubNet-plus"

# Check environment override
if ($env:FULLSUBNET_PATH -and (Test-Path $env:FULLSUBNET_PATH)) {
    $fsnRepo = (Resolve-Path $env:FULLSUBNET_PATH).Path
    Write-Host "Using FULLSUBNET_PATH override: $fsnRepo" -ForegroundColor Green
} elseif (Test-Path $defaultRepoPath) {
    $fsnRepo = (Resolve-Path $defaultRepoPath).Path
    Write-Host "Found existing FullSubNet+ repository at: $fsnRepo" -ForegroundColor Green
} else {
    Write-Host ""
    Write-Host "Cloning official FullSubNet+ repository to sibling directory..." -ForegroundColor Cyan
    Write-Host "  Target: $defaultRepoPath" -ForegroundColor DarkGray
    git clone https://github.com/RookieJunChen/FullSubNet-plus.git $defaultRepoPath
    if ($LASTEXITCODE -ne 0) {
        Write-Host "ERROR: Failed to clone FullSubNet-plus repository." -ForegroundColor Red
        Write-Host "Check your internet connection and git installation." -ForegroundColor Yellow
        exit 1
    }
    $fsnRepo = (Resolve-Path $defaultRepoPath).Path
    Write-Host "Cloned FullSubNet+ successfully." -ForegroundColor Green
}

# ---------------------------------------------------------------------------
# Step 3: Create .venv-fsn Virtual Environment
# ---------------------------------------------------------------------------
$venvDir = Join-Path $fsnRepo ".venv-fsn"
$fsnPython = Join-Path $venvDir "Scripts\python.exe"

if (-not (Test-Path $fsnPython)) {
    Write-Host ""
    Write-Host "Creating virtual environment: $venvDir" -ForegroundColor Cyan
    $parts = $pythonCmd -split " "
    if ($parts.Length -gt 1) {
        & $parts[0] $parts[1] -m venv $venvDir
    } else {
        & $parts[0] -m venv $venvDir
    }

    if (-not (Test-Path $fsnPython)) {
        Write-Host "ERROR: Failed to create virtual environment at $venvDir" -ForegroundColor Red
        exit 1
    }
    Write-Host "Virtual environment created successfully." -ForegroundColor Green
} else {
    Write-Host "Existing .venv-fsn found: $venvDir" -ForegroundColor Green
}

# ---------------------------------------------------------------------------
# Step 4: Upgrade pip and install exact dependencies
# ---------------------------------------------------------------------------
Write-Host ""
Write-Host "Configuring Python dependencies in .venv-fsn..." -ForegroundColor Cyan
& $fsnPython -m pip install --upgrade pip --quiet

Write-Host "Installing PyTorch 2.1 (CPU) and TorchAudio..." -ForegroundColor Cyan
& $fsnPython -m pip install torch==2.1.2 torchaudio==2.1.2 --index-url https://download.pytorch.org/whl/cpu --quiet
if ($LASTEXITCODE -ne 0) {
    Write-Host "ERROR: Failed to install PyTorch/TorchAudio." -ForegroundColor Red
    exit 1
}

Write-Host "Installing audio processing dependencies (librosa, soundfile, toml)..." -ForegroundColor Cyan
& $fsnPython -m pip install numpy==1.26.4 librosa==0.10.2 soundfile toml colorful --quiet
if ($LASTEXITCODE -ne 0) {
    Write-Host "ERROR: Failed to install FullSubNet+ dependencies." -ForegroundColor Red
    exit 1
}
Write-Host "Dependencies installed successfully." -ForegroundColor Green

# ---------------------------------------------------------------------------
# Step 5: Check and obtain Checkpoint (best_model.tar)
# ---------------------------------------------------------------------------
$checkpointsDir = Join-Path $fsnRepo "checkpoints"
if (-not (Test-Path $checkpointsDir)) {
    New-Item -ItemType Directory -Path $checkpointsDir | Out-Null
}

$checkpointFile = Join-Path $checkpointsDir "best_model.tar"

if (Test-Path $checkpointFile) {
    $sizeMb = [math]::Round((Get-Item $checkpointFile).Length / 1MB, 1)
    Write-Host "Checkpoint found: best_model.tar ($sizeMb MB)" -ForegroundColor Green
} else {
    Write-Host ""
    Write-Host "Checkpoint 'best_model.tar' not found in: $checkpointsDir" -ForegroundColor Yellow
    Write-Host "Attempting automated download from official repository source (~105MB)..." -ForegroundColor Cyan

    $downloadSuccess = $false
    # Direct Google Drive confirmation endpoint for best_model.tar (ID: 1UJSt1G0P_aXry-u79LLU_l9tCnNa2u7C)
    $gdriveId = "1UJSt1G0P_aXry-u79LLU_l9tCnNa2u7C"
    $downloadScript = @"
import urllib.request
import sys

url = 'https://drive.usercontent.google.com/download?id=$gdriveId&export=download&confirm=t'
dest = r'$checkpointFile'
print('Downloading checkpoint...')
try:
    urllib.request.urlretrieve(url, dest)
    import os
    if os.path.exists(dest) and os.path.getsize(dest) > 10_000_000:
        print('DOWNLOAD_OK')
        sys.exit(0)
    else:
        print('DOWNLOAD_INCOMPLETE')
        sys.exit(1)
except Exception as e:
    print(f'DOWNLOAD_ERROR: {e}')
    sys.exit(1)
"@

    $dlResult = & $fsnPython -c $downloadScript 2>&1
    if ($dlResult -match "DOWNLOAD_OK") {
        Write-Host "Checkpoint downloaded successfully!" -ForegroundColor Green
        $downloadSuccess = $true
    } else {
        # Clean up partial / HTML download if failed
        if (Test-Path $checkpointFile) {
            Remove-Item -Force $checkpointFile -ErrorAction SilentlyContinue
        }
        Write-Host ""
        Write-Host "------------------------------------------------------------" -ForegroundColor Yellow
        Write-Host "MANUAL CHECKPOINT DOWNLOAD REQUIRED:" -ForegroundColor Yellow
        Write-Host "------------------------------------------------------------" -ForegroundColor Yellow
        Write-Host "Google Drive automated download was rate-limited or blocked." -ForegroundColor White
        Write-Host "Please download the pretrained checkpoint manually from:" -ForegroundColor White
        Write-Host "  https://drive.google.com/file/d/1UJSt1G0P_aXry-u79LLU_l9tCnNa2u7C/view" -ForegroundColor Cyan
        Write-Host ""
        Write-Host "And save it as:" -ForegroundColor White
        Write-Host "  $checkpointFile" -ForegroundColor Yellow
        Write-Host "------------------------------------------------------------" -ForegroundColor Yellow
        Write-Host ""
    }
}

# ---------------------------------------------------------------------------
# Step 6: Verification Test (Model Import & Inference Check)
# ---------------------------------------------------------------------------
Write-Host ""
Write-Host "Verifying FullSubNet+ installation..." -ForegroundColor Cyan

$verifyScript = @"
import sys
import os

fsn_repo = r'$fsnRepo'
speech_enhance = os.path.join(fsn_repo, 'speech_enhance')
checkpoint_path = r'$checkpointFile'

for p in [speech_enhance, fsn_repo]:
    if p not in sys.path:
        sys.path.insert(0, p)

try:
    import torch
    from fullsubnet_plus.model.fullsubnet_plus import FullSubNet_Plus
    from audio_zen.acoustics.feature import stft, istft
    from audio_zen.acoustics.mask import decompress_cIRM
    print('IMPORT_OK')

    if os.path.isfile(checkpoint_path):
        ckpt = torch.load(checkpoint_path, map_location='cpu', weights_only=False)
        print(f'CHECKPOINT_OK epoch={ckpt.get(\"epoch\", \"?\")}')
        
        # Lightweight forward pass verification
        model_args = dict(
            num_freqs=257, look_ahead=2, sequence_model='LSTM',
            fb_num_neighbors=0, sb_num_neighbors=15,
            fb_output_activate_function='ReLU', sb_output_activate_function=False,
            fb_model_hidden_size=512, sb_model_hidden_size=384,
            channel_attention_model='TSSE', norm_type='offline_laplace_norm',
            num_groups_in_drop_band=2, kersize=[3, 5, 10],
            subband_num=1, weight_init=False
        )
        model = FullSubNet_Plus(**model_args)
        model.load_state_dict(ckpt['model'])
        model.eval()
        dummy_in = torch.randn(1, 1, 257, 10)
        with torch.no_grad():
            out = model(dummy_in, dummy_in, dummy_in)
        print('INFERENCE_OK')
    else:
        print('CHECKPOINT_PENDING')
except Exception as e:
    import traceback
    print(f'VERIFICATION_FAILED: {e}\n{traceback.format_exc()}')
    sys.exit(1)
"@

$vResult = & $fsnPython -c $verifyScript 2>&1
$vResultStr = $vResult -join "`n"

if ($vResultStr -match "IMPORT_OK" -and $vResultStr -match "CHECKPOINT_OK" -and $vResultStr -match "INFERENCE_OK") {
    Write-Host ""
    Write-Host "============================================" -ForegroundColor Green
    Write-Host "  FullSubNet+ environment ready!" -ForegroundColor Green
    Write-Host "============================================" -ForegroundColor Green
    Write-Host ""
    Write-Host "  Repository:   $fsnRepo" -ForegroundColor White
    Write-Host "  Python:       $pythonVersion" -ForegroundColor White
    Write-Host "  Venv:         $venvDir" -ForegroundColor White
    Write-Host "  Checkpoint:   $checkpointFile" -ForegroundColor White
    Write-Host "  Status:       Verification passed (100% operational)" -ForegroundColor Green
    Write-Host ""
} elseif ($vResultStr -match "IMPORT_OK" -and $vResultStr -match "CHECKPOINT_PENDING") {
    Write-Host ""
    Write-Host "============================================" -ForegroundColor Yellow
    Write-Host "  FullSubNet+ setup almost complete!" -ForegroundColor Yellow
    Write-Host "============================================" -ForegroundColor Yellow
    Write-Host ""
    Write-Host "  Modules and virtual environment are verified." -ForegroundColor Green
    Write-Host "  Please place 'best_model.tar' into:" -ForegroundColor Yellow
    Write-Host "    $checkpointFile" -ForegroundColor White
    Write-Host "  Then re-run this script to verify inference." -ForegroundColor White
    Write-Host ""
} else {
    Write-Host "ERROR: FullSubNet+ verification failed:" -ForegroundColor Red
    Write-Host $vResultStr -ForegroundColor Red
    exit 1
}
