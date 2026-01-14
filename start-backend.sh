#!/bin/bash

# Start Backend Script for Take My Dictation
# This script starts the FastAPI backend server with proper error handling

set -e  # Exit on error

# Colors for output
GREEN='\033[0;32m'
RED='\033[0;31m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

echo -e "${GREEN}🚀 Starting Take My Dictation Backend...${NC}"

# Get the directory where this script is located
SCRIPT_DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" && pwd )"
cd "$SCRIPT_DIR"

# Check if virtual environment exists
if [ ! -d "venv" ]; then
    echo -e "${RED}❌ Virtual environment not found!${NC}"
    echo "Please run: python -m venv venv && source venv/bin/activate && pip install -r requirements.txt"
    exit 1
fi

# Check if .env file exists
if [ ! -f ".env" ]; then
    echo -e "${RED}❌ .env file not found!${NC}"
    echo "Please create .env file with required variables"
    exit 1
fi

# Activate virtual environment
echo -e "${YELLOW}📦 Activating virtual environment...${NC}"
source venv/bin/activate

# Check if port 8000 is already in use
if lsof -Pi :8000 -sTCP:LISTEN -t >/dev/null 2>&1; then
    echo -e "${YELLOW}⚠️  Port 8000 is already in use. Stopping existing process...${NC}"
    lsof -ti:8000 | xargs kill -9 2>/dev/null || true
    sleep 2
fi

# Check if required packages are installed
echo -e "${YELLOW}📋 Checking dependencies...${NC}"
python -c "import fastapi, uvicorn, sqlalchemy, openai" 2>/dev/null || {
    echo -e "${RED}❌ Missing dependencies!${NC}"
    echo "Installing requirements..."
    pip install -r requirements.txt
}

# Create uploads directory if it doesn't exist
mkdir -p uploads

# Start the server
echo -e "${GREEN}✅ Starting FastAPI server on http://localhost:8000${NC}"
echo -e "${YELLOW}📝 Logs will be displayed below. Press Ctrl+C to stop.${NC}"
echo ""

python -m uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
