#!/bin/bash
W="$(cd "$(dirname "$0")/../.." && pwd)"
source "$W/.venv/bin/activate" 2>/dev/null || true
cd "$W"
exec python3 lab/lab/evolution/engine.py start
