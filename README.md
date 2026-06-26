# SuneelWorkSpace System Blueprint

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
  - Codex: AGENTS.md, ~/.codex/AGENTS.md
  - Gemini/OpenCode launchers in bin/
  |
  v
Shared Workspace Brain
  agent-system/
    shared rules, identity, safety, memory, decisions, tasks, state, logs
  |
  +--> identity/
  |     base profile, tone profile, decision profile, prompts
  |     adaptive loop: feedback -> weighted signals -> bounded updates
  |
  +--> anticipation/
  |     command/workflow events -> sequence patterns -> suggested next actions
  |
  +--> research-engine/
  |     idea capture -> research plan -> analysis -> decision
  |
  +--> orchestrator/
  |     task routing, agent selection, routing history, gstack hints
  |
  +--> goal-engine/
  |     goal creation, planning, execution, monitoring, dependency graph
  |
  +--> comms/
  |     mail and iMessage search/draft/status support with send approval gates
  |
  +--> mcp/
  |     workspace-brain resources, indexes, shared context access
  |
  +--> autolab/
        bounded self-improvement experiments, evaluator, reports, rollback state
```

## 2. Core Subsystems

### Agent System

Path: `agent-system/`

This is the shared source for workspace rules, identity context, memory, tasks, logs, and state.

Important files:

- `agent-system/shared/AGENT_SYSTEM.md`: canonical shared system policy.
- `agent-system/shared/IDENTITY.md`: shared user/workspace identity context.
- `agent-system/shared/SAFETY_BOUNDARIES.md`: safety rules.
- `agent-system/shared/BOUNDED_SELF_UPGRADE.md`: allowed and approval-gated self-upgrades.
- `agent-system/memory/MEMORY.md`: stable facts.
- `agent-system/memory/DECISIONS.md`: important choices and reasons.
- `agent-system/memory/PATTERNS.md`: recurring operating patterns.
- `agent-system/memory/INSIGHTS.md`: higher-level learning.
- `agent-system/tasks/ACTIVE_TASKS.md`: current tasks.
- `agent-system/tasks/COMPLETED_TASKS.md`: completed task history.
- `agent-system/memory/SESSION_HANDOFF.md`: latest handoff.
- `agent-system/state/CURRENT_STATE.json`: current state.
- `agent-system/state/WORKSPACE_HEALTH.json`: health and readiness.

### Identity System

Path: `identity/`

The identity system defines how agents should sound, decide, plan, and communicate for Suneel.

Base files:

- `identity/profile/identity_profile.md`: core identity profile.
- `identity/profile/tone_profile.md`: writing and tone rules.
- `identity/profile/decision_profile.md`: decision rules.
- `identity/profile/preferences.json`: structured preferences.
- `identity/profile/behavioral_patterns.json`: behavior patterns.
- `identity/prompts/identity_prompt.md`: agent identity prompt.
- `identity/prompts/communication_prompt.md`: email/message/summarization voice prompt.
- `identity/integration/routing_identity.json`: routing and autonomy rules.
- `identity/reports/identity_summary.md`: human-readable summary.

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

Path: `identity/adaptive/`

The adaptive identity loop improves Suneel's voice and decision behavior from real interaction outcomes.

Files:

- `identity/adaptive/feedback_log.json`: raw feedback events.
- `identity/adaptive/signal_weights.json`: quality weights for signal types.
- `identity/adaptive/signal_memory.json`: extracted weighted signals.
- `identity/adaptive/pattern_updates.json`: proposed and active adjustments.
- `identity/adaptive/drift_guardrails.json`: strict drift limits.
- `identity/adaptive/adaptation_state.json`: current loop state.
- `identity/adaptive/reports/adaptation_report.md`: report.
- `identity/adaptive/adaptive_identity.py`: learning engine.

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

Path: `anticipation/`

The anticipation engine records command and workflow sequences, detects repeated patterns, and suggests next actions before Suneel asks.

Files:

- `anticipation/prediction_engine.py`: prediction engine.
- `anticipation/prediction_memory.json`: command/workflow event memory.
- `anticipation/behavior_patterns.json`: built-in and learned behavior patterns.
- `anticipation/action_suggestions.md`: latest suggestions.
- `anticipation/reports/anticipation_report.md`: report.

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

Path: `research-engine/`

Turns rough ideas into durable local research artifacts.

Files:

- `research-engine/research_engine.py`: engine.
- `research-engine/ideas/`: captured ideas.
- `research-engine/plans/`: research plans.
- `research-engine/analyses/`: comparisons and analysis.
- `research-engine/decisions/`: decision records.

Main commands:

- `idea-start`: capture an idea.
- `idea-run`: capture, plan, analyze, and draft a decision.

### Comms Subsystem

Path: `comms/`

Supports email and iMessage workflows while preserving safety boundaries.

Important files:

- `comms/config/comms_config.json`: comms config, identity, adaptive identity, anticipation pointers.
- `comms/mail/`: mail state/logs/scripts.
- `comms/imessage/`: iMessage state/logs/scripts.
- `comms/reports/latest_comms_report.md`: report.

Rules:

- Drafting is allowed.
- Searching/status is allowed.
- Sending requires explicit approval.
- Deleting/archive/forward/contact actions require approval.
- Drafts should use `identity/prompts/communication_prompt.md`.

### MCP Workspace Brain

Path: `mcp/`

The MCP subsystem exposes workspace resources to connected agents.

Important files:

- `mcp/server/main.py`: MCP server.
- `mcp/server/config/resource_map.json`: resource registry.
- `mcp/server/storage/memory_index.db`: local index.
- `mcp/server/state/last_index.json`: latest index metadata.

Important resources include:

- `workspace://identity/profile`
- `workspace://identity/adaptive/feedback-log`
- `workspace://identity/adaptive/signal-weights`
- `workspace://anticipation/memory`
- `workspace://anticipation/suggestions`
- `workspace://audit/system`
- `workspace://readme/blueprint`
- `workspace://tools/inventory`
- `workspace://research/index`
- `workspace://memory/patterns`

