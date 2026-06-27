# Session Closeout Checklist

## Update

- `brain/memory/SESSION_HANDOFF.md`
- `heart/tasks/ACTIVE_TASKS.md`
- `heart/tasks/COMPLETED_TASKS.md`
- `blood/logs/SESSION_LOG.md`
- `spine/state/CURRENT_STATE.json`
- `spine/state/WORKSPACE_HEALTH.json` if health changed

## Automatic Safety Net

- `agent-autoclose` runs from `use-codex`, `use-claude`, shell exit hooks, and startup recovery.
- Manual `agent-finish` is optional during normal use, but intentional agent-authored closeout is still preferred when possible.

## Consider Updating

- `brain/memory/MEMORY.md` for durable facts.
- `brain/memory/DECISIONS.md` for important decisions and reasons.

## Verify

- Important files exist.
- Scripts still run.
- JSON remains valid.
- Any backups are noted.
- The next agent can continue from `SESSION_HANDOFF.md`.

## Final Response

Tell Suneel:

- What changed.
- Important file paths.
- How to use it.
- Any limitations or follow-up recommendations.
