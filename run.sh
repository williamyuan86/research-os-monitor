#!/bin/bash

# Colors
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m'

echo -e "${GREEN}Research OS Monitor${NC} - Starting services..."

# Start backend
echo -e "${YELLOW}Starting backend on port 8000...${NC}"
cd "$(dirname "$0")/backend"
pip install -q -r requirements.txt 2>/dev/null
uvicorn api.main:app --host 0.0.0.0 --port 8000 --reload &
BACKEND_PID=$!

# Wait for backend
sleep 3

# Start frontend
echo -e "${YELLOW}Starting frontend on port 5173...${NC}"
cd "$(dirname "$0")/frontend"
npm install --silent 2>/dev/null
npm run dev &
FRONTEND_PID=$!

echo ""
echo -e "${GREEN}Services started!${NC}"
echo "  Backend: http://localhost:8000"
echo "  Frontend: http://localhost:5173"
echo "  API Docs: http://localhost:8000/docs"
echo ""
echo "Press Ctrl+C to stop all services"

# Cleanup on exit
trap "kill $BACKEND_PID $FRONTEND_PID 2>/dev/null" EXIT

wait
