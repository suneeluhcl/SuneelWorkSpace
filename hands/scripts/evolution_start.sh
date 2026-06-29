#!/bin/bash
W="${SUNEEL_WORKSPACE:-$HOME/SuneelWorkSpace}"
source "$W/.venv/bin/activate" 2>/dev/null || true
cd "$W"
exec python3 hands/scripts/evolution_daemon.py "$@"
