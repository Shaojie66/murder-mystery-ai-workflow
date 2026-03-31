#!/bin/bash
# Murder Wizard Web - Local Development Startup Script

set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(dirname "$SCRIPT_DIR")"

echo "=========================================="
echo "  Murder Wizard - 剧本杀创作工作流"
echo "=========================================="
echo ""

# Check if Python dependencies are installed
if ! python -c "import fastapi" 2>/dev/null; then
    echo "Installing Python dependencies..."
    cd "$PROJECT_ROOT/murder_wizard_web/backend"
    pip install -r requirements.txt
fi

# Check if Node dependencies are installed
if [ ! -d "$PROJECT_ROOT/murder_wizard_web/frontend/node_modules" ]; then
    echo "Installing Node dependencies..."
    cd "$PROJECT_ROOT/murder_wizard_web/frontend"
    npm install
fi

echo ""
echo "Starting services..."
echo ""

# Function to cleanup on exit
cleanup() {
    echo ""
    echo "Shutting down..."
    [ -n "$BACKEND_PID" ] && kill $BACKEND_PID 2>/dev/null
    [ -n "$FRONTEND_PID" ] && kill $FRONTEND_PID 2>/dev/null
    exit 0
}

trap cleanup SIGINT SIGTERM

# Start backend
echo "🚀 Starting Backend (FastAPI)..."
cd "$PROJECT_ROOT/murder_wizard_web/backend"
PYTHONPATH="$PROJECT_ROOT/murder_wizard_web/backend" python main.py &
BACKEND_PID=$!
sleep 2

# Start frontend dev server
echo "⚡ Starting Frontend (Vite dev server)..."
cd "$PROJECT_ROOT/murder_wizard_web/frontend"
npm run dev &
FRONTEND_PID=$!
sleep 2

echo ""
echo "=========================================="
echo "  Services started!"
echo ""
echo "  Frontend: http://localhost:5173"
echo "  Backend:  http://localhost:8000"
echo "  API Docs: http://localhost:8000/docs"
echo ""
echo "  Press Ctrl+C to stop"
echo "=========================================="
echo ""

# Wait for both processes
wait $BACKEND_PID $FRONTEND_PID
