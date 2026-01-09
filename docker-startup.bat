@echo off
REM ============================================================================
REM STGen Docker Startup Script for Windows
REM Use this to run STGen completely in Docker (no local dependencies needed!)
REM ============================================================================

setlocal enabledelayedexpansion

set PROJECT_ROOT=%~dp0

echo.
echo ============================================================================
echo              STGen - Docker Deployment (Windows)
echo ============================================================================
echo.

REM Check if Docker is installed
docker --version >nul 2>&1
if %errorlevel% neq 0 (
    echo [ERROR] Docker is not installed!
    echo.
    echo [*] Download Docker Desktop from: https://www.docker.com/products/docker-desktop
    echo [*] After installation, restart your computer and try again
    echo.
    pause
    exit /b 1
)

echo [+] Docker found!
echo [+] Starting STGen containers with docker-compose...
echo.

REM Start containers
cd /d "%PROJECT_ROOT%"
docker-compose up -d

if %errorlevel% neq 0 (
    echo [ERROR] Failed to start Docker containers
    echo [*] Make sure Docker Desktop is running
    echo [*] Try: docker-compose up -d (for more details)
    pause
    exit /b 1
)

echo.
echo ============================================================================
echo                    ✓ DOCKER CONTAINERS STARTED
echo ============================================================================
echo.
echo [*] Web Dashboard:
echo     - Frontend:  http://localhost:3000
echo     - Backend:   http://localhost:8000
echo     - API Docs:  http://localhost:8000/docs
echo.
echo [*] Useful Commands:
echo.
echo    View logs:
echo     docker-compose logs -f
echo.
echo    Run CLI command inside container:
echo     docker exec stgen python -m stgen.main --help
echo.
echo    Run comparison test in container:
echo     docker exec stgen python run_comparison_test.py
echo.
echo    Stop everything:
echo     docker-compose down
echo.
echo    Restart containers:
echo     docker-compose restart
echo.
echo    View running containers:
echo     docker ps
echo.
echo ============================================================================
echo.

REM Show logs
echo [*] Showing container logs (Ctrl+C to exit)...
echo.
timeout /t 2 /nobreak >nul
docker-compose logs -f
