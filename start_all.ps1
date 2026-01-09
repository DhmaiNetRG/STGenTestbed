# ============================================================================
# STGen Complete System Startup Script for Windows (PowerShell)
# Starts Web UI (Frontend + Backend) + CLI ready
# ============================================================================
# Run with: powershell -ExecutionPolicy Bypass -File start_all.ps1

param(
    [switch]$Admin = $false
)

$ErrorActionPreference = "Stop"

$ProjectRoot = Split-Path -Parent $MyInvocation.MyCommand.Path
$Venv = "$ProjectRoot\myenv"
$Python = "$Venv\Scripts\python.exe"
$LogsDir = "$ProjectRoot\logs"

Write-Host ""
Write-Host "============================================================================" -ForegroundColor Cyan
Write-Host "          STGen Complete System Startup (Web + CLI) - Windows" -ForegroundColor Cyan
Write-Host "============================================================================" -ForegroundColor Cyan
Write-Host ""

# Create logs directory
if (-not (Test-Path $LogsDir)) {
    New-Item -ItemType Directory -Path $LogsDir -Force | Out-Null
}

# Check if Python is installed
try {
    $pythonVersion = & python --version 2>&1
    Write-Host "[+] Found Python: $pythonVersion" -ForegroundColor Green
}
catch {
    Write-Host "[ERROR] Python is not installed or not in PATH" -ForegroundColor Red
    Write-Host "[*] Please install Python 3.12+ from https://www.python.org/downloads/" -ForegroundColor Yellow
    Write-Host "[*] Make sure to check 'Add Python to PATH' during installation" -ForegroundColor Yellow
    Read-Host "Press Enter to exit"
    exit 1
}

# Check if virtual environment exists
if (-not (Test-Path $Venv)) {
    Write-Host "[*] Virtual environment not found. Creating..." -ForegroundColor Yellow
    & python -m venv "$Venv"
}

# Activate virtual environment
Write-Host "[+] Activating virtual environment..." -ForegroundColor Green
& "$Venv\Scripts\Activate.ps1"

# Install/update dependencies
Write-Host "[+] Ensuring dependencies are installed..." -ForegroundColor Green
& $Python -m pip install -q --upgrade pip
& $Python -m pip install -q -r "$ProjectRoot\requirements.txt"

# Start Backend API (FastAPI)
Write-Host "[+] Starting Backend API (FastAPI) on port 8000..." -ForegroundColor Green
$BackendJob = Start-Process -FilePath $Python `
    -ArgumentList "-m uvicorn app:app --host 0.0.0.0 --port 8000 --reload" `
    -WorkingDirectory "$ProjectRoot\stgen-ui\backend" `
    -PassThru `
    -NoNewWindow `
    -RedirectStandardOutput "$LogsDir\backend.log" `
    -RedirectStandardError "$LogsDir\backend_error.log"

Start-Sleep -Seconds 3

# Start Frontend (React)
Write-Host "[+] Starting Frontend (React) on port 3000..." -ForegroundColor Green

# Check if node_modules exists
$FrontendPath = "$ProjectRoot\stgen-ui\frontend"
if (-not (Test-Path "$FrontendPath\node_modules")) {
    Write-Host "[*] Installing npm dependencies..." -ForegroundColor Yellow
    Set-Location $FrontendPath
    & npm install -q
}

$FrontendJob = Start-Process -FilePath "cmd.exe" `
    -ArgumentList "/c npm start" `
    -WorkingDirectory $FrontendPath `
    -PassThru `
    -RedirectStandardOutput "$LogsDir\frontend.log" `
    -RedirectStandardError "$LogsDir\frontend_error.log"

Start-Sleep -Seconds 5

Write-Host ""
Write-Host "============================================================================" -ForegroundColor Green
Write-Host "                       ✓ SYSTEM READY" -ForegroundColor Green
Write-Host "============================================================================" -ForegroundColor Green
Write-Host ""
Write-Host "[*] Web Dashboard:" -ForegroundColor Cyan
Write-Host "     - Frontend: http://localhost:3000" -ForegroundColor White
Write-Host "     - Backend API: http://localhost:8000" -ForegroundColor White
Write-Host "     - API Docs: http://localhost:8000/docs" -ForegroundColor White
Write-Host ""
Write-Host "[*] Running Processes:" -ForegroundColor Cyan
Write-Host "     - Backend (PID $($BackendJob.Id))" -ForegroundColor White
Write-Host "     - Frontend (PID $($FrontendJob.Id))" -ForegroundColor White
Write-Host ""
Write-Host "[*] Open browser: http://localhost:3000" -ForegroundColor Yellow
Write-Host ""
Write-Host "[*] To stop everything:" -ForegroundColor Yellow
Write-Host "     - Press Ctrl+C or close this window" -ForegroundColor White
Write-Host "     - Or run: .\stop_all.ps1" -ForegroundColor White
Write-Host ""

Write-Host "Press Ctrl+C to stop all services..." -ForegroundColor Yellow

# Wait for jobs to complete
Wait-Job -Job $BackendJob, $FrontendJob

Write-Host ""
Write-Host "Services stopped." -ForegroundColor Green
