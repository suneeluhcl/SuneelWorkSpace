---
name: adwi-commit
description: Pre-commit safety checklist for Adwi. Runs syntax check, 3-file NLU sync, and Gmail regression tests before committing. Ensures CLAUDE.md and backlog are up to date. Use before every git commit on this repo.
---

You are running the Adwi pre-commit checklist. Follow each step in order and stop if anything fails.

## Pre-commit checklist

### 1. Syntax check
```bash
python3 -m py_compile adwi/adwi_cli.py && \
python3 -m py_compile adwi/logs/simeval/run_large_eval.py && \
python3 -m py_compile adwi/logs/simeval/run_large_eval_p2.py && \
echo "✓ All syntax OK"
```
**Stop if any fail.**

### 2. Three-file NLU sync
Run `/adwi-sync-check` to verify intent patterns are consistent across all 3 files.

### 3. Fast regression test
Run `/adwi-check` (syntax + Gmail NLU regression suite, ~5 seconds).
**Stop if any tests fail.**

### 4. CLAUDE.md currency check
- Is the eval table in CLAUDE.md current? (matches the most recent eval run if one was done this session)
- If eval was run and pass rates changed, update the table before committing.

### 5. Backlog currency check
- Were any NHR items applied? If yes, verify they're marked `✅ Applied` in `adwi/adwi/spine/docs/NLU_REPAIR_BACKLOG.md`.
- Were any bugs fixed? Verify `notes/adwi-mistakes-and-fixes.md` has an entry.

### 6. Git status review
```bash
git diff --stat HEAD
git status --short
```
Review the changed files. Confirm nothing in `secrets/`, `config/.env`, or `*.db` files is staged.

### 7. Stage and commit
Stage only the relevant files (never `git add -A` blindly):
```bash
git add <specific files>
git diff --cached --name-only  # verify what's staged
```

Then commit with a message following this pattern:
- NLU fixes: `nlu: apply NHR-XXX — <description>`
- Feature additions: `feat: <description>`
- Bug fixes: `fix: <description>`  
- Docs updates: `docs: update <what>`
- Eval/analysis: `eval: <description>`

**Never use `--no-verify`.**

## After commit
Run `bin/adwi-git-backup` if you want to push to remote immediately (otherwise the 30-min LaunchAgent will do it).
