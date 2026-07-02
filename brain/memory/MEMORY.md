# Shared Memory

## Durable Facts

- Canonical workspace path: `~/SuneelWorkSpace`.
- This workspace is shared by ALL agents: Antigravity (agy), Claude Code, Codex CLI, Gemini CLI, and OpenCode.
- All agents read and write the same shared memory, task state, handoff, and log files.
- Suneel may use any agent at any time — they all share one brain.
- Suneel wants local automation and workflows.
- Suneel is new to development and prefers clear, precise, step-by-step behavior.
- Approved local setup actions should be performed directly by the agent when safe.
- Avoid money-related actions.
- Avoid destructive actions without explicit approval.
- Prefer clean organization, minimal duplication, and a single source of truth.
- Suneel wants the workspace to feel alive, self-maintaining, self-repairing, and state of the art while staying simple and transparent.
- Suneel uses the Microsoft 365 Copilot Chat Mac app to brainstorm ideas and engineer prompts. These prompts are pasted into the active workspace agent, which must execute the instructions precisely while aligning with the workspace architecture.


## Environment Notes

- Suneel Bikkasani, Apple M4 Max, macOS 15.
- New projects should generally live under `~/SuneelWorkSpace/projects/`.
- Codex bootstrap files live in `~/SuneelWorkSpace/hands/codex/`.
- Adwi local AI OS archive: `https://github.com/sndboxTesting/adwi`.
- Background maintenance is local, lightweight, implemented with launchd calling workspace scripts.

## Agent Roster

- **Antigravity (agy)**: Primary orchestrator. Global: `~/.gemini/config/AGENTS.md`. Workspace: `~/SuneelWorkSpace/.agents/AGENTS.md`. MCP: headroom + workspace-brain.
- **Claude Code**: Deep coding. Global: `~/.claude/CLAUDE.md`. Workspace: `~/SuneelWorkSpace/CLAUDE.md` + `.claude/settings.local.json`.
- **Codex CLI**: Agentic runs. Global: `~/.hands/codex/AGENTS.md`. Config: `~/.hands/codex/config.toml`.
- **Gemini CLI**: Free fallback (1K req/day). Launch: `swgemini`. Config: `~/.gemini/settings.json`. Workspace: `~/SuneelWorkSpace/GEMINI.md`.
- **OpenCode**: Free fallback (Groq). Launch: `swopencode`. Config: `~/SuneelWorkSpace/opencode.json`.

## Token Optimization Infrastructure

- **Headroom proxy** at `http://127.0.0.1:8787`: Compresses context on every API call. Saves ~$197+ lifetime. Claude, Codex, and Antigravity all route through it.
- **RTK**: Auto-rewrites bash commands for 50-90% CLI output token savings. Configured as PreToolUse hook for Claude Code + workspace, and as a skill for Antigravity.
- **savings** alias: Run `savings` in terminal to see combined savings report.
- **workflow-audit**: Level 1 Agentic OS auditing tool. Analyzes prompt history to find repeated tasks and recommend new skills.
- **gstack-create**: Automates GStack skill stubbing and Claude Code slash-command symlinking.
- **self-repair skill**: A GStack reasoning skill (`/self-repair`) providing systematic diagnostic, health-check, code-fix, and rollback procedures.
- **copilot-optimizer skill**: A GStack reasoning skill (`/copilot-optimizer`) to brainstorm and package raw ideas into structured prompts optimized for Microsoft 365 Copilot Chat.


## 2026-07-02 - Java full-stack dev arsenal

- Developer helpers live in `hands/scripts/dev/`, symlinked in `hands/bin/`: `java-build` (Maven/Gradle wrapper-aware compact builds), `dev-stack` (docker service orchestration + `init` compose generator), `spring-watch` (Spring Boot log anomaly detection, optional `--ollama`), `pr-setup` (gh PR checkout + build + migration report), `dev-projects-scan` (catalogs repos → `spine/system-context/developer_projects.json`).
- `history-insights` analyzes `~/.zsh_history` (secrets-redacting) → `spine/audit/shell_insights.md`.
- No JDK/Maven/Gradle installed on this Mac yet; helpers detect this and suggest installs rather than failing cryptically.
- Structured lessons live in `brain/memory/LESSONS.md`, distilled nightly by `lab/autolab/log_learn_engine.py`; `lab/autolab/daily_evolve.py` ends with a deterministic verify() gate (run-tests + agent-doctor).

## Memory Rules

- Store only stable, useful facts here.
- Do not store secrets, tokens, passwords, private keys, billing data, or temporary noise.
- Prefer updating an existing bullet over adding duplicates.

## 2026-06-26 - Personal AI operating system upgrade

