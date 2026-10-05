#!/usr/bin/env bash
set -euo pipefail
cd "$(dirname "$0")"
python3 -m http.server 4173 >/tmp/omasteamdeck.log 2>&1 &
PID=$!
trap 'kill "$PID" 2>/dev/null || true' EXIT
sleep .5
if command -v xdg-open >/dev/null; then xdg-open http://127.0.0.1:4173; fi
wait "$PID"
