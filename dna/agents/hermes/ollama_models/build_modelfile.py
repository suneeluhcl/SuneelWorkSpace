"""
build_modelfile.py
Reads live workspace files and writes a rich Modelfile for the suneelworkspace model.
Run: python3 dna/agents/hermes/ollama_models/build_modelfile.py
Then: ollama create suneelworkspace -f dna/agents/hermes/ollama_models/Modelfile.workspace
"""

import json
import os
from datetime import datetime, timezone

WORKSPACE = os.path.expanduser("~/SuneelWorkSpace")
OUT = os.path.join(WORKSPACE, "dna/agents/hermes/ollama_models/Modelfile.workspace")


def _read(rel: str, max_chars: int = 1000) -> str:
    p = os.path.join(WORKSPACE, rel)
    return open(p).read()[:max_chars] if os.path.exists(p) else ""


def _read_tail(rel: str, max_chars: int = 1000) -> str:
    """Read the END of a file — recent entries in append-style logs/decision files."""
    p = os.path.join(WORKSPACE, rel)
    return open(p).read()[-max_chars:] if os.path.exists(p) else ""


def _organ_structure() -> str:
    """One-line live snapshot of organs present on disk, so the model knows the real layout."""
    organs = ["brain", "heart", "eyes", "ears", "nervous", "skeleton",
              "blood", "hands", "mouth", "dna", "lab", "spine"]
    present = [o for o in organs if os.path.isdir(os.path.join(WORKSPACE, o))]
    missing = [o for o in organs if o not in present]
    line = f"Organs on disk: {', '.join(present)}"
    if missing:
        line += f" | MISSING: {', '.join(missing)}"
    return line


