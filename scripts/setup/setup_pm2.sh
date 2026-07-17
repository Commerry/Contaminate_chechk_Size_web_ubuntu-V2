#!/bin/bash
# ========================================================================
# PSE Vision - Setup PM2 for Auto-Start
# Installs PM2 and configures it to start on boot
# ========================================================================

set -e

# Get script directory
SCRIPT_DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" && pwd )"
cd "$SCRIPT_DIR"

echo ""
echo "========================================================"
echo "  PSE Vision - PM2 Auto-Start Setup"
echo "========================================================"
echo ""

# Check if Node.js is installed
if ! command -v node &> /dev/null; then
    echo "[ERROR] Node.js not found!"
    echo "Please run ./install.sh first to install dependencies"
    exit 1
fi

# Install PM2 globally
echo "[1/5] Installing PM2..."
if command -v pm2 &> /dev/null; then
    echo "[INFO] PM2 already installed: $(pm2 --version)"
else
    sudo npm install -g pm2 --quiet
    echo "[OK] PM2 installed: $(pm2 --version)"
fi
echo ""

# Stop any existing PM2 processes
echo "[2/5] Stopping existing PM2 processes..."
pm2 delete all 2>/dev/null || true
pm2 kill 2>/dev/null || true
echo "[OK] Cleaned up"
echo ""

# Update ecosystem.config.js with current path
echo "[3/5] Configuring PM2 ecosystem..."
CURRENT_PATH=$(pwd)
sed -i "s|cwd: '/home/adminpse/pse-vision'|cwd: '$CURRENT_PATH'|g" ecosystem.config.js
echo "[OK] Ecosystem configured for: $CURRENT_PATH"
echo ""

# Start applications with PM2
echo "[4/5] Starting applications with PM2..."

# Start backend only (display app will start on desktop login)
pm2 start ecosystem.config.js --only pse-vision-backend

# Save PM2 process list
pm2 save

echo "[OK] Backend started with PM2"
echo ""

# Setup PM2 to start on boot
echo "[5/5] Setting up PM2 startup..."
STARTUP_CMD=$(pm2 startup systemd -u $USER --hp $HOME | grep 'sudo')
echo "[INFO] Running startup command..."
eval $STARTUP_CMD

echo "[OK] PM2 startup configured"
echo ""

# Show status
echo "========================================================"
echo "  PM2 Status"
echo "========================================================"
pm2 status
echo ""

echo "========================================================"
echo "  ✓ PM2 SETUP COMPLETE"
echo "========================================================"
echo ""
echo "Useful PM2 commands:"
echo "  • View status:   pm2 status"
echo "  • View logs:     pm2 logs"
echo "  • Restart:       pm2 restart pse-vision-backend"
echo "  • Stop:          pm2 stop pse-vision-backend"
echo "  • Monitor:       pm2 monit"
echo ""
echo "Backend is now running at: http://localhost:64020"
echo ""
