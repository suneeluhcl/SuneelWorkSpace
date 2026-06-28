"""
context_injector.py
Loads live workspace context and injects it into every Ollama call.
Every engine should call build_context() and pass it as the system prompt.
"""

import json
import os
from datetime import datetime, timezone

WORKSPACE = os.path.expanduser("~/SuneelWorkSpace")
_CONTEXT_CACHE: dict = {}
_CACHE_TTL = 300  # 5 min


def _read(path: str, max_chars: int = 2000) -> str:
    full = os.path.join(WORKSPACE, path)
    if not os.path.exists(full):
        return ""
    try:
        return open(full).read()[:max_chars]
    except Exception:
        return ""


def _read_json(path: str) -> dict:
    full = os.path.join(WORKSPACE, path)
    if not os.path.exists(full):
        return {}
    try:
        return json.load(open(full))
    except Exception:
        return {}


def build_context(task_type: str = "general", max_chars: int = 4000) -> str:
    """Build a workspace-aware context string for Ollama system prompts."""
    global _CONTEXT_CACHE
    cache_key = task_type
    cached = _CONTEXT_CACHE.get(cache_key, {})
    if cached and (datetime.now(timezone.utc).timestamp() - cached.get("ts", 0)) < _CACHE_TTL:
        return cached["context"]

    sections = []

    # Identity
    identity = _read("dna/identity/profile/identity_profile.md", 800)
    tone = _read("dna/identity/profile/tone_profile.md", 400)
    if identity:
        sections.append(f"## Suneel's Identity\n{identity}")
    if tone:
        sections.append(f"## Tone Profile\n{tone}")

    # Workspace architecture
    sections.append("""## Workspace Architecture
SuneelWorkSpace is a 12-organ human-body-modeled AI workspace on macOS (M4 Max, 64GB RAM).
Organs: brain (memory/search), heart (tasks/routing), eyes (dashboard), ears (monitors),
nervous (propagator/MCP), skeleton (rules), blood (logs/telemetry), hands (scripts/CLI),
mouth (comms), dna (identity), lab (experiments/autolab), spine (health/state).
CLI commands live as symlinks in hands/bin/. Nerve events flow via nervous/nerve_propagator.py.
Ollama models: suneelworkspace (llama3.3:70b base), codellama, llama3.1, mistral, llama3.2, llama3.3:70b.""")

    # Current state
    state = _read_json("spine/state/CURRENT_STATE.json")
    health = _read_json("spine/state/WORKSPACE_HEALTH.json")
    if state or health:
        score = health.get("health_score", "?")
        sections.append(f"## Current State\nHealth score: {score}/100 | State: {json.dumps(state)[:300]}")

    # Memory
    memory = _read("brain/memory/MEMORY.md", 1200)
    if memory:
        sections.append(f"## Durable Memory\n{memory}")

    # Active tasks
    tasks = _read("heart/tasks/ACTIVE_TASKS.md", 600)
    if tasks:
        sections.append(f"## Active Tasks\n{tasks}")

    # Session handoff
    handoff = _read("brain/memory/SESSION_HANDOFF.md", 600)
    if handoff:
        sections.append(f"## Latest Session Handoff\n{handoff}")

    # Decisions (for code/architecture tasks)
    if task_type in ("code_review", "architecture", "general", "repair"):
        decisions = _read("brain/memory/DECISIONS.md", 600)
        if decisions:
            sections.append(f"## Key Decisions\n{decisions}")

    # Patterns (for repair/learning tasks)
    if task_type in ("repair", "learning", "general"):
        patterns = _read("brain/memory/PATTERNS.md", 400)
        if patterns:
            sections.append(f"## Patterns\n{patterns}")

    full_context = "\n\n".join(sections)[:max_chars]

    _CONTEXT_CACHE[cache_key] = {
        "context": full_context,
        "ts": datetime.now(timezone.utc).timestamp(),
    }
    return full_context


def ask_ollama_with_context(
    prompt: str,
    model: str = "suneelworkspace",
    task_type: str = "general",
    timeout: int = 120,
    temperature: float = 0.2,
    num_ctx: int = 8192,
) -> str:
    """Drop-in replacement for ask_ollama() — injects workspace context."""
    import urllib.request

    context = build_context(task_type)
    system = f"""You are an AI engine inside SuneelWorkSpace — a living, self-maintaining local AI workspace.

{context}

## Behavior Rules
- Be direct, concise, no fluff.
- Produce actionable output: specific file paths, exact commands, structured JSON.
- SAFE actions only unless explicitly told otherwise.
- Never suggest destroying files, leaking credentials, or billing changes.
- Suneel's tone: short, direct, casual, smart. Match it."""

    payload = json.dumps({
        "model": model,
        "system": system,
        "prompt": prompt,
        "stream": False,
        "options": {
            "temperature": temperature,
            "num_ctx": num_ctx,
        },
    }).encode()

    import urllib.request as _ur
    req = _ur.Request(
        "http://localhost:11434/api/generate",
        data=payload,
        headers={"Content-Type": "application/json"},
        method="POST",
    )
    try:
        with _ur.urlopen(req, timeout=timeout) as r:
            return json.loads(r.read()).get("response", "").strip()
    except Exception as e:
        return f"[ollama error: {e}]"


def invalidate_cache():
    global _CONTEXT_CACHE
    _CONTEXT_CACHE = {}


if __name__ == "__main__":
    print("Building context...")
    ctx = build_context("general")
    print(f"Context length: {len(ctx)} chars")
    print("\n--- Preview ---")
    print(ctx[:800])
