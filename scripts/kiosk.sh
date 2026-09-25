#!/usr/bin/env bash
# Open the local dashboard in a fullscreen browser. SSH is left alone.
# Disabled unless RP5_UI_KIOSK=true. Experimental on Pocknix until confirmed on hardware.
set -euo pipefail

if [[ "${RP5_UI_KIOSK:-false}" != "true" ]]; then
  printf '[!] kiosk is off\n'
  exit 0
fi

PORT="${RP5_LLM_PORT:-8080}"
URL="http://127.0.0.1:${PORT}/"
BROWSER=""
for candidate in chromium chromium-browser google-chrome firefox; do
  if command -v "$candidate" >/dev/null 2>&1; then
    BROWSER=$candidate
    break
  fi
done

if [[ -z "$BROWSER" ]]; then
  printf '[!] kiosk is on, but no chromium or firefox binary was found\n'
  exit 0
fi

case "$BROWSER" in
  firefox)
    exec "$BROWSER" --kiosk "$URL"
    ;;
  *)
    exec "$BROWSER" --kiosk --no-first-run --disable-translate "$URL"
    ;;
esac
