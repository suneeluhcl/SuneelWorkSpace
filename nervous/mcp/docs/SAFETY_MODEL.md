# Safety Model

workspace-brain enforces a layered safety model: most operations are read-only, and write operations are narrowly bounded.

## Principles

1. **Read by default** — resources and most tools only read files.
2. **Write in approved areas only** — mutating tools only touch files listed in `tool_policies.json`.
3. **No arbitrary shell execution** — tools that run scripts invoke specific known scripts (agent-doctor, agent-repair, workspace-report), not arbitrary commands.
4. **No unrestricted filesystem writes** — no tool writes outside the mutable area.
5. **No credential exposure** — no tool reads or returns auth.json, secrets, tokens, or private keys.
6. **Backup before overwrite** — tools that replace files (create_handoff_draft, update_task_status) create a `.bak` copy first.
7. **Append-only for logs** — SESSION_LOG.md is append-only. MEMORY.md and DECISIONS.md are append-only.
8. **Dry-run mode** — set `"dry_run_mutating_tools": true` in server_config.json to make all writes print `[DRY RUN]` instead.
9. **Access logging** — every tool call is logged to `mcp_access.log` (JSONL) with timestamp and arguments.

## Mutable area (tools may write here)

```
brain/memory/MEMORY.md
brain/memory/DECISIONS.md
brain/memory/NOTES.md
brain/memory/SESSION_HANDOFF.md
heart/tasks/ACTIVE_TASKS.md
heart/tasks/TASK_QUEUE.md
blood/logs/SESSION_LOG.md
nervous/nervous/mcp/server/state/mcp_state.json
nervous/nervous/mcp/server/logs/
```

## Protected area (tools never write here)

```
skeleton/rules/          (canonical instructions — read-only)
spine/state/           (written only by agent-doctor, agent-repair, agent-autoclose)
lab/autolab/                      (written only by autolab scripts)
bin/                          (workspace scripts — never modified by MCP)
automation/                   (maintenance scripts — never modified by MCP)
~/.claude/                    (Claude config — never modified by MCP tools)
~/.hands/codex/                     (Codex config — never modified by MCP tools)
```

Note: `mcp-repair` (a shell script, not an MCP tool) does modify `~/.claude/settings.json` and `~/.hands/codex/config.toml` when fixing broken registration — but only on explicit operator invocation, not via tool calls.

## Tool-level permission table

See `server/config/tool_policies.json` for the complete machine-readable table.

Summary:
- All tools: `read: true`
- Write tools: add_memory_note, add_decision, add_task, update_task_status, append_session_note, create_handoff_draft, trigger_reindex, run_workspace_repair_safe
- Exec tools: trigger_reindex, run_workspace_doctor, run_workspace_repair_safe, generate_workspace_report

## Access logging

Every tool call writes a JSONL line to `nervous/nervous/mcp/server/logs/mcp_access.log`:
```json
{"ts": "2026-06-24T...", "tool": "search_memory", "args": {"query": "NLU"}}
```

Mutating operations are also logged to `nervous/nervous/mcp/server/logs/mcp_server.log`.
