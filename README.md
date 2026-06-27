# SuneelWorkSpace System Blueprint

## EXECUTIVE SUMMARY (FAST LOAD)
- **Role**: Local-first personal AI operating system workspace.
- **Components**: Incorporates identity, stateful memory, workflows, MCP connectors, and execution orchestration.
- **Real-world execution**: Supports direct local tool execution, GitHub, and macOS shortcuts automation.
- **Knowledge Brain**: Integrated with Obsidian brain storage layer for notes and generated runnable workflows.
- **Self-Evolution**: Daily self-improvement loops scan log contexts and optimize parameters.
- **Shared Context**: Enables multi-agent workspace continuity (Claude, Codex, Gemini, OpenCode).
- **Safety & Integrity**: Enforced via duplication-guard, AST/syntax checks, and canonical integrity checks.

## START HERE (FOR AI AGENTS)
Welcome external agent! Follow this boot sequence for immediate alignment:
1. **Load Identity**: Read `dna/dna/identity/prompts/identity_prompt.md` and related profile configs.
2. **Access memory**: Read `brain/memory/MEMORY.md` and active tasks list.
3. **Read MCP resource map**: Inspect `nervous/nervous/mcp/server/config/resource_map.json` and capabilities list.
4. **Inspect context**: Read `spine/state/ACTIVE_CONTEXT.json`.
5. **Check workflows**: Look up priority order in `brain/system/workflow_priority.json`.
6. **Execution pattern**: Execute using `intent` → `select workflow` → `run workflow` → `record outcome` pipeline.
*Do NOT treat this as a simple project. This is a stateful AI operating system.*

## CAPABILITY MAP
### What the system CAN do:
- **Run Workflows**: Execute MCP and non-MCP workflows compiled dynamically.
- **Chain Tools**: Compose multi-step pipelines and pass outputs between steps.
- **Operate GitHub**: List PRs and create tracking issues.
- **Automate macOS**: Retrieve, list, and run shortcuts.
- **Manage Files**: Perform scoped reads, writes, listings, and duplication checks.
- **Research via Web**: Fetch search results using Brave search MCP.
- **Manage Knowledge**: Keep Obsidian notes synced and extract executable scripts.

### What REQUIRES user approval (CONTROLLED / RESTRICTED):
- **Outbound Communication**: Sending iMessage or emails (gated approval).
- **External Installs**: Changing system directories or npm/pip package installations.
- **Destructive Actions**: Deleting, modifying core files, or running overrides.

## HOW TO SUGGEST ENHANCEMENTS
If you identify optimization vectors or logic gaps, propose improvements by:
1. **Adding Workflows**: Write new step-by-step Markdown notes in `brain/workflows/`.
2. **Expanding Connectors**: Add new capabilities to the MCP config.
3. **Optimizing**: Refine parameters or suggest script upgrades.
*DO NOT suggest rebuilding the system, duplicating code, or breaking canonical structures.*

## SYSTEM RULES (NON-NEGOTIABLE)
- **Zero Duplication**: Do not build parallel features. Upgrade or extend existing systems.
- **Integrity Gates**: Run `duplication-guard` and `integrity-guard` before editing source files.
- **Canonical Subsystems**: Always use canonical helpers in `bin/` or `scripts/`.
- **Clean Symlinks**: All executables in `bin/` must remain as relative symlinks.

## SYSTEM EXPANSION STRATEGY
The system scales horizontally by:
1. **MCP Connectors**: Introducing specialized API/tool bridges.
2. **Workflows**: Defining high-level pipelines in Obsidian notes.
3. **Identity/Priority Tuning**: Updating score matrices and prompt patterns.
*Avoid rewriting core engine architectures or introducing redundant logic layers.*

## IDEAL INTERACTION MODEL
- **User Intent**: The user provides high-level goals.
- **System Routing**: The system maps the intent to the best workflow, runs it, logs outcome metrics to `workflow_performance.json`, and evolves executing parameters dynamically.

## EXTERNAL AGENT OBJECTIVE
If you are an external AI:
Your goals are to reduce user friction, increase automation reliability, enhance execution quality, propose safe optimizations, and expand capability integrations without introducing duplicate code.

---

This README is the complete operating blueprint for `~/SuneelWorkSpace`.

If this file is copied into another environment, another AI agent should understand what the system is, how it thinks, where memory lives, what commands exist, what is safe, what is not safe, and how to extend it without rebuilding.

## 1. System Overview

`SuneelWorkSpace` is Suneel's local-first personal AI operating system workspace.

It is designed to be:

- Predictive, not only reactive.
- Identity-aware, so outputs match Suneel's style.
- Adaptive, so identity improves from real feedback without drifting.
- Research-capable, so rough ideas become plans, comparisons, and decisions.
- Agent-shared, so Claude, Codex, Gemini, OpenCode, and MCP tools use the same memory.
- Safe and inspectable, with plain files as the source of truth.

The system helps with:

- Coding and local automation.
- Workspace self-improvement.
- Research and idea development.
- Goal planning and execution.
- Email and messaging support.
- Tool discovery and recommendations.
- MCP-backed shared memory.
- Autolab experiments and repair loops.
- Anticipatory next-action suggestions.

### Architecture Diagram

```text
Suneel
  |
  v
Agent Entry Points
  - Claude: CLAUDE.md, ~/.claude/CLAUDE.md
  - Codex: AGENTS.md, ~/.hands/codex/AGENTS.md
  - Gemini/OpenCode launchers in bin/
  |
  v
Shared Workspace Brain
  brain/memory/
    shared rules, identity, safety, memory, decisions, tasks, state, logs
  |
  +--> dna/identity/
  |     base profile, tone profile, decision profile, prompts
  |     adaptive loop: feedback -> weighted signals -> bounded updates
  |
  +--> brain/anticipation/
  |     command/workflow events -> sequence patterns -> suggested next actions
  |
  +--> brain/research/
  |     idea capture -> research plan -> analysis -> decision
  |
  +--> heart/orchestrator/
  |     task routing, agent selection, routing history, gstack hints
  |
  +--> heart/goals/
  |     goal creation, planning, execution, monitoring, dependency graph
  |
  +--> mouth/comms/
  |     mail and iMessage search/draft/status support with send approval gates
  |
  +--> nervous/mcp/
  |     workspace-brain resources, indexes, shared context access
  |
  +--> lab/autolab/
        bounded self-improvement experiments, evaluator, reports, rollback state
```

