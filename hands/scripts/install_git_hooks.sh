#!/usr/bin/env bash
# install_git_hooks.sh
# Installs the codellama pre-commit review hook into .git/hooks/

set -euo pipefail
WORKSPACE="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
HOOKS_DIR="$WORKSPACE/.git/hooks"
PRE_COMMIT="$HOOKS_DIR/pre-commit"

if [ ! -d "$HOOKS_DIR" ]; then
  echo "No .git/hooks directory found at $HOOKS_DIR"
  exit 1
fi

# Write the pre-commit hook
cat > "$PRE_COMMIT" << 'HOOK'
#!/usr/bin/env bash
WORKSPACE="$(git rev-parse --show-toplevel 2>/dev/null || echo "")"
if [ -n "$WORKSPACE" ] && [ -f "$WORKSPACE/hands/scripts/pre_commit_hook.sh" ]; then
  bash "$WORKSPACE/hands/scripts/pre_commit_hook.sh"
fi
HOOK

chmod +x "$PRE_COMMIT"
echo "Installed pre-commit hook → $PRE_COMMIT"
echo "codellama will review Python diffs before every commit (warn-only, won't block)."
