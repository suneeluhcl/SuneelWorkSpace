# Recovery Guide

## Broken client registration

### Claude not seeing workspace-brain
```sh
# Check
python3 -c "import json; d=json.load(open('$HOME/.claude/settings.json')); print(d.get('mcpServers',{}).get('workspace-brain','MISSING'))"

# Fix (auto)
~/SuneelWorkSpace/nervous/mcp/server/scripts/mcp-repair
```

### Codex not seeing workspace-brain
```sh
# Check
grep workspace-brain ~/.hands/codex/config.toml

# Fix (auto)
~/SuneelWorkSpace/nervous/mcp/server/scripts/mcp-repair
```

## Empty or broken index

The index is fully disposable — delete it and rebuild.
```sh
rm -f ~/SuneelWorkSpace/nervous/mcp/server/storage/memory_index.db
~/SuneelWorkSpace/nervous/mcp/server/scripts/mcp-reindex
```

Or just run:
```sh
~/SuneelWorkSpace/nervous/mcp/server/scripts/mcp-repair
```

## Server won't start (mcp package missing)

The server uses `uv run --with-requirements nervous/mcp/server/requirements.txt` (pinned to `mcp==1.28.0`). If uv is not installed:
```sh
brew install uv
```

If the mcp package fails to install, check your network connection. uv downloads it from PyPI on first use.

Test: `uv run --with-requirements nervous/mcp/server/requirements.txt python3 -c "import mcp; print('ok')"`

## Corrupted config files

Backups are created at registration time (`.bak-mcp-repair`). Restore:
```sh
cp ~/.claude/settings.json.bak-mcp-repair ~/.claude/settings.json
cp ~/.hands/codex/config.toml.bak-mcp-repair ~/.hands/codex/config.toml
# Then re-run mcp-repair
~/SuneelWorkSpace/nervous/mcp/server/scripts/mcp-repair
```

## Server errors (check logs)

```sh
tail -50 ~/SuneelWorkSpace/nervous/mcp/server/logs/mcp_server.log
tail -20 ~/SuneelWorkSpace/nervous/mcp/server/logs/mcp_access.log
```

## Run full diagnostics

```sh
~/SuneelWorkSpace/nervous/mcp/server/scripts/mcp-doctor
~/SuneelWorkSpace/nervous/mcp/server/scripts/mcp-test
```

## Nuclear reset (if everything is broken)

```sh
# Remove the index
rm -f ~/SuneelWorkSpace/nervous/mcp/server/storage/memory_index.db

# Reset state
echo '{"server_version":"1.0.0"}' > ~/SuneelWorkSpace/nervous/mcp/server/state/mcp_state.json

# Re-run repair (re-registers clients, rebuilds index)
~/SuneelWorkSpace/nervous/mcp/server/scripts/mcp-repair

# Verify
~/SuneelWorkSpace/nervous/mcp/server/scripts/mcp-doctor
~/SuneelWorkSpace/nervous/mcp/server/scripts/mcp-test
```

## Workspace source files missing

If authoritative files are missing, the MCP server still starts but returns `[File not found]` for affected resources. Fix by running:
```sh
~/SuneelWorkSpace/bin/agent-repair
```
