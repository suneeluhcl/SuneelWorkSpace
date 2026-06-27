#!/usr/bin/env bash
# prompt-promote — Promote a passing prompt version (score >= 70)
set -euo pipefail

WORKSPACE="${WORKSPACE:-$HOME/SuneelWorkSpace}"
VERSIONS_DIR="$WORKSPACE/dna/dna/dna/identity/prompts/versions"
RESULTS_DIR="$WORKSPACE/dna/dna/dna/identity/prompts/eval/eval_results"
LOG_FILE="$WORKSPACE/blood/logs/prompt_versions.log"

VERSION="${1:-}"
if [[ -z "$VERSION" ]]; then
  echo "Usage: prompt-promote <version>  (e.g. prompt-promote v2)"
  exit 1
fi

# Strip leading 'v' if not provided
[[ "$VERSION" == v* ]] || VERSION="v${VERSION}"

VERSION_FILE="$VERSIONS_DIR/identity_prompt_${VERSION}.md"
if [[ ! -f "$VERSION_FILE" ]]; then
  echo "❌ Version file not found: $VERSION_FILE"
  exit 1
fi

# Check for a passing eval result
PASSING_RESULT=$(python3 - "$RESULTS_DIR" "$VERSION" << 'PYEOF'
import json, sys, os
from pathlib import Path

results_dir = Path(sys.argv[1])
version = sys.argv[2]
best = None
best_score = 0

for f in results_dir.glob(f"result_{version}_*.json"):
    try:
        d = json.loads(f.read_text())
        score = d.get('overall_score', 0)
        if score >= 70 and score > best_score:
            best = f.name
            best_score = score
    except Exception:
        pass

if best:
    print(f"{best} score={best_score:.0f}")
else:
    print("NONE")
PYEOF
)

if [[ "$PASSING_RESULT" == "NONE" ]]; then
  echo "❌ No passing eval result (score >= 70) found for $VERSION"
  echo "   Run: prompt-eval --version $VERSION"
  exit 1
fi

# Update symlink
CURRENT_LINK="$VERSIONS_DIR/identity_prompt_current.md"
cd "$VERSIONS_DIR"
ln -sf "identity_prompt_${VERSION}.md" "identity_prompt_current.md"

mkdir -p "$(dirname "$LOG_FILE")"
echo "$(date -u +"%Y-%m-%dT%H:%M:%SZ") promoted ${VERSION} | result: ${PASSING_RESULT}" >> "$LOG_FILE"

echo "✅ Promoted identity_prompt_${VERSION}.md → identity_prompt_current.md"
echo "   Eval result: $PASSING_RESULT"
