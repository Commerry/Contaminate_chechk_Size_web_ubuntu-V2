#!/usr/bin/env bash
set -euo pipefail

# Install backend Python requirements on Raspberry Pi (uses piwheels)
# Usage: sudo -H bash install_requirements_pi.sh
# or run as the 'pi' user (no sudo) when connected to the internet

ROOT_DIR="$(cd "$(dirname "$0")/../.." && pwd)"
REQ_FILE="$ROOT_DIR/python_scripts/backend_requirements.txt"
VENV_DIR="$ROOT_DIR/venv"
LOGFILE="$ROOT_DIR/pip_install.log"

RETRIES=3
SLEEP_BETWEEN_RETRIES=5

echo "[install] Project root: $ROOT_DIR"
echo "[install] Requirements file: $REQ_FILE"

if [ ! -f "$REQ_FILE" ]; then
  echo "ERROR: requirements file not found: $REQ_FILE" >&2
  exit 2
fi

if ! command -v python3 >/dev/null 2>&1; then
  echo "ERROR: python3 not found in PATH" >&2
  exit 3
fi

echo "[install] Creating virtual environment at $VENV_DIR (if missing)"
python3 -m venv "$VENV_DIR"

echo "[install] Activating venv"
# shellcheck disable=SC1091
source "$VENV_DIR/bin/activate"

echo "[install] Upgrading pip, wheel, setuptools"
pip install --upgrade pip wheel setuptools

install_reqs() {
  echo "[install] pip install (piwheels preferred) -> log: $LOGFILE"
  pip install --prefer-binary --no-cache-dir \
    --index-url=https://www.piwheels.org/simple \
    --extra-index-url=https://pypi.org/simple \
    -r "$REQ_FILE" 2>&1 | tee "$LOGFILE"
}

i=0
until [ "$i" -ge $RETRIES ]; do
  if install_reqs; then
    echo "[install] Requirements installed successfully"
    exit 0
  fi
  i=$((i+1))
  echo "[install] Attempt $i/$RETRIES failed; retrying in ${SLEEP_BETWEEN_RETRIES}s..."
  sleep $SLEEP_BETWEEN_RETRIES
done

echo "ERROR: Failed to install requirements after $RETRIES attempts. See $LOGFILE" >&2
exit 1
