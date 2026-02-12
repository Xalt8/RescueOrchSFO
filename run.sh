#!/bin/bash
set -e
ROOT="$(cd "$(dirname "$0")" && pwd)"
BACKEND_PID=""
FRONTEND_PID=""

cleanup() {
  echo ""
  echo "Shutting down..."
  [ -n "$BACKEND_PID" ] && kill $BACKEND_PID 2>/dev/null
  [ -n "$FRONTEND_PID" ] && kill $FRONTEND_PID 2>/dev/null
  exit 0
}
trap cleanup SIGINT SIGTERM

# Check for port conflicts
if lsof -i:8000 -sTCP:LISTEN -t >/dev/null 2>&1; then
  echo "Port 8000 is in use. Stopping existing process..."
  lsof -ti:8000 | xargs kill -9 2>/dev/null || true
  sleep 2
fi
if lsof -i:5173 -sTCP:LISTEN -t >/dev/null 2>&1; then
  echo "Port 5173 is in use. Stopping existing process..."
  lsof -ti:5173 | xargs kill -9 2>/dev/null || true
  sleep 1
fi

# Backend
cd "$ROOT/backend"
if [ ! -d "venv" ]; then
  echo "Creating virtual environment..."
  python3 -m venv venv
fi
source venv/bin/activate
pip install -q -r requirements.txt
echo "Starting backend on http://localhost:8000"
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000 &
BACKEND_PID=$!

# Frontend
cd "$ROOT/frontend"
[ ! -d "node_modules" ] && npm install
echo "Starting frontend on http://localhost:5173"
# npm run dev &
npm run dev -- --host 0.0.0.0 &
FRONTEND_PID=$!

echo ""
echo "Rescue Command Center running:"
echo "  Backend:  http://localhost:8000 (docs: /docs)"
echo "  Frontend: http://localhost:5173"
echo ""
echo "Press Ctrl+C to stop both"
wait
