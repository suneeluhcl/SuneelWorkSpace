# Phase 3: Intelligence — Closing The Loop

**Date:** 2026-06-26  
**Status:** Approved  
**Source spec:** `~/Downloads/🧠 SuneelWorkSpace — Phase 3 Intelligence Closing The Loop.md`

---

## Goal

Transform SuneelWorkSpace from a reactive assistant into a self-improving, world-aware intelligence system. Eight subsystems organized into three dependency tiers, each building on the previous.

---

## Tier 1 — Data Layer (P3.1, P3.2)

### P3.2 — Structured Execution Telemetry

**Purpose:** Ground-truth data store for all agent activity. Everything else reads from here.

**Files:**
```
blood/telemetry/
  telemetry.db              ← SQLite, all traces
  telemetry_writer.py       ← write_trace(agent, task_type, duration_ms, tokens_in, tokens_out, outcome, payload)
  telemetry_query.py        ← CLI: telemetry-query summary|agent|task-type|anomalies [--days N]
  telemetry_anomaly.py      ← flag regressions >20% vs 7-day baseline
  schema.sql                ← CREATE TABLE traces (...)
```

**Schema:** `traces(id, timestamp, agent, task_type, duration_ms, tokens_in, tokens_out, outcome, payload_json)`

**CLI:** `telemetry-query summary --days 7` → table per agent/task-type with success rate, avg tokens, avg duration.

**Anomaly rule:** If current 24h avg for any (agent, task_type) pair deviates >20% from 7-day baseline, write to `blood/telemetry/anomalies.json` and print warning.

### P3.1 — Closed Feedback Loop

**Purpose:** Convert Suneel's qualitative feedback into training records that flow through autolab → eval → promotion.

**Files:**
```
dna/feedback/
  inbox/                    ← drop .md files here
  processed/                ← archived after ingestion
  feedback_ingest.py        ← parse, tag, emit JSONL training record
lab/autolab/training_data/
  feedback_<timestamp>.jsonl
```

**Flow:** Drop `.md` in `feedback/inbox/` → `feedback-ingest` → tags by agent/intent/outcome → writes JSONL to `lab/autolab/training_data/` → existing `evaluator.py` + `promotion_gate.py` run on next autolab cycle → promoted changes committed back.

**CLI:** `feedback-ingest` (runs all pending), `feedback-status` (shows queue depth and last promotion).

---

## Tier 2 — Intelligence Layer (P3.3, P3.4, P3.6)

### P3.3 — Cross-Agent Output Comparison

**Purpose:** Live leaderboard of agent performance per task type, fed back into routing decisions.

**Files:**
```
blood/telemetry/comparison/
  leaderboard.json          ← capability scores per (agent, task_type)
  compare_agents.py         ← reads telemetry.db, builds comparison table
  score_updater.py          ← recomputes scores after each telemetry write
```

**Capability score:** `0.87 * success_rate + 0.13 * (1 - normalized_latency)` per (agent, task_type) pair, updated on each `telemetry-query` call.

**CLI:** `agent-compare --task-type code_review` → side-by-side table (Claude / Codex / Gemini) with success rate, avg tokens, avg duration, capability score.

**Router integration:** `heart/orchestrator/router/` reads `leaderboard.json` when routing; picks agent with highest capability score for matched task type.

### P3.4 — Brain Context Injector

**Purpose:** Auto-pull relevant knowledge from Obsidian vault before any agent task.

**Files:**
```
brain/
  context_injector.py       ← keyword+tag search brain/vault/, returns top 3-5 hits
  context_cache.json        ← LRU cache, TTL 1h
```

**Search strategy:** Keyword match on task description against note filenames + frontmatter tags + first 200 chars of content. Score by recency + match density. Return top 5 as `## Context from brain:` block.

**CLI:** `brain-inject "task description"` → prints injected context block.

**Router integration:** Every `route-task` call invokes `brain-inject` and prepends context to the outbound task prompt.

### P3.6 — External World Monitor

**Purpose:** Watch RSS, GitHub, Arxiv for changes relevant to active goals. Surface them in a morning brief.

**Files:**
```
ears/monitor/
  monitor_config.json       ← feeds, repos, topics, check intervals
  monitor_runner.py         ← orchestrates all sources, deduplicates, scores relevance
  sources/
    rss_monitor.py          ← fetch and parse RSS feeds
    github_monitor.py       ← watch repos for new releases/issues
    arxiv_monitor.py        ← search Arxiv topics matching active goals
  digest/
    digest_builder.py       ← build morning brief from scored items
    digest_formatter.py     ← format as Markdown
  cache/
    rss_<date>.json
    github_<date>.json
    arxiv_<date>.json
```

**Relevance scoring:** Each item scored 0–1 against keywords extracted from `heart/tasks/ACTIVE_TASKS.md` and `heart/orchestrator/state/`. Items scoring >0.4 included in digest.

**Output:** `brain/logs/morning_brief_<date>.md`

