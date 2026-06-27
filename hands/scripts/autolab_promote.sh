#!/usr/bin/env bash
set -euo pipefail

WORKSPACE="${WORKSPACE:-$HOME/SuneelWorkSpace}"
python3 "$WORKSPACE/lab/lab/autolab/promotion_gate.py" "$@"
