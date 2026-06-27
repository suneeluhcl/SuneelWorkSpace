#!/usr/bin/env python3
"""Ingest feedback .md files → JSONL training records → lab/autolab/training_data/."""

import json
import re
import shutil
import sys
from datetime import datetime, timezone
from pathlib import Path

INBOX = Path(__file__).parent / "inbox"
PROCESSED = Path(__file__).parent / "processed"
TRAINING_DATA = Path(__file__).parent.parent.parent / "autolab" / "training_data"

# Known agents for tagging
KNOWN_AGENTS = {"claude", "codex", "gemini", "opencode", "copilot"}
KNOWN_OUTCOMES = {"good", "bad", "partial", "wrong", "excellent", "poor"}
KNOWN_INTENTS = {
    "code_review", "code_edit", "research", "planning", "debug",
    "refactor", "explain", "write", "test", "deploy", "health_check",
}


def _extract_tags(content: str, filename: str) -> dict:
    """Extract agent/intent/outcome from frontmatter or content heuristics."""
    tags = {"agent": "unknown", "intent": "unknown", "outcome": "partial", "notes": ""}

    # Try YAML-style frontmatter
    fm_match = re.search(r"^---\n(.*?)\n---", content, re.DOTALL)
    if fm_match:
        for line in fm_match.group(1).splitlines():
            if ":" in line:
                k, _, v = line.partition(":")
                k, v = k.strip().lower(), v.strip().lower()
                if k in ("agent",) and v in KNOWN_AGENTS:
                    tags["agent"] = v
                elif k in ("intent", "task_type") and v in KNOWN_INTENTS:
                    tags["intent"] = v
                elif k in ("outcome", "rating") and v in KNOWN_OUTCOMES:
                    tags["outcome"] = "success" if v in ("good", "excellent") else \
                                      "fail" if v in ("bad", "wrong", "poor") else "partial"

    # Fallback: scan content for agent mentions
    lower = content.lower()
    for agent in KNOWN_AGENTS:
        if agent in lower:
            tags["agent"] = agent
            break
    for intent in KNOWN_INTENTS:
        if intent.replace("_", " ") in lower or intent in lower:
            tags["intent"] = intent
            break

    # Use filename hints
    for part in re.split(r"[_\-\s]", filename.lower()):
        if part in KNOWN_AGENTS:
            tags["agent"] = part
        if part in KNOWN_OUTCOMES:
            tags["outcome"] = "success" if part in ("good", "excellent") else \
                              "fail" if part in ("bad", "wrong", "poor") else "partial"

    # Extract free-text notes (first non-frontmatter paragraph)
    body = re.sub(r"^---\n.*?\n---\n", "", content, flags=re.DOTALL).strip()
    tags["notes"] = body[:500]
    return tags


def ingest_file(path: Path) -> dict:
    content = path.read_text(encoding="utf-8")
    tags = _extract_tags(content, path.stem)

    record = {
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "source_file": path.name,
        "agent": tags["agent"],
        "intent": tags["intent"],
        "outcome": tags["outcome"],
        "notes": tags["notes"],
        "raw_content": content,
    }

    # Write JSONL record
    TRAINING_DATA.mkdir(parents=True, exist_ok=True)
    ts = datetime.now(timezone.utc).strftime("%Y%m%d_%H%M%S")
    out_path = TRAINING_DATA / f"feedback_{ts}_{path.stem}.jsonl"
    out_path.write_text(json.dumps(record) + "\n")

    # Archive source
    PROCESSED.mkdir(parents=True, exist_ok=True)
    shutil.move(str(path), PROCESSED / path.name)

    return record


def run_all() -> list[dict]:
    INBOX.mkdir(parents=True, exist_ok=True)
    pending = list(INBOX.glob("*.md"))
    if not pending:
        print("No feedback files in inbox.")
        return []

    results = []
    for p in pending:
        rec = ingest_file(p)
        print(f"  ingested: {p.name} → agent={rec['agent']} intent={rec['intent']} outcome={rec['outcome']}")
        results.append(rec)
    return results


def status() -> None:
    INBOX.mkdir(parents=True, exist_ok=True)
    PROCESSED.mkdir(parents=True, exist_ok=True)
    pending = list(INBOX.glob("*.md"))
    processed = list(PROCESSED.glob("*.md"))
    training = list(TRAINING_DATA.glob("*.jsonl")) if TRAINING_DATA.exists() else []
    print(f"Inbox:         {len(pending)} pending")
    print(f"Processed:     {len(processed)} archived")
    print(f"Training data: {len(training)} records")


def main() -> None:
    if len(sys.argv) > 1 and sys.argv[1] == "status":
        status()
    else:
        records = run_all()
        if records:
            print(f"\n{len(records)} feedback record(s) ingested → lab/autolab/training_data/")
            print("Run 'autolab-run' to trigger eval cycle.")


if __name__ == "__main__":
    main()
