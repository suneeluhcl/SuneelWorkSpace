# Architecture Audit — 12-Organ System

Generated: 2026-07-01

## Scope

Full audit of all 12 organs post-restructure (the 2026-06-26 move from the flat `agent-system`/`mcp`/`orchestrator`/`goal-engine`/`autolab`/`comms` layout into `brain/heart/eyes/ears/nervous/skeleton/blood/hands/mouth/dna/lab/spine`), plus the self-healing loop end-to-end, plus Ollama/local-model usage. Six parallel research passes; every finding below is backed by a direct file read, grep, or live system check (`launchctl`, `ps`, `crontab`, `du`) — not speculation. Backups under `.agent-backups/` and `spine/backups/` were treated as historical, not live code.

## Scorecard

| Organ | Verdict | Headline issue |
|---|---|---|
| brain | drifted | `brain/vault/vault/` is a full self-nested duplicate; two parallel RAG/vector stacks never reconciled |
| heart | drifted, partially orphaned | goal-scheduler has zero real executions ever; `orchestrator/` is undocumented scope creep with a second "router" |
| eyes | drifted, partially orphaned | dashboard is real but not running; visual screenshot-healer has never fired once |
| ears | healthy | cleanest organ; only gaps are a missing test file and a stale README |
| nervous | drifted | mcp/ absorption is legitimate, but live automation still points at stale/broken paths; nerve_inbox is write-only |
| skeleton | healthy content / drifted enforcement | its one enforced rule ("symlink, never copy" into hands/bin) was being violated elsewhere (now fixed) |
| blood | stale | telemetry pipeline silently dead since Jun 26 via a swallowed `except: pass` (now fixed) |
| hands | drifted | 2 broken LaunchAgent symlinks, 1 actively-failing job (exit 127), 16-command `readme-*` family orphaned from `bin/`, 93GB unpruned `.agent-backups/` |
| mouth | healthy | tight scope, real safety policy (confirm-to-send, hashed logging); iMessage send path works but has 0 real sends logged; Mail is an intentional stub |
| dna | drifted | identity/voice guidance duplicated across 5 files; adaptive-identity loop stale since Jun 26 |
| lab | stale (orphaned scheduler) | self-evolution/autolab hasn't run in 5 days — broken launchd symlink, compounded by `agent-maintain` calling wrong paths (now fixed) |
| spine | healthy (core state) / drifted (surrounding audit files) | `WORKSPACE_HEALTH.json`/`CURRENT_STATE.json`/`INDEX.json` are correctly wired and fresh; `spine/audit/`, `ACTIVE_SESSION.json`, `LAST_KNOWN_GOOD.json` are 5 days stale |

## The single biggest root cause

Two `~/Library/LaunchAgents` symlinks (`com.suneelworkspace.maintenance.plist`, `com.suneelworkspace.autolab.plist`) point at `/Users/MAC/SuneelWorkSpace/automation/launchd/...`, a path that stopped existing when the reorg moved that directory to `hands/automation/launchd/...`. Both are dangling symlinks; `launchctl` has no record of either service. This alone explains most of the staleness found workspace-wide: the hourly health-check-and-repair job and the 6-hourly autolab job have not run since the reorg.

`agent-doctor`'s own launchd check cannot catch this: it uses `pathlib.Path.exists()`, which returns `False` for a broken symlink but doesn't distinguish "not configured" from "configured but broken" — so `WORKSPACE_HEALTH.json` reported 0 issues while the core automation was fully offline. (Detection gap fixed this session — see below.)

Compounding it: even once the launchd job is reloaded, `hands/bin/agent-maintain` (the script it runs) had ~10 more broken path references left over from the same reorg (`autolab/` → `lab/autolab/`, `mcp/` → `nervous/mcp/`, `agent-system/logs/` → `blood/logs/`, `comms/` → `mouth/comms/`, `orchestrator/` → `heart/orchestrator/`, `goal-engine/` → `heart/goals/`) — every one silently no-op'd via `[ -f ]`/`[ -x ]` guards. Fixed this session (with your explicit approval, since it changes what the automation does once it runs).

A parallel legacy-path bug independently killed `blood/`'s telemetry pipeline (`eyes/dashboard/pipeline/pipeline.py` importing from a nonexistent `agent-system/telemetry`, swallowed by a bare `except: pass`) — fixed this session.

