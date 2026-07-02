# Workspace Map

This document outlines the directory structure and organization of Suneel's workspace.

## Root Directories

- [bin/](file:///Users/MAC/SuneelWorkSpace/bin) — The primary command-line interface entrypoints. Contains scripts like `agent-doctor`, `agent-maintain`, and `next`.
- [spine/docs/](file:///Users/MAC/SuneelWorkSpace/docs) — System architecture, maps, and external integrations (e.g. `gstack` templates).
- [brain/memory/](file:///Users/MAC/SuneelWorkSpace/agent-system) — Central memory, task tracking, and workspace health files.
- [brain/anticipation/](file:///Users/MAC/SuneelWorkSpace/anticipation) — Prediction engine (`prediction_engine.py`) and semi-autonomous execution engine (`execution_engine.py`).
- [lab/autolab/](file:///Users/MAC/SuneelWorkSpace/autolab) — Safe, bounded mutation testing and self-improvement loops.
- [automation/](file:///Users/MAC/SuneelWorkSpace/automation) — Launchd daemons and git hooks for scheduling maintenance.
- [mouth/comms/](file:///Users/MAC/SuneelWorkSpace/comms) — Local communication modules interfacing with macOS iMessage and Mail.
- [heart/goals/](file:///Users/MAC/SuneelWorkSpace/goal-engine) — Graph-based goal parser and execution engine.
- [dna/identity/](file:///Users/MAC/SuneelWorkSpace/identity) — Voice, tone, profile, and decision alignment models matching Suneel's identity.
- [nervous/mcp/](file:///Users/MAC/SuneelWorkSpace/mcp) — Model Context Protocol configurations and tools.
- [brain/vault/](file:///Users/MAC/SuneelWorkSpace/obsidian-vault) — Structured human-readable notes, canvases, and local knowledge graphs.
- [heart/orchestrator/](file:///Users/MAC/SuneelWorkSpace/orchestrator) — Agent selector, task classification, and scoring models.
- [projects/](file:///Users/MAC/SuneelWorkSpace/projects) — Active user software development projects.
- [brain/research/](file:///Users/MAC/SuneelWorkSpace/research-engine) — Structured research gathering, decision recording, and comparative summaries.
- [scripts/](file:///Users/MAC/SuneelWorkSpace/scripts) — Utility system scripts such as the capability auditor.
- [spine/snapshots/](file:///Users/MAC/SuneelWorkSpace/snapshots) — Automated backups of the workspace's state and dependencies.
- [spine/system-context/](file:///Users/MAC/SuneelWorkSpace/system-context) — Environment configuration, profile definitions, and local capabilities inventory.
- [spine/tools/](file:///Users/MAC/SuneelWorkSpace/tools) — Recommendations and inventories of available system tools.
- [spine/audit/](file:///Users/MAC/SuneelWorkSpace/audit) — Workspace health analyses, gap analysis, and cleanup plans.

## System Subdirectories Detailed

### `brain/memory/`
- `memory/` — Fact storage (`MEMORY.md`), choice record (`DECISIONS.md`), and session handoffs.
- `shared/` — Bounded upgrade policies, safety boundaries, and workflow instructions.
- `state/` — Live health telemetry (`WORKSPACE_HEALTH.json`) and session states.
- `tasks/` — Active (`ACTIVE_TASKS.md`), queued, and completed lists.
- `logs/` — Maintenance and change logs, plus the `archive/` folder containing compressed historical logs.
- `templates/` — Blueprints for structured documentation.

### `brain/anticipation/`
- `prediction_engine.py` — Infers user intents from patterns.
- `execution_engine.py` — Executes actions using defined safety tiers (SAFE, CONTROLLED, RESTRICTED).
- `execution_state.json` — Tracks the history of semi-autonomous execution.
- `action_suggestions.md` — Viewable ranked actions matching current context.

### `spine/audit/`
- `file_graph.json` — Comprehensive workspace file inventory, classifications, and sizes.
- `duplication_clusters.json` — Tracked duplicate file groups and their resolution (symlinks vs. archiving).
- `system_audit.md` — Full metadata, gap analyses, and improvement plans.

### `bin/`
- The CLI command layer. Subsystem scripts (e.g. goal commands, MCP controls, orchestrator routers) are defined as relative symlinks to their source directories (`heart/goals/scripts/`, `nervous/mcp/server/scripts/`, `heart/orchestrator/scripts/`) to eliminate file duplication while maintaining CLI invocation compatibility.

