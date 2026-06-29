#!/usr/bin/env bash
# hands/scripts/rebuild_model.sh
# Refresh the suneelworkspace Ollama model from the latest training data.
#
# Steps:
#   1. Run autotrainer.py to extract new instruction pairs into training_dataset.json
#   2. Run build_modelfile.py to regenerate the Modelfile
#   3. Run: ollama create suneelworkspace -f Modelfile.workspace
#
# Usage: rebuild-model [--skip-train] [--dry-run]

set -euo pipefail

WORKSPACE="${SUNEEL_WORKSPACE:-$HOME/SuneelWorkSpace}"
MODEL_DIR="$WORKSPACE/dna/agents/hermes/ollama_models"
PYTHON="${WORKSPACE}/.venv/bin/python3"
[ -f "$PYTHON" ] || PYTHON="python3"

SKIP_TRAIN=0
DRY_RUN=0
for arg in "$@"; do
    [[ "$arg" == "--skip-train" ]] && SKIP_TRAIN=1
    [[ "$arg" == "--dry-run" ]]    && DRY_RUN=1
done

echo "[rebuild-model] SuneelWorkSpace model rebuild"
echo "  workspace : $WORKSPACE"
echo "  model_dir : $MODEL_DIR"
echo "  dry_run   : $DRY_RUN"
echo ""

# ── Step 1: extract new training pairs ────────────────────────────────────────
if [ "$SKIP_TRAIN" -eq 0 ]; then
    echo "[rebuild-model] step 1/3 — extracting training data..."
    if [ "$DRY_RUN" -eq 1 ]; then
        echo "  [dry-run] would run: $PYTHON $MODEL_DIR/autotrainer.py"
    else
        "$PYTHON" "$MODEL_DIR/autotrainer.py" || { echo "  autotrainer failed — continuing"; }
    fi
else
    echo "[rebuild-model] step 1/3 — skipped (--skip-train)"
fi

# ── Step 2: regenerate Modelfile ──────────────────────────────────────────────
echo "[rebuild-model] step 2/3 — regenerating Modelfile..."
if [ "$DRY_RUN" -eq 1 ]; then
    echo "  [dry-run] would run: $PYTHON $MODEL_DIR/build_modelfile.py"
else
    if [ -f "$MODEL_DIR/build_modelfile.py" ]; then
        "$PYTHON" "$MODEL_DIR/build_modelfile.py" \
            || { echo "  build_modelfile failed — continuing with existing Modelfile"; }
    else
        echo "  build_modelfile.py not found — skipping"
    fi
fi

# ── Step 3: rebuild Ollama model ──────────────────────────────────────────────
echo "[rebuild-model] step 3/3 — creating Ollama model 'suneelworkspace'..."
MODELFILE="$MODEL_DIR/Modelfile.workspace"

if [ ! -f "$MODELFILE" ]; then
    echo "  ERROR: $MODELFILE not found — cannot rebuild model"
    exit 1
fi

if [ "$DRY_RUN" -eq 1 ]; then
    echo "  [dry-run] would run: ollama create suneelworkspace -f $MODELFILE"
    echo "[rebuild-model] dry-run complete"
    exit 0
fi

if ! command -v ollama &>/dev/null; then
    echo "  ERROR: ollama not found on PATH"
    exit 1
fi

ollama create suneelworkspace -f "$MODELFILE"
echo ""
echo "[rebuild-model] done — model 'suneelworkspace' rebuilt successfully"
