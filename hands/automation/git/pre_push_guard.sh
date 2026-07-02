#!/usr/bin/env bash
# Git pre-push hook — validates READMEs, applies smart push policy, blocks on failure.
# Install: ln -sf ~/SuneelWorkSpace/hands/automation/git/pre_push_guard.sh .git/hooks/pre-push
#
# Flow:
#   1. Detect changed files vs remote
#   2. Update READMEs for affected folders (rule-based, fast)
#   3. Rebuild root README
#   4. Apply smart push policy (spine/config/readme_policy.json)
#   5. Run validator — exit 1 to block push if failed
set -uo pipefail

WORKSPACE="$(git rev-parse --show-toplevel 2>/dev/null || echo "$HOME/SuneelWorkSpace")"
VENV_PY="$WORKSPACE/.venv/bin/python3"
POLICY_FILE="$WORKSPACE/spine/config/readme_policy.json"
LOG="$WORKSPACE/blood/logs/readme_intelligence.log"
TIMESTAMP="$(date '+%Y-%m-%d %H:%M:%S')"

log() { echo "[$TIMESTAMP] [pre-push] $*" | tee -a "$LOG"; }

# Safe mode: check policy file and env
SAFE_MODE="false"
if [[ "${README_SAFE_MODE:-}" =~ ^(1|true|yes)$ ]]; then
  SAFE_MODE="true"
fi

# Sanity: Python available?
if [[ ! -x "$VENV_PY" ]]; then
  echo "⚠️  README guard: .venv/bin/python3 not found — skipping (non-blocking)"
  exit 0
fi

echo ""
echo "🔍 README pre-push validation (Phase 3)..."
[[ "$SAFE_MODE" == "true" ]] && echo "  ⚡ SAFE MODE: all blocks downgraded to warnings"

# Load policy thresholds from JSON
HEALTH_BLOCK_THRESHOLD=40
HEALTH_WARN_THRESHOLD=60
DRIFT_SECONDS=120
if [[ -f "$POLICY_FILE" ]] && command -v python3 &>/dev/null; then
  HEALTH_BLOCK_THRESHOLD=$(python3 -c "import json; d=json.load(open('$POLICY_FILE')); print(d.get('thresholds',{}).get('health_block_threshold',40))" 2>/dev/null || echo 40)
  HEALTH_WARN_THRESHOLD=$(python3 -c "import json; d=json.load(open('$POLICY_FILE')); print(d.get('thresholds',{}).get('health_warn_threshold',60))" 2>/dev/null || echo 60)
fi

BLOCKED=0
WARNINGS=0

_block_or_warn() {
  local severity="$1"
  local rule_id="$2"
  local message="$3"
  if [[ "$SAFE_MODE" == "true" || "$severity" != "critical" && "$severity" != "high" ]]; then
    echo "  ⚠️  WARN [$rule_id]: $message"
    WARNINGS=$((WARNINGS + 1))
  else
    echo "  ❌ BLOCK [$rule_id]: $message"
    BLOCKED=1
  fi
}

