#!/usr/bin/env python3
"""
dna/agents/hermes/ollama_models/autotrainer.py

Workspace auto-trainer dataset builder.

Extracts instruction–response pairs from:
  1. Git commits (last 300) → workspace-action pairs
  2. blood/logs/daily_improvements.md → improvement description pairs
  3. blood/logs/repair_loop.jsonl → failure→fix instruction pairs
  4. nerve.json files → organ dependency knowledge pairs
  5. brain/memory/DECISIONS.md → architecture decision pairs
  6. skeleton/rules/*.md → safety rule knowledge pairs

Writes output to:
  dna/agents/hermes/ollama_models/training_dataset.json
  (standard instruction/response format + Ollama messages format)

Also regenerates training_data.jsonl (Ollama fine-tune JSONL) by merging
the existing file with new pairs (deduped by instruction text).

CLI:
    python3 dna/agents/hermes/ollama_models/autotrainer.py
    python3 dna/agents/hermes/ollama_models/autotrainer.py --stats
    python3 dna/agents/hermes/ollama_models/autotrainer.py --merge-only
"""

import json
import os
import re
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path

WORKSPACE = Path(os.path.expanduser("~/SuneelWorkSpace"))
MODEL_DIR = WORKSPACE / "dna/agents/hermes/ollama_models"
DATASET_JSON = MODEL_DIR / "training_dataset.json"
TRAINING_JSONL = MODEL_DIR / "training_data.jsonl"

SYSTEM_PROMPT = (
    "You are the SuneelWorkSpace AI — a specialized intelligence engine built into "
    "Suneel Bikkasani's living, self-maintaining local AI workspace on macOS M4 Max. "
    "You know the 12-organ architecture (brain, heart, eyes, ears, nervous, skeleton, "
    "blood, hands, mouth, dna, lab, spine), the safety boundaries, all active agents, "
    "and workspace state. Be direct, concise, and actionable."
)

ORGANS = [
    "brain", "heart", "eyes", "ears", "nervous",
    "skeleton", "blood", "hands", "mouth", "dna", "lab", "spine",
]


# ── source extractors ──────────────────────────────────────────────────────────

def _from_git_commits(limit: int = 300) -> list[dict]:
    """git commit messages → workspace-action pairs."""
    try:
        r = subprocess.run(
            ["git", "log", f"--max-count={limit}", "--pretty=format:%s|||%b", "--no-merges"],
            cwd=WORKSPACE, capture_output=True, text=True, timeout=30
        )
    except Exception:
        return []

    pairs = []
    for line in r.stdout.strip().splitlines():
        if "|||" not in line:
            continue
        subject, _, body = line.partition("|||")
        subject = subject.strip()
        body = body.strip()
        if not subject or subject.startswith("chore(readme)"):
            continue
        response = subject
        if body:
            response = f"{subject}\n\n{body[:300]}"
        pairs.append(_make_pair(
            f"What workspace change does this commit represent: '{subject}'?",
            response,
        ))
    return pairs


def _from_daily_improvements() -> list[dict]:
    """blood/logs/daily_improvements.md → improvement pairs."""
    p = WORKSPACE / "blood/logs/daily_improvements.md"
    if not p.exists():
        return []
    content = p.read_text(encoding="utf-8", errors="ignore")
    blocks = re.split(r"^#+\s+", content, flags=re.MULTILINE)
    pairs = []
    for block in blocks[1:]:
        lines = block.strip().splitlines()
        if not lines:
            continue
        title = lines[0].strip()
        body = "\n".join(lines[1:]).strip()
        if len(title) < 5 or not body:
            continue
        pairs.append(_make_pair(
            f"How was this workspace improvement implemented: '{title}'?",
            body[:500],
        ))
    return pairs


