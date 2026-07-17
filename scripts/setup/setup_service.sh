#!/bin/bash
# ========================================================================
# PSE Vision - Setup Systemd Service for Auto-Start
# This script installs systemd service for backend
# Requires sudo privileges
# ========================================================================

set -e  # Exit on error

# Get script directory
SCRIPT_DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" && pwd )"
CURRENT_USER=$(whoami)

echo ""
echo "========================================================"
echo "  PSE Vision - Systemd Service Setup"
echo "========================================================"
echo ""
echo "This will:"
echo "  1. Create systemd service file"
echo "  2. Enable auto-start on boot"
echo "  3. Start the service now"
echo ""
read -p "Continue? (y/n) " -n 1 -r
echo ""

if [[ ! $REPLY =~ ^[Yy]$ ]]; then
    echo "Cancelled."
    exit 0
fi

# Check if running as root
if [ "$EUID" -eq 0 ]; then 
    echo "[ERROR] Please run as normal user, not root!"
    echo "The script will ask for sudo password when needed."
    exit 1
fi

echo ""
echo "[1/4] Creating service file..."

# Create service file with correct paths
SERVICE_FILE="/tmp/pse-vision-backend.service"
cat > "$SERVICE_FILE" << EOF
[Unit]
Description=PSE Vision Backend Server
After=network.target

[Service]
Type=simple
User=$CURRENT_USER
WorkingDirectory=$SCRIPT_DIR/python_scripts
ExecStart=/usr/bin/python3 $SCRIPT_DIR/python_scripts/backend_server.py
Restart=always
RestartSec=10
StandardOutput=journal
StandardError=journal

[Install]
WantedBy=multi-user.target
EOF

echo "[OK] Service file created"
echo ""

echo "[2/4] Installing service..."
sudo cp "$SERVICE_FILE" /etc/systemd/system/pse-vision-backend.service
sudo systemctl daemon-reload
echo "[OK] Service installed"
echo ""

echo "[3/4] Enabling auto-start..."
sudo systemctl enable pse-vision-backend.service
echo "[OK] Auto-start enabled"
echo ""

echo "[4/4] Starting service..."
sudo systemctl start pse-vision-backend.service
echo "[OK] Service started"
echo ""

# Check status
echo "========================================================"
echo "  Service Status"
echo "========================================================"
sudo systemctl status pse-vision-backend.service --no-pager || true
echo ""

echo "========================================================"
echo "  ✓ SETUP COMPLETE"
echo "========================================================"
echo ""
echo "Useful commands:"
echo "  • Check status:  sudo systemctl status pse-vision-backend"
echo "  • Stop service:  sudo systemctl stop pse-vision-backend"
echo "  • Start service: sudo systemctl start pse-vision-backend"
echo "  • Restart:       sudo systemctl restart pse-vision-backend"
echo "  • View logs:     sudo journalctl -u pse-vision-backend -f"
echo "  • Disable:       sudo systemctl disable pse-vision-backend"
echo ""
echo "Backend is now running at: http://localhost:64020"
echo ""
