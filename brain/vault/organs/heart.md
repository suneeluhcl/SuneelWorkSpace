---
organ: "heart"
workspace_health: ?
last_sync: "2026-06-29 02:39 UTC"
issues: 1
tags:
  - organ/heart
  - workspace/suneelworkspace
---
# heart

> Synced from SuneelWorkSpace — 2026-06-29 02:39 UTC

## Capabilities
**Provides**: model_router, model_registry, health_checker, task_queue, goals, orchestrator
**Needs**: memory, workspace_health, nerve_propagator
**CLI**: `model-status`

## Active Tasks

- [ ] Keep the shared agent workspace handoff files current after each meaningful agent session.
- [ ] Use `agent-doctor` before repairing suspicious workspace issues.
- [ ] Use `agent-finish "summary"` at the end of meaningful Claude or Codex sessions.
- [ ] Add project-specific instructions inside individual project folders only when needed.

## Diagnostic Warnings

- ⚠️ Scripts found outside canonical subsystem directories: conftest.py, readme_sync.py, __init__.py, test_daemon.py, autonomous_repair_loop.py, test_runner.py, __init__.py, test_ollama_engines.py, __init__.py, test_full_pipeline.py, __init__.py, __init__.py, __init__.py, __init__.py, test_nervous.py, __init__.py, __init__.py, __init__.py, test_heart.py, __init__.py, __init__.py, __init__.py, __init__.py, test_blood.py, __init__.py, __init__.py, __init__.py, test_brain.py, __init__.py, __init__.py, __init__.py, test_eyes.py

## Commands

Run `agent-doctor` to refresh health → `- [ ] agent-doctor`
Run nerve heal → `- [ ] nerve-heal`

---
_Edit task checkboxes to sync back to ACTIVE_TASKS.md._
_Add `- [ ] <cli-command>` and check it to trigger that command._
