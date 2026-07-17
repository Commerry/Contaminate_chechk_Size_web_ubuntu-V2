#!/bin/bash
# ========================================================================
# PSE Vision - Dev Launcher (Ubuntu/Linux)
# Usage: ./dev.sh  (from project root)
#
# - Kills any existing process on port 64020 (backend) and 64021 (frontend)
# - Starts Python backend + Vite frontend concurrently
# - Ctrl+C kills both cleanly
# ========================================================================

# Get script directory
SCRIPT_DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" && pwd )"
cd "$SCRIPT_DIR"

PORTS=(64020 64021)

# ── Kill any process listening on the given port ──────────────────────────────
kill_port() {
    local port=$1
    if command -v lsof &> /dev/null; then
        lsof -ti:$port | xargs -r kill -9 2>/dev/null || true
    elif command -v fuser &> /dev/null; then
        fuser -k ${port}/tcp 2>/dev/null || true
    fi
}

echo ""
echo "===================================================="
echo "  PSE Vision - Dev Launcher"
echo "===================================================="
echo ""

echo "[1/2] Clearing existing processes..."
for port in "${PORTS[@]}"; do
    kill_port $port
    echo "  [KILL] Port $port cleared"
done
echo "[OK]  Ports 64020 and 64021 are free"
echo ""

echo "[2/2] Starting Backend + Frontend..."
echo ""

# Trap Ctrl+C to kill both processes
trap 'kill $(jobs -p) 2>/dev/null; exit' INT TERM

# Start Backend
echo "─────────────────────────────────────────────────────"
echo "  BACKEND (port 64021)"
echo "─────────────────────────────────────────────────────"
cd "$SCRIPT_DIR/python_scripts"
# Use virtual environment python
if [ -f "$SCRIPT_DIR/venv/bin/python" ]; then
    "$SCRIPT_DIR/venv/bin/python" backend_server.py &
else
    python3 backend_server.py &
fi
BACKEND_PID=$!

# Start Frontend
sleep 2
echo ""
echo "─────────────────────────────────────────────────────"
echo "  FRONTEND (port 64020)"
echo "─────────────────────────────────────────────────────"
cd "$SCRIPT_DIR/frontend"
npm run dev &
FRONTEND_PID=$!

# Wait for both processes
wait $BACKEND_PID $FRONTEND_PID
