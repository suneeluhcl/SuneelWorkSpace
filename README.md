<!-- README_PROTECTED: manual -->
# SuneelWorkSpace — Complete System Blueprint

> This README is the authoritative drop-in context for any AI agent, prompt engineer, or LLM entering this workspace. Reading this file alone is sufficient to understand the entire system: its architecture, identity, safety rules, memory, tasks, capabilities, and how to operate it.

**Owner**: Suneel Bikkasani  
**Machine**: Apple M4 Max, 64 GB RAM, macOS 15  
**Path**: `~/SuneelWorkSpace`  
**Last updated**: 2026-06-28

---

## 1. System Goal

Suneel is building a smart personal AI operating system — self-improving, self-updating, self-repairing, and capable of performing, testing, training, and learning from mistakes via simple commands. It should feel JARVIS-like: reactive, self-aware, advanced — while staying grounded, safe, and fully inspectable through plain files.

All state is file-based (Markdown + JSON). No opaque databases. Any agent can read and write the same files.

---

## 2. Agent Roster

This workspace is **shared** — all agents read and write the same memory, tasks, handoffs, and logs:

| Agent | Role | Config |
|-------|------|--------|
| **Antigravity (agy)** | Primary orchestrator, brainstorming | `~/.gemini/config/AGENTS.md`, `~/SuneelWorkSpace/.agents/AGENTS.md` |
| **Claude Code** | Deep coding, implementation | `~/.claude/CLAUDE.md`, `~/SuneelWorkSpace/CLAUDE.md` |
| **Codex CLI** | Agentic runs, batch tasks | `~/.hands/codex/AGENTS.md`, `config.toml` |
| **Gemini CLI** | Free fallback (1K req/day) | Launch: `swgemini`, `~/SuneelWorkSpace/GEMINI.md` |
| **OpenCode** | Free fallback (Groq) | Launch: `swopencode`, `~/SuneelWorkSpace/opencode.json` |
| **Hermes** | Local Ollama agent (tirith) | `dna/agents/hermes/`, model: `suneelworkspace` |

**Canonical instruction source** for all agents: `skeleton/rules/AGENT_SYSTEM.md`

---

## 3. Identity & Voice

Before drafting, planning, or communicating on Suneel's behalf, load all 5 identity files:

```
dna/identity/prompts/identity_prompt.md
dna/identity/prompts/communication_prompt.md
dna/identity/profile/identity_profile.md
dna/identity/profile/tone_profile.md
dna/identity/profile/decision_profile.md
```

**Voice**: short, direct, casual, conversational, smart, structured, softened. Never harsh or condescending.

**Personality**: nerdy, tech-savvy, introverted, optimistic, tactical, deep-thinking, self-improving.

**Workflow style**: Default to autopilot. Ask only for safety-gated or destructive actions.

**Preferred tool selection order**: simplicity → cost → power → speed → reliability.

---

## 4. Session Boot (Mandatory)

Every agent session must begin with:

```
✅ Loading workspace shared brain
```

Then read these 11 files in order before any meaningful work:

```
1.  skeleton/rules/AGENT_SYSTEM.md         ← canonical operating rules
2.  skeleton/rules/IDENTITY.md             ← identity spec
3.  skeleton/rules/WORKFLOW_RULES.md       ← code/commit workflow
4.  skeleton/rules/SAFETY_BOUNDARIES.md   ← hard limits
5.  skeleton/rules/STARTUP_CHECKLIST.md   ← this checklist (full detail)
6.  brain/memory/MEMORY.md                ← durable workspace facts
7.  brain/memory/DECISIONS.md             ← architectural decisions
8.  heart/tasks/ACTIVE_TASKS.md           ← current task list
9.  brain/memory/SESSION_HANDOFF.md       ← previous session summary
10. spine/state/CURRENT_STATE.json        ← live workspace state
11. spine/state/WORKSPACE_HEALTH.json     ← health score + issues
```

Shortcut: `agent-start` handles all of this and prints a brief.

**Session closeout** (after meaningful work):

```
agent-finish "one-sentence summary of what was done"
```

This updates: `SESSION_HANDOFF.md`, `ACTIVE_TASKS.md`, `SESSION_LOG.md`, `CURRENT_STATE.json`.

---

## 5. Safety Boundaries