### Orchestrator

Path: `orchestrator/`

Routes tasks to the right agent/tool mode.

Important files:

- `orchestrator/router/task_types.json`
- `orchestrator/router/agent_profiles.json`
- `orchestrator/router/gstack_policy.json`
- `orchestrator/router/system_intelligence_policy.md`
- `orchestrator/state/current_routing_state.json`
- `orchestrator/reports/routing_report.md`

It uses:

- Task type.
- Agent profiles.
- GStack hints.
- Identity routing rules.
- Anticipatory suggestions.

### Goal Engine

Path: `goal-engine/`

Turns goals into tasks, plans, dependency graphs, execution runs, and reports.

Important files:

- `goal-engine/goals/active_goals.md`
- `goal-engine/planner/planner.md`
- `goal-engine/planner/idea_execution_pipeline.md`
- `goal-engine/graph/task_graph.json`
- `goal-engine/state/goal_state.json`
- `goal-engine/execution/execution_log.md`

Goal execution records adaptive identity and anticipation events.

### Autolab

Path: `autolab/`

Autolab is the bounded workspace self-improvement lab.

Important files:

- `autolab/program.md`
- `autolab/mutation_policy.md`
- `autolab/safeguards.md`
- `autolab/evaluator.md`
- `autolab/current_frontier.md`
- `autolab/meta/adaptive_identity_strategy.md`
- `autolab/meta/anticipation_strategy.md`
- `autolab/reports/latest_report.md`

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

- `anticipation/current_context.json`

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

Ranking is implemented in `anticipation/prediction_engine.py`.

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
| `system-audit` | Refreshes `audit/system_audit.md`. | Need full system overview. |
| `system-gaps` | Refreshes `audit/gap_analysis.md`. | Need current gaps and priorities. |
| `system-capabilities` | Refreshes `system-context/system_profile.json`. | Need safe machine/workspace capability summary. |
| `system-recommend` | Refreshes `tools/recommendations.md`. | Need improvement ideas. |
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

