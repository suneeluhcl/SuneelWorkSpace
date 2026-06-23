# Adwi Autoresearch — Overnight Improvement Program

You are running as an autonomous agent in the Adwi repository overnight.
Your job is to run a loop of small, safe, targeted experiments that improve
Adwi quality. The operator is asleep. Do not pause to ask questions.

---

## Step 0 — Orientation (do this first, every time)

1. Read `CLAUDE.md` — understand the repo structure and current NLU baseline.
2. Read `adwi/docs/NLU_REPAIR_BACKLOG.md` — prioritized fix list with exact proposals.
3. Run the baseline checks to establish YOUR current numbers on this session:

```bash
python3 -m py_compile adwi/adwi_cli.py && echo "syntax OK"
python3 -m unittest adwi/simlab/tests/test_nlu_regex.py 2>&1 | tail -2
adwi/bin/validate-docs 2>&1 | tail -3
adwi/.venv/bin/python3 -m pytest adwi/tests/test_remote_control_surface.py -q 2>&1 | tail -2
adwi/.venv/bin/python3 -m pytest adwi/tests/ --ignore=adwi/tests/test_search_orchestrator.py -q 2>&1 | tail -3
```

4. Create the results file with a baseline row:

```bash
printf 'commit\tnlu_pass\tnlu_total\tdocs_pass\tdocs_total\tsec_pass\tsec_total\tstatus\tdescription\n' > adwi/autoresearch-results.tsv
printf '%s\t%s\t%s\t%s\t%s\t%s\t%s\t%s\t%s\n' \
  "$(git rev-parse --short HEAD)" \
  <nlu_pass> <nlu_total> <docs_pass> <docs_total> <sec_pass> <sec_total> \
  "keep" "baseline" >> adwi/autoresearch-results.tsv
```

5. Create the experiment branch (do this ONCE per session):

```bash
git checkout -b adwi-autoresearch/<TAG>
```

6. Commit the baseline TSV:

```bash
git add adwi/autoresearch-results.tsv
git commit -m "autoresearch: baseline — session <TAG>"
```

---

## What you CAN do

Edit only files in the following allowlist:

```
adwi/*.py                         (adwi_cli.py, reason_engine.py, memory.py, etc.)
adwi/bin/                         (bin scripts — shell and Python)
adwi/commands/                    (command modules if they exist)
adwi/config/*.example             (safe example/template configs only)
adwi/docs/                        (documentation)
adwi/eval/                        (eval harnesses)
adwi/scripts/                     (utility scripts)
adwi/services/command-api/        (Command API — read-only routes only)
adwi/services/mcp/                (MCP servers)
adwi/services/telegram-bridge/    (Telegram bridge)
adwi/simlab/                      (SimLab modules and tests)
adwi/tests/                       (test files)
adwi/automation/workflows/        (n8n workflow JSON files — source only)
adwi/autoresearch-results.tsv     (your results log on this branch)
README.md
CLAUDE.md
```

---

## What you CANNOT do

**Hard denylist — never touch these:**

```
adwi/config/.env                  (live secrets)
secrets/                          (credentials)
adwi/infra/docker/n8n-data/       (live n8n DB)
adwi/infra/docker/n8n-data-backup-*/
obsidian-vault/                   (personal notes)
adwi/memory.db                    (live runtime DB)
adwi/knowledge.db                 (live runtime DB)
adwi/training-data/               (captured training data — do not alter)
logs/                             (runtime log files)
adwi/logs/simeval/                (eval evidence chain — read is OK, write is NOT)
                                  EXCEPTION: adwi/logs/simeval/run_large_eval.py and
                                  adwi/logs/simeval/run_large_eval_p2.py MAY be edited
                                  ONLY to mirror NLU changes from adwi_cli.py. Do not
                                  touch any other file under adwi/logs/simeval/.
*.sqlite *.db                     (any database file)
~/Library/LaunchAgents/           (LaunchAgent plists)
adwi/config/infra_ports.json      (only touch if validate-docs explicitly requires)
```

**Never run these:**
- `ollama pull` or `ollama rm` or any model management command
- `launchctl load/unload` — do not touch running services
- `docker compose up/down/restart` — do not restart containers
- `git push` — do not push to remote
- `git add -A` or `git add .` — never use blanket add; always name specific files
- `rm -rf` on anything outside your branch's experiment files
- Any command that requires sudo

---

## Experiment loop

Once setup is complete, run this loop indefinitely until manually interrupted:

### 1. Choose one narrow experiment

Pick ONE improvement from this priority list (in order):
1. Fix a known failing test in `adwi/tests/` (especially `test_search_orchestrator.py` — 13 failures)
2. Apply an open NHR item from `adwi/docs/NLU_REPAIR_BACKLOG.md`
3. Add missing test coverage for an untested command or edge case
4. Fix a stale doc reference caught by validate-docs
5. Improve a bin script for robustness (error handling, missing exit codes)
6. Add a new NLU eval scenario to the test harnesses (must be synced to all 3 files)

Do NOT attempt:
- Large refactors
- Multi-file architectural changes in one commit
- Anything that touches the denylist