These are hard limits. **No exceptions. No overrides. Not negotiable.**

| Action | Rule |
|--------|------|
| Delete important files | Never without backup + explicit approval |
| Money / billing / accounts | Never |
| Outbound comms (email, iMessage, Slack) | Never without explicit approval |
| Database migrations | Never without explicit approval |
| Destructive git ops (force push, reset --hard) | Never without explicit approval |
| LLM-generated symlink fixes | Never auto-apply — always queue to controlled queue |
| LLM-provided file paths | Always validate with `_path_within_workspace()` first |

**Action classification**:
- **SAFE** (autopilot): read, analyze, search, generate files, append logs, create tasks
- **CONTROLLED** (check first): modify configs, install packages, change system files
- **HUMAN_REQUIRED** (always ask): send messages, delete branches, billing, external installs

Destructive/low-confidence suggestions → `blood/logs/repair_loop_controlled_queue.json` or `blood/logs/suggestion_controlled_queue.json` for human review.

---

## 6. Architecture — 12 Organs

The workspace is organized as a human body metaphor. Each organ has a `nerve.json` (v1.1) with `provides`, `needs`, `key_files`, and `cli_commands`.

### 🧠 brain — Memory & Intelligence
**Path**: `brain/`

What it does:
- **Semantic memory search** — ChromaDB vector store + sentence-transformers
- **Anticipation engine** — predicts next actions from behavior patterns, ranks top 3–5 suggestions
- **Memory curation** — Ollama keeps MEMORY.md, DECISIONS.md, PATTERNS.md accurate and lean
- **Research engine** — idea capture → research plan → analysis → decision pipeline
- **Knowledge graph** — cross-organ dependency graph

Key files:
```
brain/memory/MEMORY.md                 ← durable workspace facts (single source of truth)
brain/memory/DECISIONS.md             ← key decisions with reasoning
brain/memory/PATTERNS.md              ← recurring operating patterns
brain/memory/INSIGHTS.md              ← higher-level learnings
brain/memory/SESSION_HANDOFF.md       ← latest session summary for continuity
brain/memory/memory_curator.py        ← Ollama-powered curation (suneelworkspace model)
brain/memory/vector/semantic_search.py ← vector search
brain/anticipation/prediction_engine.py ← next-action prediction
brain/anticipation/action_suggestions.md ← current ranked suggestions
brain/research/                        ← idea pipeline scripts
brain/graph/build_graph.py             ← knowledge graph builder
```

CLI: `memory-search "q"`, `memory-curate`, `memory-reindex`, `morning-brief-personal`, `idea-start`, `idea-run`

---

### ❤️ heart — Goals, Tasks & Model Routing
**Path**: `heart/`

What it does:
- **Task queues** — ACTIVE_TASKS.md, TASK_QUEUE.md, COMPLETED_TASKS.md
- **Goal engine** — full lifecycle: create, execute, monitor, complete
- **Model router** — selects best Ollama/cloud model per task type
- **Model rotator** — scores models by time-of-day, task affinity, availability
- **Quota tracker** — tracks API usage

Key files:
```
heart/tasks/ACTIVE_TASKS.md           ← in-progress tasks
heart/tasks/TASK_QUEUE.md             ← queued tasks (fed by suggestion_consumer)
heart/tasks/COMPLETED_TASKS.md        ← finished tasks log
heart/model_router/router.py          ← returns {"id": model, "score": float}
heart/model_router/model_rotator.py   ← scores models by context
heart/model_router/health_checker.py  ← model availability check
heart/model_router/quota_tracker.py   ← API quota tracking
heart/goals/                          ← goal lifecycle scripts
heart/orchestrator/                   ← DAG + mesh routing
```

Models:

| Model | Base | Strengths | Default Use |
|-------|------|-----------|-------------|
| `suneelworkspace` | llama3.3:70b | workspace-aware | repair, curation, general |
| `codellama` | — | code analysis | code review, pre-commit |
| `llama3.3:70b` | — | heavy reasoning | complex analysis |
| `llama3.1` | — | balanced | learning, memory |
| `mistral` | — | security | security scanning |
| `llama3.2` | — | fast/light | quick queries |

CLI: `model-route`, `model-health`, `model-rotate`, `model-status`, `goal-create`, `goal-status`, `goal-execute`, `goal-complete`

