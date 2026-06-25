# Agent Vault Navigation Guidelines

This file outlines the rules and conventions that all AI agents (Claude Code, Codex, Antigravity) must follow when interacting with the Obsidian vault.

## Navigation Patterns

1. **Start at index maps**: Before scanning all files or directories blindly, load the root [index.md](file:///Users/MAC/SuneelWorkSpace/obsidian-vault/index.md) first to understand the vault structure.
2. **Follow folder directories**: Follow index maps down to target directories (e.g. `knowledge/index.md`) instead of performing expensive recursive glob searches.
3. **Respect index integrity**: When creating a new file in `knowledge/`, always update [knowledge/index.md](file:///Users/MAC/SuneelWorkSpace/obsidian-vault/knowledge/index.md) to register the file.
4. **Use relative symlinks**: If you link files across the vault, use relative links so they resolve properly on all systems.

## Naming Conventions
- Capitalize names: Use Capital Letters for files (e.g. `System Map.md`).
- Multi-word spacing: Prefer spaces over underscores/hyphens in file names (e.g., `Template Guide.md`).
- Keep it descriptive: Nouns only, indicating what the file contains.

## State Management
- Never overwrite human-written journals or daily notes without explicit approval.
- Ensure state parameters or json exports are placed in the `agent-system/` or `automation/` tracks, rather than cluttering Suneel's personal notes.
