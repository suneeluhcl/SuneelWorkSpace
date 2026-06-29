#!/usr/bin/env bash
# test-daemon-start — launch the real-time test watcher daemon
# Monitors 12 organ directories; runs organ-specific tests on file save.
# Streams events to the dashboard via POST /api/tests/event.
set -euo pipefail

WORKSPACE="${SUNEEL_WORKSPACE:-$HOME/SuneelWorkSpace}"
VENV_PY="$WORKSPACE/.venv/bin/python3"
PYTHON="${VENV_PY:-python3}"
[[ -x "$VENV_PY" ]] && PYTHON="$VENV_PY"

LOG="$WORKSPACE/blood/logs/test_daemon.log"
mkdir -p "$(dirname "$LOG")"

echo "[test-daemon] starting — workspace: $WORKSPACE"
echo "[test-daemon] log: $LOG"
echo "[test-daemon] press Ctrl-C to stop"

exec "$PYTHON" "$WORKSPACE/tests/test_daemon.py" "$@" 2>&1 | tee -a "$LOG"
