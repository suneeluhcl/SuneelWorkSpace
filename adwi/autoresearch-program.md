# Adwi Autoresearch — Overnight Improvement Program

You are running as an autonomous agent in an **isolated git worktree**.
Your working directory is NOT the root repo — it is a clean branch checkout.
Your job is to loop through small, safe, targeted experiments that improve Adwi quality.
The operator is asleep. Do NOT pause to ask questions. Do NOT wait for user input.

---

## Hook warnings — DO NOT STOP for these

You may see messages like:
- `PreToolUse:Bash hook error`
- `Failed with non-blocking status code`
- `hook error`

These come from background monitoring tools (headroom, RTK). They do NOT mean your
command failed. The tool result immediately after the hook message is the real outcome.
If the actual command output looks correct, continue the loop. Only stop if the
command itself (not the hook) produced an unexpected result that blocks progress.

---

## Step 0 — Orientation (do this first, every time)

1. Confirm your location:

```bash
pwd         # must be inside .worktrees/adwi-autoresearch/<tag>
git branch  # must show adwi-autoresearch/<tag>
git status  # must be clean (no uncommitted changes yet)
```

2. Set the ROOT variable for commands that need the shared venv or root-only tools:

```bash
ROOT=/Users/MAC/SuneelWorkSpace
```

3. Read `CLAUDE.md` (present in this worktree) for NLU baseline and repo structure.
4. Read `adwi/docs/NLU_REPAIR_BACKLOG.md` for the prioritized fix list.

5. Run baseline checks to establish YOUR numbers for this session:

```bash
python3 -m py_compile adwi/adwi_cli.py && echo "syntax OK"
python3 -m unittest adwi/simlab/tests/test_nlu_regex.py 2>&1 | tail -2
adwi/bin/validate-docs 2>&1 | tail -3
$ROOT/adwi/.venv/bin/python3 -m pytest adwi/tests/test_remote_control_surface.py -q 2>&1 | tail -2
$ROOT/adwi/.venv/bin/python3 -m pytest adwi/tests/ --ignore=adwi/tests/test_search_orchestrator.py -q 2>&1 | tail -3
```

Note: `adwi/.venv/` lives in the root repo, not in this worktree. Always use `$ROOT/adwi/.venv/` for pytest.

6. Create the results TSV with a baseline row (replace `<values>` with actual numbers):

```bash
printf 'commit\tnlu_pass\tnlu_total\tdocs_pass\tdocs_total\tsec_pass\tsec_total\tstatus\tdescription\n' \
    > adwi/autoresearch-results.tsv
printf '%s\t%d\t%d\t%d\t%d\t%d\t%d\t%s\t%s\n' \
    "$(git rev-parse --short HEAD)" \
    <nlu_pass> <nlu_total> <docs_pass> <docs_total> <sec_pass> <sec_total> \
    "keep" "baseline" >> adwi/autoresearch-results.tsv
```

7. Commit the baseline (this creates the first commit on your branch):

```bash
git add adwi/autoresearch-results.tsv
git commit -m "autoresearch: baseline — session <TAG>"
```

---

## Isolation rules — your worktree vs the root repo

**You are in:** `.worktrees/adwi-autoresearch/<tag>`
**Root repo is at:** `/Users/MAC/SuneelWorkSpace`

- Do NOT `cd /Users/MAC/SuneelWorkSpace` or modify any root-repo runtime files.
- Do NOT modify `logs/adwi_system_log.md`, `obsidian-vault/`, or any `logs/` file.
- Do NOT read or modify `/Users/MAC/SuneelWorkSpace/adwi/memory.db` or `.knowledge.db`.
- Use `$ROOT/adwi/.venv/bin/python3` (absolute) for pytest; other commands work relatively.
- Your git operations (checkout, commit, reset) affect only YOUR branch in YOUR worktree.
- The root repo's `main` branch may receive auto-backup commits overnight — this does NOT affect your worktree.

---

## What you CAN edit (allowlist)

Files in your worktree, matching these paths:

```
adwi/*.py                         (adwi_cli.py, reason_engine.py, memory.py, etc.)
adwi/bin/                         (bin scripts — shell and Python)
adwi/config/*.example             (safe example/template configs only)
adwi/docs/                        (documentation)
adwi/scripts/                     (utility scripts)
adwi/services/command-api/        (Command API — read-only routes only)
adwi/services/mcp/                (MCP servers)
adwi/services/telegram-bridge/    (Telegram bridge)
adwi/simlab/                      (SimLab modules and tests)
adwi/tests/                       (test files)
adwi/automation/workflows/        (n8n workflow JSON files — source only)
adwi/autoresearch-results.tsv     (your session log — this branch only)
adwi/logs/simeval/run_large_eval.py       (NLU sync ONLY)
adwi/logs/simeval/run_large_eval_p2.py    (NLU sync ONLY)
README.md
CLAUDE.md
```

---

## What you CANNOT touch (denylist)