---

### 👁️ eyes — Dashboard & Visual Monitoring
**Path**: `eyes/`

What it does:
- **FastAPI dashboard** at `http://localhost:7777` — full workspace visibility
- **6-stage execution pipeline** — Brainstorm → Plan → Confirm → Implement → Test → Wire (WebSocket-streamed)
- **13 live auto-refreshing widgets** — goals, memory, models, nerve system, test suite, and more
- **Visual monitor** — screenshot capture + Ollama-powered visual repair
- **Approval queue** — human gate for controlled actions

Key files:
```
eyes/dashboard/server.py           ← FastAPI app (33.7KB): all routes, WebSocket, pipeline
eyes/dashboard/index.html          ← Dashboard UI (HTMX panels)
eyes/dashboard/static/dashboard.js ← WebSocket client, polling, runTests(), runRepairLoop()
eyes/dashboard/pipeline/pipeline.py ← 6-stage pipeline engine
eyes/dashboard/widgets/            ← 13 widget renderers (all HTML-escaped)
eyes/visual/screenshot_manager.py  ← screenshot capture
eyes/visual/visual_repair_agent.py ← Ollama visual repair
```

API endpoints:
```
GET  /api/health               health score
GET  /api/tests/status         latest test run results (JSON)
POST /api/tests/run            trigger test suite (background)
POST /api/tests/repair-loop    trigger autonomous repair loop (background)
GET  /api/nerve/status         all 12 organ statuses
GET  /api/models/status        model rotation stats
GET  /api/ollama/status        Ollama server + model list
GET  /api/hermes/status        Hermes agent status
POST /api/health/repair        launch 8-stage health repair pipeline
GET  /api/readme-health        README freshness scores
```

Security: WebSocket origins validated; quick actions against server allowlist; all widget HTML uses `html.escape()`.

CLI: `workspace-dashboard`

---

### 👂 ears — External Monitors & Morning Brief
**Path**: `ears/`

What it does:
- Polls RSS feeds, GitHub notifications, custom sources on schedule
- Builds structured daily digest from all monitor outputs
- Ollama-scores and ranks content for Suneel's interests
- Delivers personalized morning brief

Key files:
```
ears/monitor_runner.py      ← runs all monitors on schedule
ears/digest_builder.py      ← assembles digest from monitor outputs
ears/personalized_brief.py  ← Ollama-powered personal scoring + ranking
ears/monitors/              ← individual monitor scripts (RSS, GitHub, custom)
ears/briefs/                ← historical brief archives
```

CLI: `morning-brief`, `morning-brief-personal`, `monitor-run`, `monitor-status`

---

### ⚡ nervous — Event Bus, Nerve Healer & MCP
**Path**: `nervous/`

What it does:
- **Nerve propagator** — inter-organ event bus (all 12 organs publish/subscribe here)
- **Nerve healer** — Ollama auto-healer repairs broken organ connections every 6h
- **Nerve registry** — maps all 12 organs: their `provides`, `needs`, key files
- **MCP connectors** — gateway to Claude, Codex, and other model connectors

Key files:
```
nervous/nerve_propagator.py   ← event bus: notify_change() + get_status()
nervous/nerve_healer.py       ← Ollama healer (suneelworkspace model)
nervous/nerve_registry.json   ← 12-organ dependency map
nervous/nerve_status.py       ← prints organ statuses
nervous/gateway/              ← MCP gateway
nervous/mcp/                  ← MCP connectors (Claude, Codex)
```

API (used by all organs):
```python
from nervous.nerve_propagator import notify_change, get_status

payload = notify_change("brain", "memory_updated", "brain/memory/MEMORY.md")
# payload["event_type"] == "memory_updated"   ← KEY: use "event_type" not "change_type"

status = get_status()   # {"brain": {"healthy": True, ...}, ...} for all 12 organs
```

Nerve.json format (v1.1) — every organ has one at its root:
```json
{
  "version": "1.1",
  "organ": "brain",
  "provides": ["memory", "search", "context"],
  "needs": ["spine/state", "heart/tasks"],
  "key_files": ["brain/memory/MEMORY.md"],
  "cli_commands": ["memory-search", "memory-curate"]
}
```

CLI: `nerve-status`, `nerve-heal`, `nerve-check`

