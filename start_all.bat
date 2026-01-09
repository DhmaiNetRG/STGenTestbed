@echo off
REM ============================================================================
REM STGen Complete System Startup Script for Windows
REM Intelligently uses Docker if available, otherwise local Python
REM ============================================================================

setlocal enabledelayedexpansion

set PROJECT_ROOT=%~dp0
set VENV=%PROJECT_ROOT%myenv
set LOGS_DIR=%PROJECT_ROOT%logs

echo.
echo ============================================================================
echo          STGen Complete System Startup - Windows
echo ============================================================================
echo.

REM ============================================================================
REM CHECK FOR DOCKER FIRST (RECOMMENDED)
REM ============================================================================
echo [*] Checking for Docker installation...
docker --version >nul 2>&1
if %errorlevel% equ 0 (
    echo.
    echo ============================================================================
    echo                    USING DOCKER (Recommended)
    echo ============================================================================
    echo.
    echo [+] Docker found! Using containerized deployment...
    echo [+] Starting STGen with docker-compose...
    echo.
    
    REM Check if docker-compose file exists
    if exist "%PROJECT_ROOT%docker-compose.yml" (
        docker-compose -f "%PROJECT_ROOT%docker-compose.yml" up -d
        
        if %errorlevel% equ 0 (
            echo.
            echo ============================================================================
            echo                    ✓ DOCKER SYSTEM READY
            echo ============================================================================
            echo.
            echo [*] Web Dashboard (in Docker):
            echo     - Frontend: http://localhost:3000
            echo     - Backend API: http://localhost:8000
            echo     - API Docs: http://localhost:8000/docs
            echo.
            echo [*] CLI Usage (inside container):
            echo     docker exec stgen python -m stgen.main --help
            echo.
            echo [*] View logs:
            echo     docker-compose logs -f
            echo.
            echo [*] Stop everything:
            echo     docker-compose down
            echo.
            echo ============================================================================
            echo.
            pause
            exit /b 0
        ) else (
            echo [ERROR] Failed to start Docker containers
            echo [*] Make sure Docker daemon is running
            pause
            exit /b 1
        )
    ) else (
        echo [ERROR] docker-compose.yml not found in %PROJECT_ROOT%
        pause
        exit /b 1
    )
) else (
    echo [!] Docker not found. Using local Python setup...
    echo.
    echo [*] RECOMMENDED: Install Docker Desktop from https://www.docker.com/products/docker-desktop
    echo [*] Docker eliminates dependency issues and works everywhere
    echo.
    REM Fall through to local setup below
)

echo.
echo ============================================================================
echo                    USING LOCAL PYTHON (Fallback)
echo ============================================================================
echo.

REM Create logs directory
if not exist "%LOGS_DIR%" mkdir "%LOGS_DIR%"

REM Check if Python is available in PATH
python --version >nul 2>&1
if %errorlevel% neq 0 (
    echo [ERROR] Python is not installed or not in PATH
    echo [*] Please choose one of these options:
    echo.
    echo [*] OPTION 1: Install Docker (RECOMMENDED - No Python needed!)
    echo     Download: https://www.docker.com/products/docker-desktop
    echo     Then run: docker-compose up -d
    echo.
    echo [*] OPTION 2: Install Python locally
    echo     1. Download Python 3.12+ from: https://www.python.org/downloads/
    echo     2. CHECK: "Add Python to PATH" during installation
    echo     3. Restart this script
    echo.
    pause
    exit /b 1
)

set "PYTHON_CMD=python"

echo [+] Starting local Python setup (venv)...
echo.

REM Check if virtual environment exists
if not exist "%VENV%" (
    echo [*] Virtual environment not found. Creating...
    "%PYTHON_CMD%" -m venv "%VENV%"
)

REM Activate virtual environment
echo [+] Activating virtual environment...
call "%VENV%\Scripts\activate.bat"

REM Install/update dependencies
echo [+] Ensuring dependencies are installed...
"%VENV%\Scripts\python.exe" -m pip install -q --upgrade pip
"%VENV%\Scripts\python.exe" -m pip install -q -r "%PROJECT_ROOT%requirements.txt"

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
echo     3. %PYTHON% -m stgen.main --help
echo.
echo [*] Open browser: http://localhost:3000
echo.
echo [*] To stop everything:
echo     - Close the two command windows (Backend & Frontend)
echo     - Or run: stop_all.bat
echo.

pause
