#!/usr/bin/env bash
# prompt-new — Create a new version of the identity prompt for editing
set -euo pipefail

WORKSPACE="${WORKSPACE:-$HOME/SuneelWorkSpace}"
VERSIONS_DIR="$WORKSPACE/dna/dna/dna/identity/prompts/versions"
LOG_FILE="$WORKSPACE/blood/logs/prompt_versions.log"
TODAY=$(date +"%Y-%m-%d")

# Find current version number from symlink
CURRENT_LINK="$VERSIONS_DIR/identity_prompt_current.md"
if [[ -L "$CURRENT_LINK" ]]; then
  CURRENT_TARGET=$(readlink "$CURRENT_LINK")
  CURRENT_VER=$(echo "$CURRENT_TARGET" | grep -o 'v[0-9]*' | tail -1)
  CURRENT_NUM="${CURRENT_VER#v}"
else
  CURRENT_NUM=1
fi

NEXT_NUM=$((CURRENT_NUM + 1))
NEW_VER="v${NEXT_NUM}"
NEW_FILE="$VERSIONS_DIR/identity_prompt_${NEW_VER}.md"

if [[ -f "$NEW_FILE" ]]; then
  echo "Version $NEW_VER already exists: $NEW_FILE"
  exit 1
fi

# Copy current as new version with updated header
CURRENT_FILE="$VERSIONS_DIR/identity_prompt_v${CURRENT_NUM}.md"
if [[ ! -f "$CURRENT_FILE" ]]; then
  CURRENT_FILE="$WORKSPACE/dna/dna/dna/identity/prompts/identity_prompt.md"
fi

# Write new version file with YAML frontmatter
cat > "$NEW_FILE" << EOF
---
version: ${NEW_VER}
created: ${TODAY}
status: draft
eval_score: null
promoted_from: v${CURRENT_NUM}
notes: "Draft — run prompt-eval --version ${NEW_VER} to score"
---

$(grep -v '^---' "$CURRENT_FILE" | sed '/^version:/d;/^created:/d;/^status:/d;/^eval_score:/d;/^promoted_from:/d;/^notes:/d' | sed '/^---$/d')
EOF

echo "✅ Created identity_prompt_${NEW_VER}.md"
echo "   Edit it, then run: prompt-eval --version ${NEW_VER}"
echo "   Promote if passing: prompt-promote ${NEW_VER}"

mkdir -p "$(dirname "$LOG_FILE")"
echo "$(date -u +"%Y-%m-%dT%H:%M:%SZ") created ${NEW_VER} from v${CURRENT_NUM}" >> "$LOG_FILE"