---

### 🦴 skeleton — Rules, Safety & Instructions
**Path**: `skeleton/`

What it does: holds all canonical operating rules that every agent reads at session start.

Key files:
```
skeleton/rules/AGENT_SYSTEM.md        ← canonical rules (source of truth for ALL agents)
skeleton/rules/IDENTITY.md            ← identity: voice, tone, communication style
skeleton/rules/WORKFLOW_RULES.md      ← code changes, commit style, agent handoffs
skeleton/rules/SAFETY_BOUNDARIES.md  ← hard limits (see Section 5 above)
skeleton/rules/STARTUP_CHECKLIST.md  ← full ordered startup (see Section 4 above)
skeleton/rules/BOUNDED_SELF_UPGRADE.md ← safe workspace self-modification rules
```

---

### 🩸 blood — Logs, Telemetry & Controlled Queues
**Path**: `blood/`

What it does:
- Every agent, engine, and script writes structured JSONL logs here
- SQLite telemetry for metrics, performance, event history
- Anomaly detection on log patterns
- Controlled queues for LLM-suggested destructive actions (human review required)

Key files:
```
blood/logs/SESSION_LOG.md                      ← human-readable session summaries
blood/logs/pre_commit_review.jsonl             ← codellama pre-commit code reviews
blood/logs/nerve_events.jsonl                  ← all organ nerve events
blood/logs/execution_history.jsonl             ← 6-stage pipeline execution history
blood/logs/ollama_suggestions.md               ← raw LLM suggestions from all engines
blood/logs/code_review_report.md               ← Python file analysis
blood/logs/nerve_healer.jsonl                  ← organ healing events
blood/logs/repair_loop_controlled_queue.json   ← LLM symlink fixes awaiting human approval
blood/logs/suggestion_controlled_queue.json    ← low-confidence suggestions awaiting review
blood/telemetry/telemetry.db                   ← SQLite metrics database
blood/telemetry/log_query.py                   ← query telemetry + JSONL
blood/telemetry/anomaly_detector.py            ← anomaly flagging
```

Gitignored (high-churn runtime): `blood/logs/readme_intelligence.log`, `tests/reports/junit_*.xml`, `blood/logs/repair_loop.jsonl`

---

### 🤲 hands — 194 CLI Commands, Scripts & Automation
**Path**: `hands/`

What it does:
- `hands/bin/` — 194 symlinks; every workspace command lives here
- `hands/scripts/` — 50+ actual script implementations
- `hands/automation/dag/pipelines/night_shift.yaml` — nightly DAG pipeline
- `hands/automation/plists/` — launchd job configuration
- `hands/scripts/pre_commit_hook.sh` — codellama code review on every git commit
- `hands/automation/readme/` — README intelligence system (synthesizer, generator, validator)

**The symlink rule**: Every entry in `hands/bin/` must be a symlink (never a plain file). Enforced by `tests/organs/hands/test_hands.py`. To add a command: `ln -sf "$WORKSPACE/hands/scripts/script.sh" "$WORKSPACE/hands/bin/command-name"`.

**README auto-system**: The pre-push hook at `.git/hooks/pre-push` calls `hands/automation/readme/root_synthesizer.py`. It respects `<!-- README_PROTECTED: manual -->` markers (skips regeneration when found).

---

### 🗣️ mouth — Communication Dispatch
**Path**: `mouth/`

What it does:
- Intent dispatcher routes intents to channels (mail, iMessage)
- `intent_map.json` defines 9+ intent → handler mappings
- Adapters: Gmail (mail.py), iMessage (imessage.py, macOS only)
- **HUMAN_REQUIRED**: all outbound communication requires explicit approval

Key files:
```
mouth/ws.py              ← intent dispatcher
mouth/intent_map.json    ← 9 intent → channel mappings
mouth/comms/mail.py      ← Gmail adapter
mouth/comms/imessage.py  ← iMessage adapter
mouth/dispatcher/        ← dispatcher core
```

CLI: `mouth-dispatch "intent"`, `mouth-status`

---

### 🧬 dna — Identity, Hermes Agent & Model Training
**Path**: `dna/`

