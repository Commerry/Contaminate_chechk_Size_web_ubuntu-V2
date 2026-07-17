#!/bin/bash
# ========================================================================
# PSE Vision - Complete Installation for Ubuntu/Linux
# Safe to run on fresh install OR existing install (will update)
# ========================================================================

set -e  # Exit on error

echo ""
echo "========================================================"
echo ""
echo "     PSE VISION - ONE-CLICK INSTALLATION (Ubuntu)"
echo ""
echo "========================================================"
echo ""

# Get script directory
SCRIPT_DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" && pwd )"
cd "$SCRIPT_DIR"

# ========================================================================
# Step 0: Stop existing running system (if any)
# ========================================================================
echo "[0/5] Stopping existing system (if running)..."

# Kill processes using port 64020
if command -v lsof &> /dev/null; then
    lsof -ti:64020 | xargs -r kill -9 2>/dev/null || true
elif command -v fuser &> /dev/null; then
    fuser -k 64020/tcp 2>/dev/null || true
fi

# Kill any python backend process
pkill -f "backend_server.py" 2>/dev/null || true

sleep 2
echo "[OK] Ready to install"
echo ""

# ========================================================================
# Step 1: Check Python
# ========================================================================
echo "[1/5] Checking Python..."
if ! command -v python3 &> /dev/null; then
    echo "[ERROR] Python3 not found!"
    echo "Please install Python 3.8+ using:"
    echo "  sudo apt update"
    echo "  sudo apt install python3 python3-pip python3-venv"
    exit 1
fi

python3 --version
echo "[OK] Python found"
echo ""

# ========================================================================
# Step 2: Install/Update Python Packages
# ========================================================================
echo "[2/5] Installing/Updating Python packages..."

# Install system dependencies for OpenCV and depthai
echo "[INFO] Installing system dependencies..."
sudo apt-get update -qq
sudo apt-get install -y -qq \
    python3-full \
    python3-pip \
    python3-venv \
    libusb-1.0-0-dev \
    libopencv-dev \
    python3-opencv \
    udev \
    libgl1-mesa-glx \
    libglib2.0-0 2>&1 | grep -v "^Setting up\|^Processing\|^Preparing" || true

# Create virtual environment if not exists
if [ ! -d "venv" ]; then
    echo "[INFO] Creating virtual environment..."
    python3 -m venv venv
fi

# Activate virtual environment
echo "[INFO] Activating virtual environment..."
source venv/bin/activate

# Upgrade pip in venv
echo "[INFO] Upgrading pip..."
pip install --upgrade pip --quiet

# Install Python packages in venv
cd python_scripts
echo "[INFO] Installing Python packages..."
pip install -r backend_requirements.txt --quiet

# Verify all critical packages can be imported
echo "[INFO] Verifying package imports..."
python -c "import flask, flask_cors, flask_socketio, cv2, numpy, depthai; print('[OK] All packages verified')"

if [ $? -ne 0 ]; then
    echo "[ERROR] Package verification failed - trying repair install..."
    pip install -r backend_requirements.txt --force-reinstall --quiet
    python -c "import flask, flask_cors, flask_socketio, cv2, numpy, depthai; print('[OK] Repair successful')"
    
    if [ $? -ne 0 ]; then
        echo "[ERROR] Failed to install required Python packages"
        deactivate
        exit 1
    fi
fi

cd ..

# Setup udev rules for OAK-D camera (requires sudo)
echo "[INFO] Setting up camera permissions..."
echo 'SUBSYSTEM=="usb", ATTRS{idVendor}=="03e7", MODE="0666"' | sudo tee /etc/udev/rules.d/80-movidius.rules > /dev/null
sudo udevadm control --reload-rules && sudo udevadm trigger || true

echo "[OK] Python packages ready"
cd ..
echo ""

# ========================================================================
# Step 3: Check Node.js, Install Frontend packages and Build
# ========================================================================
echo "[3/5] Checking Node.js..."
if ! command -v node &> /dev/null; then
    echo "[ERROR] Node.js not found!"
    echo "Please install Node.js 16+ using:"
    echo "  curl -fsSL https://deb.nodesource.com/setup_18.x | sudo -E bash -"
    echo "  sudo apt-get install -y nodejs"
    exit 1
fi

node --version
npm --version
echo "[OK] Node.js found"
echo ""

# ========================================================================
# Step 4: Install Frontend Dependencies and Build
# ========================================================================
echo "[4/5] Installing Frontend dependencies..."
cd frontend

# Install dependencies
npm install --quiet 2>&1 | grep -E "added|removed|updated|audited" || true

# Build frontend
echo "[INFO] Building frontend..."
npm run build 2>&1 | grep -E "built|✓|error|warning" || echo "[INFO] Building..."

if [ ! -d "dist" ] || [ ! -f "dist/index.html" ]; then
    echo "[ERROR] Frontend build failed - dist/index.html not found"
    exit 1
fi

echo "[OK] Frontend built successfully"
cd ..
echo ""

# ========================================================================
# Step 5: Install PM2 for process management
# ========================================================================
echo "[5/6] Installing PM2..."
if command -v pm2 &> /dev/null; then
    echo "[INFO] PM2 already installed: $(pm2 --version)"
else
    sudo npm install -g pm2 --quiet 2>&1 | grep -E "added|removed|updated" || true
    echo "[OK] PM2 installed: $(pm2 --version)"
fi
echo ""

# ========================================================================
# Create start scripts
# ========================================================================
echo "[6/6] Creating startup scripts..."

# Make scripts executable
chmod +x start.sh dev.sh setup_pm2.sh 2>/dev/null || true

# Create data directory for SQLite
mkdir -p data

# Create logs directory for PM2
mkdir -p logs

# Create desktop entry for auto-start (optional)
cat > pse-vision.desktop << EOF
[Desktop Entry]
Type=Application
Name=PSE Vision
Comment=PSE Vision System
Exec=$SCRIPT_DIR/start.sh
Path=$SCRIPT_DIR
Terminal=false
StartupNotify=true
EOF

echo "[OK] Startup scripts created"
echo ""

# ========================================================================
# Installation Complete
# ========================================================================
echo "========================================================"
echo "  ✓ INSTALLATION COMPLETE"
echo "========================================================"
echo ""
echo "Quick Start:"
echo "  1. Start Backend + Admin Web:"
echo "     ./start.sh"
echo ""
echo "  2. Access Admin Web:"
echo "     http://localhost:64020"
echo ""
echo "  3. (Optional) Setup PM2 auto-start:"
echo "     ./setup_pm2.sh"
echo ""
echo "Database:"
echo "  • SQLite (local) is enabled by default"
echo "  • Database path: data/pse_vision.db"
echo "  • Configure in Admin Web → Database Settings"
echo ""
echo "For more info: cat README_UBUNTU.md"
echo "========================================================"
echo ""
