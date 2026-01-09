#!/bin/bash

# ============================================================================
# STGen Complete System Shutdown Script
# Gracefully stops Web UI (Frontend + Backend)
# ============================================================================

GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m'

echo -e "${YELLOW}🛑 Stopping STGen system...${NC}"

# Kill all Node processes (frontend)
echo -e "${GREEN}✓ Stopping Frontend...${NC}"
pkill -f "node.*frontend" || true
pkill -f "npm.*start" || true

# Kill all Python processes (backend)
echo -e "${GREEN}✓ Stopping Backend...${NC}"
pkill -f "uvicorn.*app:app" || true

# Wait a moment
sleep 2

# Check if processes are still running
if pgrep -f "node.*frontend" > /dev/null; then
    echo -e "${YELLOW}⚠️  Forcefully killing frontend...${NC}"
    pkill -9 -f "node.*frontend" || true
fi

if pgrep -f "uvicorn.*app:app" > /dev/null; then
    echo -e "${YELLOW}⚠️  Forcefully killing backend...${NC}"
    pkill -9 -f "uvicorn.*app:app" || true
fi

echo -e "${GREEN}✅ All services stopped${NC}"
