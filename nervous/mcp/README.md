# workspace-brain MCP Server

A **local** MCP (Model Context Protocol) server that gives Claude and Codex structured access to this workspace's shared intelligence: memory, tasks, decisions, state, health, and autolab data.

## What it is

Think of it as a smart, safe interface over your workspace files. Instead of reading raw files, Claude and Codex can ask structured questions like:

- "What are my active tasks?" → `search_tasks`
- "What decisions have we made about X?" → `search_decisions`
- "What is the current workspace health?" → `get_workspace_health`
- "Add a memory note about Y" → `add_memory_note`

The file system (`brain/memory/`, `lab/autolab/`, etc.) remains the **source of truth**. This server is a structured access layer over those files, not a replacement.

## How it works

1. Claude or Codex starts the server automatically as a subprocess when needed (stdio mode).
2. The server reads from authoritative workspace files.
3. A local SQLite index enables fast keyword search across all workspace documents.
4. Mutating tools only touch pre-approved, safe files (see `spine/docs/SAFETY_MODEL.md`).

## Quick reference

```sh
# Check status
~/SuneelWorkSpace/nervous/nervous/mcp/server/scripts/mcp-status

# Rebuild the search index (after big changes)
~/SuneelWorkSpace/nervous/nervous/mcp/server/scripts/mcp-reindex

# Health check
~/SuneelWorkSpace/nervous/nervous/mcp/server/scripts/mcp-doctor

# Run all tests
~/SuneelWorkSpace/nervous/nervous/mcp/server/scripts/mcp-test

# Auto-repair issues
~/SuneelWorkSpace/nervous/nervous/mcp/server/scripts/mcp-repair

# Print capability report
~/SuneelWorkSpace/nervous/nervous/mcp/server/scripts/mcp-report
```

## Key paths

| What | Where |
|------|-------|
| Server entrypoint | `nervous/nervous/mcp/server/main.py` |
| Config | `nervous/nervous/mcp/server/config/` |
| Search index | `nervous/nervous/mcp/server/storage/memory_index.db` |
| Logs | `nervous/nervous/mcp/server/logs/` |
| State | `nervous/nervous/mcp/server/state/` |
| Management scripts | `nervous/nervous/mcp/server/scripts/` |
| Documentation | `nervous/mcp/spine/docs/` |

## Docs

- [HOW_IT_WORKS.md](spine/docs/HOW_IT_WORKS.md) — architecture and lifecycle
- [TOOL_REFERENCE.md](spine/docs/TOOL_REFERENCE.md) — all MCP tools
- [RESOURCE_REFERENCE.md](spine/docs/RESOURCE_REFERENCE.md) — all MCP resources
- [SAFETY_MODEL.md](spine/docs/SAFETY_MODEL.md) — mutation rules and boundaries
- [RECOVERY.md](spine/docs/RECOVERY.md) — how to recover from problems
