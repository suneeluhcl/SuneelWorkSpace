"""
lab/autolab/log_learn_engine.py
Parses execution_history.jsonl and repair_loop.jsonl to extract successful
code repairs, groups them by error type, and compiles new training pairs
into dna/agents/hermes/ollama_models/training_data.jsonl.

Safe to re-run: deduplicates by (error_type, fix_summary) before appending.
"""

import json
import os
import re
import sys
from datetime import datetime, timezone
from pathlib import Path

WORKSPACE = Path(os.path.expanduser("~/SuneelWorkSpace"))
EXEC_HISTORY = WORKSPACE / "blood/logs/execution_history.jsonl"
REPAIR_LOG = WORKSPACE / "blood/logs/repair_loop.jsonl"
TRAINING_DATA = WORKSPACE / "dna/agents/hermes/ollama_models/training_data.jsonl"
LEARN_LOG = WORKSPACE / "blood/logs/log_learn_engine.jsonl"
EVOLVE_LOG = WORKSPACE / "blood/logs/daily_evolve.jsonl"
LESSONS_MD = WORKSPACE / "brain/memory/LESSONS.md"
LESSONS_JSON = WORKSPACE / "lab/autolab/meta/lessons.json"


def _read_jsonl(path: Path) -> list[dict]:
    if not path.exists():
        return []
    records = []
    for line in path.read_text(errors="ignore").splitlines():
        line = line.strip()
        if not line:
            continue
        try:
            records.append(json.loads(line))
        except json.JSONDecodeError:
            continue
    return records


def _load_existing_pairs() -> set[str]:
    """Return set of dedup keys for already-known training pairs."""
    if not TRAINING_DATA.exists():
        return set()
    keys: set[str] = set()
    for line in TRAINING_DATA.read_text(errors="ignore").splitlines():
        try:
            rec = json.loads(line)
            key = (rec.get("input", "")[:80] + "|" + rec.get("output", "")[:80])
            keys.add(key)
        except Exception:
            continue
    return keys


def _classify_error(text: str) -> str:
    """Classify an error message into a category string."""
    t = text.lower()
    if "importerror" in t or "modulenotfounderror" in t:
        return "import_error"
    if "assertionerror" in t or "assert" in t:
        return "assertion_error"
    if "typeerror" in t:
        return "type_error"
    if "attributeerror" in t:
        return "attribute_error"
    if "keyerror" in t:
        return "key_error"
    if "filenotfounderror" in t or "no such file" in t:
        return "file_not_found"
    if "syntaxerror" in t:
        return "syntax_error"
    if "permissionerror" in t:
        return "permission_error"
    if "connectionerror" in t or "timeout" in t:
        return "connection_error"
    return "general_error"


def _extract_from_repair_log(records: list[dict]) -> list[dict]:
    """Extract successful fix pairs from repair_loop.jsonl."""
    pairs: list[dict] = []
    # Pair up: repair_start → test_result(after_repair=True, passed=True)
    pending: dict[str, dict] = {}

    for rec in records:
        rtype = rec.get("type", "")
        organ = rec.get("organ", "unknown")

        if rtype == "test_result" and not rec.get("after_repair"):
            if not rec.get("passed"):
                pending[organ] = rec

        elif rtype == "test_result" and rec.get("after_repair") and rec.get("passed"):
            failed = pending.pop(organ, None)
            if failed:
                error_text = failed.get("output", "") or failed.get("stdout", "")
                error_type = _classify_error(error_text)
                pairs.append({
                    "source": "repair_loop",
                    "error_type": error_type,
                    "organ": organ,
                    "input": (
                        f"Tests were failing in the {organ} organ with this output:\n"
                        f"{error_text[:400]}\n\nWhat SAFE fix should be applied?"
                    ),
                    "output": (
                        f"The repair loop successfully fixed the {organ} organ. "
                        f"Error type: {error_type}. After applying SAFE fixes, "
                        "all tests passed."
                    ),
                })
    return pairs


def _extract_from_exec_history(records: list[dict]) -> list[dict]:
    """Extract successful pipeline execution pairs from execution_history.jsonl."""
    pairs: list[dict] = []
    for rec in records:
        stage = rec.get("stage", "")
        status = rec.get("status", "")
        output = rec.get("output", "") or rec.get("result", "") or ""
        command = rec.get("command", "") or rec.get("action", "")

        if status in ("success", "completed", "passed") and command and output:
            pairs.append({
                "source": "execution_history",
                "error_type": "none",
                "stage": stage,
                "input": (
                    f"In SuneelWorkSpace pipeline stage '{stage}', the command "
                    f"'{command}' was run. What was the expected outcome?"
                ),
                "output": (
                    f"Command '{command}' completed successfully. "
                    f"Output: {str(output)[:300]}"
                ),
            })
    return pairs


