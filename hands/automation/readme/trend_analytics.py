#!/usr/bin/env python3
"""
Trend Analytics — tracks README health over time.

Writes snapshots to: spine/readme_metrics_history.json
Adds ## 📈 Trends section to high-impact folder READMEs.

Each snapshot:
  {timestamp, overall_score, total_folders, healthy, warning, critical, low_health_count}
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

HISTORY_PATH = WORKSPACE / "spine/readme_metrics_history.json"
CACHE_PATH = WORKSPACE / "spine/readme_health_cache.json"
MAX_SNAPSHOTS = 90  # keep 90 days


def _load_history() -> list:
    if HISTORY_PATH.exists():
        try:
            return json.loads(HISTORY_PATH.read_text()).get("snapshots", [])
        except Exception:
            pass
    return []


def _load_cache() -> dict:
    if CACHE_PATH.exists():
        try:
            return json.loads(CACHE_PATH.read_text())
        except Exception:
            pass
    return {}


def record_snapshot() -> dict:
    """Record current health state as a snapshot. Returns the snapshot."""
    cache = _load_cache()
    scores = [v.get("health_score", 0) for v in cache.values() if isinstance(v, dict) and "health_score" in v]

    if not scores:
        return {}

    snapshot = {
        "timestamp": datetime.now().isoformat(),
        "date": datetime.now().strftime("%Y-%m-%d"),
        "overall_score": round(sum(scores) / len(scores), 1),
        "total_folders": len(scores),
        "healthy": len([s for s in scores if s >= 80]),
        "warning": len([s for s in scores if 60 <= s < 80]),
        "critical": len([s for s in scores if s < 60]),
        "min_score": min(scores),
        "max_score": max(scores),
    }

    history = _load_history()
    # Deduplicate by date (keep latest per day)
    existing_dates = {s.get("date"): i for i, s in enumerate(history)}
    today = snapshot["date"]
    if today in existing_dates:
        history[existing_dates[today]] = snapshot
    else:
        history.append(snapshot)

    # Trim to MAX_SNAPSHOTS
    history = sorted(history, key=lambda x: x.get("timestamp", ""))[-MAX_SNAPSHOTS:]

    data = {
        "updated": datetime.now().isoformat(),
        "snapshots": history,
    }
    tmp = HISTORY_PATH.with_suffix(".tmp.json")
    HISTORY_PATH.parent.mkdir(parents=True, exist_ok=True)
    tmp.write_text(json.dumps(data, indent=2))
    tmp.rename(HISTORY_PATH)
    return snapshot


def get_trend_summary(days: int = 7) -> dict:
    """Get trend over last N days."""
    history = _load_history()
    if not history:
        return {"trend": "no_data", "snapshots": []}

    recent = sorted(history, key=lambda x: x.get("timestamp", ""))[-days:]
    if len(recent) < 2:
        return {"trend": "insufficient_data", "snapshots": recent}

    first = recent[0].get("overall_score", 0)
    last = recent[-1].get("overall_score", 0)
    delta = round(last - first, 1)

    if delta > 2:
        trend = "improving"
    elif delta < -2:
        trend = "degrading"
    else:
        trend = "stable"

    return {
        "trend": trend,
        "delta": delta,
        "start_score": first,
        "end_score": last,
        "snapshots": recent,
        "days_tracked": len(recent),
    }


def build_trends_section(folder_path: str = None) -> str:
    """Generate ## 📈 Trends section. Uses workspace-wide metrics."""
    lines = ["## 📈 Trends\n"]
    summary = get_trend_summary(7)

    if summary["trend"] == "no_data":
        lines.append("No historical data yet. Run `readme-trends` to start tracking.\n")
        return "\n".join(lines)

    trend_emoji = {"improving": "📈", "degrading": "📉", "stable": "➡️", "insufficient_data": "❓"}
    lines.append(f"**7-day trend:** {trend_emoji.get(summary['trend'], '?')} {summary['trend'].upper()}")

    if "delta" in summary:
        sign = "+" if summary["delta"] >= 0 else ""
        lines.append(f"**Score change:** {sign}{summary['delta']} ({summary['start_score']} → {summary['end_score']})\n")

    snapshots = summary.get("snapshots", [])
    if len(snapshots) >= 2:
        lines.append("**Recent history (last 5 snapshots):**")
        for snap in snapshots[-5:]:
            score = snap.get("overall_score", "?")
            date = snap.get("date", snap.get("timestamp", "?")[:10])
            healthy = snap.get("healthy", 0)
            critical = snap.get("critical", 0)
            lines.append(f"- `{date}` — {score}/100 ({healthy} healthy, {critical} critical)")
        lines.append("")

    lines.append(f"*{summary.get('days_tracked', 0)} day(s) of history | updated daily by nightly automation*")
    return "\n".join(lines)


if __name__ == "__main__":
    import argparse
    parser = argparse.ArgumentParser(description="Track README health trends over time")
    parser.add_argument("--record", action="store_true", help="Record a new snapshot")
    parser.add_argument("--summary", action="store_true", help="Show trend summary")
    parser.add_argument("--days", type=int, default=7, help="Days to show in summary")
    args = parser.parse_args()

    if args.record:
        snap = record_snapshot()
        if snap:
            print(f"Recorded snapshot: {snap['date']} | overall={snap['overall_score']} | healthy={snap['healthy']} | critical={snap['critical']}")
        else:
            print("No cache data found — run readme-update-all first")
    else:
        summary = get_trend_summary(args.days)
        print(f"Trend: {summary['trend']}")
        if "delta" in summary:
            print(f"Delta: {'+' if summary['delta'] >= 0 else ''}{summary['delta']}")
        for snap in summary.get("snapshots", []):
            print(f"  {snap.get('date', '?')}: {snap.get('overall_score', '?')}/100")
