#!/usr/bin/env bash
# install_eval_stack.sh
# Installs the Adwi nightly eval stack (promptfoo, DeepEval, Giskard, Playwright, k6, Langfuse optional)
#
# Usage:
#   ./scripts/install_eval_stack.sh          # install everything
#   ./scripts/install_eval_stack.sh --skip-langfuse
#   ./scripts/install_eval_stack.sh --check  # validate only, no install
#
# Prerequisites: brew, node 18+, python3 venv at adwi/.venv

set -euo pipefail

REPO_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
VENV="$REPO_ROOT/adwi/.venv"
PY="$VENV/bin/python3"
PIP="$VENV/bin/pip3"

SKIP_LANGFUSE=false
CHECK_ONLY=false

for arg in "$@"; do
  case "$arg" in
    --skip-langfuse) SKIP_LANGFUSE=true ;;
    --check) CHECK_ONLY=true ;;
  esac
done

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------
info()    { echo "  ✅ $*"; }
warn()    { echo "  ⚠️  $*"; }
fail()    { echo "  ❌ $*" >&2; }
section() { echo -e "\n─────────────────────────────────────────"; echo "  $*"; echo "─────────────────────────────────────────"; }

check_cmd() {
  if command -v "$1" &>/dev/null; then
    info "$1 found ($(command -v "$1"))"
    return 0
  else
    fail "$1 not found"
    return 1
  fi
}

# ---------------------------------------------------------------------------
# Validate prerequisites
# ---------------------------------------------------------------------------
section "Checking prerequisites"

check_cmd brew       || { fail "Install Homebrew first: https://brew.sh"; exit 1; }
check_cmd python3    || { fail "Python3 not found"; exit 1; }
check_cmd node       || warn "Node.js not found — promptfoo and Playwright will be skipped"
check_cmd npm        || warn "npm not found"

if [ -d "$VENV" ]; then
  info "Python venv found at $VENV"
else
  warn "Python venv not found at $VENV — some Python installs may fail"
  VENV=""
  PY="python3"
  PIP="pip3"
fi

if $CHECK_ONLY; then
  section "Check mode — validating existing installs"
  check_cmd k6 || warn "k6 not installed"
  command -v npx &>/dev/null && npx --yes promptfoo@latest --version 2>/dev/null && info "promptfoo available via npx" || warn "promptfoo not cached"
  $PY -c "import deepeval; print('deepeval', deepeval.__version__)" 2>/dev/null && info "deepeval installed" || warn "deepeval not installed"
  $PY -c "import giskard; print('giskard OK')" 2>/dev/null && info "giskard installed" || warn "giskard not installed"
  $PY -c "import yaml; print('pyyaml OK')" 2>/dev/null && info "pyyaml installed" || warn "pyyaml not installed"
  npx --yes playwright@latest --version 2>/dev/null && info "playwright available via npx" || warn "playwright not cached"
  echo ""
  echo "Run without --check to install missing components."
  exit 0
fi

# ---------------------------------------------------------------------------
# 1. k6 (perf testing)
# ---------------------------------------------------------------------------
section "1. Installing k6"
if command -v k6 &>/dev/null; then
  info "k6 already installed: $(k6 version 2>&1 | head -1)"
else
  brew install k6
  info "k6 installed: $(k6 version 2>&1 | head -1)"
fi

# ---------------------------------------------------------------------------
# 2. Python packages (DeepEval, Giskard, pyyaml, pandas)
# ---------------------------------------------------------------------------
section "2. Installing Python eval packages"

if [ -n "$VENV" ]; then
  $PIP install --quiet --upgrade pip

  # pyyaml (config loading)
  $PIP install --quiet "pyyaml>=6.0"
  info "pyyaml installed"

  # pandas (Giskard dependency)
  $PIP install --quiet "pandas>=2.0"
  info "pandas installed"

  # DeepEval
  $PIP install --quiet "deepeval>=0.21"
  info "deepeval installed: $($PY -c 'import deepeval; print(deepeval.__version__)')"

  # Giskard OSS
  $PIP install --quiet "giskard>=2.0"
  info "giskard installed: $($PY -c 'import giskard; print(giskard.__version__)')"

  # pytest (for DeepEval test suite)
  $PIP install --quiet "pytest>=7.0"
  info "pytest installed"

  # scikit-learn (optional, for advanced clustering — graceful fallback exists)
  $PIP install --quiet "scikit-learn>=1.3" || warn "scikit-learn install failed — using built-in k-means"
else
  warn "No venv found — skipping Python package installs"
fi

# ---------------------------------------------------------------------------
# 3. Node packages (promptfoo, Playwright) — via npx (no global install)
# ---------------------------------------------------------------------------
section "3. Caching Node packages via npx"

