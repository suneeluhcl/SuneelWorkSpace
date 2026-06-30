---
organ: "spine"
workspace_health: ?
last_sync: "2026-06-30 05:12 UTC"
issues: 0
tags:
  - organ/spine
  - workspace/suneelworkspace
---
# spine

> Synced from SuneelWorkSpace — 2026-06-30 05:12 UTC

## Capabilities
**Provides**: workspace_health, current_state, health_history, diagnostic_scheduler, enhancement_logger, readme_health, snapshots
**Needs**: nerve_propagator, agent_doctor, blood_logs
**CLI**: `agent-doctor, workspace-snapshot, diagnostics-start, diagnostics-stop`

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