## 2. Core Subsystems

### Agent System

Path: `brain/memory/`

This is the shared source for workspace rules, identity context, memory, tasks, logs, and state.

Important files:

- `skeleton/rules/AGENT_SYSTEM.md`: canonical shared system policy.
- `skeleton/rules/IDENTITY.md`: shared user/workspace identity context.
- `skeleton/rules/SAFETY_BOUNDARIES.md`: safety rules.
- `skeleton/rules/BOUNDED_SELF_UPGRADE.md`: allowed and approval-gated self-upgrades.
- `brain/memory/MEMORY.md`: stable facts.
- `brain/memory/DECISIONS.md`: important choices and reasons.
- `brain/memory/PATTERNS.md`: recurring operating patterns.
- `brain/memory/INSIGHTS.md`: higher-level learning.
- `heart/tasks/ACTIVE_TASKS.md`: current tasks.
- `heart/tasks/COMPLETED_TASKS.md`: completed task history.
- `brain/memory/SESSION_HANDOFF.md`: latest handoff.
- `spine/state/CURRENT_STATE.json`: current state.
- `spine/state/WORKSPACE_HEALTH.json`: health and readiness.

### Identity System

Path: `dna/identity/`

The identity system defines how agents should sound, decide, plan, and communicate for Suneel.

Base files:

- `dna/dna/identity/profile/identity_profile.md`: core identity profile.
- `dna/dna/identity/profile/tone_profile.md`: writing and tone rules.
- `dna/dna/identity/profile/decision_profile.md`: decision rules.
- `dna/dna/identity/profile/preferences.json`: structured preferences.
- `dna/dna/identity/profile/behavioral_patterns.json`: behavior patterns.
- `dna/dna/identity/prompts/identity_prompt.md`: agent identity prompt.
- `dna/dna/identity/prompts/communication_prompt.md`: email/message/summarization voice prompt.
- `dna/identity/integration/routing_identity.json`: routing and autonomy rules.
- `dna/identity/reports/identity_summary.md`: human-readable summary.

Suneel's base style:

- Short.
- Direct.
- Casual.
- Conversational.
- Smart.
- Structured when useful.
- Softened, not harsh.
- Never condescending.

Decision style:

- Analysis first.
- Intuition second.
- Break uncertainty into small problems.
- Prefer tools by simplicity, cost, power, speed, reliability.
- Autopilot by default.
- Ask only for serious system risk or safety-gated actions.

### Adaptive Identity

Path: `dna/dna/identity/adaptive/`

The adaptive identity loop improves Suneel's voice and decision behavior from real interaction outcomes.

Files:

- `dna/dna/identity/adaptive/feedback_log.json`: raw feedback events.
- `dna/dna/identity/adaptive/signal_weights.json`: quality weights for signal types.
- `dna/dna/identity/adaptive/signal_memory.json`: extracted weighted signals.
- `dna/dna/identity/adaptive/pattern_updates.json`: proposed and active adjustments.
- `dna/dna/identity/adaptive/drift_guardrails.json`: strict drift limits.
- `dna/dna/identity/adaptive/adaptation_state.json`: current loop state.
- `dna/dna/identity/adaptive/reports/adaptation_report.md`: report.
- `dna/dna/identity/adaptive/adaptive_identity.py`: learning engine.

Signal weights:

```json
{
  "accepted": 0.2,
  "light_edit": 0.4,
  "heavy_edit": 0.8,
  "rejected": 1.0,
  "manual_adjust": 1.2,
  "repeat_preference": 1.0,
  "goal_outcome_success": 0.7,
  "goal_outcome_failure": 1.1
}
```

Learning rule:

- Patterns are based on weighted evidence, not raw counts.
- Rejections and manual adjustments matter more than simple acceptances.
- Multiple signals are required before behavior changes.
- Updates are small.
- Base identity rules are never overridden.

### Anticipation Engine

Path: `brain/anticipation/`

The anticipation engine records command and workflow sequences, detects repeated patterns, and suggests next actions before Suneel asks.

Files:

- `brain/anticipation/prediction_engine.py`: prediction engine.
- `brain/anticipation/prediction_memory.json`: command/workflow event memory.
- `brain/anticipation/behavior_patterns.json`: built-in and learned behavior patterns.
- `brain/anticipation/action_suggestions.md`: latest suggestions.
- `brain/anticipation/reports/anticipation_report.md`: report.

Rules:

- Suggest only.
- Pre-plan only.
- Pre-compute only.
- Never auto-execute actions.
- Never override safety boundaries.

Example suggestions:

- After `imsg-recent`: suggest reviewing messages or drafting replies.
- After `goal-create`: suggest `goal-plan`.
- After `idea-run`: suggest reviewing analysis and converting accepted work into a goal.
- After `system-gaps`: suggest opening the improvement plan or running `improve-system`.

### Research Engine

Path: `brain/research/`

Turns rough ideas into durable local research artifacts.

Files:

- `brain/research/research_engine.py`: engine.
- `brain/research/ideas/`: captured ideas.
- `brain/research/plans/`: research plans.
- `brain/research/analyses/`: comparisons and analysis.
- `brain/research/decisions/`: decision records.

Main commands:

- `idea-start`: capture an idea.
- `idea-run`: capture, plan, analyze, and draft a decision.

### Comms Subsystem

Path: `mouth/comms/`

Supports email and iMessage workflows while preserving safety boundaries.

Important files:

- `mouth/mouth/comms/config/comms_config.json`: comms config, identity, adaptive identity, anticipation pointers.
- `mouth/comms/mail/`: mail state/logs/scripts.
- `mouth/comms/imessage/`: iMessage state/logs/scripts.
- `mouth/comms/reports/latest_comms_report.md`: report.