What it does:
- Identity profiles defining Suneel's voice, tone, and decision style
- Hermes agent (tirith) built on Ollama — the local AI agent layer
- `Modelfile.workspace` — builds the `suneelworkspace` Ollama model
- Training data — 103 pairs extracted from workspace history
- Adaptive identity loop learns slowly from accepted/rejected outputs

Key files:
```
dna/identity/prompts/identity_prompt.md               ← identity injection template
dna/identity/prompts/communication_prompt.md          ← comm style prompt
dna/identity/profile/identity_profile.md              ← who Suneel is
dna/identity/profile/tone_profile.md                  ← voice spec
dna/identity/profile/decision_profile.md              ← decision-making style
dna/agents/hermes/ollama_models/Modelfile.workspace   ← suneelworkspace definition (9,553 chars)
dna/agents/hermes/ollama_models/build_modelfile.py    ← rebuilds Modelfile from live state
dna/agents/hermes/ollama_models/build_training_data.py ← extracts training pairs
dna/agents/hermes/ollama_models/training_data.jsonl   ← 103 training pairs (~41KB)
dna/agents/hermes/skills/                             ← Hermes skill definitions
dna/feedback/                                         ← adapt loop feedback records
```

The `suneelworkspace` Ollama model:
```
FROM llama3.3:70b
SYSTEM """[9,553-char system prompt: identity, 12 organs, active tasks,
           decisions, patterns, safety boundaries]"""
PARAMETER temperature 0.2 | num_ctx 8192 | top_p 0.9 | repeat_penalty 1.1
```

Rebuild: `rebuild-model` (re-reads live workspace files → regenerates → `ollama create suneelworkspace`)

CLI: `rebuild-model`, `build-training-data`, `hermes-run`, `hermes-status`

---

### 🧪 lab — 9 Ollama Engines, Autolab & Evolution
**Path**: `lab/`

What it does:
- Hosts and schedules all 9 Ollama intelligence engines
- Context injector enriches every Ollama call with live workspace state
- Suggestion consumer closes the output→action loop
- Autolab experiment framework for workspace self-improvement
- Evolution engine for self-evaluation and improvement proposals

Engines (all in `lab/autolab/`, orchestrated by `ollama_orchestrator.py`):

| Engine | File | Model | Schedule | Purpose |
|--------|------|-------|----------|---------|
| Orchestrator | `ollama_orchestrator.py` | — | every 5 min | schedules all engines |
| Repair | `ollama_repair_engine.py` | suneelworkspace | every 4h | SAFE workspace fix suggestions |
| Nerve Healer | `nervous/nerve_healer.py` (link) | suneelworkspace | every 6h | heal broken organ connections |
| Memory Curator | `brain/memory/memory_curator.py` (link) | suneelworkspace | every 12h | keep MEMORY.md/DECISIONS.md lean |
| Learning | `ollama_learn_engine.py` | llama3.1 | every 8h | skill generation from experiments |
| Code Review | `code_review_engine.py` | codellama | every 6h | Python file review |
| Security Scan | `security_scanner.py` | mistral | every 12h | detect secrets, unsafe patterns |
| Experiment Skills | `experiment_skill_generator.py` | suneelworkspace | every 6h | extract skills from experiments |
| Suggestion Consumer | `suggestion_consumer.py` | — | every 2h | convert suggestions → task queue |
| Model Rebuild | (weekly) | — | weekly | rebuild suneelworkspace Modelfile |

**Context injector** (`lab/autolab/context_injector.py`) — used by every engine:
```python
from lab.autolab.context_injector import ask_ollama_with_context
response = ask_ollama_with_context(
    prompt="...",
    model="suneelworkspace",
    task_type="repair",     # general | repair | review | security
    timeout=120, temperature=0.2, num_ctx=8192
)
# Injects 4,000 chars of live context as system prompt (5-min TTL cache)
# Context: identity_profile, tone_profile, WORKSPACE_HEALTH, MEMORY, ACTIVE_TASKS,
#          SESSION_HANDOFF, DECISIONS, PATTERNS
```

**Suggestion consumer** (`lab/autolab/suggestion_consumer.py`):
- SAFE + confidence ≥ 0.75 → appends to `heart/tasks/TASK_QUEUE.md`
- Below threshold → `blood/logs/suggestion_controlled_queue.json`

