#!/usr/bin/env python3
"""
memory_curator.py
Uses local Ollama to curate brain/memory/ files.
Finds stale entries, contradictions, missing insights.
Adds new insights from recent sessions.
Keeps memory lean, accurate, and useful.
"""

import json
import os
import re
import urllib.request
from datetime import datetime, timezone

MEMORY_FILES = {
    "brain/memory/MEMORY.md": "stable facts about the workspace and Suneel",
    "brain/memory/DECISIONS.md": "important decisions made and their reasons",
    "brain/memory/PATTERNS.md": "recurring operating patterns",
    "brain/memory/INSIGHTS.md": "higher-level learnings",
}
OLLAMA_BASE = "http://localhost:11434"
CURATION_LOG = "blood/logs/memory_curation.jsonl"
CURATION_REPORT = "blood/logs/memory_curation_report.md"


def ask_ollama(prompt: str, model: str = "suneelworkspace", timeout: int = 180) -> str:
    try:
        from lab.autolab.context_injector import ask_ollama_with_context
        return ask_ollama_with_context(prompt, model=model, task_type="general",
                                       timeout=timeout, temperature=0.3, num_ctx=8192)
    except ImportError:
        pass
    payload = json.dumps({
        "model": model,
        "prompt": prompt,
        "stream": False,
        "options": {"temperature": 0.3, "num_ctx": 8192}
    }).encode()
    req = urllib.request.Request(
        f"{OLLAMA_BASE}/api/generate",
        data=payload,
        headers={"Content-Type": "application/json"},
        method="POST"
    )
    try:
        with urllib.request.urlopen(req, timeout=timeout) as r:
            return json.loads(r.read()).get("response", "").strip()
    except Exception:
        return ""


def read_recent_session_data() -> str:
    """Read recent session handoffs and nerve events for context."""
    context = []

    handoff_path = "brain/memory/SESSION_HANDOFF.md"
    if os.path.exists(handoff_path):
        content = open(handoff_path).read()[-2000:]
        context.append(f"Recent session handoff:\n{content}")

    nerve_log = "blood/logs/nerve_events.jsonl"
    if os.path.exists(nerve_log):
        events = []
        with open(nerve_log) as f:
            for line in f.readlines()[-20:]:
                try:
                    events.append(json.loads(line))
                except Exception:
                    pass
        if events:
            event_text = "\n".join([
                f"- {e.get('source_organ','?')} -> {e.get('change_type','?')}: {e.get('details','')}"
                for e in events
            ])
            context.append(f"Recent nerve events:\n{event_text}")

    suggestions_path = "blood/logs/ollama_suggestions.md"
    if os.path.exists(suggestions_path):
        content = open(suggestions_path).read()[-1000:]
        context.append(f"Recent Ollama suggestions:\n{content}")

    return "\n\n".join(context)


def curate_memory_file(filepath: str, file_purpose: str, recent_context: str) -> dict:
    """Curate a single memory file."""
    if not os.path.exists(filepath):
        return {"status": "file_not_found"}

    content = open(filepath).read()

    prompt = f"""You are curating a memory file for SuneelWorkSpace.

File: {filepath}
Purpose: {file_purpose}

Current content:
{content[:3000]}

Recent workspace activity:
{recent_context[:2000]}

Analyze this memory file and:
1. Find STALE entries (outdated, no longer true, superseded)
2. Find CONTRADICTIONS (entries that conflict with each other or recent activity)
3. Find MISSING insights (important things from recent activity not yet captured)
4. Suggest ADDITIONS (new facts/decisions/patterns worth remembering)

Respond in JSON only:
{{
  "stale_entries": [
    {{"text": "exact text that is stale", "reason": "why it's stale"}}
  ],
  "contradictions": [
    {{"entry1": "...", "entry2": "...", "resolution": "which is correct"}}
  ],
  "missing_insights": [
    {{"insight": "what should be added", "category": "fact|decision|pattern|insight"}}
  ],
  "additions": [
    "## New Entry\\n\\nContent to add to the file"
  ],
  "overall_health": "good|fair|poor",
  "summary": "one sentence"
}}"""

    response = ask_ollama(prompt, model="llama3.1")
    if not response:
        return {"status": "ollama_error"}

    try:
        match = re.search(r'\{.*\}', response, re.DOTALL)
        if match:
            result = json.loads(match.group())
            result["filepath"] = filepath
            result["curated_at"] = datetime.now(timezone.utc).isoformat()
            return result
    except Exception:
        pass
    return {"status": "parse_error"}


def apply_curation(filepath: str, curation: dict) -> int:
    """Apply safe curation changes — only appending, never deleting."""
    if not os.path.exists(filepath):
        return 0

    additions = curation.get("additions", [])
    if not additions:
        return 0

    with open(filepath, "a") as f:
        f.write("\n\n---\n*Added by memory curator — " +
                datetime.now().strftime("%Y-%m-%d") + "*\n\n")
        for addition in additions[:3]:  # Max 3 additions per run
            f.write(addition + "\n\n")
    return len(additions[:3])


def run_memory_curation() -> dict:
    """Run full memory curation cycle."""
    print("Memory Curator starting...")

    recent_context = read_recent_session_data()
    total_changes = 0
    all_curations = []

    for filepath, purpose in MEMORY_FILES.items():
        print(f"  Curating {filepath}...")
        curation = curate_memory_file(filepath, purpose, recent_context)

        if curation.get("status"):
            print(f"    {curation['status']}")
            continue

        stale = len(curation.get("stale_entries", []))
        missing = len(curation.get("missing_insights", []))
        additions = len(curation.get("additions", []))
        quality = curation.get("overall_health", "?")

        print(f"    Quality: {quality} | Stale: {stale} | Missing: {missing} | Additions: {additions}")

        changes = apply_curation(filepath, curation)
        total_changes += changes

        all_curations.append(curation)

        os.makedirs(os.path.dirname(CURATION_LOG), exist_ok=True)
        with open(CURATION_LOG, "a") as f:
            f.write(json.dumps({
                "timestamp": datetime.now(timezone.utc).isoformat(),
                "filepath": filepath,
                "stale_count": stale,
                "missing_count": missing,
                "additions_applied": changes,
                "quality": quality,
                "summary": curation.get("summary", ""),
            }) + "\n")

    report_lines = [
        f"# Memory Curation Report — {datetime.now().strftime('%Y-%m-%d %H:%M')}",
        f"",
        f"**Files curated:** {len(all_curations)} | **Changes applied:** {total_changes}",
        f"",
    ]
    for c in all_curations:
        report_lines.append(f"## {c.get('filepath', '?')}")
        report_lines.append(f"*{c.get('summary', '')}*")
        for entry in c.get("stale_entries", [])[:3]:
            report_lines.append(f"- Stale: {entry.get('reason', '')}")
        for insight in c.get("missing_insights", [])[:3]:
            report_lines.append(f"- Missing: {insight.get('insight', '')}")
        report_lines.append("")

    os.makedirs(os.path.dirname(CURATION_REPORT), exist_ok=True)
    with open(CURATION_REPORT, "w") as f:
        f.write("\n".join(report_lines))

    print(f"\nMemory curation complete — {total_changes} changes applied")
    print(f"   Report: {CURATION_REPORT}")

    return {"files_curated": len(all_curations), "changes_applied": total_changes}


if __name__ == "__main__":
    run_memory_curation()
