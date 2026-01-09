#!/bin/bash

# ============================================================================
# STGen Complete System Startup Script
# Starts Web UI (Frontend + Backend) + CLI ready
# ============================================================================

set -e

PROJECT_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
VENV="$PROJECT_ROOT/myenv"
PYTHON="$VENV/bin/python3"

# Colors for output
GREEN='\033[0;32m'
BLUE='\033[0;34m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

echo -e "${BLUE}╔════════════════════════════════════════════════════════════╗${NC}"
echo -e "${BLUE}║        STGen Complete System Startup (Web + CLI)            ║${NC}"
echo -e "${BLUE}╚════════════════════════════════════════════════════════════╝${NC}"

# Check if virtual environment exists
if [ ! -d "$VENV" ]; then
    echo -e "${YELLOW}⚠️  Virtual environment not found. Creating...${NC}"
    python3 -m venv "$VENV"
fi

# Activate virtual environment
echo -e "${BLUE}📦 Activating virtual environment...${NC}"
source "$VENV/bin/activate"

# Install/update dependencies
echo -e "${BLUE}📦 Ensuring dependencies are installed...${NC}"
pip install -q --upgrade pip
pip install -q -r "$PROJECT_ROOT/requirements.txt"

# Navigate to project root
cd "$PROJECT_ROOT"

# Start Backend API (FastAPI)
echo -e "${GREEN}✓ Starting Backend API (FastAPI) on port 8000...${NC}"
cd "$PROJECT_ROOT/stgen-ui/backend"
$PYTHON -m uvicorn app:app --host 0.0.0.0 --port 8000 --reload > "$PROJECT_ROOT/logs/backend.log" 2>&1 &
BACKEND_PID=$!
echo -e "${GREEN}  ✓ Backend PID: $BACKEND_PID${NC}"

# Wait for backend to be ready
echo -e "${BLUE}⏳ Waiting for backend to start...${NC}"
sleep 3

# Start Frontend (React)
echo -e "${GREEN}✓ Starting Frontend (React) on port 3000...${NC}"
cd "$PROJECT_ROOT/stgen-ui/frontend"

# Check if node_modules exists
if [ ! -d "node_modules" ]; then
    echo -e "${YELLOW}  Installing npm dependencies...${NC}"
    npm install -q
fi

PORT=3000 npm start > "$PROJECT_ROOT/logs/frontend.log" 2>&1 &
FRONTEND_PID=$!
echo -e "${GREEN}  ✓ Frontend PID: $FRONTEND_PID${NC}"

# Wait for frontend to be ready
sleep 5

echo -e "${BLUE}"
echo "╔════════════════════════════════════════════════════════════╗"
echo "║                   ✅ SYSTEM READY                          ║"
echo "╚════════════════════════════════════════════════════════════╝"
echo ""
echo -e "${GREEN}📊 Web Dashboard:${NC}"
echo -e "   🌐 Frontend: http://localhost:3000${NC}"
echo -e "   🔌 Backend API: http://localhost:8000${NC}"
echo -e "   📖 API Docs: http://localhost:8000/docs${NC}"
echo ""
echo -e "${GREEN}💻 CLI Usage (from project root):${NC}"
echo -e "   source myenv/bin/activate${NC}"
echo -e "   python stgen/main.py --help${NC}"
echo ""
echo -e "${GREEN}📋 Running Processes:${NC}"
echo -e "   Backend  (PID $BACKEND_PID): $PYTHON -m uvicorn app:app"
echo -e "   Frontend (PID $FRONTEND_PID): npm start${NC}"
echo ""
echo -e "${YELLOW}🔑 Quick Commands:${NC}"
echo -e "   Kill backend:   kill $BACKEND_PID"
echo -e "   Kill frontend:  kill $FRONTEND_PID"
echo -e "   Kill all:       kill $BACKEND_PID $FRONTEND_PID"
echo -e "   View logs:      tail -f logs/backend.log"
echo -e "   View logs:      tail -f logs/frontend.log${NC}"
echo ""
echo -e "${YELLOW}🛑 To stop everything, press Ctrl+C or run:${NC}"
echo -e "   ./stop_all.sh${NC}"
echo ""

# Create logs directory if it doesn't exist
mkdir -p "$PROJECT_ROOT/logs"

# Wait for user to stop
echo -e "${BLUE}Press Ctrl+C to stop all services...${NC}"
wait