**Security constraints**:
- All LLM-provided paths → `_path_within_workspace()`: rejects absolute paths, `..`, NUL bytes
- `create_file` → only to `_ALLOWED_CREATE_DIRS = ("tests/", "blood/logs/", "lab/autolab/experiments/")`
- `fix_symlink` → NEVER auto-applied; always queued

CLI: `ollama-stack-start`, `ollama-stack-status`, `ollama-stack-stop`, `ollama-orchestrate`, `ollama-repair`, `ollama-review`, `ollama-learn`, `security-scan`, `consume-suggestions`, `experiment-skills`, `rebuild-model`, `build-training-data`

---

### 🫀 spine — Health State, Diagnostics & README Intelligence
**Path**: `spine/`

What it does:
- `CURRENT_STATE.json` + `WORKSPACE_HEALTH.json` track live workspace state
- Diagnostic scheduler runs periodic health checks across all organs
- Audit logs, snapshots, backups
- README intelligence system tracks freshness across all organ READMEs (auto-updates every 30 min)
- Enhancement logger records workspace improvements

Key files:
```
spine/state/CURRENT_STATE.json            ← live state: session, tasks, health score
spine/state/WORKSPACE_HEALTH.json         ← health score, open issues, organ statuses
spine/diagnostics/diagnostic_scheduler.py ← periodic health check scheduler
spine/enhancement_logger.py               ← records enhancements
spine/audit/                              ← audit logs + decision records
spine/backups/ + spine/snapshots/         ← periodic state backups
spine/readme_health_cache.json            ← cached README health scores
spine/readme_metrics_history.json         ← health score history
spine/readme_dependency_map.json          ← cross-README dependency graph
spine/readme_policy.json                  ← README update policy rules
```

CLI: `agent-doctor`

---

## 7. Ollama Intelligence Stack Summary

**6 local models** × **9 engines** = the workspace AI layer.

All engines use `lab/autolab/context_injector.py` for workspace-aware prompting. The `suneelworkspace` model has Suneel's identity, all 12 organs, tasks, and decisions baked into its 9,553-char system prompt — it is never a generic LLM.

```bash
ollama-stack-start     # tmux: 'ollama-orchestrator' + 'nerve-healer' sessions
ollama-stack-status    # show each engine: DUE (needs to run) vs IDLE (wait)
ollama-stack-stop      # kill both tmux sessions
rebuild-model          # regenerate Modelfile.workspace → ollama create suneelworkspace
consume-suggestions    # manually flush suggestions → TASK_QUEUE.md
```

---

## 8. Memory System

All persistent workspace knowledge lives in plain Markdown:

| File | Updated By | Purpose |
|------|-----------|---------|
| `brain/memory/MEMORY.md` | Agents, curator | Durable workspace facts (single source of truth) |
| `brain/memory/DECISIONS.md` | Agents, curator | Architectural decisions with reasoning |
| `brain/memory/PATTERNS.md` | Curator | Recurring operating patterns |
| `brain/memory/INSIGHTS.md` | Curator | Higher-level learnings |
| `brain/memory/SESSION_HANDOFF.md` | `agent-finish` | Latest session summary for next agent |

**Rules**: store only stable facts; prefer updating over duplicating; curator runs every 12h (marks stale with `[STALE]`, never deletes).

---

## 9. Test Suite

**Status**: 103/103 passing (0.4s)

```bash
run-tests              # pytest + JUnit XML + JSON report → tests/reports/latest.json
repair-loop            # Ollama analyzes failures, applies SAFE fixes, retries ≤5x (target 95%)
readme-sync            # sync all READMEs with test results
install-git-hooks      # install codellama pre-commit hook
```

Test structure:
```
tests/
  conftest.py                                 ← shared fixtures
  test_runner.py                              ← master runner + JUnit XML + JSON reports
  autonomous_repair_loop.py                   ← Ollama-powered repair loop
  readme_sync.py                              ← README updater
  reports/latest.json                         ← most recent results
  organs/{brain,heart,eyes,ears,mouth,hands,blood,dna,spine}/test_*.py
  integration/test_full_pipeline.py
  nerve_system/test_nervous.py
  ollama_engines/test_ollama_engines.py
  security/test_security.py
  performance/test_performance.py
```

**Pre-commit hook** (`hands/scripts/pre_commit_hook.sh`):
- Triggers on every `git commit`; staged Python diff → `codellama` (warn-only, never blocks)
- Security: zero shell variable interpolation into code strings (all dynamic values via `sys.argv`)

