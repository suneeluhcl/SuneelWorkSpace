---
organ: "blood"
workspace_health: 100
last_sync: "2026-07-01 05:41 UTC"
issues: 1
tags:
  - organ/blood
  - workspace/suneelworkspace
---
# blood

> Synced from SuneelWorkSpace — 2026-07-01 05:41 UTC

## Capabilities
**Provides**: telemetry_db, session_log, execution_history, nerve_events, night_ops, enhancements_log
**Needs**: nerve_propagator
**CLI**: `log-enhancement, telemetry-query`

## Active Tasks

- [ ] Keep the shared agent workspace handoff files current after each meaningful agent session.
- [ ] Use `agent-doctor` before repairing suspicious workspace issues.
- [ ] Use `agent-finish "summary"` at the end of meaningful Claude or Codex sessions.
- [ ] Add project-specific instructions inside individual project folders only when needed.

## Diagnostic Warnings

- ⚠️ Scripts found outside canonical subsystem directories: scenario_runner.py, conftest.py, readme_sync.py, __init__.py, test_daemon.py, autonomous_repair_loop.py, test_runner.py, chaos_monkey.py, __init__.py, test_ollama_engines.py, __init__.py, test_full_pipeline.py, __init__.py, __init__.py, __init__.py, __init__.py, test_nervous.py, __init__.py, __init__.py, __init__.py, test_heart.py, __init__.py, __init__.py, __init__.py, __init__.py, test_blood.py, __init__.py, __init__.py, __init__.py, test_brain.py, __init__.py, __init__.py, __init__.py, test_eyes.py

## Commands

Run `agent-doctor` to refresh health → `- [ ] agent-doctor`
Run nerve heal → `- [ ] nerve-heal`

---
_Edit task checkboxes to sync back to ACTIVE_TASKS.md._
_Add `- [ ] <cli-command>` and check it to trigger that command._