## Self-healing loop — gap ranking

1. Hourly self-repair job dead, invisible to its own health check (root cause above; detection bug fixed, launchd symlink itself still broken — **flagged, needs approval**).
2. `agent-repair` never acts on any of `agent-doctor`'s structural findings (`misplaced_script`, `misplaced_config`, `non_symlink_bin_file`, `internal_script_duplication`, `gstack_drift`) — confirmed zero consumers repo-wide. Detection and repair are two disconnected systems.
3. The nervous system is write-only: 4,400+ notification files sit unread across organ `nerve_inbox/` dirs; `check_inbox()`/`clear_inbox()` are called only in tests.
4. The most complete pipeline (`night_shift` DAG: repair-loop → tests → chaos_monkey → hermes learning) has never been scheduled at all — no plist, no crontab.
5. 6-hourly autolab job dead via the same broken-symlink pattern as #1.
6. `agent-doctor` only checks 1 of 5 relevant launchd jobs.
7. No test-suite pass/fail check, no secrets scan, no disk-usage check feed into `WORKSPACE_HEALTH.json`.
8. Two disconnected maintenance logs (fixed this session — `agent-maintain` now logs to the canonical `blood/logs/MAINTENANCE_LOG.md`).
9. The one real learning loop (`autotrainer.py` reading `blood/logs/repair_loop.jsonl`) is starved because its only input (`tests/autonomous_repair_loop.py`) is never scheduled (same as #4).
10. `auto_fixes_applied` (currently 132) is a run-counter, not a fix-counter — increments regardless of whether anything relevant was actually fixed.

## Ollama / local-model usage — current state

The "Ollama Maximum Potential" 9-engine stack (repair, learn, review, security, deep-scan, orchestration) is real, working code — but **effectively dormant**. Nothing in launchd/cron starts it; the tmux stack isn't running; `ollama_suggestions.md` has been stale since Jun 28. Only two things run Ollama automatically: `evolution_daemon.py` (launchd, `RunAtLoad`) and `memory_curator.py` (nightly 2am via `daily-evolve`, confirmed real inference in logs).

Genuine, currently-unfilled opportunities (checked against what already exists so nothing here duplicates real infrastructure):
- Plain-English health narration (existing `personalized_brief.py` only templates numbers, doesn't narrate)
- Semantic staleness detection for READMEs (existing checker is explicitly rule-based only, "no Claude API cost" — this is why several stale READMEs were only caught by hand this session)
- `blood/logs/*.jsonl` rotation/summarization (nothing rotates these; `memory_curator.py` curates a different set of files)
- Failure-explanation tool (no standalone version; only exists bundled inside the dormant repair engine)
- Changelog generation from git log (does not exist anywhere)
- Session-handoff summarization (`agent-finish` just templates shell substitutions, no model call)

Already working and shouldn't be rebuilt: the LLM-Wiki RAG pipeline (`brain/wiki/wiki_ingest.py` + `wiki_query.py`, confirmed real dated synthesis output), and nightly training-data capture (`autotrainer.py`, confirmed growing nightly) — though the `suneelworkspace` model itself is never automatically rebuilt from that accumulating data (`rebuild-model` is manual-only).

## Proposed direction (Phase 4 — recommendation, not yet executed)

**Keep the 12-organ structure.** It's a sound, legible mental model and most of the organs map cleanly to their stated purpose. The problems found are not architectural — they're reorg debris (stale paths), unconsumed scaffolding (nerve_inbox, goal engine, visual healer), and missing wiring (broken launchd symlinks) — not a case for restructuring again. A second restructure right now would just create a new generation of the same stale-path bugs.

Recommended next moves, roughly in priority order:
1. Fix the two broken LaunchAgent symlinks (re-point them at `hands/automation/launchd/`, then `launchctl load`) — restores the hourly/6-hourly jobs. **Needs your approval** (launchd change).
2. Reconcile `heart/orchestrator/` vs `heart/model_router/` naming, or fold orchestrator's routing concerns into one place — cosmetic/organizational, not urgent.
3. Decide whether `heart`'s goal-scheduler and `eyes`'s visual healer are still wanted; if not, mark them explicitly deprecated rather than leaving live-looking scaffolding that never runs.
4. Add a retention/pruning policy for `.agent-backups/` (93GB, unbounded, growing ~18 snapshots/day with increasing per-snapshot size) — **flagged, needs approval** (deletion of historical data).
5. Wire a real consumer for `nerve_inbox/` (or decide it's not needed and stop producing to it) — currently pure write-only across every organ.
6. Have `agent-repair` actually consume `WORKSPACE_HEALTH.json`'s `repair_suggestions` array instead of running a fixed, unrelated checklist.

## Fixed this session (safe, low-risk, applied directly)

- `gstack-verify`/`gstack-repair`: stale config/status paths from before the `nervous/` reorg — verified working (`gstack-verify` now reports OK).
- `hands/scripts/agent-doctor`: 3 false positives fixed (nested-closure duplicate detection, `bin/README.md` symlink requirement, `tests/` misplaced-script flag) + launchd broken-symlink detection blind spot fixed (now correctly flags dangling symlinks instead of silently treating them as "not configured").
- `dna/agents/hermes/workspace_config.yaml` relocated into `config/` (no live references).
- `spine/readme_policy.json` relocated into `spine/config/`, with all 3 referencing scripts updated (`pre_push_guard.sh`, `auto_commit.py`, `run_nightly.sh`) — verified.
- `hands/bin/agent-maintain`: ~10 broken legacy path references fixed (approved explicitly — this restores real automated actions once the job is loaded).
- `hands/bin/telemetry-write`: converted from a byte-identical copy to a proper symlink, per the skeleton rule (approved explicitly).
- `eyes/dashboard/pipeline/pipeline.py`: fixed the telemetry import path that was silently killing all control-center telemetry writes since the reorg.

Workspace health: 7 issues → 0 at the point of the first pass; several new findings surfaced by the deeper 6-agent audit are listed above as flagged/pending, not yet reflected in `WORKSPACE_HEALTH.json`'s check coverage.

## Approved and completed (same session, after explicit sign-off)

All 8 items below were flagged as needing approval; all were approved and applied, each verified working:

- **Re-pointed + reloaded the 2 broken LaunchAgent symlinks** (maintenance, autolab). Confirmed live: the hourly maintenance job has run correctly every hour since (verified via new `.agent-backups` snapshots at regular intervals).
- **Fixed `com.suneel.codex-env.plist`** — was referencing a deleted `codex/` path (exit 127 every run); now points at `hands/codex/set-launch-env.zsh`, repo-tracked under `hands/automation/launchd/`, exit 0 confirmed.
- **Reconciled `com.suneel.daily-evolve.plist`** — fixed the doubled `nervous/nervous/` path in the repo copy (correct is `nervous/mcp/server/logs/`), confirmed no other drift between repo and installed versions, replaced the installed real-file copy with a symlink to the repo source (matching the convention used by the other jobs).
- **Scheduled the `night_shift` DAG** — new `com.suneelworkspace.night-shift.plist` at 22:00 daily, running `dag-run` directly against the existing pipeline. Validated with `dag-validate` (also fixed 2 bugs in that validator: a stale `scripts/` path and no PATH-fallback for system binaries like `python3`).

## `hermes` CLI entrypoint — built (follow-up session, same day)

`dna/agents/hermes/` had real Ollama training-data capture but no runnable `hermes` command anywhere — the underlying agent (`~/.hermes/hermes-agent/venv/bin/hermes`, a real `tirith` v0.16.0 install) was already there and working, just never wrapped and exposed as a workspace CLI command the way `hermes-night`/`hermes-start`/`hermes-continue` already were.

Added `hands/bin/hermes` (symlinked to `bin/hermes`), mirroring the existing `hermes-night` wrapper's established `chat -q "<prompt>" -Q` non-interactive pattern. It strips the `--non-interactive`/`--continue` flags the `night_shift.yaml` pipeline already hard-codes for its `hermes_health_check` step and forwards the actual prompt. Verified end-to-end with the exact pipeline invocation (`hermes --non-interactive --continue "..."` → real response, exit 0). `dag-validate` now reports **PASS — 14 steps validated** (was 1 error before this fix) — the `night_shift` DAG has zero remaining known gaps.
- **`.agent-backups/` retention** — added a `prune_backups()` function to `common.sh` (age parsed from the snapshot directory name, since directory mtimes turned out to be unreliable — they get touched after creation and don't reflect true age), wired into the hourly maintenance run at a 7-day rolling window. One-time cleanup at a 48-hour cutoff freed 78GB (94GB → 16GB).
- **`nerve_inbox/` drain** — new `hands/scripts/nerve_inbox_drain.py`, wired into hourly maintenance: logs a one-line per-organ summary (event counts by source organ) to `blood/logs/MAINTENANCE_LOG.md`, then clears the inbox. Cleared the existing 4,479-file backlog across 6 organs; ongoing growth now gets drained hourly instead of accumulating forever.
- **Removed `brain/vault/vault/`** (the full self-nested duplicate directory) and the separate stale duplicate `brain/vault/research/research_engine.py` (confirmed unimported anywhere, and actually the stale copy — it still referenced pre-reorg paths like `agent-system/memory/` that the live `brain/research/research_engine.py` had already moved past).
- **Restored all 47 orphaned `hands/bin/*` scripts** to `bin/` symlinks, including the full 16-command `readme-*` family and `nerve-heal`.

Deliberately *not* merged: `brain/memory/vector/semantic_search.py` (ChromaDB, used only by the MCP gateway's search endpoint) and `brain/research/workspace_rag.py` (SQLite/FTS, used by autoresearch/wiki_query/reasoning-sidecar) look like overlapping "vector search" on the surface but actually serve different call sites with different backends — reconciling them is a real architecture decision, not a cleanup, and is left as a recommendation, not an action.

Workspace health after all fixes: **0 issues** (re-verified after every change in this batch).

## Systemic doubled-path corruption — found and resolved (follow-up session, same day)

Verification testing first surfaced 3 instances of a doubled-path bug pattern (`system_intelligence.py` writing to top-level `audit/` instead of `spine/audit/`; `auto_discover.py` referencing `nervous/nervous/...` and `heart/heart/...`). A broader scan then found the real scope: **dozens more instances across the codebase** — `nervous/mcp/server/config/{resource_map,server_config,tool_policies}.json`, `nervous/mcp/server/main.py`, `heart/orchestrator/mesh/mesh_monitor.py`, `spine/audit/{file_graph,duplication_clusters}.json`, `brain/memory/{MEMORY,DECISIONS,PATTERNS}.md`, several `hands/scripts/*.sh` prompt/autolab scripts, `mouth/comms/docs/`, `nervous/mcp/docs/`, and more.

**Root cause, confirmed:** `hands/scripts/update_all_paths.py` — a one-time "Phase 13 path updater" — processed `.py`/`.md`/`.json`/`.sh` files across the whole tree without excluding itself, so every run rewrote its *own source code* using its *own* replacement rules. Its mapping table's `from`/`to` pairs literally already contained double/triple-doubled paths mapping to one-more-doubled versions (e.g. `"heart/heart/heart/orchestrator/mesh/"` → `"heart/heart/heart/heart/orchestrator/mesh/"`), proving it had already run against itself multiple times, escalating the corruption further each run. It had no callers anywhere (never wired into automation) — it was a manual one-time tool whose job was long done and which had become actively dangerous to ever run again. **Deleted.**

**Fix applied:** wrote a one-time normalizer (in the scratchpad, not committed — deliberately not repeating the mistake of leaving a path-fixing script in the repo) that idempotently collapses `<organ>/<organ>/` → `<organ>/` per file, run first in dry-run/diff-preview mode and reviewed before any writes. Explicitly excluded: `lab/autolab/quarantine/` and `lab/autolab/snapshots/` (deliberate historical restore-point snapshots), `blood/logs/SESSION_LOG.md` and `heart/tasks/COMPLETED_TASKS.md` (append-only historical records — not living config), `dna/agents/hermes/ollama_models/training_data*.json*` (frozen training data, not live config), 2 false-positive matches (`adwi/simlab/lab/...` — a real, unrelated path from a different project matching `lab/lab` only as a substring), and this audit report itself (which quotes the bug pattern as a literal example — fixing it would have destroyed the example). Also deleted one untracked, stray triple-nested `nervous/nervous/nervous/...` directory left over from a previous bad run (stale content, never committed to git).

**Result:** 54 files fixed + 4 stale permission-allowlist entries in `.claude/settings.local.json` + the culprit script removed. All JSON re-validated as parseable, all touched `.py`/`.sh` re-validated for syntax, MCP server module re-verified importable, full test suite (103/103) still passing, `gstack-verify` OK, health 0 issues.