Rules:

- Drafting is allowed.
- Searching/status is allowed.
- Sending requires explicit approval.
- Deleting/archive/forward/contact actions require approval.
- Drafts should use `dna/dna/identity/prompts/communication_prompt.md`.

### MCP Workspace Brain

Path: `nervous/mcp/`

The MCP subsystem exposes workspace resources to connected agents.

Important files:

- `nervous/nervous/mcp/server/main.py`: MCP server.
- `nervous/nervous/mcp/server/config/resource_map.json`: resource registry.
- `nervous/nervous/mcp/server/storage/memory_index.db`: local index.
- `nervous/nervous/mcp/server/state/last_index.json`: latest index metadata.

Important resources include:

- `workspace://dna/identity/profile`
- `workspace://dna/dna/identity/adaptive/feedback-log`
- `workspace://dna/dna/identity/adaptive/signal-weights`
- `workspace://brain/anticipation/memory`
- `workspace://brain/anticipation/suggestions`
- `workspace://spine/audit/system`
- `workspace://readme/blueprint`
- `workspace://spine/tools/inventory`
- `workspace://research/index`
- `workspace://memory/patterns`

### Orchestrator

Path: `heart/orchestrator/`

Routes tasks to the right agent/tool mode.

Important files:

- `heart/heart/orchestrator/router/task_types.json`
- `heart/heart/orchestrator/router/agent_profiles.json`
- `heart/heart/orchestrator/router/gstack_policy.json`
- `heart/heart/orchestrator/router/system_intelligence_policy.md`
- `heart/orchestrator/state/current_routing_state.json`
- `heart/orchestrator/reports/routing_report.md`

It uses:

- Task type.
- Agent profiles.
- GStack hints.
- Identity routing rules.
- Anticipatory suggestions.

### Goal Engine

Path: `heart/goals/`

Turns goals into tasks, plans, dependency graphs, execution runs, and reports.

Important files:

- `heart/goals/goals/active_goals.md`
- `heart/goals/planner/planner.md`
- `heart/goals/planner/idea_execution_pipeline.md`
- `heart/goals/graph/task_graph.json`
- `heart/goals/state/goal_state.json`
- `heart/goals/execution/execution_log.md`

Goal execution records adaptive identity and anticipation events.

### Autolab

Path: `lab/autolab/`

Autolab is the bounded workspace self-improvement lab.

Important files:

- `lab/autolab/program.md`
- `lab/autolab/mutation_policy.md`
- `lab/autolab/safeguards.md`
- `lab/autolab/evaluator.md`
- `lab/autolab/current_frontier.md`
- `lab/autolab/meta/adaptive_identity_strategy.md`
- `lab/autolab/meta/anticipation_strategy.md`
- `lab/autolab/reports/latest_report.md`

Autolab may recommend improvements, but it must not override identity or execute unsafe changes automatically.

## 3. How The System Thinks

The system uses three layers:

1. Identity drives tone and decisions.
2. Adaptive identity learns from behavior.
3. Anticipation predicts next actions.

Flow:

```text
User request
  -> load shared rules and identity
  -> inspect current workspace state
  -> decide whether to act or ask
  -> execute safe local work
  -> record feedback/workflow signals
  -> update adaptive memory and anticipation memory
  -> suggest next actions
  -> update handoff/logs/state
```

Identity is the anchor. Adaptive learning is tuning. Anticipation is suggestion. Safety boundaries override all three.

## Intent Layer

The system must infer user intent before acting.

Intent categories:

- `messaging`
- `email`
- `research`
- `system_improvement`
- `development`
- `idea_execution`
- `maintenance`
- `unknown`

Intent is inferred from:

- Command used.
- Recent actions.
- Goal context.
- Task wording or route context.

Intent is stored in:

- `brain/anticipation/current_context.json`

Agent behavior:

1. Infer intent.
2. Align the response to that intent.
3. Filter suggestions based on that intent.
4. Keep suggestions relevant, minimal, and safe.

The intent layer does not execute anything. It only helps the system choose the right tone, workflow, and next-step suggestions.

## Ranked Suggestions

After any meaningful action, the system may suggest next steps.

Suggestion rules:

- Suggestions must be ranked.
- Suggestions must be limited to the top 3-5.
- Suggestions must be relevant to current intent.
- Suggestions must be high-signal, not generic.
- Suggestions must never auto-execute.

Scoring contract:

```text
suggestion_score =
  frequency_weight
  + success_weight
  + recency_weight
  + identity_alignment
  + intent_alignment
```

Output format:

```text
Suggested next actions:
1. [HIGH] ...
2. [MED] ...
3. [LOW] ...
```

Ranking is implemented in `brain/anticipation/prediction_engine.py`.

## 4. Command Reference

Run commands from `~/SuneelWorkSpace` or ensure `~/SuneelWorkSpace/bin` is on `PATH`.

### Agent And Maintenance

| Command | What it does | When to use |
|---|---|---|
| `agent-start` | Loads startup context and session state. | Start of an agent session. |
| `agent-finish "summary"` | Updates handoff, logs, state, and reports. | End of meaningful work. |
| `agent-status` | Shows workspace health/status summary. | Quick system check. |
| `agent-doctor` | Runs workspace health checks. | Before repair or after upgrades. |
| `agent-repair` | Repairs small known workspace issues. | When doctor reports repairable issues. |
| `agent-maintain` | Runs maintenance, doctor, reports, and refreshes. | Routine upkeep. |
| `agent-autoclose` | Idempotent session closeout/recovery. | Used by wrappers and startup recovery. |
| `agent-test-loop` | Test loop helper. | Validate repeated agent workflows. |

### System Intelligence

