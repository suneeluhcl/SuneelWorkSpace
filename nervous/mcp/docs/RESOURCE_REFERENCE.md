# Resource Reference

Resources are read-only views of authoritative workspace files. They are accessed by URI.

## Workspace Intelligence

| URI | Source file | Description |
|-----|-------------|-------------|
| `workspace://overview` | `skeleton/rules/AGENT_SYSTEM.md` | Canonical workspace instructions |
| `workspace://identity` | `skeleton/rules/IDENTITY.md` | Agent identity and context |
| `workspace://workflow-rules` | `skeleton/rules/WORKFLOW_RULES.md` | Workflow rules |
| `workspace://safety` | `skeleton/rules/SAFETY_BOUNDARIES.md` | Safety boundaries |
| `workspace://startup-checklist` | `skeleton/rules/STARTUP_CHECKLIST.md` | Startup checklist |

## Memory & Decisions

| URI | Source file | Description |
|-----|-------------|-------------|
| `workspace://memory` | `brain/memory/MEMORY.md` | Persistent memory |
| `workspace://decisions` | `brain/memory/DECISIONS.md` | Important decisions |
| `workspace://handoff` | `brain/memory/SESSION_HANDOFF.md` | Latest session handoff |
| `workspace://notes` | `brain/memory/NOTES.md` | Temporary notes |

## Tasks

| URI | Source file | Description |
|-----|-------------|-------------|
| `workspace://tasks/active` | `heart/tasks/ACTIVE_TASKS.md` | Active tasks |
| `workspace://tasks/queue` | `heart/tasks/TASK_QUEUE.md` | Task queue |
| `workspace://tasks/completed` | `heart/tasks/COMPLETED_TASKS.md` | Completed tasks |

## State & Health

| URI | Source file | Description |
|-----|-------------|-------------|
| `workspace://state` | `spine/state/CURRENT_STATE.json` | Current state JSON |
| `workspace://health` | `spine/state/WORKSPACE_HEALTH.json` | Workspace health JSON |

## Autolab

| URI | Source file | Description |
|-----|-------------|-------------|
| `workspace://lab/autolab/frontier` | `lab/autolab/current_frontier.md` | Current frontier score and strategy |
| `workspace://lab/autolab/program` | `lab/autolab/program.md` | Autolab program and mutation policy |
| `workspace://lab/autolab/insights` | `lab/autolab/meta/insights.md` | Learning insights |
| `workspace://lab/autolab/patterns` | `lab/autolab/meta/patterns.json` | Observed patterns |
| `workspace://lab/autolab/failures` | `lab/autolab/meta/failure_patterns.json` | Failure patterns |
| `workspace://lab/autolab/learning` | `lab/autolab/meta/learning_log.md` | Full learning log |

## Derived Views

| URI | Source | Description |
|-----|--------|-------------|
| `workspace://digest` | state + health + handoff + tasks | Compact one-page workspace summary |
| `workspace://logs/recent` | `blood/logs/SESSION_LOG.md` | Last 200 lines of session log |
| `workspace://nervous/mcp/state` | `nervous/mcp/server/state/mcp_state.json` | MCP subsystem state |

## Prompts (reusable context assembles)

| Name | Description |
|------|-------------|
| `startup_context` | State + health + handoff + tasks — use on session start |
| `closeout_context` | Checklist of what to update on session close |
| `workspace_status_brief` | One-page status summary |
| `autolab_summary` | Frontier + insights + failure patterns |
| `maintenance_summary` | State + health + last index metadata |
