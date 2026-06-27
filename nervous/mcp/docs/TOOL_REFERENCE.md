# Tool Reference

All tools exposed by workspace-brain. Tools marked **[READ]** are safe read-only. Tools marked **[WRITE]** append or update workspace files within the allowed mutable area. Tools marked **[EXEC]** run a bounded workspace script.

## Read Tools

### `query_workspace_context(focus="")`
Returns combined workspace context: overview, state, health, handoff, active tasks.
If `focus` is provided, filters sections containing that keyword.
**[READ]**

### `get_current_state()`
Returns `spine/state/CURRENT_STATE.json` as text.
**[READ]**

### `get_recent_handoff()`
Returns `brain/memory/SESSION_HANDOFF.md` as text.
**[READ]**

### `search_memory(query, limit=10)`
Keyword search across MEMORY.md, DECISIONS.md, NOTES.md via the FTS index.
Falls back to grep if index is empty.
**[READ]**

### `search_decisions(query, limit=10)`
Keyword search scoped to decisions content.
**[READ]**

### `search_tasks(query, limit=10)`
Keyword search across ACTIVE_TASKS.md, TASK_QUEUE.md, COMPLETED_TASKS.md.
**[READ]**

### `search_autolab_results(query, limit=10)`
Keyword search across autolab results, insights, patterns.
**[READ]**

### `list_active_hypotheses()`
Returns the current autolab frontier and experiment queue.
**[READ]**

### `get_workspace_health()`
Returns `spine/state/WORKSPACE_HEALTH.json`.
**[READ]**

### `get_recent_changes()`
Returns `git status --short` and `git log --oneline -10` from the workspace.
**[READ]**

## Write Tools

### `add_memory_note(note, tags="")`
Appends a note to `brain/memory/MEMORY.md`.
Creates a `.bak` backup before writing.
**[WRITE]**

### `add_decision(decision, reason="", tags="")`
Appends a decision to `brain/memory/DECISIONS.md`.
**[WRITE]**

### `add_task(task, queue="active")`
Adds a task line to ACTIVE_TASKS.md (`queue="active"`) or TASK_QUEUE.md (`queue="queue"`).
**[WRITE]**

### `update_task_status(task_substring, new_status)`
Finds lines in ACTIVE_TASKS.md containing `task_substring` and appends a status tag.
Creates a `.bak` backup before writing.
`new_status` examples: `DONE`, `IN-PROGRESS`, `BLOCKED`, `CANCELLED`.
**[WRITE]**

### `append_session_note(note)`
Appends a timestamped note to `blood/logs/SESSION_LOG.md`.
**[WRITE]**

### `create_handoff_draft(summary, changed="", verification="", open_items="")`
Overwrites `brain/memory/SESSION_HANDOFF.md` with a structured handoff.
Creates a `.bak` backup before writing.
**[WRITE]**

## Exec Tools

### `trigger_reindex()`
Rebuilds the SQLite search index from authoritative workspace files.
**[EXEC + WRITE]**

### `run_workspace_doctor()`
Runs `~/SuneelWorkSpace/bin/agent-doctor` and returns output.
Read-only check; does not modify files.
**[EXEC]**

### `run_workspace_repair_safe()`
Runs `~/SuneelWorkSpace/bin/agent-repair --quiet`.
Limited to existing safe repair logic.
**[EXEC + WRITE]**

### `generate_workspace_report()`
Runs `~/SuneelWorkSpace/bin/workspace-report` and returns output.
**[EXEC]**

## Dry-run mode

Set `"dry_run_mutating_tools": true` in `server/config/server_config.json` to make all write tools print `[DRY RUN]` instead of modifying files.
