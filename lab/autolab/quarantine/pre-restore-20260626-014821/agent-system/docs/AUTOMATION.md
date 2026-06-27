# Automation

## Purpose

Automation keeps `~/SuneelWorkSpace` healthy without requiring Suneel to remember manual startup steps.

## Commands

- `agent-start`: Runs preflight repair, refreshes the index, records startup, and prints context.
- `agent-autoclose`: Automatically checkpoints handoff, logs, state, and health context on wrapper exit, shell exit, or startup recovery.
- `agent-status`: Shows current state, health, latest handoff, and active tasks.
- `agent-doctor`: Runs a full health check and writes `WORKSPACE_HEALTH.json`.
- `agent-repair`: Safely fixes known small issues.
- `agent-maintain`: Runs doctor, repair where safe, index refresh, status report, and lightweight backup.
- `workspace-context`: Prints the files an agent must read first.
- `workspace-index`: Regenerates `INDEX.json`.
- `workspace-report`: Regenerates `automation/reports/status-latest.md`.
- `workspace-backup`: Creates timestamped core backups.
- `workspace-changes`: Shows recent git or filesystem changes.

## Autolab

Autolab lives at `~/SuneelWorkSpace/lab/autolab/`.

It adds a safe workspace-autoresearch loop:

1. Evaluate current workspace fitness.
2. Snapshot the allowed mutable surface.
3. Try one bounded improvement.
4. Evaluate again.
5. Keep only if safety gates pass and score improves.
6. Otherwise restore the snapshot and log the rollback.

Periodic autolab automation runs evaluation only by default. Mutating experiments are conservative and bounded.

Autolab v2 also runs pattern analysis. Maintenance may run a single bounded experiment only when the score is below perfect and the last experiment is old enough, so it does not create noisy loops.

## Background Maintenance

When configured, macOS launchd runs:

`~/SuneelWorkSpace/bin/agent-maintain`

The job label is:

`com.suneelworkspace.maintenance`

The workspace copy of the plist is:

`~/SuneelWorkSpace/automation/launchd/com.suneelworkspace.maintenance.plist`

The user LaunchAgents entry is:

`~/Library/LaunchAgents/com.suneelworkspace.maintenance.plist`

## Safety

Maintenance is intentionally conservative. It may recreate known symlinks, directories, executable permissions, generated indexes, and generated JSON state files.

It must not delete human-authored content or merge separate workspaces blindly.

## Automatic Session Closeout

There are three closeout paths:

- Wrapper closeout: `use-codex` and `use-claude` launch the tool, wait for it to exit, then run `agent-autoclose`.
- Shell closeout: the zsh hook runs `agent-autoclose --shell-exit` when a shell exits from inside `~/SuneelWorkSpace`.
- Startup recovery: `agent-start` detects an open prior session and runs `agent-autoclose --startup-recovery`.

`agent-autoclose` is idempotent. If there is no active session and no new checkpoint material, it skips log spam.

## Logs And Reports

- Maintenance log: `blood/logs/MAINTENANCE_LOG.md`
- Health JSON: `spine/state/WORKSPACE_HEALTH.json`
- Index JSON: `spine/state/INDEX.json`
- Latest report: `automation/reports/status-latest.md`
