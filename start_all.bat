@echo off
REM ============================================================================
REM STGen Complete System Startup Script for Windows
REM Starts Web UI (Frontend + Backend) + CLI ready
REM ============================================================================

setlocal enabledelayedexpansion

set PROJECT_ROOT=%~dp0
set VENV=%PROJECT_ROOT%myenv
set PYTHON=%VENV%\Scripts\python.exe
set LOGS_DIR=%PROJECT_ROOT%logs

REM Colors (Windows 10+ supports ANSI)
for /F %%A in ('echo prompt $H ^| cmd') do set "BS=%%A"

echo.
echo ============================================================================
echo          STGen Complete System Startup (Web + CLI) - Windows
echo ============================================================================
echo.

REM Create logs directory
if not exist "%LOGS_DIR%" mkdir "%LOGS_DIR%"

REM Check if virtual environment exists
if not exist "%VENV%" (
    echo [*] Virtual environment not found. Creating...
    python -m venv "%VENV%"
)

REM Activate virtual environment
echo [+] Activating virtual environment...
call "%VENV%\Scripts\activate.bat"

REM Install/update dependencies
echo [+] Ensuring dependencies are installed...
"%PYTHON%" -m pip install -q --upgrade pip
"%PYTHON%" -m pip install -q -r "%PROJECT_ROOT%requirements.txt"

REM Start Backend API (FastAPI)
echo [+] Starting Backend API (FastAPI) on port 8000...
cd /d "%PROJECT_ROOT%stgen-ui\backend"
start "STGen Backend" "%PYTHON%" -m uvicorn app:app --host 0.0.0.0 --port 8000 --reload
timeout /t 3 /nobreak >nul

REM Start Frontend (React)
echo [+] Starting Frontend (React) on port 3000...
cd /d "%PROJECT_ROOT%stgen-ui\frontend"

REM Check if node_modules exists
if not exist "node_modules" (
    echo [*] Installing npm dependencies...
    call npm install -q
)

start "STGen Frontend" cmd /k "npm start"
timeout /t 5 /nobreak >nul

echo.
echo ============================================================================
echo                       ✓ SYSTEM READY
echo ============================================================================
echo.
echo [*] Web Dashboard:
echo     - Frontend: http://localhost:3000
echo     - Backend API: http://localhost:8000
echo     - API Docs: http://localhost:8000/docs
echo.
echo [*] CLI Usage (from project root in command prompt):
echo     1. cd stgen-ui\backend
echo     2. %VENV%\Scripts\activate.bat
echo     3. python -m stgen.main --help
echo.
echo [*] Open browser: http://localhost:3000
echo.
echo [*] To stop everything:
echo     - Close the two command windows (Backend & Frontend)
echo     - Or run: stop_all.bat
echo.

pause