### 2. Make the change

Edit only allowlisted files. Keep the diff small and focused.

### 3. Run the fast gate (always first)

```bash
python3 -m py_compile adwi/adwi_cli.py 2>&1 && echo "syntax OK"
python3 -m unittest adwi/simlab/tests/test_nlu_regex.py 2>&1 | tail -2
```

If the fast gate fails: revert immediately, log as `crash`, move on.

### 4. Run the full gate (before keeping)

```bash
adwi/bin/validate-docs 2>&1 | tail -3
adwi/.venv/bin/python3 -m pytest adwi/tests/test_remote_control_surface.py -q 2>&1 | tail -2
adwi/.venv/bin/python3 -m pytest adwi/tests/ --ignore=adwi/tests/test_search_orchestrator.py -q 2>&1 | tail -3
```

### 5. Pre-commit denylist check (required before every keep)

Before staging anything, run:

```bash
git diff --name-only
git diff --cached --name-only
```

Verify that NO changed file matches these patterns:
- `adwi/config/.env` or any `.env` file
- `secrets/`
- `adwi/infra/docker/n8n-data*`
- `obsidian-vault/`
- `adwi/memory.db` or `adwi/knowledge.db` or any `*.db` / `*.sqlite`
- `adwi/training-data/`
- `logs/` (runtime logs)
- `adwi/logs/simeval/` except `run_large_eval.py` or `run_large_eval_p2.py`
- `~/Library/LaunchAgents/`

If ANY denylist file appears in the diff → treat as crash, revert, do not commit.

Only then proceed to stage using explicit file names.

### 6. Commit or revert

**Keep (improvement or no regression with net-positive change):**
```bash
git add <specific files only — never -A>
git commit -m "autoresearch: <short description>"
```

**Discard (regression or neutral with no net gain):**
```bash
git reset --hard <last kept commit hash>
```

### 7. Log the result

Append to `adwi/autoresearch-results.tsv`:
```bash
printf '%s\t%d\t%d\t%d\t%d\t%d\t%d\t%s\t%s\n' \
  "$(git rev-parse --short HEAD)" \
  <nlu_pass> <nlu_total> <docs_pass> <docs_total> <sec_pass> <sec_total> \
  "keep|discard|crash" "<description>" >> adwi/autoresearch-results.tsv
git add adwi/autoresearch-results.tsv
git commit --amend --no-edit
```

For discards, record the hash that was reverted away from, then reset to the last kept commit.

### 8. Repeat

Go back to step 1. Do NOT stop. Do NOT ask if you should continue.
If you run out of obvious improvements: re-read `NLU_REPAIR_BACKLOG.md`,
look at the 13 failing `test_search_orchestrator.py` tests, or add more eval coverage.

---

## Keep / Discard criteria

**Keep if ALL of these hold:**
- `python3 -m py_compile adwi/adwi_cli.py` → OK
- NLU tests: pass count >= baseline (no regressions introduced)
- validate-docs: pass count >= baseline (no doc check newly failing)
- Security surface tests: pass count >= baseline
- Non-search_orchestrator registry tests: pass count >= baseline
- The change has a clear positive purpose (not noise)

**Discard if ANY of these:**
- Syntax error in any Python file
- Any previously-passing NLU test now fails
- validate-docs FAIL count > baseline
- Security surface test regression
- The experiment produced no improvement and no learning

**Crash if:**
- A test suite fails to even run (import error, missing dependency, timeout)
- Treat as discard and revert

---

## Safety rules (non-negotiable)

1. **Never modify denylist files.** If your experiment requires touching a denylist file, skip it and choose a different experiment.
2. **Never `git add -A`.** Always name the exact files you intend to commit.
3. **Never push.** Branches accumulate locally; the operator reviews them in the morning.
4. **Never restart services.** Adwi nightly, command-api, Telegram bridge, n8n, Obsidian bridge — all running live. Do not touch them.
5. **Never read `.env` or `secrets/`.** You do not need them; if an experiment requires live API calls, skip it.
6. **Sync NLU changes across all 3 files.** Any change to `_REGEX_INTENTS` or `_INTENT_SYSTEM` in `adwi_cli.py` must be mirrored to `adwi/logs/simeval/run_large_eval.py` and `adwi/logs/simeval/run_large_eval_p2.py` before the commit is kept. These two files are the only permitted writes under `adwi/logs/simeval/`. All other files in that directory are read-only.
7. **One experiment = one commit.** Do not bundle unrelated changes.
8. **If you are confused or stuck:** log a `crash` entry, `git reset --hard` to the last kept commit, and try a different experiment type.

---

## Session timeout

If a single experiment (edit + test cycle) exceeds **10 minutes wall clock**, treat it as a crash. Revert and move on.

---

## What a good overnight session looks like

```
baseline → fix search_orchestrator test → +1 fix → +1 NLU scenario → +1 doc fix → ...
```

Morning: operator runs `adwi-autoresearch-morning` and sees which branches have improvements,
reviews diffs, cherry-picks or merges what looks good.