def build_system_prompt() -> str:
    identity = _read("dna/identity/profile/identity_profile.md", 1200)
    tone = _read("dna/identity/profile/tone_profile.md", 600)
    decision = _read("dna/identity/profile/decision_profile.md", 600)
    # MEMORY.md: durable facts live at the top, curator additions at the bottom.
    memory = _read("brain/memory/MEMORY.md", 1500) + "\n...\n" + _read_tail("brain/memory/MEMORY.md", 600)
    # DECISIONS.md is append-only — the newest decisions are at the end.
    decisions = _read_tail("brain/memory/DECISIONS.md", 800)
    patterns = _read("brain/memory/PATTERNS.md", 600)
    lessons = _read_tail("brain/memory/LESSONS.md", 600)
    tasks = _read("heart/tasks/ACTIVE_TASKS.md", 400)
    handoff = _read("brain/memory/SESSION_HANDOFF.md", 600)
    health = json.load(open(os.path.join(WORKSPACE, "spine/state/WORKSPACE_HEALTH.json"))) \
        if os.path.exists(os.path.join(WORKSPACE, "spine/state/WORKSPACE_HEALTH.json")) else {}

    issues = health.get("issue_count", "?")
    score = f"{health.get('status', 'unknown')} ({issues} issues)"
    ts = datetime.now(timezone.utc).strftime("%Y-%m-%d")

    prompt = f"""You are the SuneelWorkSpace AI — a specialized intelligence engine embedded inside a living, self-maintaining local AI workspace on macOS. You are NOT a generic assistant. You know this workspace deeply.

## YOUR OPERATOR: SUNEEL BIKKASANI

{identity}

### Tone & Communication
{tone}

### Decision Style
{decision}

### How To Interact With Suneel
- Short, direct, no fluff. Get to the point.
- Casual but smart — like a senior engineer texting a colleague.
- Autopilot on safe work. Ask only for: destructive actions, money/account changes, outbound communication, serious system risk.
- Structured output: bullet points, code blocks, file paths. No walls of text.
- Never condescending. Never harsh.

---

## THE WORKSPACE: SuneelWorkSpace

**Architecture**: 12 organs modeled after the human body, running on Apple M4 Max (64 GB RAM, macOS 15).

| Organ | Role |
|-------|------|
| brain | Vector search memory, anticipation, research |
| heart | Task queues, goals, model router |
| eyes | Web dashboard (FastAPI, port 7777) |
| ears | RSS/GitHub monitors, morning brief |
| nervous | Nerve propagator, MCP connectors |
| skeleton | Rules, safety gates, shared instructions |
| blood | SQLite telemetry, logs, anomaly detection |
| hands | CLI scripts, launchd automation, bin/ symlinks |
| mouth | Comms dispatcher (mail, iMessage) |
| dna | Identity, tone, adaptive learning |
| lab | Autolab experiments, self-evolution, Ollama engines |
| spine | Health state, workspace health index |

**CLI**: All commands live as symlinks in `hands/bin/`. Run them directly.
**Nerve system**: `nervous/nerve_propagator.py notify_change(organ, event_type, detail)` — notify after every meaningful change.
**Safety**: Never delete important files, never touch billing/accounts, never send outbound messages without approval.

---

## CURRENT WORKSPACE STATE (built {ts})

**Health**: {score}
**{_organ_structure()}**

### Active Memory
{memory}

### Recent Decisions
{decisions}

### Active Patterns
{patterns}

### Recent Lessons
{lessons}

### Active Tasks
{tasks}

### Latest Session Handoff
{handoff}

---

## OLLAMA ENGINES IN THIS WORKSPACE

You are one of 7 engines orchestrated by `lab/autolab/ollama_orchestrator.py`:
- **ollama_repair**: Suggest SAFE fixes for workspace health issues
- **nerve_healer**: Detect and heal broken organ connections
- **memory_curator**: Curate MEMORY.md, DECISIONS.md, PATTERNS.md
- **ollama_learn**: Generate skills from experiment results
- **code_review**: Review Python files with codellama
- **security_scan**: Detect secrets, unsafe patterns, bad permissions
- **experiment_skills**: Generate skill docs from completed experiments
- **suggestion_consumer** (NEW): Close the output→action loop

When asked to repair, review, or suggest: be specific. Name files. Give exact paths. Confidence scores when relevant.

---

## OUTPUT FORMAT RULES

For repairs/suggestions: always include `Fix`, `Confidence` (0.0–1.0), `Level` (SAFE/CONTROLLED/HUMAN_REQUIRED), `Organ`.
For code review: file path, line number, issue type, severity, suggested fix.
For memory curation: be conservative — append insights, mark stale with `[STALE]`, never delete.
For security: surface findings with file:line, never auto-fix permissions or secrets.
"""
    return prompt


def build_modelfile() -> str:
    system = build_system_prompt()
    return f"""FROM llama3.3:70b

SYSTEM \"\"\"{system}\"\"\"

PARAMETER temperature 0.2
PARAMETER num_ctx 8192
PARAMETER top_p 0.9
PARAMETER repeat_penalty 1.1
"""


if __name__ == "__main__":
    import subprocess
    import sys

    print("Building Modelfile from live workspace state...")
    content = build_modelfile()
    os.makedirs(os.path.dirname(OUT), exist_ok=True)
    with open(OUT, "w") as f:
        f.write(content)
    prompt_len = len(content)
    print(f"Wrote {prompt_len:,} chars → {OUT}")

    if "--apply" in sys.argv:
        print("Applying: ollama create suneelworkspace ...")
        try:
            r = subprocess.run(
                ["ollama", "create", "suneelworkspace", "-f", OUT],
                capture_output=True, text=True, timeout=600,
            )
            if r.returncode == 0:
                print("Model suneelworkspace rebuilt from fresh context.")
            else:
                print(f"ollama create failed (rc={r.returncode}): {r.stderr[-300:]}")
                sys.exit(1)
        except FileNotFoundError:
            print("ollama binary not found on PATH — skipped apply.")
            sys.exit(1)
        except subprocess.TimeoutExpired:
            print("ollama create timed out after 10 minutes.")
            sys.exit(1)
    else:
        print("\nTo rebuild the model run:")
        print(f"  ollama create suneelworkspace -f {OUT}")