```
adwi/config/.env                  (live secrets)
secrets/                          (credentials)
adwi/infra/docker/n8n-data*/      (live n8n DB)
obsidian-vault/                   (personal notes)
adwi/memory.db                    (live runtime DB — root repo only)
adwi/knowledge.db                 (live runtime DB — root repo only)
adwi/training-data/               (captured training data)
logs/                             (runtime log files)
adwi/logs/simeval/                (except the two sync files listed above)
*.sqlite *.db                     (any database file)
~/Library/LaunchAgents/           (LaunchAgent plists)
```

**Never run:**
- `ollama pull/rm`, `launchctl`, `docker compose up/down`, `git push`
- `git add -A` or `git add .` — always name specific files
- `rm -rf` outside this worktree's experiment files
- `sudo`

---

## Experiment loop

Once orientation is complete, run this loop indefinitely:

### 1. Choose one narrow experiment

Priority order:
1. Fix a known failing test in `adwi/tests/` (especially `test_search_orchestrator.py` — 13 failures)
2. Apply an open NHR item from `adwi/docs/NLU_REPAIR_BACKLOG.md`
3. Add missing test coverage for an untested command or edge case
4. Fix a stale doc reference (run `adwi/bin/validate-docs` to find them)
5. Improve a bin script for robustness
6. Add a new NLU eval scenario (sync to all 3 files)

Do NOT: large refactors, multi-file architectural changes, anything touching the denylist.

### 2. Make the change

Edit only allowlisted files. Keep the diff small and focused.

### 3. Fast gate (always run first)

```bash
python3 -m py_compile adwi/adwi_cli.py 2>&1 && echo "syntax OK"
python3 -m unittest adwi/simlab/tests/test_nlu_regex.py 2>&1 | tail -2
```

If fast gate fails → revert immediately, log as `crash`, continue the loop.
If you see hook warnings during these commands → ignore the warnings; read the actual test output.

### 4. Full gate (before keeping)

```bash
adwi/bin/validate-docs 2>&1 | tail -3
$ROOT/adwi/.venv/bin/python3 -m pytest adwi/tests/test_remote_control_surface.py -q 2>&1 | tail -2
$ROOT/adwi/.venv/bin/python3 -m pytest adwi/tests/ --ignore=adwi/tests/test_search_orchestrator.py -q 2>&1 | tail -3
```

### 5. Pre-commit denylist check (required before every keep)

```bash
git diff --name-only
git diff --cached --name-only
```

Verify NO changed file matches the denylist patterns above. If any denylist file appears → treat as crash, revert.

### 6. Commit or revert

**Keep:**
```bash
git add <specific files — never -A or .>
git commit -m "autoresearch: <short description>"
```

**Discard:**
```bash
git reset --hard <last kept commit hash>
```

### 7. Log the result

```bash
printf '%s\t%d\t%d\t%d\t%d\t%d\t%d\t%s\t%s\n' \
    "$(git rev-parse --short HEAD)" \
    <nlu_pass> <nlu_total> <docs_pass> <docs_total> <sec_pass> <sec_total> \
    "keep|discard|crash" "<description>" >> adwi/autoresearch-results.tsv
git add adwi/autoresearch-results.tsv
git commit --amend --no-edit
```

For discards: record the attempted commit hash, then reset to the last kept commit. Append a discard row using the PRE-reset HEAD hash.

### 8. Repeat

Go back to step 1. Do NOT stop. Do NOT ask if you should continue.
If you run out of ideas: re-read `NLU_REPAIR_BACKLOG.md`, look at the 13 failing `test_search_orchestrator.py` tests, or add more eval scenarios.

---

## Keep / Discard criteria

**Keep if ALL hold:**
- Syntax check OK
- NLU pass count ≥ baseline (no regressions)
- validate-docs pass count ≥ baseline
- Security surface tests pass count ≥ baseline
- Registry tests pass count ≥ baseline (excl. test_search_orchestrator.py)
- Change has a clear positive purpose

**Discard if ANY:**
- Syntax error in any Python file
- Any previously-passing NLU test now fails
- validate-docs fail count > baseline
- Security surface test regression
- The experiment produced no improvement

**Crash if:**
- A test suite fails to run (import error, missing dep, timeout)
- Treat as discard, revert, continue

---

## NLU sync rule

Any edit to `_REGEX_INTENTS` or `_INTENT_SYSTEM` in `adwi_cli.py` must be mirrored to:
- `adwi/logs/simeval/run_large_eval.py`
- `adwi/logs/simeval/run_large_eval_p2.py`

These are the ONLY permitted writes under `adwi/logs/simeval/`. Do not touch any other file there.

---

## Per-experiment timeout

If a single experiment (edit + test cycle) exceeds **10 minutes wall clock**, treat it as a crash. Revert and move on.

---

## What a good overnight session looks like

```
baseline commit → fix search_orchestrator test → +1 NLU scenario → +1 doc fix → ...
```

The operator runs `adwi-autoresearch-morning` to review diffs and cherry-pick improvements.
