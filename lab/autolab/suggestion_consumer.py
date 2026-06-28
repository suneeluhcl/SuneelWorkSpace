"""
suggestion_consumer.py
Closes the Ollama output→action gap.
Reads suggestions from repair/security/review engines and converts them into
real tasks or queues them for human review.
Run: consume-suggestions
"""

import json
import os
import re
import sys
from datetime import datetime, timezone

WORKSPACE = os.path.expanduser("~/SuneelWorkSpace")
sys.path.insert(0, WORKSPACE)

SUGGESTION_SOURCES = [
    ("blood/logs/ollama_suggestions.md", "repair_engine"),
    ("blood/logs/code_review_report.md", "code_review"),
]
TASK_QUEUE = "heart/tasks/TASK_QUEUE.md"
CONSUMED_LOG = "blood/logs/suggestion_consumer.jsonl"
CONTROLLED_QUEUE = "blood/logs/suggestion_controlled_queue.json"

SAFE_CONFIDENCE_THRESHOLD = 0.75
AUTO_APPLY_LEVELS = {"SAFE"}


def _read(path: str) -> str:
    full = os.path.join(WORKSPACE, path)
    return open(full).read() if os.path.exists(full) else ""


def _append_log(entry: dict):
    path = os.path.join(WORKSPACE, CONSUMED_LOG)
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, "a") as f:
        f.write(json.dumps(entry) + "\n")


def _queue_controlled(item: dict):
    path = os.path.join(WORKSPACE, CONTROLLED_QUEUE)
    try:
        existing = json.load(open(path)) if os.path.exists(path) else []
    except Exception:
        existing = []
    existing.append({**item, "queued_at": datetime.now(timezone.utc).isoformat()})
    json.dump(existing, open(path, "w"), indent=2)


def parse_suggestions_md(content: str, source: str) -> list[dict]:
    """Parse suggestion markdown blocks into structured dicts."""
    suggestions = []
    blocks = re.split(r"^## Suggestion \d+", content, flags=re.MULTILINE)
    for block in blocks[1:]:
        fix_m = re.search(r"\*\*Fix\*\*:\s*`?([^`\n]+)`?", block)
        conf_m = re.search(r"\*\*Confidence\*\*:\s*([\d.]+)", block)
        level_m = re.search(r"\*\*Level\*\*:\s*(\w+)", block)
        organ_m = re.search(r"\*\*Organ\*\*:\s*(\w+)", block)
        detail_m = re.search(r"\*\*Detail\*\*:\s*(.+)", block)
        if fix_m:
            suggestions.append({
                "fix": fix_m.group(1).strip(),
                "confidence": float(conf_m.group(1)) if conf_m else 0.5,
                "level": level_m.group(1).upper() if level_m else "CONTROLLED",
                "organ": organ_m.group(1) if organ_m else "unknown",
                "detail": detail_m.group(1).strip() if detail_m else "",
                "source": source,
            })

    # Also parse improvement ideas section
    ideas_section = re.search(r"## Improvement Ideas\n(.*?)(?=\n##|\Z)", content, re.DOTALL)
    if ideas_section:
        for line in ideas_section.group(1).strip().split("\n"):
            idea_m = re.match(r"-\s+\*\*(\w+)\*\*\s+\[(\w+)\]:\s+(.+)", line)
            if idea_m:
                suggestions.append({
                    "fix": idea_m.group(3).strip()[:100],
                    "confidence": 0.6,
                    "level": "CONTROLLED",
                    "organ": idea_m.group(1).lower(),
                    "detail": f"Size: {idea_m.group(2)}",
                    "source": source,
                })
    return suggestions


def append_to_task_queue(suggestion: dict):
    """Add an actionable task to the task queue markdown."""
    path = os.path.join(WORKSPACE, TASK_QUEUE)
    os.makedirs(os.path.dirname(path), exist_ok=True)
    ts = datetime.now(timezone.utc).strftime("%Y-%m-%d")
    task_line = (
        f"\n- [{ts}] **[AUTO]** {suggestion['fix']} "
        f"(organ: {suggestion['organ']}, confidence: {suggestion['confidence']:.0%}, "
        f"source: {suggestion['source']})"
    )
    if os.path.exists(path):
        content = open(path).read()
        # Don't add duplicates
        if suggestion["fix"][:40] in content:
            return False
    with open(path, "a") as f:
        f.write(task_line + "\n")
    return True


def notify_nerve(organ: str, detail: str):
    try:
        from nervous.nerve_propagator import notify_change
        notify_change(organ, "suggestion_consumed", detail)
    except Exception:
        pass


def consume_suggestions(dry_run: bool = False) -> dict:
    results = {
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "total_parsed": 0,
        "tasks_created": 0,
        "controlled_queued": 0,
        "skipped_low_confidence": 0,
    }

    all_suggestions = []
    for rel_path, source in SUGGESTION_SOURCES:
        content = _read(rel_path)
        if content:
            parsed = parse_suggestions_md(content, source)
            all_suggestions.extend(parsed)
            print(f"  Parsed {len(parsed)} suggestions from {rel_path}")

    results["total_parsed"] = len(all_suggestions)

    for s in all_suggestions:
        if s["confidence"] < SAFE_CONFIDENCE_THRESHOLD:
            results["skipped_low_confidence"] += 1
            continue

        if s["level"] in AUTO_APPLY_LEVELS and s["confidence"] >= SAFE_CONFIDENCE_THRESHOLD:
            if not dry_run:
                added = append_to_task_queue(s)
                if added:
                    results["tasks_created"] += 1
                    notify_nerve(s.get("organ", "lab"), s["fix"][:60])
                    print(f"  → Task created: {s['fix'][:60]}")
                    _append_log({**s, "action": "task_created"})
        else:
            if not dry_run:
                _queue_controlled(s)
                results["controlled_queued"] += 1
                print(f"  → Queued (controlled): {s['fix'][:60]}")
                _append_log({**s, "action": "controlled_queued"})

    if not dry_run:
        _append_log({**results, "type": "run_summary"})

    print(f"\nDone: {results['tasks_created']} tasks created, "
          f"{results['controlled_queued']} queued for review, "
          f"{results['skipped_low_confidence']} skipped (low confidence)")
    return results


if __name__ == "__main__":
    import argparse
    parser = argparse.ArgumentParser()
    parser.add_argument("--dry-run", action="store_true")
    args = parser.parse_args()
    print("Consuming Ollama suggestions...\n")
    consume_suggestions(dry_run=args.dry_run)
