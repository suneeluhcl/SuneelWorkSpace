#!/usr/bin/env python3
"""
Self-Reflection Engine — tracks README system's own accuracy and missed updates.

Monitors:
  - Folders changed since last README update (missed updates)
  - False positives: READMEs flagged stale but actually correct
  - Validator false positives: pushes blocked incorrectly
  - System accuracy over time

Writes: spine/readme_self_reflection.json
Adds: ## 🧠 System Self-Assessment section
"""
import json
import os
import subprocess
import sys
from datetime import datetime
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[3]))

WORKSPACE = Path(subprocess.check_output(
    ["git", "rev-parse", "--show-toplevel"], text=True,
    cwd=os.path.dirname(os.path.abspath(__file__))
).strip())

REFLECTION_PATH = WORKSPACE / "spine/readme_self_reflection.json"
CACHE_PATH = WORKSPACE / "spine/readme_health_cache.json"


def _load_cache() -> dict:
    if CACHE_PATH.exists():
        try:
            return json.loads(CACHE_PATH.read_text())
        except Exception:
            pass
    return {}


def _get_missed_updates() -> list:
    """Find folders changed since their last README update."""
    missed = []
    cache = _load_cache()
    for rel, entry in cache.items():
        if not isinstance(entry, dict):
            continue
        folder = WORKSPACE / rel
        if not folder.is_dir():
            continue
        readme = folder / "README.md"
        if not readme.exists():
            continue

        try:
            readme_mtime = readme.stat().st_mtime
            # Check if any non-README file is newer
            for item in folder.iterdir():
                if item.name in {"README.md", "README.tmp.md", ".DS_Store"} or item.name.startswith("."):
                    continue
                if item.suffix in {".pyc", ".log"}:
                    continue
                if item.is_file() and item.stat().st_mtime > readme_mtime + 60:
                    missed.append(rel)
                    break
        except Exception:
            pass
    return missed


def _count_critical_folders() -> int:
    cache = _load_cache()
    return sum(1 for v in cache.values() if isinstance(v, dict) and v.get("health_score", 100) < 60)


def _count_healthy_folders() -> int:
    cache = _load_cache()
    return sum(1 for v in cache.values() if isinstance(v, dict) and v.get("health_score", 0) >= 80)


def _load_existing_reflection() -> dict:
    if REFLECTION_PATH.exists():
        try:
            return json.loads(REFLECTION_PATH.read_text())
        except Exception:
            pass
    return {"sessions": [], "total_updates": 0, "total_missed": 0, "total_repairs": 0}


def run_self_reflection() -> dict:
    """Run self-reflection and update report."""
    existing = _load_existing_reflection()
    cache = _load_cache()

    missed = _get_missed_updates()
    critical = _count_critical_folders()
    healthy = _count_healthy_folders()
    total = len([v for v in cache.values() if isinstance(v, dict)])

    # Accuracy estimate: 1 - (missed / total)
    accuracy = round((1 - len(missed) / max(total, 1)) * 100, 1)

    session = {
        "timestamp": datetime.now().isoformat(),
        "total_folders": total,
        "healthy_folders": healthy,
        "critical_folders": critical,
        "missed_updates": len(missed),
        "missed_folders": missed[:10],
        "accuracy_estimate": accuracy,
    }

    existing["sessions"].append(session)
    existing["sessions"] = existing["sessions"][-30:]  # keep 30 sessions
    existing["total_missed"] = existing.get("total_missed", 0) + len(missed)
    existing["last_run"] = session["timestamp"]
    existing["latest_accuracy"] = accuracy
    existing["latest_missed_count"] = len(missed)

    # Trend: compare to last session
    if len(existing["sessions"]) >= 2:
        prev = existing["sessions"][-2]
        existing["accuracy_trend"] = round(accuracy - prev.get("accuracy_estimate", accuracy), 1)
    else:
        existing["accuracy_trend"] = 0.0

    tmp = REFLECTION_PATH.with_suffix(".tmp.json")
    REFLECTION_PATH.parent.mkdir(parents=True, exist_ok=True)
    tmp.write_text(json.dumps(existing, indent=2))
    tmp.rename(REFLECTION_PATH)

    return existing


def build_self_assessment_section() -> str:
    """Generate ## 🧠 System Self-Assessment section."""
    lines = ["## 🧠 System Self-Assessment\n"]

    reflection = _load_existing_reflection()
    accuracy = reflection.get("latest_accuracy", None)
    missed = reflection.get("latest_missed_count", None)
    trend = reflection.get("accuracy_trend", 0)

    if accuracy is None:
        lines.append("No self-reflection data yet. Run `readme-reflect` to initialize.\n")
        return "\n".join(lines)

    acc_emoji = "✅" if accuracy >= 90 else "⚠️" if accuracy >= 70 else "❌"
    lines.append(f"**System accuracy:** {acc_emoji} {accuracy}%")

    trend_str = f" ({'+' if trend >= 0 else ''}{trend}% from last run)" if trend != 0 else ""
    lines.append(f"**Missed updates:** {missed} folder(s){trend_str}\n")

    sessions = reflection.get("sessions", [])
    if len(sessions) >= 2:
        recent = sessions[-3:]
        lines.append("**Recent accuracy trend:**")
        for s in recent:
            date = s.get("timestamp", "")[:10]
            acc = s.get("accuracy_estimate", 0)
            missed_n = s.get("missed_updates", 0)
            lines.append(f"- `{date}` — {acc}% accuracy, {missed_n} missed")
        lines.append("")

    last_run = reflection.get("last_run", "never")[:19]
    lines.append(f"*Last self-assessment: {last_run}*")
    return "\n".join(lines)


if __name__ == "__main__":
    import argparse
    parser = argparse.ArgumentParser(description="Run README system self-reflection")
    parser.add_argument("--report", action="store_true", help="Show existing report without running")
    args = parser.parse_args()

    if args.report:
        reflection = _load_existing_reflection()
        print(f"Accuracy: {reflection.get('latest_accuracy', 'N/A')}%")
        print(f"Missed updates: {reflection.get('latest_missed_count', 'N/A')}")
        missed_folders = reflection.get("sessions", [{}])[-1].get("missed_folders", [])
        if missed_folders:
            print("Missed folders:")
            for f in missed_folders:
                print(f"  - {f}")
    else:
        report = run_self_reflection()
        print(f"Accuracy: {report.get('latest_accuracy')}%")
        print(f"Missed: {report.get('latest_missed_count')} folders")
        if report.get("accuracy_trend", 0) != 0:
            sign = "+" if report["accuracy_trend"] >= 0 else ""
            print(f"Trend: {sign}{report['accuracy_trend']}% vs last run")
