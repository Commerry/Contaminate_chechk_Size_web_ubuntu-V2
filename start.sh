#!/bin/bash
# ========================================================================
# PSE Vision - Start System (Ubuntu/Linux)
# Run this file to start Backend + Admin Web
# ========================================================================

# Get script directory
SCRIPT_DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" && pwd )"
cd "$SCRIPT_DIR"

echo "========================================================"
echo "  PSE Vision - Starting System"
echo "========================================================"
echo ""

# Kill existing processes on port 64020
echo "[INFO] Stopping existing processes..."
if command -v lsof &> /dev/null; then
    lsof -ti:64020 | xargs -r kill -9 2>/dev/null || true
elif command -v fuser &> /dev/null; then
    fuser -k 64020/tcp 2>/dev/null || true
fi

# Kill any python backend process
pkill -f "backend_server.py" 2>/dev/null || true
sleep 2

# Start Backend
echo "[INFO] Starting Backend Server..."
cd "$SCRIPT_DIR/python_scripts"

# Use virtual environment python
if [ -f "$SCRIPT_DIR/venv/bin/python" ]; then
    "$SCRIPT_DIR/venv/bin/python" backend_server.py &
else
    python3 backend_server.py &
fi
BACKEND_PID=$!

echo "[OK] Backend started (PID: $BACKEND_PID)"
echo ""

# Wait for backend to initialize
echo "[INFO] Waiting for backend to initialize..."
sleep 8

# Check if backend is running
if ! ps -p $BACKEND_PID > /dev/null; then
    echo "[ERROR] Backend failed to start!"
    exit 1
fi

# Open Admin Web in browser
echo "[INFO] Opening Admin Web in browser..."
if command -v xdg-open &> /dev/null; then
    xdg-open http://localhost:64020 2>/dev/null &
elif command -v gnome-open &> /dev/null; then
    gnome-open http://localhost:64020 2>/dev/null &
fi

echo ""
echo "========================================================"
echo "  ✓ PSE Vision Started Successfully"
echo "========================================================"
echo ""
echo "  • Backend Server: http://localhost:64020 (PID: $BACKEND_PID)"
echo "  • Admin Web: http://localhost:64020"
echo ""
echo "  To stop: Press Ctrl+C or run:"
echo "    kill $BACKEND_PID"
echo ""
echo "========================================================"
echo ""

# Wait for backend process
wait $BACKEND_PID