| Command | What it does | When to use |
|---|---|---|
| `system-audit` | Refreshes `spine/audit/system_audit.md`. | Need full system overview. |
| `system-gaps` | Refreshes `spine/audit/gap_analysis.md`. | Need current gaps and priorities. |
| `system-capabilities` | Refreshes `spine/system-context/system_profile.json`. | Need safe machine/workspace capability summary. |
| `system-recommend` | Refreshes `spine/tools/recommendations.md`. | Need improvement ideas. |
| `improve-system` | Runs bounded system intelligence refresh. | Safe local self-improvement scan. |
| `anticipate` | Records or asks for next-action suggestions. | Work with prediction engine directly. |

`anticipate` subcommands:

- `anticipate intent <command>`: infer and store intent.
- `anticipate suggest <command>`: print ranked suggestions.
- `anticipate record --command <command>`: record an action and update prediction memory.
- `anticipate report`: refresh anticipation report.

### Identity

| Command | What it does | When to use |
|---|---|---|
| `identity-accept <id>` | Records accepted output feedback. | Mark an output as good. |
| `identity-reject <id> "reason"` | Records rejected output feedback. | Teach the system what missed. |
| `identity-adjust "instruction"` | Records a manual identity adjustment. | Give direct style/behavior correction. |

### Research And Ideas

| Command | What it does | When to use |
|---|---|---|
| `idea-start` | Captures a raw idea. | Save a new idea. |
| `idea-run` | Captures, researches, analyzes, and drafts a decision. | Turn an idea into a plan. |

Lower-level scripts also exist in `brain/research/scripts/`: `idea-bootstrap`, `idea-capture`, `idea-research`, `idea-analyze`, `idea-decide`.

### Goal Engine

| Command | What it does | When to use |
|---|---|---|
| `goal-create` | Creates a goal. | Start goal-driven work. |
| `goal-plan` | Decomposes a goal into tasks. | Before execution. |
| `goal-execute` | Executes planned goal tasks. | Run safe planned work. |
| `goal-monitor` | Monitors active goals. | Track progress. |
| `goal-status` | Shows goal status. | Check current goal state. |
| `goal-complete` | Marks a goal complete. | After verification. |
| `goal-fail` | Marks a goal failed. | When a goal cannot continue. |
| `goal-adapt` | Adjusts goal planning/state. | When plan needs revision. |

### Orchestrator

| Command | What it does | When to use |
|---|---|---|
| `route-task` | Recommends agent/tool/mode for a task. | Before assigning work. |
| `route-execute` | Executes routed work. | Run routed workflows. |
| `route-analyze` | Analyzes routing behavior. | Improve routing. |
| `route-learn` | Updates routing learning. | After repeated routing evidence. |

### Comms

| Command | What it does | When to use |
|---|---|---|
| `comms-status` | Shows comms subsystem status. | Check email/message readiness. |
| `comms-doctor` | Checks comms setup. | Diagnose comms issues. |
| `comms-permissions-check` | Checks permissions. | Before mail/message automation. |
| `comms-report` | Generates comms report. | Review comms state. |
| `mail-status` | Shows mail state. | Check mail readiness. |
| `mail-recent` | Lists recent mail metadata. | Triage mail. |
| `mail-search` | Searches mail metadata/content as configured. | Find mail. |
| `mail-draft-reply` | Drafts a mail reply. | Prepare a reply for review. |
| `imessage-status` | Shows iMessage state. | Check message readiness. |
| `imessage-recent` | Lists recent message metadata. | Triage messages. |
| `imessage-search` | Searches messages. | Find message context. |
| `imessage-send-draft` | Creates/sends through approval flow as configured. | Draft message flow. |
| `imsg-recent` | Short alias for recent iMessage workflow. | Quick message triage. |
| `imsg-search` | Short alias for iMessage search. | Quick message search. |
| `imsg-draft` | Short alias for drafting message. | Draft message. |
| `imsg-send-confirmed` | Confirmed send path. | Only after explicit approval. |
| `install-imessage-plugin` | Installs/links iMessage plugin support. | Only when intentionally configuring comms. |

### MCP

| Command | What it does | When to use |
|---|---|---|
| `mcp-start` | Starts MCP server. | Enable MCP workspace brain. |
| `mcp-stop` | Stops MCP server. | Stop MCP. |
| `mcp-status` | Shows MCP status. | Check server/index state. |
| `mcp-doctor` | Checks MCP health. | Diagnose MCP. |
| `mcp-reindex` | Rebuilds workspace-brain index. | After new memory/resources. |
| `mcp-repair` | Repairs known MCP issues. | When doctor finds repairable problems. |
| `mcp-report` | Generates MCP report. | Review MCP state. |
| `mcp-test` | Tests MCP functionality. | Validate MCP. |

### GStack

| Command | What it does | When to use |
|---|---|---|
| `gstack-create` | Creates/sets up gstack assets. | Advanced specialist mode setup. |
| `gstack-repair` | Repairs gstack setup. | When gstack verification fails. |
| `gstack-verify` | Verifies gstack integration. | Before specialist workflows. |

### Workspace Utilities

| Command | What it does | When to use |
|---|---|---|
| `workspace-context` | Prints startup/workspace context. | Fast orientation. |
| `workspace-index` | Refreshes/prints workspace index. | Inspect file map. |
| `workspace-report` | Generates workspace report. | Review system state. |
| `workspace-backup` | Creates backup. | Before risky changes. |
| `workspace-changes` | Shows workspace changes. | Review uncommitted work. |
| `workflow-audit` | Audits workflow setup. | Check workflow health. |

### Agent Launchers

| Command | What it does | When to use |
|---|---|---|
| `use-claude` | Starts Claude wrapper/context. | Claude session. |
| `use-codex` | Starts Codex wrapper/context. | Codex session. |
| `use-gemini` | Starts Gemini fallback. | Free/fallback agent. |
| `use-opencode` | Starts OpenCode fallback. | Free/fallback agent. |
| `use-opencode-gemini` | Hybrid fallback launcher. | Alternative fallback path. |
| `use-claude-imessage` | Claude with iMessage context. | Comms-focused Claude work. |

## 5. Workflow Examples

### Idea To Execution

