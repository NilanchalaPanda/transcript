#!/bin/bash

echo "=================================="
echo "🚀 Starting Audio Timestamp Generator"
echo "=================================="

# Colors for output
GREEN='\033[0;32m'
BLUE='\033[0;34m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# Check if nginx is installed
if ! command -v nginx &> /dev/null; then
    echo -e "${YELLOW}⚠️  nginx is not installed!${NC}"
    echo "Installing nginx..."
    if [[ "$OSTYPE" == "darwin"* ]]; then
        # macOS
        brew install nginx
    elif [[ "$OSTYPE" == "linux-gnu"* ]]; then
        # Linux
        sudo apt-get update && sudo apt-get install -y nginx
    else
        echo "Please install nginx manually"
        exit 1
    fi
fi

# Kill any existing processes on the ports
echo -e "${BLUE}🧹 Cleaning up existing processes...${NC}"
lsof -ti:5001 | xargs kill -9 2>/dev/null || true
lsof -ti:5173 | xargs kill -9 2>/dev/null || true
lsof -ti:8080 | xargs kill -9 2>/dev/null || true

# Start backend (Flask)
echo -e "${GREEN}🔧 Starting Flask backend on port 5001...${NC}"
cd /Users/dhruveel/Development_Tools/rani-timestamps-generator
source venv/bin/activate
python app.py &
BACKEND_PID=$!
echo "Backend PID: $BACKEND_PID"

# Wait for backend to start
sleep 3

# Start frontend (Vite)
echo -e "${GREEN}🎨 Starting Vite frontend on port 5173...${NC}"
cd /Users/dhruveel/Development_Tools/rani-timestamps-generator/frontend
npm run dev &
FRONTEND_PID=$!
echo "Frontend PID: $FRONTEND_PID"

# Wait for frontend to start
sleep 5

# Start nginx
echo -e "${GREEN}🌐 Starting nginx on port 8080...${NC}"
cd /Users/dhruveel/Development_Tools/rani-timestamps-generator
nginx -c "$(pwd)/nginx.conf" -p "$(pwd)"
NGINX_PID=$!

echo ""
echo "=================================="
echo -e "${GREEN}✅ All services started!${NC}"
echo "=================================="
echo -e "${BLUE}Backend:${NC}  http://localhost:5001"
echo -e "${BLUE}Frontend:${NC} http://localhost:5173"
echo -e "${BLUE}Nginx:${NC}    http://localhost:8080"
echo ""
echo -e "${YELLOW}📡 Now expose port 8080 with ngrok:${NC}"
echo -e "${GREEN}   ngrok http 8080${NC}"
echo ""
echo "=================================="
echo "Press Ctrl+C to stop all services"
echo "=================================="

# Trap Ctrl+C to kill all processes
trap "echo 'Stopping all services...'; kill $BACKEND_PID $FRONTEND_PID 2>/dev/null; nginx -s stop -c $(pwd)/nginx.conf -p $(pwd) 2>/dev/null; exit" INT

# Wait indefinitely
wait