def _from_repair_log() -> list[dict]:
    """blood/logs/repair_loop.jsonl → failure→fix pairs."""
    p = WORKSPACE / "blood/logs/repair_loop.jsonl"
    if not p.exists():
        return []
    pairs = []
    for line in p.read_text(encoding="utf-8", errors="ignore").splitlines():
        try:
            record = json.loads(line)
        except Exception:
            continue
        fixes = record.get("fixes_applied_details", record.get("fixes", []))
        failures = record.get("failures", [])
        if not fixes or not failures:
            continue
        for failure in failures[:3]:
            test = failure.get("test", "")
            message = failure.get("message", "")
            if not test:
                continue
            for fix in fixes[:2]:
                root_cause = fix.get("root_cause", "")
                fix_type = fix.get("fix_type", "")
                target = fix.get("target_path", "")
                if root_cause and fix_type:
                    pairs.append(_make_pair(
                        f"A test failed: '{test}'. Error: {message[:200]}. How do you fix it?",
                        f"Root cause: {root_cause}. Fix: {fix_type} on {target}.".strip(". "),
                    ))
    return pairs


def _from_nerve_json() -> list[dict]:
    """nerve.json files → organ dependency knowledge pairs."""
    pairs = []
    for organ in ORGANS:
        p = WORKSPACE / organ / "nerve.json"
        if not p.exists():
            continue
        try:
            nerve = json.loads(p.read_text())
        except Exception:
            continue
        listens = nerve.get("listens_from", [])
        publishes = nerve.get("publishes_to", nerve.get("events", []))
        if listens:
            pairs.append(_make_pair(
                f"What organs does '{organ}' listen to / depend on?",
                f"The '{organ}' organ listens from: {', '.join(listens) if isinstance(listens, list) else listens}.",
            ))
        if publishes:
            pub_list = publishes if isinstance(publishes, list) else [publishes]
            pairs.append(_make_pair(
                f"What events or organs does '{organ}' publish or notify?",
                f"The '{organ}' organ publishes/notifies: {', '.join(str(x) for x in pub_list[:5])}.",
            ))
    return pairs


def _from_decisions() -> list[dict]:
    """brain/memory/DECISIONS.md → architecture decision pairs."""
    p = WORKSPACE / "brain/memory/DECISIONS.md"
    if not p.exists():
        return []
    content = p.read_text(encoding="utf-8", errors="ignore")
    # Split on decision headers (## Decision N or ## Title)
    blocks = re.split(r"^#{2,3}\s+", content, flags=re.MULTILINE)
    pairs = []
    for block in blocks[1:]:
        lines = block.strip().splitlines()
        if not lines:
            continue
        title = lines[0].strip()
        body = "\n".join(lines[1:]).strip()
        if len(title) < 8 or not body:
            continue
        pairs.append(_make_pair(
            f"What is the architectural decision about '{title}'?",
            body[:600],
        ))
    return pairs


def _from_safety_rules() -> list[dict]:
    """skeleton/rules/*.md → safety boundary knowledge pairs."""
    rules_dir = WORKSPACE / "skeleton/rules"
    if not rules_dir.exists():
        return []
    pairs = []
    for md_file in rules_dir.glob("*.md"):
        content = md_file.read_text(encoding="utf-8", errors="ignore")
        pairs.append(_make_pair(
            f"What are the rules and constraints defined in '{md_file.name}'?",
            content[:800],
        ))
    return pairs


# ── pair factory ───────────────────────────────────────────────────────────────

def _make_pair(instruction: str, response: str) -> dict:
    return {
        "instruction": instruction.strip(),
        "response": response.strip(),
        "messages": [
            {"role": "system",    "content": SYSTEM_PROMPT},
            {"role": "user",      "content": instruction.strip()},
            {"role": "assistant", "content": response.strip()},
        ],
    }


# ── deduplication ──────────────────────────────────────────────────────────────

def _dedupe(pairs: list[dict]) -> list[dict]:
    seen: set[str] = set()
    out: list[dict] = []
    for p in pairs:
        key = p["instruction"][:120].lower().strip()
        if key not in seen:
            seen.add(key)
            out.append(p)
    return out


# ── main build ─────────────────────────────────────────────────────────────────

