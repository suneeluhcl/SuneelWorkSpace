# Idea To Execution Pipeline

The goal engine should use this sequence for new ideas and system improvements:

1. Capture the idea with `idea-start` or `idea-run`.
2. Review the generated research plan and analysis.
3. Convert accepted work into a goal using the existing goal-engine scripts.
4. Route the work through the orchestrator.
5. Verify implementation with focused tests or command smoke tests.
6. Promote durable knowledge into shared memory and decisions.

## Safety Defaults

- Prefer existing local commands before adding new subsystems.
- Prefer plain files over hidden state or external services.
- Treat external installs, private-folder indexing, and communication sends as approval-gated.

## Identity Defaults

- Keep plans short, direct, casual, and clear.
- Use conversational flow unless a checklist is more useful.
- Act on autopilot for safe steps.
- Preserve Suneel's hard boundary: never wipe the system or delete important files automatically.

## Anticipation Defaults

- After `goal-create`, suggest `goal-plan`.
- After `goal-plan`, suggest routing or execution only when safe.
- Record goal execution cycles into `brain/anticipation/prediction_memory.json`.
- Keep recommendations as suggestions, not automatic execution.
