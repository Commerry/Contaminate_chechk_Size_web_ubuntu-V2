#!/usr/bin/env bash
set -e

PROXY_URL="http://10.201.0.54:8080"

echo "== Appending proxy env to ~/.profile =="
cat >> ~/.profile <<'EOF'
export HTTP_PROXY="${PROXY_URL}"
export http_proxy="${PROXY_URL}"
export HTTPS_PROXY="${PROXY_URL}"
export https_proxy="${PROXY_URL}"
export NO_PROXY="localhost,127.0.0.1,10.201.0.0/16"
export no_proxy="$NO_PROXY"
EOF

echo "== Writing pip config =="
mkdir -p ~/.config/pip
cat > ~/.config/pip/pip.conf <<EOF
[global]
proxy = ${PROXY_URL}
EOF

echo "== Writing APT proxy config (requires sudo) =="
sudo tee /etc/apt/apt.conf.d/95proxy > /dev/null <<EOF
Acquire::http::Proxy "${PROXY_URL}/";
Acquire::https::Proxy "${PROXY_URL}/";
EOF

echo "== Running apt update and installing python3-opencv =="
sudo apt update || true
sudo apt install -y python3-opencv libopencv-dev || true

# Link venv to system site-packages so apt-installed cv2 is available
if [ -x ./venv/bin/python ]; then
  PYVER=$(./venv/bin/python -c "import sys; print(f'{sys.version_info.major}.{sys.version_info.minor}')")
  SITE_PACKAGES="venv/lib/python${PYVER}/site-packages"
  mkdir -p "${SITE_PACKAGES}"
  echo "/usr/lib/python3/dist-packages" | tee "${SITE_PACKAGES}/system-site-packages.pth" > /dev/null
fi

echo "== Upgrade pip/setuptools/wheel in venv using proxy (if venv exists) =="
if [ -x ./venv/bin/python ]; then
  ./venv/bin/python -m pip install --upgrade pip setuptools wheel --proxy ${PROXY_URL} || true
  ./venv/bin/pip install --proxy ${PROXY_URL} flask flask-cors flask-socketio || true
fi

echo "== Restart backend and show logs =="
pkill -f backend_server.py || true
nohup ./venv/bin/python python_scripts/backend_server.py > backend.log 2>&1 &

sleep 3

echo "== backend.log (tail 200) =="
tail -n 200 backend.log || true

echo "== Preview request =="
if curl -sS http://localhost:64020/api/calibration/preview -o /tmp/preview.jpg; then
  ls -lh /tmp/preview.jpg || true
else
  echo "preview failed"
fi

echo "== Auto-detect request =="
if curl -sS -X POST http://localhost:64020/api/calibration/auto-detect -H 'Content-Type: application/json' -d '{}' ; then
  true
else
  echo 'auto-detect failed'
fi

echo "== Done script =="