def _append_new_pairs(new_pairs: list[dict], existing_keys: set[str]) -> int:
    TRAINING_DATA.parent.mkdir(parents=True, exist_ok=True)
    added = 0
    with open(TRAINING_DATA, "a") as f:
        for pair in new_pairs:
            key = (pair.get("input", "")[:80] + "|" + pair.get("output", "")[:80])
            if key in existing_keys:
                continue
            existing_keys.add(key)
            pair["ts"] = datetime.now(timezone.utc).isoformat()
            f.write(json.dumps(pair) + "\n")
            added += 1
    return added


def _extract_lessons(repair_pairs: list[dict], evolve_records: list[dict]) -> list[dict]:
    """Distill durable lessons: recurring error types and repeatedly failing evolve passes."""
    lessons: list[dict] = []

    error_counts: dict[str, int] = {}
    for pair in repair_pairs:
        et = pair.get("error_type", "general_error")
        if et != "none":
            error_counts[et] = error_counts.get(et, 0) + 1
    for et, count in sorted(error_counts.items(), key=lambda x: -x[1]):
        if count >= 2:
            lessons.append({
                "key": f"recurring_error:{et}",
                "lesson": (
                    f"`{et}` was auto-repaired {count} times. Recurring repairs "
                    "signal a root cause worth a permanent fix instead of re-healing."
                ),
            })

    pass_failures: dict[str, int] = {}
    for rec in evolve_records:
        for p in rec.get("passes", []):
            if p.get("status") in ("failed", "timeout", "error"):
                name = p.get("pass", "unknown")
                pass_failures[name] = pass_failures.get(name, 0) + 1
    for name, count in sorted(pass_failures.items(), key=lambda x: -x[1]):
        if count >= 2:
            lessons.append({
                "key": f"failing_pass:{name}",
                "lesson": (
                    f"Nightly pass `{name}` failed {count} times in daily_evolve. "
                    "Inspect its script and last output before the next cycle."
                ),
            })
    return lessons


def _write_lessons(lessons: list[dict]) -> int:
    """Append only-new lessons to LESSONS.md, deduplicated via LESSONS_JSON keys."""
    known: dict = {}
    if LESSONS_JSON.exists():
        try:
            known = json.loads(LESSONS_JSON.read_text())
        except Exception:
            known = {}
    seen: set[str] = set(known.get("keys", []))
    fresh = [l for l in lessons if l["key"] not in seen]
    if not fresh:
        return 0

    today = datetime.now(timezone.utc).strftime("%Y-%m-%d")
    LESSONS_MD.parent.mkdir(parents=True, exist_ok=True)
    header = "" if LESSONS_MD.exists() else (
        "# Lessons\n\nStructured lessons distilled nightly from logs by "
        "`lab/autolab/log_learn_engine.py`. Append-only.\n"
    )
    with open(LESSONS_MD, "a") as f:
        f.write(header + f"\n## {today} — log-learn digest\n\n")
        for l in fresh:
            f.write(f"- {l['lesson']}\n")
            seen.add(l["key"])

    LESSONS_JSON.parent.mkdir(parents=True, exist_ok=True)
    known["keys"] = sorted(seen)
    known["updated_at"] = datetime.now(timezone.utc).isoformat()
    LESSONS_JSON.write_text(json.dumps(known, indent=2))
    return len(fresh)


def run() -> dict:
    existing_keys = _load_existing_pairs()
    before = len(existing_keys)

    repair_records = _read_jsonl(REPAIR_LOG)
    exec_records = _read_jsonl(EXEC_HISTORY)

    repair_pairs = _extract_from_repair_log(repair_records)
    exec_pairs = _extract_from_exec_history(exec_records)
    all_pairs = repair_pairs + exec_pairs

    added = _append_new_pairs(all_pairs, existing_keys)

    evolve_records = _read_jsonl(EVOLVE_LOG)
    lessons = _extract_lessons(repair_pairs, evolve_records)
    lessons_added = _write_lessons(lessons)

    result = {
        "ts": datetime.now(timezone.utc).isoformat(),
        "repair_records_scanned": len(repair_records),
        "exec_records_scanned": len(exec_records),
        "candidates": len(all_pairs),
        "new_pairs_added": added,
        "total_training_pairs": before + added,
        "lessons_added": lessons_added,
    }

    # Append to learn log
    LEARN_LOG.parent.mkdir(parents=True, exist_ok=True)
    with open(LEARN_LOG, "a") as f:
        f.write(json.dumps(result) + "\n")

    return result


if __name__ == "__main__":
    result = run()
    print(f"[log-learn] scanned {result['repair_records_scanned']} repair + "
          f"{result['exec_records_scanned']} exec records")
    print(f"[log-learn] added {result['new_pairs_added']} new training pairs "
          f"(total: {result['total_training_pairs']})")