- The workspace now has a bounded system intelligence layer: `system-audit`, `system-gaps`, `system-capabilities`, `system-recommend`, and `improve-system`.
- Durable audit artifacts live in `spine/audit/`; safe machine metadata lives in `spine/system-context/system_profile.json`; local tool discovery lives in `spine/tools/`.
- The research engine lives in `brain/research/` and supports `idea-start`, `idea-run`, and lower-level `idea-*` scripts for idea capture, research plans, analyses, and decisions.
- Bounded self-upgrade policy is documented in `skeleton/rules/BOUNDED_SELF_UPGRADE.md`.

## 2026-06-26 - Suneel identity capture

- Identity subsystem lives in `dna/identity/`.
- Suneel's preferred voice is short, direct, casual, conversational, smart, structured, softened, and never harsh or condescending.
- Suneel prefers autopilot by default, with questions only for serious system risk or safety-gated actions.
- Suneel chooses tools by simplicity, cost, power, speed, then reliability.
- Hard boundary: never wipe the system or delete important files automatically.
- Adaptive identity loop lives in `dna/identity/adaptive/` and learns slowly from accepted, edited, rejected, and adjusted outputs while preserving the original identity profile.
- Adaptive identity now uses weighted signals from `dna/identity/adaptive/signal_weights.json` so rejected/manual/heavy-edit feedback influences learning more than simple acceptance.

## 2026-06-26 - Anticipatory intelligence

- Anticipation subsystem lives in `brain/anticipation/`.
- Prediction engine path: `brain/anticipation/prediction_engine.py`.
- Prediction memory path: `brain/anticipation/prediction_memory.json`.
- Current suggestions path: `brain/anticipation/action_suggestions.md`.
- Anticipation suggests next actions only; it never auto-executes or overrides safety boundaries.
- `README.md` is now the complete system blueprint and AI-agent drop-in context.
- Intent detection stores current intent in `brain/anticipation/current_context.json` using categories: messaging, email, research, system_improvement, development, idea_execution, maintenance, unknown.
- Suggestions are ranked with `frequency_weight + success_weight + recency_weight + identity_alignment + intent_alignment` and limited to top 3-5.
- Session boot contract in `README.md` requires agents to say `✅ Loading workspace shared brain` and confirm context loaded before meaningful work.


---
*Added by memory curator — 2026-06-28*

## Recent Projects

List of recent projects under `~/SuneelWorkSpace/projects/` to track progress and identify trends.

## Ollama Integration Progress

Summary of Ollama's integration with the workspace, including any new features or capabilities enabled by this integration.



---
*Added by memory curator — 2026-06-28*

## Recent Agent Performance

Add a section to track the performance of each agent, including metrics such as response time, accuracy, and resource utilization.

## New Projects

Create a new section to document recent projects, including project goals, timelines, and key milestones.



---
*Added by memory curator — 2026-06-29*

## Recent Projects

* Implemented Karpathy-style LLM-Wiki persistent knowledge base with ingest, lint, and query compounding pipelines

## New Skills

* Automated model rotation and versioning in heart/

## Predictive Maintenance System

* Developed using blood/telemetry data to forecast potential anomalies



---
*Added by memory curator — 2026-06-30*

## Recent Ollama Suggestions

*Generated: 2026-06-28T15:34:54.270067+00:00*

The recent Ollama suggestions indicate a need for memory reindexing and agent doctoring.

## Recent Nerve Events

The recent nerve events suggest that Suneel has been actively working on various projects, including skeleton, blood, hands, mouth, dna, lab, spine, brain, heart, eyes, ears, nervous, and lab.



---
*Added by memory curator — 2026-07-01*

## Recent Projects

* Implemented Karpathy-style LLM-Wiki persistent knowledge base with ingest, lint, and query compounding pipelines

## Ollama Suggestions

* Investigate and implement `mcp-reindex`, `memory-reindex`, and `agent-doctor` suggestions



---
*Added by memory curator — 2026-07-02*

## Recent Activity

Recent session handoff involved consolidating the workspace root by moving docs to spine/docs and deleting legacy directories. This should be reflected in the Environment Notes section.

## Integration with Hands Organ

The hands organ's CLI scripts are not integrated with the suneelworkspace model, which is a medium-priority improvement idea. This should be added to the Improvement Ideas section.



---
*Added by memory curator — 2026-07-02*

## Recent Ollama Suggestions

Ollama suggestions have been integrated into the workspace to provide proactive maintenance recommendations. These suggestions should be reviewed regularly to ensure timely action.

## Agent Capabilities

Each agent's capabilities and limitations should be documented in a separate section to facilitate better decision-making when choosing which agents to use for specific tasks.

