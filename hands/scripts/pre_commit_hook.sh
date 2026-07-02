#!/usr/bin/env bash
# pre_commit_hook.sh
# codellama reviews the staged diff before every commit.
# Issues printed as warnings — commit is NOT blocked (warn-only mode).

set -euo pipefail

WORKSPACE="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
OLLAMA_BASE="http://localhost:11434"
LOG="$WORKSPACE/blood/logs/pre_commit_review.jsonl"
MIN_DIFF_LINES=5

# Only run if Ollama is reachable
if ! curl -sf "$OLLAMA_BASE/api/tags" -o /dev/null 2>/dev/null; then
  exit 0
fi

# Get the staged diff (Python files only). head closing the pipe early on a
# large diff sends SIGPIPE back to git diff; under pipefail that would abort
# the whole hook, so fall back to an empty diff instead of failing the commit.
DIFF=$(git diff --cached --diff-filter=ACM -- "*.py" 2>/dev/null | head -200) || DIFF=""

if [ -z "$DIFF" ] || [ "$(echo "$DIFF" | wc -l)" -lt "$MIN_DIFF_LINES" ]; then
  exit 0
fi

PROMPT="Review this Python diff from SuneelWorkSpace for bugs, security issues, or bad patterns. Be brief. List only real issues with file:line. If clean, say LGTM.

$DIFF"

PAYLOAD=$(python3 -c "import json,sys; print(json.dumps({'model':'codellama','prompt':sys.argv[1],'stream':False,'options':{'temperature':0.1,'num_ctx':4096,'num_predict':300}}))" "$PROMPT" 2>/dev/null)

RESPONSE=$(curl -sf --max-time 30 -X POST "$OLLAMA_BASE/api/generate" \
  -H "Content-Type: application/json" \
  -d "$PAYLOAD" 2>/dev/null | python3 -c "import json,sys; d=json.loads(sys.stdin.read()); print(d.get('response','').strip())" 2>/dev/null || echo "")

if [ -z "$RESPONSE" ]; then
  exit 0
fi

# Log the review — all dynamic values passed via argv, nothing interpolated into code
DIFF_LINES=$(printf '%s' "$DIFF" | wc -l | tr -d ' ')
python3 -c "
import json, os, sys
from datetime import datetime, timezone
log, response, diff_lines = sys.argv[1], sys.argv[2], int(sys.argv[3])
os.makedirs(os.path.dirname(log), exist_ok=True)
with open(log, 'a') as f:
    f.write(json.dumps({'ts': datetime.now(timezone.utc).isoformat(),
                        'response': response[:500], 'diff_lines': diff_lines}) + '\n')
" "$LOG" "$RESPONSE" "$DIFF_LINES" 2>/dev/null || true

# Print review — warn only, don't block
if echo "$RESPONSE" | grep -qiE "issue|error|warning|security|bug|problem|risk|CRITICAL|HIGH"; then
  echo ""
  echo "⚠️  codellama pre-commit review:"
  echo "$RESPONSE" | head -20
  echo ""
fi

exit 0
