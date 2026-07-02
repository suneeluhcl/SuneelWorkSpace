#!/usr/bin/env bash
# prompt-rollback — Roll back to the previous prompt version
set -euo pipefail

WORKSPACE="${WORKSPACE:-$HOME/SuneelWorkSpace}"
VERSIONS_DIR="$WORKSPACE/dna/identity/prompts/versions"
LOG_FILE="$WORKSPACE/blood/logs/prompt_versions.log"

CURRENT_LINK="$VERSIONS_DIR/identity_prompt_current.md"
if [[ ! -L "$CURRENT_LINK" ]]; then
  echo "❌ No current symlink found at $CURRENT_LINK"
  exit 1
fi

CURRENT_TARGET=$(readlink "$CURRENT_LINK")
CURRENT_NUM=$(echo "$CURRENT_TARGET" | grep -o '[0-9]*' | tail -1)

if [[ "$CURRENT_NUM" -le 1 ]]; then
  echo "❌ Already at v1 — cannot roll back further"
  exit 1
fi

PREV_NUM=$((CURRENT_NUM - 1))
PREV_VERSION="v${PREV_NUM}"
PREV_FILE="$VERSIONS_DIR/identity_prompt_${PREV_VERSION}.md"

if [[ ! -f "$PREV_FILE" ]]; then
  echo "❌ Previous version file not found: $PREV_FILE"
  exit 1
fi

cd "$VERSIONS_DIR"
ln -sf "identity_prompt_${PREV_VERSION}.md" "identity_prompt_current.md"

mkdir -p "$(dirname "$LOG_FILE")"
echo "$(date -u +"%Y-%m-%dT%H:%M:%SZ") rolled back from v${CURRENT_NUM} to ${PREV_VERSION}" >> "$LOG_FILE"

echo "✅ Rolled back: v${CURRENT_NUM} → ${PREV_VERSION}"
echo "   Current prompt: identity_prompt_${PREV_VERSION}.md"
