#!/usr/bin/env bash
set -euo pipefail
cd "$(dirname "$0")"
PORT=4173
python3 -m http.server "$PORT" >/tmp/omasteamdeck.log 2>&1 &
SERVER=$!
trap 'kill "$SERVER" 2>/dev/null || true' EXIT
sleep .4
URL="http://127.0.0.1:$PORT"
# Prefer an installed Chromium-family browser in standalone app/fullscreen mode.
for B in chromium chromium-browser google-chrome-stable google-chrome brave-browser brave; do
  if command -v "$B" >/dev/null 2>&1; then exec "$B" --app="$URL" --start-fullscreen --no-first-run; fi
done
xdg-open "$URL"
wait "$SERVER"