```sh
idea-run "Build a new workflow" "What it should do"
goal-create
goal-plan
route-task "implement the accepted workflow"
route-execute
goal-monitor
goal-complete
agent-finish "summary"
```

What happens:

- Research engine captures and analyzes the idea.
- Goal engine turns it into tasks.
- Orchestrator chooses the right execution path.
- Adaptive identity records feedback.
- Anticipation suggests the next step.

### Messaging Workflow

```sh
imsg-recent
imsg-draft
imsg-send-confirmed
```

Rules:

- Recent/search/draft workflows can run locally.
- Drafts follow Suneel's communication profile.
- Sending requires explicit approval.
- Anticipation may suggest drafting replies after recent-message review.

### Mail Workflow

```sh
mail-recent
mail-search "topic"
mail-draft-reply
```

Rules:

- Draft only unless Suneel confirms send.
- Use `dna/dna/identity/prompts/communication_prompt.md`.
- Keep tone short, direct, casual, and softened.

### System Improvement Workflow

```sh
system-audit
system-gaps
system-recommend
improve-system
agent-doctor
mcp-reindex
agent-finish "summary"
```

What happens:

- Audit detects current state.
- Gaps are classified.
- Recommendations are generated.
- Safe local improvements refresh.
- Health and MCP index are validated.

## 6. Data And Memory Map

| Area | Path | Purpose |
|---|---|---|
| Canonical rules | `skeleton/rules/` | System policy, identity, workflow, safety. |
| Durable memory | `brain/memory/` | Facts, decisions, patterns, insights, handoff. |
| Tasks | `heart/tasks/` | Active, queued, and completed tasks. |
| State | `spine/state/` | Current state and health JSON. |
| Logs | `blood/logs/` | Session logs. |
| Identity | `dna/identity/` | Profile, tone, decision, prompts. |
| Adaptive identity | `dna/dna/identity/adaptive/` | Feedback, weighted signals, bounded adjustments. |
| Anticipation | `brain/anticipation/` | Prediction memory, behavior patterns, suggestions. |
| Research | `brain/research/` | Ideas, plans, analyses, decisions. |
| Orchestrator | `heart/orchestrator/` | Routing policies, state, reports. |
| Goals | `heart/goals/` | Goals, plans, graphs, execution logs. |
| Comms | `mouth/comms/` | Mail/iMessage config, state, logs, reports. |
| MCP | `nervous/mcp/` | Server, resource map, index DB, state. |
| Autolab | `lab/autolab/` | Self-improvement experiments, evaluator, reports. |
| Audit | `spine/audit/` | System audit, gap analysis, improvement plan. |
| Tools | `spine/tools/` | Tool inventory and recommendations. |

### Full Folder Coverage

These top-level folders are part of the workspace and are intentionally documented:

| Folder | Purpose |
|---|---|
| `.agent-backups/` | Timestamped backups created before/around agent maintenance and repairs. |
| `.agents/` | Antigravity/agent-specific config and skills. |
| `.claude/` | Workspace Claude-related config/cache when present. |
| `.gstack/` | GStack specialist-mode local files. |
| `.rtk/` | RTK/token-filter local state. |
| `.serena/` | Serena/tooling state if enabled. |
| `.vscode/` | Local editor configuration. |
| `brain/memory/` | Shared brain, rules, memory, logs, state. |
| `brain/anticipation/` | Intent detection, prediction memory, ranked next-action suggestions. |
| `spine/audit/` | System audit, gap analysis, improvement plan. |
| `lab/autolab/` | Bounded self-improvement lab. |
| `automation/` | Local automation helpers and maintenance support. |
| `bin/` | User-facing command wrappers. |
| `hands/codex/` | Codex-specific workspace files. |
| `mouth/comms/` | Mail and iMessage workflows. |
| `spine/docs/` | Documentation and specs. |
| `heart/goals/` | Goals, planning, execution, monitoring. |
| `dna/identity/` | Identity, adaptive identity, tone, decision profiles. |
| `nervous/mcp/` | Workspace-brain MCP server and resource index. |
| `brain/vault/` | Obsidian-facing knowledge vault. |
| `heart/orchestrator/` | Routing and agent selection. |
| `projects/` | Project work area. |
| `brain/research/` | Idea capture, research, analysis, decisions. |
| `scripts/` | Shared local scripts behind commands. |
| `spine/snapshots/` | Snapshot state for recovery/experiments. |
| `spine/system-context/` | Safe metadata-only machine/workspace profile. |
| `spine/tools/` | Tool inventory and recommendations. |
| System context | `spine/system-context/` | Safe machine/workspace profile. |

Inspect commands:

```sh
agent-status
agent-doctor
mcp-status
system-gaps
anticipate report
python3 -m json.tool dna/dna/identity/adaptive/signal_memory.json
```

## 7. Safety Model

Hard rules:

- No money actions.
- No account upgrades.
- No purchases.
- No destructive actions without explicit approval and backup.
- No automatic system wipe.
- No automatic deletion of important files.
- No automatic sending of emails/messages.
- No deep private indexing outside approved scope.
- No hidden state when a plain file will work.
- No blind merges between similar workspace folders.

Bounded adaptation:

- Base identity is protected.
- Drift guardrails control all adaptive changes.
- Weighted signals improve quality, but do not override explicit preferences.
- Large tone or safety changes require review.

Anticipation safety:

- SAFE actions (read-only, status checks) are automatically executed when the suggestion has high confidence (>= 0.8) AND context strength is strong (> 0.7).
- SAFE actions that do not meet these criteria, and all CONTROLLED actions (drafting, planning, creating files), require explicit user confirmation.
- RESTRICTED actions (destructives, installs, comms) are blocked by default and require explicit justification/reasoning.
- Suggestions can pre-plan or pre-compute only.
- User approval is required before risky action.

Local-first:

- Plain files are the source of truth.
- MCP index is local.
- Research artifacts are local.
- Machine awareness is metadata-only unless explicitly expanded.

## System Capabilities

### The System Can Do

