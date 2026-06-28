"""
build_training_data.py
Builds a JSONL training dataset from SuneelWorkSpace history:
- git commits → prompt/response pairs
- SESSION_LOG.md → session pairs
- memory curator outputs → curation pairs
- repair engine outputs → repair pairs
Output: dna/agents/hermes/ollama_models/training_data.jsonl
"""

import json
import os
import re
import subprocess
from datetime import datetime, timezone

WORKSPACE = os.path.expanduser("~/SuneelWorkSpace")
OUT = os.path.join(WORKSPACE, "dna/agents/hermes/ollama_models/training_data.jsonl")
SYSTEM_STUB = "You are the SuneelWorkSpace AI — a specialized intelligence engine."


def _git_log_pairs() -> list[dict]:
    """Extract commit messages as workspace-action examples."""
    try:
        result = subprocess.run(
            ["git", "log", "--pretty=format:%H|%s|%b", "--no-merges", "-100"],
            cwd=WORKSPACE, capture_output=True, text=True
        )
        pairs = []
        for line in result.stdout.strip().split("\n"):
            if "|" not in line:
                continue
            parts = line.split("|", 2)
            if len(parts) < 2:
                continue
            sha, subject, body = parts[0], parts[1], parts[2] if len(parts) > 2 else ""
            if not subject.strip():
                continue
            pairs.append({
                "messages": [
                    {"role": "system", "content": SYSTEM_STUB},
                    {"role": "user", "content": f"Summarize what was done in this workspace commit: {subject}"},
                    {"role": "assistant", "content": f"{subject}. {body[:200]}".strip(". ")},
                ]
            })
        return pairs
    except Exception:
        return []


def _repair_log_pairs() -> list[dict]:
    """Extract repair suggestions as examples."""
    path = os.path.join(WORKSPACE, "blood/logs/ollama_suggestions.md")
    if not os.path.exists(path):
        return []
    content = open(path).read()
    blocks = re.split(r"^## Suggestion \d+", content, flags=re.MULTILINE)
    pairs = []
    for block in blocks[1:]:
        fix_m = re.search(r"\*\*Fix\*\*:\s*`?([^`\n]+)`?", block)
        conf_m = re.search(r"\*\*Confidence\*\*:\s*([\d.]+)", block)
        organ_m = re.search(r"\*\*Organ\*\*:\s*(\w+)", block)
        if fix_m:
            pairs.append({
                "messages": [
                    {"role": "system", "content": SYSTEM_STUB},
                    {"role": "user", "content": f"What should be repaired in the {organ_m.group(1) if organ_m else 'workspace'} organ?"},
                    {"role": "assistant", "content": f"**Fix**: {fix_m.group(1).strip()}\n**Confidence**: {conf_m.group(1) if conf_m else '0.8'}\n**Level**: SAFE"},
                ]
            })
    return pairs


def _session_log_pairs() -> list[dict]:
    """Extract session log entries as examples."""
    path = os.path.join(WORKSPACE, "blood/logs/SESSION_LOG.md")
    if not os.path.exists(path):
        return []
    content = open(path).read()
    sessions = re.split(r"^## Session", content, flags=re.MULTILINE)
    pairs = []
    for session in sessions[1:10]:
        summary_m = re.search(r"\*\*Summary\*\*:\s*(.+)", session)
        completed_m = re.findall(r"- (.+)", session)
        if summary_m and completed_m:
            pairs.append({
                "messages": [
                    {"role": "system", "content": SYSTEM_STUB},
                    {"role": "user", "content": "What was accomplished in the latest workspace session?"},
                    {"role": "assistant", "content": f"{summary_m.group(1).strip()}\n\nCompleted:\n" + "\n".join(f"- {c}" for c in completed_m[:5])},
                ]
            })
    return pairs


def _security_pairs() -> list[dict]:
    """Extract security findings as examples."""
    path = os.path.join(WORKSPACE, "blood/logs/security_scan.jsonl")
    if not os.path.exists(path):
        return []
    pairs = []
    for line in open(path).readlines()[-20:]:
        try:
            entry = json.loads(line)
            if entry.get("issues"):
                for issue in entry["issues"][:3]:
                    pairs.append({
                        "messages": [
                            {"role": "system", "content": SYSTEM_STUB},
                            {"role": "user", "content": f"Review {issue.get('file', 'this file')} for security issues."},
                            {"role": "assistant", "content": f"**{issue.get('severity','MEDIUM')}** at line {issue.get('line','?')}: {issue.get('message','')}\n**Fix**: {issue.get('fix', 'Review and remediate.')}"},
                        ]
                    })
        except Exception:
            continue
    return pairs


def build_training_data() -> int:
    print("Building training data from workspace history...")
    all_pairs = []

    sources = [
        ("git commits", _git_log_pairs),
        ("repair suggestions", _repair_log_pairs),
        ("session logs", _session_log_pairs),
        ("security findings", _security_pairs),
    ]

    for name, fn in sources:
        pairs = fn()
        print(f"  {name}: {len(pairs)} pairs")
        all_pairs.extend(pairs)

    os.makedirs(os.path.dirname(OUT), exist_ok=True)
    with open(OUT, "w") as f:
        for pair in all_pairs:
            f.write(json.dumps(pair) + "\n")

    print(f"\nTotal: {len(all_pairs)} training pairs → {OUT}")
    return len(all_pairs)


if __name__ == "__main__":
    build_training_data()