if command -v npx &>/dev/null; then
  # Cache promptfoo locally
  cd "$REPO_ROOT/eval/promptfoo"
  if [ ! -d node_modules ]; then
    npm init -y --quiet 2>/dev/null || true
  fi
  npx --yes promptfoo@latest --version 2>/dev/null && info "promptfoo cached" || warn "promptfoo cache failed"

  # Cache Playwright + install browser
  cd "$REPO_ROOT/eval/playwright"
  if [ ! -f package.json ]; then
    npm init -y --quiet 2>/dev/null
    npm install --save-dev @playwright/test typescript 2>/dev/null || warn "Playwright npm install failed"
  fi
  npx --yes playwright@latest install chromium 2>/dev/null \
    && info "Playwright + Chromium installed" \
    || warn "Playwright browser install failed — run 'npx playwright install chromium' manually"

  cd "$REPO_ROOT"
else
  warn "npx not found — promptfoo and Playwright skipped"
fi

# ---------------------------------------------------------------------------
# 4. Langfuse (optional Docker service)
# ---------------------------------------------------------------------------
section "4. Langfuse (optional)"

if $SKIP_LANGFUSE; then
  warn "Langfuse skipped (--skip-langfuse)"
else
  LANGFUSE_COMPOSE="$REPO_ROOT/config/langfuse/docker-compose.langfuse.yml"
  if [ -f "$LANGFUSE_COMPOSE" ]; then
    if command -v docker &>/dev/null; then
      echo "  To start Langfuse: docker compose -f $LANGFUSE_COMPOSE up -d"
      echo "  Dashboard at: http://localhost:3010"
      info "Langfuse compose file ready at $LANGFUSE_COMPOSE"
    else
      warn "Docker not found — Langfuse requires Docker"
    fi
  else
    warn "Langfuse compose file not found (optional — Phoenix covers tracing)"
  fi
fi

# ---------------------------------------------------------------------------
# 5. Create required eval directories
# ---------------------------------------------------------------------------
section "5. Creating eval directories"

mkdir -p \
  "$REPO_ROOT/eval/scenarios/seeds" \
  "$REPO_ROOT/eval/scenarios/generated" \
  "$REPO_ROOT/eval/promptfoo/results" \
  "$REPO_ROOT/eval/playwright/results" \
  "$REPO_ROOT/eval/k6/results" \
  "$REPO_ROOT/logs/nightly"

touch "$REPO_ROOT/eval/nightly/__init__.py"
touch "$REPO_ROOT/eval/giskard/__init__.py"
touch "$REPO_ROOT/eval/deepeval/__init__.py"

info "Directories created"

# ---------------------------------------------------------------------------
# 6. Install LaunchAgent (nightly eval at 3 AM)
# ---------------------------------------------------------------------------
section "6. LaunchAgent (optional — nightly at 3:00 AM)"

PLIST_TEMPLATE="$REPO_ROOT/config/launchagents/com.suneel.adwi-nightly-eval.plist.template"
PLIST_DEST="$HOME/Library/LaunchAgents/com.suneel.adwi-nightly-eval.plist"

if [ -f "$PLIST_TEMPLATE" ]; then
  if [ ! -f "$PLIST_DEST" ]; then
    # Substitute actual repo path
    sed "s|__REPO_ROOT__|$REPO_ROOT|g; s|__PYTHON__|$PY|g" \
      "$PLIST_TEMPLATE" > "$PLIST_DEST"
    launchctl load "$PLIST_DEST" 2>/dev/null && info "LaunchAgent installed (3:00 AM)" || warn "LaunchAgent load failed"
  else
    info "LaunchAgent already installed at $PLIST_DEST"
  fi
else
  warn "LaunchAgent template not found at $PLIST_TEMPLATE"
fi

# ---------------------------------------------------------------------------
# 7. Validate the full install
# ---------------------------------------------------------------------------
section "7. Validation"

echo "Running eval stack validator..."
if [ -f "$REPO_ROOT/scripts/validate_eval_stack.py" ]; then
  $PY "$REPO_ROOT/scripts/validate_eval_stack.py" || warn "Validation issues found — see above"
else
  warn "validate_eval_stack.py not found"
fi

# ---------------------------------------------------------------------------
# Summary
# ---------------------------------------------------------------------------
section "Install complete"
echo ""
echo "  Next steps:"
echo "  1. Run: python3 eval/nightly/orchestrator.py"
echo "     (or wait for nightly LaunchAgent at 3:00 AM)"
echo ""
echo "  2. Morning review:"
echo "     cat logs/nightly/latest/00_morning_brief.md"
echo ""
echo "  3. Deep DeepEval tests:"
echo "     python3 -m pytest eval/deepeval/test_nlu.py -v"
echo ""
echo "  4. Promptfoo matrix:"
echo "     cd eval/promptfoo && npx promptfoo eval"
echo ""
echo "  5. Playwright smoke:"
echo "     cd eval/playwright && npx playwright test"
echo ""
echo "  6. k6 perf:"
echo "     k6 run eval/k6/api_load.js"
