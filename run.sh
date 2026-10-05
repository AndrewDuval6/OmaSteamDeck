#!/usr/bin/env bash
set -euo pipefail
cd "$(dirname "$(readlink -f "$0")")"
if [[ -x .venv/bin/python ]]; then
  PYTHON=.venv/bin/python
else
  PYTHON=python3
fi
"$PYTHON" -m omasteamdeck.runtime "$@"
exec "$PYTHON" -m omasteamdeck.app "$@"
