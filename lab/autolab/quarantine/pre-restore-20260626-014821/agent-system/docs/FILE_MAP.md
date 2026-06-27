# File Map

## Root

- `AGENTS.md`: Codex-style workspace entrypoint. Should point to `skeleton/rules/AGENT_SYSTEM.md`.
- `CLAUDE.md`: Claude-style workspace entrypoint. Should point to `skeleton/rules/AGENT_SYSTEM.md`.
- `README.md`: Human-friendly overview of the workspace.
- `.gitignore`: Basic local ignore rules.
- `bin/`: Helper scripts.
- `automation/`: Doctor, repair, launchd, hooks, and generated reports.
- `lab/autolab/`: Safe workspace autoresearch subsystem for iterative self-improvement.
- `projects/`: Place for individual projects.

## Shared Instructions

- `skeleton/rules/AGENT_SYSTEM.md`: Canonical shared instruction source.
- `skeleton/rules/IDENTITY.md`: User identity, preferences, and stable context.
- `skeleton/rules/WORKFLOW_RULES.md`: How agents should inspect, execute, verify, and close out work.
- `skeleton/rules/STARTUP_CHECKLIST.md`: Files to read at session start.
- `skeleton/rules/SESSION_CLOSEOUT_CHECKLIST.md`: Files to update before ending a session.
- `skeleton/rules/SAFETY_BOUNDARIES.md`: Non-negotiable safety limits.

## Memory

- `brain/memory/MEMORY.md`: Durable facts and stable context.
- `brain/memory/DECISIONS.md`: Important decisions and reasons.
- `brain/memory/SESSION_HANDOFF.md`: Latest handoff from the prior agent/session.
- `brain/memory/NOTES.md`: Temporary or low-stakes notes.

## Tasks

- `heart/tasks/ACTIVE_TASKS.md`: Current tasks and next steps.
- `heart/tasks/COMPLETED_TASKS.md`: Finished work.
- `heart/tasks/TASK_QUEUE.md`: Queued future work.

## Logs And State

- `blood/logs/SESSION_LOG.md`: Append-only work log.
- `blood/logs/MAINTENANCE_LOG.md`: Append-only maintenance log.
- `blood/logs/CHANGE_LOG.md`: Human-readable change history.
- `spine/state/CURRENT_STATE.json`: Machine-readable current state.
- `spine/state/WORKSPACE_HEALTH.json`: Latest doctor result.
- `spine/state/INDEX.json`: Generated index of shared files and scripts.
- `spine/state/ACTIVE_SESSION.json`: Current shell/wrapper session marker used by automatic closeout.
- `spine/state/LAST_KNOWN_GOOD.json`: Latest validation snapshot after a healthy maintenance pass.

## Templates

- `brain/memory/templates/SESSION_SUMMARY_TEMPLATE.md`: Handoff summary template.
- `brain/memory/templates/TASK_TEMPLATE.md`: Task entry template.
- `brain/memory/templates/DECISION_TEMPLATE.md`: Decision entry template.
- `brain/memory/templates/STATUS_REPORT_TEMPLATE.md`: Status report template.

## Docs

- `brain/memory/spine/docs/HOW_IT_WORKS.md`: Detailed system explanation.
- `brain/memory/spine/docs/FILE_MAP.md`: This file.
- `brain/memory/spine/docs/RECOVERY.md`: How to restore backups and repair symlinks.
- `brain/memory/spine/docs/AUTOMATION.md`: How maintenance automation works.
- `brain/memory/spine/docs/OPERATOR_GUIDE.md`: Short usage guide for Suneel.

## Scripts

- `bin/agent-start`: Runs startup preflight and prints context.
- `bin/agent-status`: Shows current state, health, handoff, and tasks.
- `bin/agent-finish`: Updates handoff, session log, state, index, and report.
- `bin/agent-autoclose`: Automatic idempotent closeout for wrapper exit, shell exit, inactivity, and startup recovery.
- `bin/agent-doctor`: Runs full health checks.
- `bin/agent-repair`: Safely repairs known issues.
- `bin/agent-maintain`: Runs recurring maintenance.
- `bin/use-codex`: Runs startup preflight, then launches Codex from the workspace.
- `bin/use-claude`: Runs startup preflight, then launches Claude from the workspace.
- `bin/workspace-context`: Prints the required startup files and compact context.
- `bin/workspace-backup`: Creates a timestamped core backup.
- `bin/workspace-index`: Regenerates `INDEX.json`.
- `bin/workspace-report`: Regenerates the latest markdown status report.
- `bin/workspace-changes`: Shows recent git or filesystem changes.

## Autolab

- `lab/autolab/program.md`: Research organization instructions for improving the workspace.
- `lab/autolab/evaluator.md`: Score and acceptance rules.
- `lab/autolab/mutation_policy.md`: Allowlist and denylist for autonomous changes.
- `lab/autolab/safeguards.md`: Safety and rollback rules.
- `lab/autolab/results.tsv`: Append-only experiment history.
- `lab/autolab/current_frontier.md`: Current best-known improvement state.
- `lab/autolab/state/latest_eval.json`: Latest score breakdown.
- `lab/autolab/meta/insights.md`: Human-readable learning summary.
- `lab/autolab/meta/patterns.json`: Successful mutation and target-area patterns.
- `lab/autolab/meta/failure_patterns.json`: Repeated failure patterns and avoidance guidance.
- `lab/autolab/meta/strategy_versions/`: Snapshots of `program.md` before strategy evolution.
- `lab/autolab/scripts/`: Autolab command suite.