---

## 10. Night Shift Pipeline

`hands/automation/dag/pipelines/night_shift.yaml` — nightly via launchd (`com.suneelworkspace.maintenance`, loaded ✅):

```
memory_curate     → curate MEMORY.md (Ollama)
brain_synthesize  → synthesize context
ollama_learn      → generate skills from experiments
hermes_brief      → build morning brief
run_tests         → full 103-test pytest suite
repair_loop       → autonomous repair (only if TEST_FAILURES > 0, max 3 iterations)
readme_sync       → sync all READMEs
```

---

## 11. Essential CLI Reference

### Agent Lifecycle
```bash
agent-start              # load startup context, print workspace brief
agent-finish "summary"   # close session: update handoffs, log, state
agent-doctor             # full diagnostic → update WORKSPACE_HEALTH.json
workspace-context        # print CURRENT_STATE.json brief
workspace-dashboard      # start FastAPI dashboard at port 7777
```

### Testing
```bash
run-tests                # full pytest suite
repair-loop              # autonomous Ollama-powered repair loop
readme-sync              # sync all READMEs
install-git-hooks        # install pre-commit hook
```

### Memory & Intelligence
```bash
memory-search "query"    # semantic vector search over brain/memory/
memory-curate            # Ollama curation pass
memory-reindex           # rebuild ChromaDB vector index
morning-brief            # build daily digest
morning-brief-personal   # Ollama-scored personalized brief
idea-start               # capture a new research idea
idea-run                 # run research pipeline on an idea
```

### Ollama Stack
```bash
ollama-stack-start       # start orchestrator + healer in tmux
ollama-stack-status      # check engine DUE/IDLE status
ollama-stack-stop        # stop tmux sessions
ollama-orchestrate       # run one scheduler pass
ollama-repair            # run repair engine directly
ollama-review            # run code review engine
ollama-learn             # run learning engine
security-scan            # run security scanner (mistral)
rebuild-model            # rebuild suneelworkspace Modelfile
consume-suggestions      # flush suggestions → TASK_QUEUE.md
build-training-data      # extract training pairs from history
```

### Goals & Tasks
```bash
goal-create              # create a goal
goal-status              # view active goals
goal-execute             # execute a goal step
goal-complete            # mark goal complete
```

### Model Routing
```bash
model-route              # route task to best model
model-health             # check all model availability
model-rotate             # get best model for a task type
model-status             # view rotation stats + quota
```

### Nerve System
```bash
nerve-status             # print all 12 organ statuses
nerve-heal               # run Ollama nerve healer
nerve-check              # validate all nerve.json files
```

### README System
```bash
readme-root-build        # rebuild root README (skips if README_PROTECTED marker found)
readme-update <folder>   # update a single organ README
readme-update-all        # update all organ READMEs
readme-validate          # validate README freshness
readme-repair            # repair stale/missing READMEs
git-safe-push            # validate + push (README guard enforced)
```

---

## 12. Token Optimization (RTK)

All bash commands should be prefixed with `rtk` for 60–90% output token savings:

```bash
rtk git status           # compact status
rtk git diff             # compact diff (80% savings)
rtk cargo test           # failures only (90% savings)
rtk next build           # route metrics (87% savings)
rtk gain                 # view savings analytics
rtk gain --history       # command history with savings
```

**Headroom proxy** at `http://127.0.0.1:8787` (`ANTHROPIC_BASE_URL`) compresses context on every Claude API call.

---

## 13. Key Files Quick Reference

