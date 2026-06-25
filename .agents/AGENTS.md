@~/.claude/RTK.md

# Shared Agent System — Antigravity (agy)

## Purpose

This is the canonical instruction source for Antigravity CLI operating inside Suneel's shared agent workspace at `~/SuneelWorkSpace`.

Antigravity, Claude Code, and Codex CLI all share the same memory, task state, logs, and handoff files. Every agent must read from and write to the same sources.

## Source Of Truth

- Canonical workspace: `~/SuneelWorkSpace`
- Canonical instruction file: `~/SuneelWorkSpace/agent-system/shared/AGENT_SYSTEM.md`
- Workspace entrypoints: `~/SuneelWorkSpace/AGENTS.md` and `~/SuneelWorkSpace/CLAUDE.md`
- Antigravity global entrypoint: `~/.gemini/config/AGENTS.md`
- Antigravity workspace customization: `~/SuneelWorkSpace/.agents/AGENTS.md`
- Codex global entrypoint: `~/.codex/AGENTS.md`
- Claude global entrypoint: `~/.claude/CLAUDE.md`

If instructions conflict inside this workspace, the canonical shared docs under `~/SuneelWorkSpace/agent-system/` are the source of truth.

## Rules

- Keep shared state file-based, transparent, and easy to inspect.
- Prefer clean organization, minimal duplication, and a single source of truth.
- Keep real source files under `~/SuneelWorkSpace` whenever possible.
- Use symlinks or thin loader files outside the workspace only when a tool needs global discovery.
- Do not perform purchases, billing changes, account upgrades, or other money-related actions.
- Avoid destructive actions. Do not delete or overwrite important files without a timestamped backup and clear reason.
- Before changing files, inspect relevant existing files and prefer upgrading over recreating.
- Perform approved local setup actions directly when safe instead of asking Suneel to copy and paste commands.
- Explain work clearly and step by step because Suneel is new to development.
- Leave a concise, high-value handoff for the next agent.

## Startup

Before meaningful work, read these files in order:

1. `~/SuneelWorkSpace/agent-system/shared/AGENT_SYSTEM.md`
2. `~/SuneelWorkSpace/agent-system/shared/IDENTITY.md`
3. `~/SuneelWorkSpace/agent-system/shared/WORKFLOW_RULES.md`
4. `~/SuneelWorkSpace/agent-system/shared/SAFETY_BOUNDARIES.md`
5. `~/SuneelWorkSpace/agent-system/shared/STARTUP_CHECKLIST.md`
6. `~/SuneelWorkSpace/agent-system/memory/MEMORY.md`
7. `~/SuneelWorkSpace/agent-system/memory/DECISIONS.md`
8. `~/SuneelWorkSpace/agent-system/tasks/ACTIVE_TASKS.md`
9. `~/SuneelWorkSpace/agent-system/tasks/TASK_QUEUE.md`
10. `~/SuneelWorkSpace/agent-system/memory/SESSION_HANDOFF.md`
11. `~/SuneelWorkSpace/agent-system/state/CURRENT_STATE.json`
12. `~/SuneelWorkSpace/agent-system/state/WORKSPACE_HEALTH.json`

Use `~/SuneelWorkSpace/bin/agent-start` or `~/SuneelWorkSpace/bin/workspace-context` to print the startup brief.

Mandatory startup behavior:

- State: "Loading workspace context".
- Read the startup checklist files before making meaningful changes.
- Summarize current state, health, active tasks, and latest handoff before acting.
- If a previous session was left open, run or rely on `agent-start` fail-safe recovery to checkpoint it.

## Closeout

After completing meaningful work, update:

- `agent-system/memory/SESSION_HANDOFF.md`
- `agent-system/tasks/ACTIVE_TASKS.md` and/or `agent-system/tasks/COMPLETED_TASKS.md`
- `agent-system/logs/SESSION_LOG.md`
- `agent-system/state/CURRENT_STATE.json`
- `agent-system/state/WORKSPACE_HEALTH.json` if system condition changed
- `agent-system/memory/MEMORY.md` or `agent-system/memory/DECISIONS.md` if durable knowledge was created

Use `~/SuneelWorkSpace/bin/agent-finish "summary"` for simple closeouts.

Automatic closeout:

- `use-codex`, `use-claude`, and shell exit hooks run `agent-autoclose` automatically.
- Manual `agent-finish` is no longer required for normal operation.
- Agents must still attempt to update handoff, logs, memory, decisions, and tasks before finishing when they can.
- If an agent misses closeout, the next startup must detect the open session and repair it with `agent-autoclose --startup-recovery`.

## Memory Policy

Put stable facts in `MEMORY.md`.
Put important choices and their reasons in `DECISIONS.md`.
Use `NOTES.md` for temporary notes that should not become permanent truth yet.
Do not store secrets, tokens, passwords, private keys, billing data, or financial details in shared memory.

## Task Policy

Use `ACTIVE_TASKS.md` for current work.
Use `TASK_QUEUE.md` for queued future work.
Move completed work to `COMPLETED_TASKS.md` with the date and a short result.
Keep task entries short enough for future agents to scan quickly.

## Handoff Policy

`SESSION_HANDOFF.md` should always describe:
- What was requested.
- What changed.
- What was verified.
- What remains.
- Risks, limits, or follow-up recommendations.

## Maintenance Policy

- Use `agent-doctor` to inspect workspace health.
- Use `agent-repair` to safely fix small issues.
- Use `agent-maintain` for recurring health, repair, index, backup, and report refresh.
- Use `agent-autoclose` for automatic, idempotent session checkpointing on wrapper exit, shell exit, and startup recovery.

## Safety Boundaries

- No money actions.
- No destructive actions without explicit approval and backup where applicable.
- No blind merges between similar workspace folders.
- No complicated database or external service for shared state.
- No hidden state when a plain file will work.

## Infrastructure

- **Headroom proxy**: Running at `http://127.0.0.1:8787` — all Anthropic API calls route through it automatically via `ANTHROPIC_BASE_URL`. This provides context compression saving ~22-30% of tokens per session.
- **RTK**: Bash commands are auto-rewritten via the `rtk-rewrite.sh` hook. Always saves 50-90% on CLI output tokens.
- **workspace-brain MCP**: Exposes shared agent-system memory, tasks, and state as MCP tools. Use it to read/write the shared brain programmatically.

## gstack Skills Available

gstack is installed at `~/.claude/skills/gstack/`. These skills are invoked as slash commands.

| Skill | When to use |
|---|---|
| `/investigate` | Debugging — unknown root cause, multi-file failures |
| `/cso` | Security — before shipping auth/input/API changes |
| `/review` | Code quality — after implementation, before commit |
| `/office-hours` | Planning — before decomposing a new goal |
| `/plan-eng-review` | Architecture — before building a new subsystem |
| `/ship` | Release — test → version bump → CHANGELOG → PR |
| `/careful` | Scripting / file ops — preview destructive commands |
| `/qa` | UI testing — browser-based flow testing |
| `/autoplan` | Full pipeline — CEO + design + eng review |
| `/self-repair` | Self-Healing — diagnoses failures, runs doctor/repair, fixes syntax, and manages rollbacks |
