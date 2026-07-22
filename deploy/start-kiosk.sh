#!/usr/bin/env bash
# Launch the PSE Vision web UI full-screen (kiosk) once the backend is up.
# Meant to be started by the desktop autostart entry after graphical login.
set -u

URL="${PSE_URL:-http://localhost:64020}"

# 1) Wait for the backend to answer (up to ~90s on cold boot)
for i in $(seq 1 90); do
  if curl -sf -o /dev/null "$URL"; then
    break
  fi
  sleep 1
done

# 2) Stop the screen from blanking / going to sleep (best-effort; X11)
if command -v xset >/dev/null 2>&1; then
  xset s off || true
  xset -dpms || true
  xset s noblank || true
fi

# 3) Find an available browser. Chromium/Chrome first (their kiosk mode hides
#    every control), Firefox as a fallback since it ships on most desktops.
BROWSER=""
for b in chromium-browser chromium google-chrome google-chrome-stable firefox; do
  if command -v "$b" >/dev/null 2>&1; then BROWSER="$b"; break; fi
done
if [ -z "$BROWSER" ]; then
  echo "[kiosk] No browser found. Install one with: sudo apt install -y chromium-browser" >&2
  exit 1
fi

# Firefox takes the URL directly and has no --app equivalent. It also hands the
# URL to an already-running instance and exits, which silently skips kiosk mode,
# so give the kiosk window its own profile and keep it off the remote channel.
if [ "$BROWSER" = "firefox" ]; then
  exec firefox --kiosk --no-remote --profile "${PSE_FF_PROFILE:-$HOME/.pse-kiosk-profile}" "$URL"
fi

# 4) Launch in kiosk mode. Flags suppress the 'restore pages' / info bars so it
#    comes up clean every boot.
exec "$BROWSER" \
  --kiosk \
  --start-fullscreen \
  --noerrdialogs \
  --disable-infobars \
  --disable-session-crashed-bubble \
  --disable-features=TranslateUI \
  --overscroll-history-navigation=0 \
  --check-for-update-interval=31536000 \
  --incognito \
  --app="$URL"