Lower-level scripts also exist in `research-engine/scripts/`: `idea-bootstrap`, `idea-capture`, `idea-research`, `idea-analyze`, `idea-decide`.

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
- Use `identity/prompts/communication_prompt.md`.
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
| Canonical rules | `agent-system/shared/` | System policy, identity, workflow, safety. |
| Durable memory | `agent-system/memory/` | Facts, decisions, patterns, insights, handoff. |
| Tasks | `agent-system/tasks/` | Active, queued, and completed tasks. |
| State | `agent-system/state/` | Current state and health JSON. |
| Logs | `agent-system/logs/` | Session logs. |
| Identity | `identity/` | Profile, tone, decision, prompts. |
| Adaptive identity | `identity/adaptive/` | Feedback, weighted signals, bounded adjustments. |
| Anticipation | `anticipation/` | Prediction memory, behavior patterns, suggestions. |
| Research | `research-engine/` | Ideas, plans, analyses, decisions. |
| Orchestrator | `orchestrator/` | Routing policies, state, reports. |
| Goals | `goal-engine/` | Goals, plans, graphs, execution logs. |
| Comms | `comms/` | Mail/iMessage config, state, logs, reports. |
| MCP | `mcp/` | Server, resource map, index DB, state. |
| Autolab | `autolab/` | Self-improvement experiments, evaluator, reports. |
| Audit | `audit/` | System audit, gap analysis, improvement plan. |
| Tools | `tools/` | Tool inventory and recommendations. |

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
| `agent-system/` | Shared brain, rules, memory, logs, state. |
| `anticipation/` | Intent detection, prediction memory, ranked next-action suggestions. |
| `audit/` | System audit, gap analysis, improvement plan. |
| `autolab/` | Bounded self-improvement lab. |
| `automation/` | Local automation helpers and maintenance support. |
| `bin/` | User-facing command wrappers. |
| `codex/` | Codex-specific workspace files. |
| `comms/` | Mail and iMessage workflows. |
| `docs/` | Documentation and specs. |
| `goal-engine/` | Goals, planning, execution, monitoring. |
| `identity/` | Identity, adaptive identity, tone, decision profiles. |
| `mcp/` | Workspace-brain MCP server and resource index. |
| `obsidian-vault/` | Obsidian-facing knowledge vault. |
| `orchestrator/` | Routing and agent selection. |
| `projects/` | Project work area. |
| `research-engine/` | Idea capture, research, analysis, decisions. |
| `scripts/` | Shared local scripts behind commands. |
| `snapshots/` | Snapshot state for recovery/experiments. |
| `system-context/` | Safe metadata-only machine/workspace profile. |
| `tools/` | Tool inventory and recommendations. |
| System context | `system-context/` | Safe machine/workspace profile. |

Inspect commands:

