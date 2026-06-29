---
organ: "hands"
workspace_health: ?
last_sync: "2026-06-29 04:54 UTC"
issues: 0
tags:
  - organ/hands
  - workspace/suneelworkspace
---
# hands

> Synced from SuneelWorkSpace — 2026-06-29 04:54 UTC

## Capabilities
**Provides**: cli_commands, scripts, automation, launchd_plists, ci_runner
**Needs**: nerve_propagator, workspace_health
**CLI**: `agent-start, agent-finish, agent-doctor, workspace-dashboard, deep-scan, morning-brief, diagnostics-start, diagnostics-stop, model-rotate, experiment-skills`

## Active Tasks

- [ ] Keep the shared agent workspace handoff files current after each meaningful agent session.
- [ ] Use `agent-doctor` before repairing suspicious workspace issues.
- [ ] Use `agent-finish "summary"` at the end of meaningful Claude or Codex sessions.
- [ ] Add project-specific instructions inside individual project folders only when needed.

## Diagnostic Warnings

✅ No issues

## Commands

Run `agent-doctor` to refresh health → `- [ ] agent-doctor`
Run nerve heal → `- [ ] nerve-heal`

---
_Edit task checkboxes to sync back to ACTIVE_TASKS.md._
_Add `- [ ] <cli-command>` and check it to trigger that command._
