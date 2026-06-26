# Identity Capture System

Local-first identity subsystem for capturing Suneel's voice, preferences, decision style, and workflow expectations.

## Workflow

1. Interview one question at a time.
2. Store each answer in `interview/responses.md`.
3. Extract signals into `interview/extracted_signals.json`.
4. Generate identity, tone, decision, and preference profiles.
5. Integrate approved identity context into Claude, Codex, MCP, orchestrator, goal-engine, and comms surfaces.

## Safety

- Do not invent identity traits.
- Use only Suneel's answers and clearly marked inferences.
- Keep all identity files inspectable plain text or JSON.
- Do not weaken existing safety boundaries.
