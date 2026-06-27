---
name: copilot-optimizer
description: >
  Optimizes and formats brainstorm ideas into context-rich prompts designed for Microsoft 365 Copilot Chat.
---

# Copilot Optimizer

## Purpose

The `copilot-optimizer` skill optimizes and packages Suneel's raw brainstorm ideas or feature requests into high-quality, structured execution prompts specifically designed for **Microsoft 365 Copilot Chat** (running locally on macOS). These engineered prompts ensure that when Copilot generates a final coding prompt, it contains all the necessary workspace context, architectural rules, and CLI tools for Suneel's active workspace agents to execute the task perfectly.

## Workflow

1. **Analyze Suneel's Raw Input**:
   - Understand the feature, script, or change Suneel wants to build.
   - Identify the scope of files or systems involved in the workspace.

2. **Retrieve Context (Optional)**:
   - Look up relevant files or configurations within `~/SuneelWorkSpace` if needed to supply specifics.
   - Reference the workspace structure outlined in the main [README.md](file:///Users/MAC/SuneelWorkSpace/README.md).

3. **Format & Package the Prompt for Copilot**:
   - Generate a structured prompt to be copy-pasted into **Microsoft 365 Copilot Chat**.
   - Emphasize to Copilot that its role is **Lead Prompt Engineer** for Suneel's shared agent workspace.
   - Instruct Copilot to format the final execution prompt so that the active workspace agent (e.g., Claude Code, Codex, Gemini, OpenCode) is strictly guided to:
     - Load and read the startup checklists (`skeleton/rules/*`) before making changes.
     - Follow the **Golden Rule** of CLI operations: always prefix commands with `rtk` (e.g., `rtk git status`, `rtk cargo build`).
     - Run `./bin/agent-doctor` before and after all code modifications to verify health.
     - Adhere strictly to the `Safety Boundaries` (no money actions, make backups before replacing files).
     - Execute the task step-by-step and write a clean session handoff in `brain/memory/SESSION_HANDOFF.md` and `blood/logs/SESSION_LOG.md`.

4. **Output Structure**:
   - Provide a brief explanation of how the optimized prompt is engineered.
   - Present the prompt inside a clean, copy-pasteable Markdown block.

## Prompt Blueprint

When generating the prompt, use this template structure:

```markdown
You are a Lead Prompt Engineer helping me design a task prompt for my local workspace AI agents. 

We are working in SuneelWorkSpace (`~/SuneelWorkSpace`), which is a shared agent environment where Claude Code, Codex CLI, Gemini CLI, OpenCode, and Antigravity coordinate context via a file-based agent-system (`brain/memory/`).

Please generate a highly structured, step-by-step task execution prompt for my workspace agent to perform the following:
[INSERT RAW IDEA / REQUEST HERE]

The final execution prompt you generate MUST include these instructions for the agent:
1. **Startup**: State "Loading workspace context" and read the startup checklist files under `skeleton/rules/` before acting.
2. **Golden Rule**: Always prefix terminal commands with `rtk` (e.g., `rtk git status`, `rtk cargo test`, `rtk agent-doctor`) for 50-90% token savings. Never use plain commands.
3. **Safety**: Do not perform destructive actions without making a timestamped backup first. No money-related actions.
4. **Health Check**: Run `./bin/agent-doctor` before editing and after finishing to ensure 100% workspace health.
5. **Closeout**: Update the session log `blood/logs/SESSION_LOG.md` and write a clear, concise handoff in `brain/memory/SESSION_HANDOFF.md`.
```

## Execution Rules
- Always use `rtk` command wrappers for any CLI execution.
- Keep session handoffs up to date in [brain/memory/SESSION_HANDOFF.md](file:///Users/MAC/SuneelWorkSpace/brain/memory/SESSION_HANDOFF.md).
- Run `./bin/agent-doctor` after executing code edits.
