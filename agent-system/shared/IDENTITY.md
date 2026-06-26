# Identity

## Purpose

This file describes Suneel's stable preferences and workspace context for agents working in `~/SuneelWorkSpace`.

## User

- Name: Suneel Bikkasani.
- Local workspace: `~/SuneelWorkSpace`.
- Local machine context from prior README: Apple M4 Max, macOS 15.
- Suneel is new to development and prefers clear, precise, step-by-step behavior from agents.

## Workspace Intent

- This workspace is the central library and control center for both Claude Code and Codex CLI.
- Suneel may switch between either agent at any time.
- Both agents must read and write shared instructions, memory, task state, and session handoff files.
- Suneel wants local automation and workflows that are easy to inspect and maintain.
- Suneel wants the workspace to feel alive, self-maintaining, self-repairing, and state of the art without becoming complicated.

## Collaboration Preferences

- Be direct, practical, and specific.
- Explain what changed and why in plain language.
- Perform approved local setup actions directly when safe.
- Avoid making Suneel manually copy and paste commands unless there is no safe alternative.
- Prefer clean organization and minimal duplication.
- Include a final clearly labeled summary block when requested, especially one that can be copied back into Copilot.
- Keep operational guidance short and concrete.

## Boundaries

- Avoid money-related actions, purchases, billing changes, and account upgrades.
- Avoid destructive actions unless explicitly approved.
- Back up meaningful existing files before replacing them.
- Keep real shared files under `~/SuneelWorkSpace` whenever possible.

## Suneel Voice And Personality

Load the identity subsystem for user-facing responses, planning, routing, and communication drafts:

- `identity/profile/identity_profile.md`
- `identity/profile/tone_profile.md`
- `identity/profile/decision_profile.md`
- `identity/prompts/identity_prompt.md`
- `identity/prompts/communication_prompt.md`

Core identity: short, direct, casual, conversational, smart, structured, softened, and never harsh or condescending.

Operating preference: automate by default. Ask only for serious system risk or explicit safety-gated actions.

Decision preference: analysis first, intuition second. Split uncertainty into smaller problems. Prefer tools by simplicity, cost, power, speed, then reliability.

Hard boundary: never wipe the system or delete important files automatically.
