#!/bin/bash

# Start All Services Script for Take My Dictation
# This script starts both backend and frontend servers

set -e  # Exit on error

# Colors for output
GREEN='\033[0;32m'
RED='\033[0;31m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

echo -e "${BLUE}╔════════════════════════════════════════╗${NC}"
echo -e "${BLUE}║   Take My Dictation - Start All       ║${NC}"
echo -e "${BLUE}╚════════════════════════════════════════╝${NC}"
echo ""

# Get the directory where this script is located
SCRIPT_DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" && pwd )"
cd "$SCRIPT_DIR"

# Function to cleanup on exit
cleanup() {
    echo ""
    echo -e "${YELLOW}🛑 Stopping all services...${NC}"

    # Kill backend
    if [ ! -z "$BACKEND_PID" ]; then
        kill $BACKEND_PID 2>/dev/null || true
    fi
    lsof -ti:8000 | xargs kill -9 2>/dev/null || true

    # Kill frontend
    if [ ! -z "$FRONTEND_PID" ]; then
        kill $FRONTEND_PID 2>/dev/null || true
    fi
    lsof -ti:3000 | xargs kill -9 2>/dev/null || true

    echo -e "${GREEN}✅ All services stopped${NC}"
    exit 0
}

# Trap Ctrl+C and cleanup
trap cleanup SIGINT SIGTERM

# Make scripts executable
chmod +x start-backend.sh start-frontend.sh

# Start Backend
echo -e "${GREEN}1️⃣  Starting Backend Server...${NC}"
./start-backend.sh > backend.log 2>&1 &
BACKEND_PID=$!

# Wait for backend to start
echo -e "${YELLOW}⏳ Waiting for backend to be ready...${NC}"
for i in {1..30}; do
    if curl -s http://localhost:8000/ > /dev/null 2>&1; then
        echo -e "${GREEN}✅ Backend is ready on http://localhost:8000${NC}"
        break
    fi
    if [ $i -eq 30 ]; then
        echo -e "${RED}❌ Backend failed to start. Check backend.log for details.${NC}"
        cat backend.log
        cleanup
        exit 1
    fi
    sleep 1
done

echo ""

# Start Frontend
echo -e "${GREEN}2️⃣  Starting Frontend Server...${NC}"
./start-frontend.sh > frontend.log 2>&1 &
FRONTEND_PID=$!

# Wait for frontend to start
echo -e "${YELLOW}⏳ Waiting for frontend to be ready...${NC}"
for i in {1..60}; do
    if curl -s http://localhost:3000/ > /dev/null 2>&1; then
        echo -e "${GREEN}✅ Frontend is ready on http://localhost:3000${NC}"
        break
    fi
    if [ $i -eq 60 ]; then
        echo -e "${RED}❌ Frontend failed to start. Check frontend.log for details.${NC}"
        cat frontend.log
        cleanup
        exit 1
    fi
    sleep 1
done

echo ""
echo -e "${BLUE}╔════════════════════════════════════════╗${NC}"
echo -e "${BLUE}║         🎉 All Services Running!       ║${NC}"
echo -e "${BLUE}╠════════════════════════════════════════╣${NC}"
echo -e "${BLUE}║                                        ║${NC}"
echo -e "${BLUE}║  Frontend: ${GREEN}http://localhost:3000${BLUE}      ║${NC}"
echo -e "${BLUE}║  Backend:  ${GREEN}http://localhost:8000${BLUE}      ║${NC}"
echo -e "${BLUE}║  API Docs: ${GREEN}http://localhost:8000/docs${BLUE} ║${NC}"
echo -e "${BLUE}║                                        ║${NC}"
echo -e "${BLUE}║  Logs:                                 ║${NC}"
echo -e "${BLUE}║  - Backend:  backend.log               ║${NC}"
echo -e "${BLUE}║  - Frontend: frontend.log              ║${NC}"
echo -e "${BLUE}║                                        ║${NC}"
echo -e "${BLUE}║  Press Ctrl+C to stop all services     ║${NC}"
echo -e "${BLUE}║                                        ║${NC}"
echo -e "${BLUE}╚════════════════════════════════════════╝${NC}"
echo ""

# Open browser
if command -v open > /dev/null 2>&1; then
    sleep 2
    open http://localhost:3000
fi

# Keep script running
echo -e "${YELLOW}📝 Monitoring services... (Press Ctrl+C to stop)${NC}"
echo ""

# Monitor both processes
while true; do
    # Check if backend is still running
    if ! kill -0 $BACKEND_PID 2>/dev/null; then
        echo -e "${RED}❌ Backend crashed! Check backend.log${NC}"
        cleanup
        exit 1
    fi

    # Check if frontend is still running
    if ! kill -0 $FRONTEND_PID 2>/dev/null; then
        echo -e "${RED}❌ Frontend crashed! Check frontend.log${NC}"
        cleanup
        exit 1
    fi

    sleep 5
done