- Inspect and summarize workspace files under `~/SuneelWorkSpace`.
- Run local maintenance, audit, doctor, and report commands.
- Generate research plans, analyses, and decision records.
- Draft email/message replies for review.
- Search configured mail/message metadata and accessible local records.
- Create and execute local goals through the goal engine.
- Route tasks through orchestrator policies.
- Record adaptive identity feedback.
- Infer intent and suggest ranked next actions.
- Reindex MCP workspace-brain resources.

### Requires Explicit Approval

- Sending email or messages.
- Deleting, moving, or overwriting important files.
- External tool/plugin installs.
- Account, billing, purchase, or subscription actions.
- Deep indexing of private folders outside approved scope.
- Destructive git/filesystem/database operations.
- Any action with serious system risk.

### Blocked By Default

- Automatic system wipe.
- Automatic deletion of important files.
- Automatic outbound communication.
- Automatic money/account changes.
- Hidden state that bypasses plain-file inspection.
- Safety boundary changes caused by adaptive identity or anticipation.

## Duplication Guard

To prevent code duplication, configuration drift, and system fragmentation, `SuneelWorkSpace` enforces a strict canonical logic and directory layout policy.

### Core Policies
- **Subsystem Logic Placement**: All subsystem logic, scripts, and utilities must live in their designated subsystem directories (e.g., `heart/goals/scripts/`, `nervous/nervous/mcp/server/scripts/`, `heart/orchestrator/scripts/`).
- **bin/ Entrypoints Only**: The root `bin/` directory must only serve as the CLI command entrypoint layer. It must **never** contain duplicate copies of subsystem scripts. Instead, all entrypoint commands in `bin/` must be created as relative symbolic links pointing to their subsystem originals.
- **Config Folder Standardization**: Configuration files (e.g. JSON/YAML policies) must reside inside designated config subfolders (e.g., `subsystem/config/`, `heart/heart/orchestrator/router/`) rather than the subsystem root.

### Command Reference
Run `duplication-guard` to pre-check any proposed file creation or modification:
- `duplication-guard <file_path> [--intent "description of purpose"]`: Validates that a file's proposed path conforms to canonical location rules and scans `spine/audit/file_graph.json` to reject files with duplicate stems or overlapping functional intents.
- Use `--force` flag to bypass warnings if intentionally creating a fork (explicit confirmation required).

## Canonical Integrity

To keep the codebase maintainable and free of redundant logic, `SuneelWorkSpace` enforces an internal code integrity standard for modifying existing files.

### Integrity Policies
- **Duplication vs. Integrity**: While the **Duplication Guard** prevents the creation of duplicate files, the **Canonical Integrity Guard** prevents the introduction of copy-paste function clones, repeated logic blocks, or parallel implementations inside existing core files.
- **Merge Audits**: All code modifications and merges must enhance code reuse and structure, not degrade it with repeated blocks of code.
- **Canonical Code Cleanliness**: Canonical scripts and programs must maintain clean definitions. Duplicate function declarations inside the same script are strictly blocked.

### Command Reference
Run `integrity-guard` before staging or merging edits into any existing file:
- `integrity-guard <target_file> [--proposed <proposed_content_file>]`: Parses the current code AST and structure (AST-based validation for Python, regex-based validation for Shell/JS) to detect internal duplicates. If duplicate function names or duplicate body logic are detected, it blocks with a Warning.
- Use `--override-integrity` flag to bypass warnings if a duplicate or fork is explicitly required.

## 8. How To Extend The System

### Add A New Tool

1. Add or install only after explicit approval if external.
2. Create a small wrapper in `bin/`.
3. Document it in `README.md`.
4. Add MCP resource entries if it creates durable files.
5. Add safety notes if it touches private data, network, accounts, or files.
6. Run `agent-doctor` and `mcp-reindex`.

### Add A New Subsystem

1. Create a top-level folder under `~/SuneelWorkSpace`.
2. Add a `README.md`.
3. Store state in plain JSON/Markdown.
4. Add command wrappers in `bin/`.
5. Register resources in `nervous/nervous/mcp/server/config/resource_map.json`.
6. Add memory/decision entries if durable.
7. Add health/status integration if relevant.
8. Update this README.

### Upgrade Safely

1. Inspect first.
2. Prefer upgrading over recreating.
3. Keep changes scoped.
4. Back up important files before risky edits.
5. Validate JSON/scripts.
6. Run `agent-doctor`.
7. Run `mcp-reindex` after new shared resources.
8. Close out with `agent-finish`.

## 9. Current Limitations And Gaps

Honest current gaps:

- Anticipation is early. It has built-in patterns and sequence learning, but needs real usage history to become strong.
- Adaptive identity is bounded and safe, but needs actual accept/edit/reject feedback to learn meaningful refinements.
- Comms workflows are intentionally safety-limited. Sending still requires explicit approval.
- Some command descriptions depend on local scripts and may need deeper per-command docs over time.
- README can explain the system, but it does not replace reading canonical safety files before risky changes.
- Tool inventory recommends additions but does not install external tools automatically.
- Autolab recommends identity and anticipation tweaks, but does not apply major behavior changes automatically.
- MCP resource coverage must be updated whenever new durable files are added.
- Private files outside the workspace are not deeply indexed by default.

## SEMI-AUTONOMOUS EXECUTION

The system includes a semi-autonomous execution layer that transitions the operating workflow from simple recommendations into level-appropriate action execution.

### Execution Levels
- **SAFE**: Read-only operations, metadata queries, and workspace health analysis (e.g. `git status`, `agent-doctor`, `agent-status`). These run automatically once selected.
- **CONTROLLED**: Local file creation, drafting, and planning operations (e.g. `goal-plan`, `git commit`). These prompt the user for quick verification (`Run this now? (y/n)`).
- **RESTRICTED**: Actions with outbound effects, file deletions, or environment changes (e.g. `imsg-send-confirmed`, `npm install`). These trigger warnings, require explicit approval (`Are you sure?`), and demand a justification reason.

### Execution Command
Run `next` from the shell to fetch intent-aware ranked suggestions, view their safety categories, and quickly execute the desired next step:
```sh
next
```

