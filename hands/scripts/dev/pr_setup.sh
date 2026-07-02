#!/usr/bin/env bash
# hands/scripts/dev/pr_setup.sh
# One-command PR review setup: checks out a GitHub PR, builds it, and reports
# database migration status so the local schema can be aligned before testing.
#
# Usage: pr-setup <pr-number> [project_dir]
set -uo pipefail

PR="${1:-}"
DIR="${2:-.}"
[ -z "$PR" ] && { echo "usage: pr-setup <pr-number> [project_dir]"; exit 2; }

cd "$DIR" || { echo "pr-setup: no such directory: $DIR"; exit 1; }
command -v gh >/dev/null || { echo "pr-setup: gh CLI not installed (brew install gh)"; exit 1; }
git rev-parse --is-inside-work-tree >/dev/null 2>&1 || { echo "pr-setup: not a git repository"; exit 1; }

echo "── 1/3 checkout PR #$PR"
gh pr checkout "$PR" || exit 1
gh pr view "$PR" --json title,author,headRefName \
  --template '   {{.title}} — {{.author.login}} ({{.headRefName}})' 2>/dev/null && echo

echo "── 2/3 build"
ROOT="${SUNEEL_WORKSPACE:-$HOME/SuneelWorkSpace}"
if [ -f pom.xml ] || [ -f build.gradle ] || [ -f build.gradle.kts ]; then
  "$ROOT/hands/bin/java-build" build . || exit 1
elif [ -f package.json ]; then
  npm install --no-fund --no-audit 2>&1 | tail -2
else
  echo "   no recognized build file — skipped"
fi

echo "── 3/3 database schema"
MIG_DIR=""
for d in src/main/resources/db/migration src/main/resources/db/changelog; do
  [ -d "$d" ] && MIG_DIR="$d" && break
done
if [ -n "$MIG_DIR" ]; then
  COUNT=$(find "$MIG_DIR" -type f | wc -l | tr -d ' ')
  LATEST=$(find "$MIG_DIR" -type f | sort | tail -1)
  echo "   $COUNT migration file(s); latest: ${LATEST#"$MIG_DIR"/}"
  BASE=$(git merge-base HEAD origin/HEAD 2>/dev/null || git merge-base HEAD main 2>/dev/null || true)
  if [ -n "$BASE" ]; then
    NEW=$(git diff --name-only "$BASE"...HEAD -- "$MIG_DIR" | sed 's/^/     + /')
    [ -n "$NEW" ] && echo "   migrations introduced by this PR:" && echo "$NEW" \
      || echo "   no new migrations in this PR"
  fi
  echo "   → if the app fails on schema errors: refresh the dev DB (dev-stack down/up) and rerun migrations"
else
  echo "   no Flyway/Liquibase migrations found — skipped"
fi

echo "✅ pr-setup complete: PR #$PR ready for local review"