def build() -> dict:
    """Collect all training pairs, deduplicate, write outputs."""
    all_pairs: list[dict] = []

    sources = [
        ("git_commits",       _from_git_commits),
        ("daily_improvements", _from_daily_improvements),
        ("repair_log",         _from_repair_log),
        ("nerve_json",         _from_nerve_json),
        ("decisions",          _from_decisions),
        ("safety_rules",       _from_safety_rules),
    ]

    counts: dict[str, int] = {}
    for name, fn in sources:
        try:
            extracted = fn()
            counts[name] = len(extracted)
            all_pairs.extend(extracted)
        except Exception as e:
            counts[name] = 0
            print(f"  [autotrainer] {name} failed: {e}")

    deduped = _dedupe(all_pairs)

    # Write training_dataset.json (standard instruction/response JSON)
    MODEL_DIR.mkdir(parents=True, exist_ok=True)
    dataset = {
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "total_pairs": len(deduped),
        "source_counts": counts,
        "system_prompt": SYSTEM_PROMPT,
        "pairs": deduped,
    }
    DATASET_JSON.write_text(json.dumps(dataset, indent=2, ensure_ascii=False))

    # Merge into training_data.jsonl (Ollama JSONL format)
    # Load existing JSONL to avoid overwriting hand-crafted pairs
    existing_keys: set[str] = set()
    existing_lines: list[str] = []
    if TRAINING_JSONL.exists():
        for line in TRAINING_JSONL.read_text(encoding="utf-8", errors="ignore").splitlines():
            try:
                rec = json.loads(line)
                msgs = rec.get("messages", [])
                user_msg = next((m["content"] for m in msgs if m.get("role") == "user"), "")
                existing_keys.add(user_msg[:120].lower().strip())
                existing_lines.append(line)
            except Exception:
                pass

    new_lines = []
    for pair in deduped:
        key = pair["instruction"][:120].lower().strip()
        if key not in existing_keys:
            new_lines.append(json.dumps({"messages": pair["messages"]}, ensure_ascii=False))

    with TRAINING_JSONL.open("a", encoding="utf-8") as f:
        for line in new_lines:
            f.write(line + "\n")

    return {
        "total_new_pairs": len(deduped),
        "merged_into_jsonl": len(new_lines),
        "source_counts": counts,
        "dataset_path": str(DATASET_JSON),
        "jsonl_path": str(TRAINING_JSONL),
    }


def stats() -> dict:
    result: dict = {}
    if DATASET_JSON.exists():
        try:
            data = json.loads(DATASET_JSON.read_text())
            result["dataset_pairs"] = data.get("total_pairs", 0)
            result["dataset_generated_at"] = data.get("generated_at", "?")
            result["source_counts"] = data.get("source_counts", {})
        except Exception:
            pass
    if TRAINING_JSONL.exists():
        result["jsonl_lines"] = sum(1 for _ in TRAINING_JSONL.read_text().splitlines() if _.strip())
    return result


# ── CLI ────────────────────────────────────────────────────────────────────────

def main() -> None:
    import argparse
    parser = argparse.ArgumentParser(description="SuneelWorkSpace auto-trainer dataset builder")
    parser.add_argument("--stats", action="store_true", help="Show current dataset stats")
    parser.add_argument("--merge-only", action="store_true", help="Skip extraction, just merge")
    args = parser.parse_args()

    if args.stats:
        s = stats()
        if not s:
            print("[autotrainer] no dataset built yet — run without --stats first")
            return
        print(f"[autotrainer] dataset: {s.get('dataset_pairs', 0)} pairs "
              f"(built {s.get('dataset_generated_at', '?')})")
        print(f"[autotrainer] training_data.jsonl: {s.get('jsonl_lines', 0)} lines")
        for src, n in s.get("source_counts", {}).items():
            print(f"  {src:25s} {n}")
        return

    print("[autotrainer] building training dataset…")
    result = build()
    print(f"[autotrainer] done — {result['total_new_pairs']} pairs extracted, "
          f"{result['merged_into_jsonl']} new lines added to JSONL")
    print(f"  dataset → {result['dataset_path']}")
    print(f"  jsonl   → {result['jsonl_path']}")
    for src, n in result["source_counts"].items():
        print(f"  {src:25s} {n} pairs")


if __name__ == "__main__":
    main()
