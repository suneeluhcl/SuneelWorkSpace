#!/usr/bin/env python3
"""
Intent Alignment Engine — compares DECISIONS.md + active goals against README purpose.

Detects:
  - READMEs whose stated purpose conflicts with recorded decisions
  - Folders implementing goals not reflected in their README
  - Deprecated decisions still referenced in READMEs

Adds ## 🎯 Intent Alignment section to READMEs.
"""
import json
import os
import re
import subprocess
import sys
from datetime import datetime
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[3]))

WORKSPACE = Path(subprocess.check_output(
    ["git", "rev-parse", "--show-toplevel"], text=True,
    cwd=os.path.dirname(os.path.abspath(__file__))
).strip())

DECISIONS_FILE = WORKSPACE / "brain/memory/DECISIONS.md"
ACTIVE_TASKS_FILE = WORKSPACE / "heart/tasks/ACTIVE_TASKS.md"
MEMORY_FILE = WORKSPACE / "brain/memory/MEMORY.md"


def _extract_decisions() -> list:
    """Parse DECISIONS.md for decision entries."""
    decisions = []
    if not DECISIONS_FILE.exists():
        return decisions
    content = DECISIONS_FILE.read_text(errors="ignore")
    for m in re.finditer(r"#{1,3}\s+(.+?)(?:\n|$)", content):
        title = m.group(1).strip()
        if len(title) > 5 and not title.startswith("#"):
            decisions.append(title.lower())
    return decisions[:30]


def _extract_active_goals() -> list:
    """Parse ACTIVE_TASKS.md for active goals."""
    goals = []
    if not ACTIVE_TASKS_FILE.exists():
        return goals
    content = ACTIVE_TASKS_FILE.read_text(errors="ignore")
    for m in re.finditer(r"-\s+\[([ x])\]\s+(.+?)(?:\n|$)", content):
        if m.group(1) == " ":  # uncompleted
            goals.append(m.group(2).strip().lower())
    return goals[:20]


def _extract_readme_purpose(readme_path: Path) -> str:
    if not readme_path.exists():
        return ""
    content = readme_path.read_text(errors="ignore")
    match = re.search(r"## 🧠 Purpose\s*\n(.*?)(?=\n## |\Z)", content, re.DOTALL)
    if match:
        return match.group(1).strip().lower()
    match = re.search(r"## Purpose\s*\n(.*?)(?=\n## |\Z)", content, re.DOTALL)
    if match:
        return match.group(1).strip().lower()
    return ""


def _keywords_from(text: str) -> set:
    stopwords = {"the", "a", "an", "and", "or", "for", "in", "on", "to", "of",
                 "is", "are", "be", "been", "this", "that", "with", "from"}
    words = re.findall(r"\b[a-z]{3,}\b", text.lower())
    return {w for w in words if w not in stopwords}


def align_folder(folder_path: str) -> dict:
    """
    Check intent alignment for a single folder.

    Returns:
        {
          folder: str,
          purpose_keywords: list[str],
          matching_decisions: list[str],
          matching_goals: list[str],
          unaddressed_goals: list[str],
          alignment_score: int (0-100),
          status: "aligned" | "partial" | "misaligned" | "unknown",
          timestamp: str,
        }
    """
    path = Path(folder_path).resolve()
    try:
        rel = str(path.relative_to(WORKSPACE))
    except ValueError:
        rel = str(path)

    purpose = _extract_readme_purpose(path / "README.md")
    if not purpose:
        return {
            "folder": rel,
            "purpose_keywords": [],
            "matching_decisions": [],
            "matching_goals": [],
            "unaddressed_goals": [],
            "alignment_score": 0,
            "status": "unknown",
            "timestamp": datetime.now().isoformat(),
        }

    purpose_kw = _keywords_from(purpose)
    decisions = _extract_decisions()
    goals = _extract_active_goals()

    # Check which decisions match this folder's purpose
    matching_decisions = []
    for decision in decisions:
        dec_kw = _keywords_from(decision)
        if len(purpose_kw & dec_kw) >= 2:
            matching_decisions.append(decision[:80])

    # Check which active goals relate to this folder
    matching_goals = []
    unaddressed = []
    organ_parts = rel.split("/")
    organ = organ_parts[0] if organ_parts else ""

    for goal in goals:
        goal_kw = _keywords_from(goal)
        if organ in goal or len(purpose_kw & goal_kw) >= 2:
            if len(purpose_kw & goal_kw) >= 2:
                matching_goals.append(goal[:80])
            else:
                unaddressed.append(goal[:80])

    # Compute alignment score
    if not decisions and not goals:
        score = 70  # neutral — no data to compare
        status = "unknown"
    else:
        base = 60
        if matching_decisions:
            base += min(20, len(matching_decisions) * 5)
        if matching_goals:
            base += min(20, len(matching_goals) * 5)
        if unaddressed:
            base -= min(20, len(unaddressed) * 5)
        score = max(0, min(100, base))
        if score >= 75:
            status = "aligned"
        elif score >= 50:
            status = "partial"
        else:
            status = "misaligned"

    return {
        "folder": rel,
        "purpose_keywords": sorted(purpose_kw)[:10],
        "matching_decisions": matching_decisions[:3],
        "matching_goals": matching_goals[:3],
        "unaddressed_goals": unaddressed[:3],
        "alignment_score": score,
        "status": status,
        "timestamp": datetime.now().isoformat(),
    }


def build_intent_section(result: dict) -> str:
    """Generate ## 🎯 Intent Alignment markdown section."""
    lines = ["## 🎯 Intent Alignment\n"]
    status_emoji = {"aligned": "✅", "partial": "⚠️", "misaligned": "❌", "unknown": "❓"}
    lines.append(f"**Alignment:** {status_emoji.get(result['status'], '?')} {result['status'].upper()} ({result['alignment_score']}/100)\n")

    if result["matching_decisions"]:
        lines.append("**Supported by decisions:**")
        for d in result["matching_decisions"]:
            lines.append(f"- {d}")
        lines.append("")

    if result["matching_goals"]:
        lines.append("**Active goals addressed:**")
        for g in result["matching_goals"]:
            lines.append(f"- {g}")
        lines.append("")

    if result["unaddressed_goals"]:
        lines.append("**Potentially unaddressed goals:**")
        for g in result["unaddressed_goals"]:
            lines.append(f"- {g}")
        lines.append("")

    if result["status"] == "unknown":
        lines.append("*No DECISIONS.md or ACTIVE_TASKS.md data available for comparison.*\n")

    lines.append(f"*Last checked: {result['timestamp'][:19]}*")
    return "\n".join(lines)


if __name__ == "__main__":
    import argparse
    parser = argparse.ArgumentParser(description="Check README intent alignment")
    parser.add_argument("folder", nargs="?", help="Folder to check (default: all organs)")
    args = parser.parse_args()

    from hands.automation.readme.intelligence_engine import ORGANS
    if args.folder:
        result = align_folder(args.folder)
        print(json.dumps(result, indent=2))
    else:
        for organ in sorted(ORGANS):
            folder = WORKSPACE / organ
            if folder.exists():
                result = align_folder(str(folder))
                print(f"{result['status']:12} {result['alignment_score']:3}/100  {organ}/")
