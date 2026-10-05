#!/usr/bin/env bash
set -euo pipefail
cd "$(dirname "$(readlink -f "$0")")"
if [[ -x .venv/bin/python ]]; then
  PYTHON=.venv/bin/python
else
  PYTHON=python3
fi
if ! "$PYTHON" -c 'from PySide6.QtWidgets import QApplication' 2>/dev/null; then
  echo 'OmaSteamDeck requires PySide6. See README.md for user-local setup.' >&2
  exit 1
fi
exec "$PYTHON" -m omasteamdeck.app "$@"