```sh
agent-status
agent-doctor
mcp-status
system-gaps
anticipate report
python3 -m json.tool identity/adaptive/signal_memory.json
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

- Suggestions are not execution.
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
5. Register resources in `mcp/server/config/resource_map.json`.
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
- `docs/` — System architecture maps, workspace map, and integration guides.
- `agent-system/` — Shared memory (`memory/`), tasks (`tasks/`), policies (`shared/`), live states (`state/`), and compressed logs (`logs/archive/`).
- `anticipation/` — Anticipatory intelligence: prediction engine, execution engine, and execution history.
- `audit/` — Security, cleanup plans, and workspace capability analyses.
- `autolab/` — Bounded self-improvement sandboxes.
- `comms/` — macOS system communication scripts.
- `goal-engine/` — Bounded goal graph planners.
- `identity/` — User behavioral profile, voice prompts, and drift guards.
- `mcp/` — Workspace-brain MCP configurations.
- `projects/` — Active projects development area.
- `research-engine/` — Local idea capture and decision recording.

## SESSION CONTINUITY

To enable seamless context transitions across workspace sessions, the continuity manager saves and restores state across tool invocations.

- **Automated Work Resumption**: The system tracks the current intent, goals, and workflows inside `agent-system/state/ACTIVE_CONTEXT.json`. When launching a new agent session via `agent-start`, the system will automatically query the active context and prompt the user to resume their work from where they left off.
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

## 10. For AI Agents


This section is the compressed drop-in intelligence context.

### Session Boot (Mandatory)

Every agent must begin by saying:

```text
✅ Loading workspace shared brain
```

Then load:

- `agent-system/shared/AGENT_SYSTEM.md`
- `agent-system/shared/IDENTITY.md`
- `agent-system/shared/SAFETY_BOUNDARIES.md`

Load identity:

- `identity/profile/identity_profile.md`
- `identity/profile/tone_profile.md`
- `identity/profile/decision_profile.md`
- `identity/profile/preferences.json`
- `identity/profile/behavioral_patterns.json`
- `identity/prompts/identity_prompt.md`
- `identity/prompts/communication_prompt.md`

Load adaptive identity:

- `identity/adaptive/feedback_log.json`
- `identity/adaptive/signal_weights.json`
- `identity/adaptive/signal_memory.json`
- `identity/adaptive/pattern_updates.json`
- `identity/adaptive/drift_guardrails.json`
- `identity/adaptive/adaptation_state.json`

Load capability context:

- `anticipation/current_context.json`
- `anticipation/prediction_memory.json`
- `anticipation/behavior_patterns.json`
- `anticipation/action_suggestions.md`
- `research-engine/README.md`
- `comms/config/comms_config.json`
- `orchestrator/router/system_intelligence_policy.md`
- `goal-engine/planner/planner.md`
- `mcp/server/config/resource_map.json`

Load session state:

- `agent-system/memory/SESSION_HANDOFF.md`
- `agent-system/state/CURRENT_STATE.json`
- `agent-system/state/WORKSPACE_HEALTH.json`

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
3. Read canonical shared files under `agent-system/shared/`.
4. Load identity:
   - `identity/prompts/identity_prompt.md`
   - `identity/prompts/communication_prompt.md`
   - `identity/profile/identity_profile.md`
   - `identity/profile/tone_profile.md`
   - `identity/profile/decision_profile.md`
5. Check recent handoff: `agent-system/memory/SESSION_HANDOFF.md`.
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

- Record feedback through `identity/adaptive/adaptive_identity.py` or commands:
  - `identity-accept`
  - `identity-reject`
  - `identity-adjust`
- Weighted identity signals live in `identity/adaptive/signal_weights.json`.
- Pattern updates live in `identity/adaptive/pattern_updates.json`.
- Drift guardrails live in `identity/adaptive/drift_guardrails.json`.
- Never let adaptive identity override explicit base identity.

Anticipation:

- Prediction engine: `anticipation/prediction_engine.py`.
- Current intent: `anticipation/current_context.json`.
- Memory: `anticipation/prediction_memory.json`.
- Suggestions: `anticipation/action_suggestions.md`.
- You may suggest next actions.
- You may pre-plan.
- You may not auto-execute suggestions without approval if safety-gated.
- Suggestions must be ranked, intent-aware, and limited to top 3-5.

Research:

- Use `idea-run` for idea to analysis.
- Store decisions in `research-engine/decisions/` and shared memory when durable.

Goals:

- Use `goal-create`, `goal-plan`, `goal-execute`, `goal-monitor`, `goal-complete`.
- Route with `route-task` and `route-execute` when agent selection matters.

MCP:

- Resource map: `mcp/server/config/resource_map.json`.
- Reindex after adding important resources: `mcp-reindex`.

Closeout:

1. Update memory/decisions/tasks if durable knowledge was created.
2. Run validation relevant to the task.
3. Run `agent-doctor`.
4. Run `agent-finish "summary"`.

Core principle:

Do not rebuild. Upgrade what exists. Keep it local, inspectable, reversible, identity-aligned, and safe.