**CLI:** `monitor-run` (all sources), `monitor-run --source arxiv`, `monitor-digest` (build brief from today's cache).

**Schedule:** Daily at 7am via `hands/automation/dag/pipelines/morning_brief.yaml`.

---

## Tier 3 — Action Layer (P3.5, P3.7, P3.8)

### P3.5 — Workflow DAG Composer

**Purpose:** Define, validate, run, and schedule multi-step workflows as YAML pipelines.

**Files:**
```
hands/automation/dag/
  dag_validator.py          ← check deps, cycles, variable refs, command existence
  dag_runner.py             ← topological sort, execution gates, template substitution, run records
  dag_scheduler.py          ← cron-style schedule registry
  schema/pipeline_schema.yaml ← canonical pipeline YAML schema
  pipelines/
    idea_to_goal.yaml
    system_health.yaml
    morning_brief.yaml
  runs/                     ← <pipeline>_<timestamp>.json run records
  schedule_registry.json
```

**Execution levels:** SAFE (auto), CONTROLLED (prompt y/n), RESTRICTED (require justification).

**Template vars:** `{{ inputs.X }}`, `{{ steps.X.outputs.Y }}`, `{{ env.X }}`, `{{ date }}`.

**CLI:** `dag-run <pipeline.yaml> [--dry-run] [--input k=v]`, `dag-validate <pipeline.yaml>`, `dag-schedule --list|--add|--remove|--run-due`.

**Symlinks in `bin/`:** `dag-run`, `dag-validate`, `dag-schedule`.

### P3.7 — Natural Language Command Dispatcher

**Purpose:** `ws "natural language"` → maps to correct workspace command via intent classification.

**Files:**
```
mouth/dispatcher/
  ws.py                     ← main entry point
  intent_classifier.py      ← keyword+pattern → intent, confidence score
  intent_map.json           ← intent → command mappings with keywords
  dispatcher_log.json       ← history of dispatches with confidence scores
```

**Confidence gate:** If top match <0.7, print top 2 candidates and ask user to pick. Log all dispatches.

**P3.3 integration:** After intent match, check `leaderboard.json` to route to best-performing agent for that intent's task type.

**CLI:** `ws "<natural language command>"` — single universal entry point.

**Symlink:** `bin/ws → ../mouth/dispatcher/ws.py`.

**Seed intents (20+):** health-check, telemetry-summary, agent-compare, run-pipeline, morning-brief, idea-start, goal-status, brain-inject, monitor-run, feedback-ingest, system-audit, etc.

### P3.8 — Self-Directed Hypothesis Generator

**Purpose:** Autolab generates its own experiment hypotheses by synthesizing telemetry anomalies, leaderboard gaps, and world monitor findings.

**Files:**
```
lab/autolab/
  hypothesis_generator.py   ← reads anomalies.json + leaderboard.json + morning_brief → generates candidates
  hypothesis_log.jsonl      ← all generated hypotheses with source signals
```

**Hypothesis sources:**
- Telemetry anomaly (P3.2) → "Agent X degrades on task type Y — hypothesis: prompt change Z"
- Leaderboard gap (P3.3) → "Codex outperforms Claude on code_edit by 30% — hypothesis: route all code_edit to Codex"
- World monitor hit (P3.6) → "New paper on prompt compression — hypothesis: apply technique to system prompts"

**Output:** Appends to `lab/autolab/experiment_queue.md` in existing format so `lab/autolab/runner.py` picks up naturally.

**CLI:** `hypothesis-generate` (run once), `hypothesis-log` (show recent hypotheses and their status).

**Schedule:** Daily after morning monitor run (via `morning_brief.yaml` DAG, added as final step).

---

## Implementation Order (Approach B — Foundation-first)

### Batch 1 — Tier 1
1. `blood/telemetry/schema.sql` + `telemetry_writer.py` + `telemetry_query.py` + `telemetry_anomaly.py`
2. `dna/feedback/` + `lab/autolab/training_data/` + `feedback_ingest.py`
3. CLI symlinks: `telemetry-query`, `feedback-ingest`, `feedback-status`
4. Validate: `telemetry-query summary --days 7`, `feedback-ingest` on test file

### Batch 2 — Tier 2
5. `comparison/compare_agents.py` + `leaderboard.json` + `score_updater.py`
6. `brain/context_injector.py` + `context_cache.json`
7. `ears/monitor/` full directory + all source monitors + digest builder
8. CLI symlinks: `agent-compare`, `brain-inject`, `monitor-run`, `monitor-digest`
9. Validate: `agent-compare`, `brain-inject "test task"`, `monitor-run --dry-run`

### Batch 3 — Tier 3
10. `hands/automation/dag/` full directory + validator + runner + scheduler + 3 seed pipelines
11. `mouth/dispatcher/` + `intent_map.json` (20+ intents) + `ws.py`
12. `lab/autolab/hypothesis_generator.py` + wire into `morning_brief.yaml`
13. CLI symlinks: `dag-run`, `dag-validate`, `dag-schedule`, `ws`
14. Validate: `dag-validate` all pipelines, `ws "run health check"`, `hypothesis-generate`

### Final
15. `agent-finish "P3 complete: all 8 subsystems operational"`

---

## New Directories Created
- `blood/telemetry/` (new — exists but empty)
- `dna/feedback/inbox/` + `feedback/processed/`
- `lab/autolab/training_data/`
- `blood/telemetry/comparison/`
- `brain/` + `brain/logs/`
- `ears/monitor/` + `ears/monitor/sources/` + `ears/digest/` + `ears/monitor/cache/`
- `hands/automation/dag/` + `dag/pipelines/` + `dag/runs/`
- `mouth/dispatcher/`

## Files Modified
- `heart/orchestrator/router/` — reads `leaderboard.json` for routing
- `lab/autolab/experiment_queue.md` — hypothesis_generator appends here
- `hands/automation/dag/pipelines/morning_brief.yaml` — adds hypothesis-generate step

## Total
~62 new files, 8 new subdirectories, 3 files modified.
