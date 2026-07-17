#!/bin/bash
# ========================================================================
# PSE Vision - Deploy to Ubuntu Server via SSH
# Deploys entire project to remote Ubuntu server
# Target: adminpse@10.1.100.78
# ========================================================================

set -e  # Exit on error

# Configuration
REMOTE_USER="adminpse"
REMOTE_HOST="10.1.100.78"
REMOTE_PATH="/home/adminpse/pse-vision"
LOCAL_PATH="$( cd "$( dirname "${BASH_SOURCE[0]}" )" && pwd )"

echo ""
echo "========================================================"
echo "  PSE Vision - Deploy to Ubuntu Server"
echo "========================================================"
echo ""
echo "Configuration:"
echo "  • Remote: $REMOTE_USER@$REMOTE_HOST"
echo "  • Path:   $REMOTE_PATH"
echo "  • Local:  $LOCAL_PATH"
echo ""
read -p "Continue deployment? (y/n) " -n 1 -r
echo ""

if [[ ! $REPLY =~ ^[Yy]$ ]]; then
    echo "Cancelled."
    exit 0
fi

# Test SSH connection
echo ""
echo "[1/6] Testing SSH connection..."
if ! ssh -o ConnectTimeout=5 "$REMOTE_USER@$REMOTE_HOST" "echo '[OK] Connection successful'" 2>/dev/null; then
    echo "[ERROR] Cannot connect to $REMOTE_USER@$REMOTE_HOST"
    echo "Please check:"
    echo "  1. Server is online"
    echo "  2. SSH credentials are correct"
    echo "  3. Network connectivity"
    exit 1
fi
echo ""

# Create remote directory
echo "[2/6] Creating remote directory..."
ssh "$REMOTE_USER@$REMOTE_HOST" "mkdir -p $REMOTE_PATH"
echo "[OK] Directory ready"
echo ""

# Build frontend before deployment
echo "[3/6] Building frontend..."
cd "$LOCAL_PATH/frontend"
if [ ! -d "node_modules" ]; then
    echo "[INFO] Installing frontend dependencies..."
    npm install --quiet
fi
npm run build 2>&1 | tail -10
if [ ! -d "dist" ] || [ ! -f "dist/index.html" ]; then
    echo "[ERROR] Frontend build failed"
    exit 1
fi
echo "[OK] Frontend built"
cd "$LOCAL_PATH"
echo ""

# Sync files to remote server
echo "[4/6] Syncing files to server..."
echo "[INFO] This may take a few minutes..."

rsync -avz --progress \
    --exclude 'node_modules' \
    --exclude '.git' \
    --exclude '__pycache__' \
    --exclude '*.pyc' \
    --exclude '.venv' \
    --exclude 'venv' \
    --exclude 'dist-installer' \
    --exclude '.vscode' \
    --exclude '.DS_Store' \
    --exclude '*.log' \
    --exclude 'logs/*' \
    "$LOCAL_PATH/" \
    "$REMOTE_USER@$REMOTE_HOST:$REMOTE_PATH/" \
    2>&1 | grep -E "sending|sent|speedup" || true

echo "[OK] Files synced"
echo ""

# Set executable permissions on remote
echo "[5/6] Setting permissions on remote..."
ssh "$REMOTE_USER@$REMOTE_HOST" << 'EOF'
cd ~/pse-vision
chmod +x *.sh
chmod +x setup_service.sh
chmod +x remove_service.sh
echo "[OK] Permissions set"
EOF
echo ""

# Display next steps
echo "[6/6] Deployment complete!"
echo ""
echo "========================================================"
echo "  ✓ DEPLOYMENT SUCCESSFUL"
echo "========================================================"
echo ""
echo "Next steps on the server:"
echo ""
echo "  1. SSH to server:"
echo "     ssh $REMOTE_USER@$REMOTE_HOST"
echo ""
echo "  2. Navigate to project:"
echo "     cd $REMOTE_PATH"
echo ""
echo "  3. Install dependencies:"
echo "     ./install.sh"
echo ""
echo "  4. Start the system:"
echo "     ./start.sh"
echo ""
echo "  5. (Optional) Setup auto-start:"
echo "     ./setup_service.sh"
echo ""
echo "  6. Access Admin Web:"
echo "     http://$REMOTE_HOST:64020"
echo ""
echo "========================================================"
echo ""
echo "Would you like to SSH into the server now? (y/n)"
read -p "> " -n 1 -r
echo ""

if [[ $REPLY =~ ^[Yy]$ ]]; then
    ssh "$REMOTE_USER@$REMOTE_HOST"
fi