## WORKSPACE STRUCTURE

The workspace is organized to keep code modular, state inspectable, and configurations protected:

- `bin/` — User-facing CLI executables and tool wrappers.
- `spine/docs/` — System architecture maps, workspace map, and integration guides.
- `brain/memory/` — Shared memory (`memory/`), tasks (`tasks/`), policies (`shared/`), live states (`state/`), and compressed logs (`logs/archive/`).
- `brain/anticipation/` — Anticipatory intelligence: prediction engine, execution engine, and execution history.
- `spine/audit/` — Security, cleanup plans, and workspace capability analyses.
- `lab/autolab/` — Bounded self-improvement sandboxes.
- `mouth/comms/` — macOS system communication scripts.
- `heart/goals/` — Bounded goal graph planners.
- `dna/identity/` — User behavioral profile, voice prompts, and drift guards.
- `nervous/mcp/` — Workspace-brain MCP configurations.
- `projects/` — Active projects development area.
- `brain/research/` — Local idea capture and decision recording.

## SESSION CONTINUITY

To enable seamless context transitions across workspace sessions, the continuity manager saves and restores state across tool invocations.

- **Automated Work Resumption**: The system tracks the current intent, goals, and workflows inside `spine/state/ACTIVE_CONTEXT.json`. When launching a new agent session via `agent-start`, the system will automatically query the active context and prompt the user to resume their work from where they left off.
- **Workflow-Aware Execution**: Running the `next` command queries this context to prioritize and display recommendations targeted directly at the active goal or workflow.
- **User Control Overrides**: Continuity is a helper, not a boundary. The user can switch workflows at any point or fully clear session history using `context-reset`.

### Context Switch Commands
- To switch active workflows:
  ```sh
  context-reset --workflow MESSAGE_OR_DEVELOPMENT
  ```
- To execute a soft reset (preserves goals, resets intents):
  ```sh
  context-reset --soft
  ```
- To perform a complete context reset:
  ```sh
  context-reset
  ```

### SAFETY RULES FOR CONTEXT
- **Guidance, Not Authority**: Context is treated purely as user-habits metadata and does not override configuration policies, workflow rules, or user intents.
- **Safety Gating Unaffected**: Context state changes never bypass or elevate the execution level constraints (SAFE, CONTROLLED, RESTRICTED).
- **No Autonomous Execution**: Active context never triggers automatic code execution or outbound communications without user input or safety confirmation.

## OBSIDIAN BRAIN

The system uses Obsidian as the primary knowledge, memory, and learning vault at `~/SuneelWorkSpace/brain/`. All durable insights, workflow captures, decisions, and system improvement logs are stored directly in Markdown files, connected using double-bracket [[backlinks]].

The brain folder structure is organized as:
- `brain/inbox/` — Drafts and quick captures.
- `brain/ideas/` — Proactive brainstorms and project options.
- `brain/decisions/` — Durable architecture locks and choices.
- `brain/workflows/` — Reusable execution traces and procedural patterns.
- `brain/system/` — System intelligence files, improvements, and discoveries.
- `brain/learning/` — Core learnings, training loops, and evaluations.
- `brain/experiments/` — Bounded sandbox tests.
- `brain/logs/` — Daily activity and run histories.

The Obsidian vault is exposed to AI agents via the MCP bridge as resources (e.g. `workspace://brain/ideas`) and specialized tools:
- `brain_read_note`: Read note content.
- `brain_write_note`: Create/append markdown notes.
- `brain_search`: Query notes case-insensitively.
- `brain_link_notes`: Link concepts with backlink syntax.
- `execute_workflow`: Execute a compiled workflow script by slug.

### KNOWLEDGE-TO-EXECUTION BRIDGE

Any markdown note captured in Obsidian that contains step-by-step instructions or command sequences is scanned and parsed automatically. The bridge extracts these sequences, validates them to filter out placeholder arguments, slash commands, or broken loop blocks, and compiles them into:
1. Runnable Python wrapper scripts at `scripts/workflows/workflow_<name>.py`.
2. Safe CLI symlinks at `bin/workflow-<name>` (which only contain relative symlinks).
3. Metadata configuration JSON files at `brain/workflows/generated/<name>.json`.

These workflows are ranked high in command suggestions, registered as MCP spine/tools/resources, and synchronized during the Daily Evolution loop. Stale or empty workflows (with 0 valid commands) are automatically cleaned up.

## DAILY EVOLUTION

The workspace is configured to self-improve daily at 2:00 AM using an automated evolution loop. Traces are stored in `brain/system/daily_improvements.md`.

The daily evolution loop:
1. Performs `system-audit`, `system-gaps`, and `system-recommend` to map structural needs.
2. Analyzes activity logs to detect inefficiencies, test failures, and repetitive patterns.
3. Automatically runs safe (SAFE level) optimization actions such as database re-indexing, log rotation, and router training.
4. Searches for new local CLI tools and MCP connectors, planning integrations in `brain/system/tool_discovery.md` (no automatic installs).

## LIFE AUTOMATION

The workspace includes a natural language interpretation layer that maps user requests to specific automation workflows.

When a user provides triggers such as:
- *"organize my life"* -> Runs doctor audits, checks directory structures, and suggests file cleanup.
- *"stay on top of tasks"* -> Runs status evaluations on active goals and lists current priorities.
- *"handle messages"* -> Traces email and message subsystem statuses.

Workflows execute safe status actions and write reusable plans to `brain/workflows/` for continuous optimization.

## APPROVED SYSTEM MCP CONNECTORS

