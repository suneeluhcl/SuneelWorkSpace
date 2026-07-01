---
organ: "eyes"
workspace_health: 100
last_sync: "2026-07-01 05:41 UTC"
issues: 2
tags:
  - organ/eyes
  - workspace/suneelworkspace
---
# eyes

> Synced from SuneelWorkSpace — 2026-07-01 05:41 UTC

## Capabilities
**Provides**: dashboard, dashboard_index, visual_monitor, widgets, nerve_monitor, ollama_status, hermes_status
**Needs**: nerve_propagator, workspace_health, heart_goals, brain_memory, ollama
**CLI**: `workspace-dashboard, dashboard-start, dashboard-stop`

## Active Tasks

- [ ] Keep the shared agent workspace handoff files current after each meaningful agent session.
- [ ] Use `agent-doctor` before repairing suspicious workspace issues.
- [ ] Use `agent-finish "summary"` at the end of meaningful Claude or Codex sessions.
- [ ] Add project-specific instructions inside individual project folders only when needed.

## Diagnostic Warnings

- ⚠️ Script 'eyes/dashboard/server.py' contains duplicate definition for function '_run' (line 828).
- ⚠️ Scripts found outside canonical subsystem directories: scenario_runner.py, conftest.py, readme_sync.py, __init__.py, test_daemon.py, autonomous_repair_loop.py, test_runner.py, chaos_monkey.py, __init__.py, test_ollama_engines.py, __init__.py, test_full_pipeline.py, __init__.py, __init__.py, __init__.py, __init__.py, test_nervous.py, __init__.py, __init__.py, __init__.py, test_heart.py, __init__.py, __init__.py, __init__.py, __init__.py, test_blood.py, __init__.py, __init__.py, __init__.py, test_brain.py, __init__.py, __init__.py, __init__.py, test_eyes.py

## Commands

Run `agent-doctor` to refresh health → `- [ ] agent-doctor`
Run nerve heal → `- [ ] nerve-heal`

---
_Edit task checkboxes to sync back to ACTIVE_TASKS.md._
_Add `- [ ] <cli-command>` and check it to trigger that command._