| File | Purpose |
|------|---------|
| `skeleton/rules/AGENT_SYSTEM.md` | Canonical rules — read this first |
| `skeleton/rules/SAFETY_BOUNDARIES.md` | Hard limits |
| `brain/memory/MEMORY.md` | Durable workspace facts |
| `brain/memory/DECISIONS.md` | Architectural decisions |
| `brain/memory/SESSION_HANDOFF.md` | Previous session summary |
| `heart/tasks/ACTIVE_TASKS.md` | Current task list |
| `heart/tasks/TASK_QUEUE.md` | Queued tasks |
| `spine/state/CURRENT_STATE.json` | Live state |
| `spine/state/WORKSPACE_HEALTH.json` | Health score + issues |
| `dna/identity/profile/identity_profile.md` | Suneel's voice and style |
| `dna/agents/hermes/ollama_models/Modelfile.workspace` | suneelworkspace definition |
| `lab/autolab/context_injector.py` | Workspace context injector |
| `lab/autolab/ollama_orchestrator.py` | Engine scheduler |
| `lab/autolab/suggestion_consumer.py` | Suggestion → task converter |
| `nervous/nerve_propagator.py` | Inter-organ event bus |
| `nervous/nerve_registry.json` | 12-organ dependency map |
| `hands/automation/dag/pipelines/night_shift.yaml` | Nightly pipeline |
| `hands/scripts/pre_commit_hook.sh` | codellama pre-commit review |
| `hands/automation/readme/root_synthesizer.py` | Root README builder (respects this marker) |
| `tests/autonomous_repair_loop.py` | Ollama repair loop |
| `blood/logs/repair_loop_controlled_queue.json` | Awaiting human review |
| `blood/logs/suggestion_controlled_queue.json` | Awaiting human review |

---

## 14. Current Workspace Health

**As of 2026-06-28**:

| Metric | Value |
|--------|-------|
| Tests | 103/103 passing ✅ |
| Ollama | running — 6 models, 9 engines ✅ |
| Dashboard | `http://localhost:7777` |
| Nerve system | 12/12 organs — nerve.json v1.1 |
| Pre-commit hook | installed (codellama, warn-only) |
| Night shift | launchd loaded ✅ |
| Health status | `repairable` (7 open issues, none blocking) |

Open issues (`spine/state/WORKSPACE_HEALTH.json`):
- `gstack_drift` — gstack-verify binary drift (warning, non-blocking)
- `codex_not_on_path` / `claude_not_on_path` — CLI tools not in current shell PATH (info only)
- `internal_script_duplication` — duplicate `_run` in `eyes/dashboard/server.py:828` (warning)
- `non_symlink_bin_file` — `hands/bin/README.md` is a plain file not a symlink (warning)
- `misplaced_script` / `misplaced_config` — overly strict diagnostic flagging `tests/` files (false positives)

---

## 15. Architectural Decisions (Key)

| Date | Decision |
|------|----------|
| 2026-06-24 | File-based shared workspace — transparent, durable, multi-agent |
| 2026-06-24 | One canonical instruction: `skeleton/rules/AGENT_SYSTEM.md` |
| 2026-06-24 | Symlink entrypoints: AGENTS.md, CLAUDE.md → canonical file |
| 2026-06-24 | `hands/bin/` = symlinks only, never plain files |
| 2026-06-24 | One launchd job for all periodic maintenance |
| 2026-06-24 | Autolab for safe bounded workspace self-improvement |
| 2026-06-25 | Microsoft 365 Copilot as external prompt engineer |
| 2026-06-25 | Bounded self-upgrade policy (local-only, no external installs without approval) |
| 2026-06-26 | `dna/identity/` as source of truth for Suneel's voice |
| 2026-06-26 | Adaptive identity loop in `dna/identity/adaptive/` |
| 2026-06-26 | `README.md` = executable system blueprint (this document) |
| 2026-06-26 | Anticipation engine — suggest only, never auto-execute |
| 2026-06-28 | suneelworkspace model on llama3.3:70b with 9,553-char baked system prompt |
| 2026-06-28 | Context injection in every Ollama call (4,000 chars, 5-min TTL) |
| 2026-06-28 | Suggestion consumer closes output→action loop |
| 2026-06-28 | LLM symlink fixes always queued, never auto-applied |
| 2026-06-28 | Shell vars never interpolated into `python3 -c` strings (sys.argv only) |
| 2026-06-28 | README_PROTECTED marker prevents root_synthesizer from clobbering hand-crafted README |

---

*This README is the zero-gap system blueprint. Any agent with only this file has everything needed to understand and operate SuneelWorkSpace.*


## TEST STATUS

**103/103 tests passing** (100.0%) [OK] — Last run: 2026-07-02 05:27 UTC

| Category | Status |
|---|---|
| Nerve Connections | Pass |
| Ollama Engines | Pass |
| Integration | Pass |

`run-tests` to run | `repair-loop` to auto-fix