The workspace integrates native Model Context Protocol (MCP) server connectors to interact safely with macOS applications, external research directories, and development tools:
- **GitHub Connector (`bin/github-mcp`)**: Connects to the GitHub API via the local `gh` utility to query PR lists, issues, and repositories. Outbound mutations require explicit user confirmation. Mapped as `workspace://github/status`.
- **Filesystem Connector (`bin/filesystem-mcp`)**: Exposes safe, boundary-checked read-only file reading and listing tools. Access attempts outside SuneelWorkSpace are blocked. Mapped as `workspace://filesystem/status`.
- **macOS Shortcuts Connector (`bin/macos-shortcuts-mcp`)**: Queries the native macOS Shortcuts list and executes authorized system automation scripts. Running individual Shortcuts requires explicit user confirmation. Mapped as `workspace://shortcuts/status`.
- **Brave Search Connector (`bin/brave-search-mcp`)**: Searches the web for fresh development research and packages the top titles, URLs, and snippets. Mapped as `workspace://search/status`.

## 10. For AI Agents


This section is the compressed drop-in intelligence context.

### Session Boot (Mandatory)

Every agent must begin by saying:

```text
✅ Loading workspace shared brain
```

Then load:

- `skeleton/rules/AGENT_SYSTEM.md`
- `skeleton/rules/IDENTITY.md`
- `skeleton/rules/SAFETY_BOUNDARIES.md`

Load identity:

- `dna/dna/dna/identity/profile/identity_profile.md`
- `dna/dna/dna/identity/profile/tone_profile.md`
- `dna/dna/dna/identity/profile/decision_profile.md`
- `dna/dna/dna/identity/profile/preferences.json`
- `dna/dna/dna/identity/profile/behavioral_patterns.json`
- `dna/dna/dna/identity/prompts/identity_prompt.md`
- `dna/dna/dna/identity/prompts/communication_prompt.md`

Load adaptive identity:

- `dna/dna/dna/identity/adaptive/feedback_log.json`
- `dna/dna/dna/identity/adaptive/signal_weights.json`
- `dna/dna/dna/identity/adaptive/signal_memory.json`
- `dna/dna/dna/identity/adaptive/pattern_updates.json`
- `dna/dna/dna/identity/adaptive/drift_guardrails.json`
- `dna/dna/dna/identity/adaptive/adaptation_state.json`

Load capability context:

- `brain/brain/anticipation/current_context.json`
- `brain/brain/anticipation/prediction_memory.json`
- `brain/brain/anticipation/behavior_patterns.json`
- `brain/brain/anticipation/action_suggestions.md`
- `brain/research/README.md`
- `mouth/mouth/mouth/comms/config/comms_config.json`
- `heart/heart/heart/orchestrator/router/system_intelligence_policy.md`
- `heart/goals/planner/planner.md`
- `nervous/nervous/nervous/mcp/server/config/resource_map.json`

Load session state:

- `brain/memory/SESSION_HANDOFF.md`
- `spine/state/CURRENT_STATE.json`
- `spine/state/WORKSPACE_HEALTH.json`

Then confirm:

```text
✅ Context, identity, memory, and capabilities loaded
```

Rules:

- No agent may operate without this boot step.
- All outputs must assume the shared brain is loaded.
- If context is missing or stale, reinitialize context before acting.
- If safety files are missing, stop and repair context before meaningful work.

You are operating in `~/SuneelWorkSpace`, Suneel's local-first personal AI operating system workspace.

Startup:

1. Say: `✅ Loading workspace shared brain`.
2. Run or rely on `bin/agent-start`.
3. Read canonical shared files under `skeleton/rules/`.
4. Load identity:
   - `dna/dna/identity/prompts/identity_prompt.md`
   - `dna/dna/identity/prompts/communication_prompt.md`
   - `dna/dna/identity/profile/identity_profile.md`
   - `dna/dna/identity/profile/tone_profile.md`
   - `dna/dna/identity/profile/decision_profile.md`
5. Check recent handoff: `brain/memory/SESSION_HANDOFF.md`.
6. Confirm: `✅ Context, identity, memory, and capabilities loaded`.

Voice:

- Short.
- Direct.
- Casual.
- Conversational.
- Smart.
- Structured enough to be clear.
- Softened.
- Never harsh.
- Never condescending.

Decision behavior:

- Autopilot for safe local work.
- Ask only for serious system risk or safety-gated actions.
- Use analysis first, intuition second.
- Split uncertainty into smaller problems.
- Prefer tools by simplicity, cost, power, speed, reliability.

Safety:

- Never wipe the system.
- Never delete important files automatically.
- Never send emails/messages without explicit approval.
- Never install external tools without explicit approval.
- Never make money/account changes.
- Never deep-index private folders unless explicitly requested.
- Use backups before risky changes.

Identity learning:

- Record feedback through `dna/dna/identity/adaptive/adaptive_identity.py` or commands:
  - `identity-accept`
  - `identity-reject`
  - `identity-adjust`
- Weighted identity signals live in `dna/dna/identity/adaptive/signal_weights.json`.
- Pattern updates live in `dna/dna/identity/adaptive/pattern_updates.json`.
- Drift guardrails live in `dna/dna/identity/adaptive/drift_guardrails.json`.
- Never let adaptive identity override explicit base identity.

Anticipation:

- Prediction engine: `brain/anticipation/prediction_engine.py`.
- Current intent: `brain/anticipation/current_context.json`.
- Memory: `brain/anticipation/prediction_memory.json`.
- Suggestions: `brain/anticipation/action_suggestions.md`.
- You may suggest next actions.
- You may pre-plan.
- You may not auto-execute suggestions without approval if safety-gated.
- Suggestions must be ranked, intent-aware, and limited to top 3-5.

Research:

- Use `idea-run` for idea to analysis.
- Store decisions in `brain/research/decisions/` and shared memory when durable.

Goals:

- Use `goal-create`, `goal-plan`, `goal-execute`, `goal-monitor`, `goal-complete`.
- Route with `route-task` and `route-execute` when agent selection matters.

MCP:

- Resource map: `nervous/nervous/mcp/server/config/resource_map.json`.
- Reindex after adding important resources: `mcp-reindex`.

Closeout:

1. Update memory/decisions/tasks if durable knowledge was created.
2. Run validation relevant to the task.
3. Run `agent-doctor`.
4. Run `agent-finish "summary"`.

Core principle:

Do not rebuild. Upgrade what exists. Keep it local, inspectable, reversible, identity-aligned, and safe.
