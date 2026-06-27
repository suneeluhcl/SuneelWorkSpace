# System Intelligence Routing Policy

Use the system intelligence layer when a task asks for audit, self-improvement, capability discovery, tool recommendations, research planning, or idea-to-execution support.

## Preferred Commands

- `system-audit`: refresh and open `spine/audit/system_audit.md`.
- `system-gaps`: refresh and open `spine/audit/gap_analysis.md`.
- `system-capabilities`: refresh `spine/system-context/system_profile.json`.
- `system-recommend`: refresh `spine/tools/recommendations.md`.
- `improve-system`: run the bounded local refresh loop without installing external tools.
- `idea-start`: capture a raw idea.
- `idea-run`: capture, plan, analyze, and draft a decision.

## Routing Notes

- Keep the existing orchestrator and goal-engine as the execution layer.
- Treat research-engine output as planning evidence, not automatic permission to install or change external services.
- Use MCP resources for audit, profile, inventory, recommendations, and research state when available.
- For communication workflows, require explicit user approval before sending, deleting, archiving, forwarding, or contacting anyone.

## Identity Routing

- Load `dna/identity/integration/routing_identity.json` before choosing ask-vs-act behavior.
- Default to autopilot for safe local work.
- Ask only for serious system risk or explicit safety-gated actions.
- Keep responses short, direct, casual, softened, smart, and structured enough to be clear.
- For tool choices, prefer simplicity, cost, power, speed, then reliability.

## Anticipatory Routing

- Check `brain/anticipation/action_suggestions.md` for precomputed next actions.
- Record route execution outcomes through `brain/anticipation/prediction_engine.py`.
- Suggestions must never auto-execute. They are planning hints only.
