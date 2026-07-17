#!/bin/bash
# ========================================================================
# PSE Vision - Remove Systemd Service
# Stops and removes the auto-start service
# ========================================================================

set -e

echo ""
echo "========================================================"
echo "  PSE Vision - Remove Systemd Service"
echo "========================================================"
echo ""

# Check if service exists
if ! systemctl list-unit-files | grep -q "pse-vision-backend.service"; then
    echo "[INFO] Service not installed"
    exit 0
fi

echo "[1/3] Stopping service..."
sudo systemctl stop pse-vision-backend.service 2>/dev/null || true
echo "[OK] Service stopped"
echo ""

echo "[2/3] Disabling auto-start..."
sudo systemctl disable pse-vision-backend.service 2>/dev/null || true
echo "[OK] Auto-start disabled"
echo ""

echo "[3/3] Removing service file..."
sudo rm -f /etc/systemd/system/pse-vision-backend.service
sudo systemctl daemon-reload
echo "[OK] Service removed"
echo ""

echo "========================================================"
echo "  ✓ SERVICE REMOVED"
echo "========================================================"
echo ""
echo "You can still start the backend manually using:"
echo "  ./start.sh"
echo ""
