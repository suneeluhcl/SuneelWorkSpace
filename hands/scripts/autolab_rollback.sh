#!/usr/bin/env bash
WORKSPACE="${WORKSPACE:-$HOME/SuneelWorkSpace}"
EXP_ID="${1:-}"
if [[ -z "$EXP_ID" ]]; then
  echo "Usage: autolab-rollback <experiment_id>"
  exit 1
fi
python3 "$WORKSPACE/lab/lab/autolab/promotion_gate.py" --rollback "$EXP_ID"