while read local_ref local_sha remote_ref remote_sha; do
  # Determine changed files
  if [[ "$remote_sha" == "0000000000000000000000000000000000000000" ]]; then
    CHANGED="$(git diff --name-only HEAD~1 HEAD 2>/dev/null || echo "")"
  else
    CHANGED="$(git diff --name-only "${remote_sha}..${local_sha}" 2>/dev/null || echo "")"
  fi

  if [[ -z "$CHANGED" ]]; then
    echo "  ✅ No file changes — README check skipped."
    continue
  fi

  CHANGED_COUNT=$(echo "$CHANGED" | wc -l | tr -d ' ')
  echo "  📂 $CHANGED_COUNT changed file(s) detected."

  # Step 1: Update READMEs for changed folders
  echo "  Step 1/4: Updating READMEs for changed folders..."
  declare -A UPDATED_FOLDERS_MAP=()
  while IFS= read -r f; do
    [[ -z "$f" ]] && continue
    FOLDER="$(dirname "$WORKSPACE/$f")"
    [[ "$FOLDER" == "$WORKSPACE" ]] && continue
    [[ ! -d "$FOLDER" ]] && continue
    case "$FOLDER" in
      */.git*|*/node_modules*|*/.venv*|*/__pycache__*|*/logs/*|*/nerve_inbox*) continue ;;
    esac
    [[ -n "${UPDATED_FOLDERS_MAP[$FOLDER]:-}" ]] && continue
    UPDATED_FOLDERS_MAP["$FOLDER"]=1
    README_SAFE_MODE="$SAFE_MODE" "$VENV_PY" "$WORKSPACE/hands/automation/readme/readme_generator.py" \
      "$FOLDER" --no-claude >> "$LOG" 2>&1 || true
  done <<< "$CHANGED"

  # Step 2: Rebuild root README
  echo "  Step 2/4: Rebuilding root README..."
  "$VENV_PY" "$WORKSPACE/hands/automation/readme/root_synthesizer.py" >> "$LOG" 2>&1 || \
    log "Root rebuild failed (non-fatal)"

  # Step 3: Apply smart push policy per changed folder
  echo "  Step 3/4: Applying smart push policy..."
  for FOLDER in "${!UPDATED_FOLDERS_MAP[@]:-}"; do
    [[ -z "$FOLDER" ]] && continue
    README="$FOLDER/README.md"
    REL_FOLDER="${FOLDER#$WORKSPACE/}"

    # Policy: missing README
    if [[ ! -f "$README" ]]; then
      _block_or_warn "critical" "missing_readme" "Missing README.md in $REL_FOLDER — run: readme-repair $REL_FOLDER"
      continue
    fi

    # Policy: README drift
    README_MTIME=$(stat -f %m "$README" 2>/dev/null || stat -c %Y "$README" 2>/dev/null || echo 0)
    FOLDER_MAX_MTIME=$(find "$FOLDER" -maxdepth 1 -not -name "README*" -not -name ".*" -newer "$README" 2>/dev/null | wc -l | tr -d ' ')
    if [[ "$FOLDER_MAX_MTIME" -gt 0 ]]; then
      _block_or_warn "high" "outdated_readme" "README drift in $REL_FOLDER — run: readme-update $REL_FOLDER"
    fi

    # Policy: health score (from cache)
    # Use env vars to pass paths into Python — never string-interpolate into -c code
    HEALTH_SCORE=100
    CACHE="$WORKSPACE/spine/readme_health_cache.json"
    if [[ -f "$CACHE" ]]; then
      HEALTH_SCORE=$(README_CACHE="$CACHE" README_FOLDER="$REL_FOLDER" python3 -c \
        'import json,os; c=json.load(open(os.environ["README_CACHE"])); e=c.get(os.environ["README_FOLDER"],{}); print(e.get("health_score",100) if isinstance(e,dict) else 100)' \
        2>/dev/null || echo 100)
    fi

    if [[ "$HEALTH_SCORE" -lt "$HEALTH_BLOCK_THRESHOLD" ]]; then
      _block_or_warn "critical" "health_score_critical" "$REL_FOLDER health=$HEALTH_SCORE (below $HEALTH_BLOCK_THRESHOLD) — run: readme-score $REL_FOLDER"
    elif [[ "$HEALTH_SCORE" -lt "$HEALTH_WARN_THRESHOLD" ]]; then
      _block_or_warn "medium" "health_score_low" "$REL_FOLDER health=$HEALTH_SCORE (below $HEALTH_WARN_THRESHOLD)"
    fi
  done

  # Step 4: Validator — final gate
  echo "  Step 4/4: Running validator..."
  if ! "$VENV_PY" "$WORKSPACE/hands/automation/readme/validator.py" >> "$LOG" 2>&1; then
    _block_or_warn "critical" "validator_failed" "Validation failed — run: readme-validate"
  fi

done

echo ""
if [[ "$BLOCKED" == "1" ]]; then
  echo "❌ Push BLOCKED by smart policy. Fix issues above and retry."
  echo "   Tip: run 'README_SAFE_MODE=1 git push' to bypass in emergencies."
  log "Push blocked: BLOCKED=$BLOCKED WARNINGS=$WARNINGS"
  exit 1
fi

if [[ "$WARNINGS" -gt 0 ]]; then
  echo "⚠️  $WARNINGS warning(s) — push allowed but please fix soon."
fi

echo "✅ README validation passed. Proceeding with push."
log "Push allowed: WARNINGS=$WARNINGS"
exit 0
