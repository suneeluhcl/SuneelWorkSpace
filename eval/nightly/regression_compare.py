"""
Regression Comparison
Compares tonight's NLU pass rate to the history of previous nights.
Writes a regression.md and regression.json to the session directory.
"""

import json
from datetime import datetime
from pathlib import Path


def _load_session_rate(session_dir: Path) -> dict | None:
    """Load the NLU pass rate from a completed session directory."""
    session_json = session_dir / "session.json"
    if session_json.exists():
        try:
            data = json.loads(session_json.read_text())
            nlu = data.get("nlu_eval", {})
            return {
                "session": session_dir.name,
                "rate": nlu.get("rate"),
                "passed": nlu.get("passed"),
                "failed": nlu.get("failed"),
                "date": nlu.get("date", session_dir.name[:8]),
            }
        except Exception:
            pass

    # Fallback: check for a simple summary file
    summary = session_dir / "00_morning_brief.md"
    if summary.exists():
        text = summary.read_text()
        import re
        m = re.search(r"Pass rate.*?(\d+\.\d+)%", text)
        if m:
            return {
                "session": session_dir.name,
                "rate": float(m.group(1)) / 100,
                "date": session_dir.name[:8],
            }
    return None


def compare_to_history(
    log_dir: Path,
    tonight_result: dict,
    session_dir: Path,
    history_window: int = 7,
) -> dict:
    """Compare tonight's results to the last N nights."""
    tonight_rate = tonight_result.get("rate")
    if tonight_rate is None:
        return {"error": "no rate in tonight's result"}

    # Load history
    history = []
    dirs = sorted(
        (d for d in log_dir.iterdir() if d.is_dir() and d.name != "latest"),
        reverse=True,
    )
    for d in dirs[: history_window + 5]:  # skip current session
        if d.name == session_dir.name:
            continue
        entry = _load_session_rate(d)
        if entry and entry.get("rate") is not None:
            history.append(entry)
        if len(history) >= history_window:
            break

    if not history:
        result = {
            "tonight_rate": tonight_rate,
            "history": [],
            "delta": None,
            "trend": "no_history",
            "note": "First nightly session — no baseline to compare against",
        }
    else:
        prev_rate = history[0]["rate"]  # most recent prior night
        delta = tonight_rate - prev_rate
        avg_rate = sum(h["rate"] for h in history) / len(history)
        delta_vs_avg = tonight_rate - avg_rate

        # Trend analysis
        rates = [h["rate"] for h in history]
        if len(rates) >= 3:
            recent_slope = (rates[0] - rates[min(2, len(rates) - 1)]) / 2
        else:
            recent_slope = 0.0

        if delta < -0.03:
            trend = "regression"
        elif delta > 0.02:
            trend = "improvement"
        elif abs(delta) < 0.01:
            trend = "stable"
        else:
            trend = "slight_change"

        # Per-category regression (if available)
        category_regression = _compare_categories(log_dir, session_dir)

        result = {
            "tonight_rate": tonight_rate,
            "previous_rate": prev_rate,
            "delta": delta,
            "delta_vs_7day_avg": delta_vs_avg,
            "seven_day_avg": avg_rate,
            "trend": trend,
            "recent_slope": recent_slope,
            "history": history,
            "category_regression": category_regression,
        }

    # Write reports
    (session_dir / "regression.json").write_text(json.dumps(result, indent=2))
    _write_regression_md(result, session_dir)
    return result


def _compare_categories(log_dir: Path, session_dir: Path) -> list[dict]:
    """Compare per-category rates if available."""
    prev_dirs = sorted(
        (d for d in log_dir.iterdir() if d.is_dir() and d.name != "latest" and d.name != session_dir.name),
        reverse=True,
    )
    if not prev_dirs:
        return []

    prev_dir = prev_dirs[0]
    tonight_clusters = session_dir / "failure_clusters.json"
    prev_clusters = prev_dir / "failure_clusters.json"
    if not tonight_clusters.exists() or not prev_clusters.exists():
        return []

    try:
        tonight_data = json.loads(tonight_clusters.read_text())
        prev_data = json.loads(prev_clusters.read_text())

        tonight_by_cat = {
            c["label"]: c["size"] for c in tonight_data.get("clusters", [])
        }
        prev_by_cat = {
            c["label"]: c["size"] for c in prev_data.get("clusters", [])
        }

        regressions = []
        for cat, tonight_fails in tonight_by_cat.items():
            prev_fails = prev_by_cat.get(cat, 0)
            if tonight_fails > prev_fails + 2:
                regressions.append({
                    "category": cat,
                    "tonight_failures": tonight_fails,
                    "prev_failures": prev_fails,
                    "change": tonight_fails - prev_fails,
                })
        return sorted(regressions, key=lambda x: -x["change"])
    except Exception:
        return []


def _write_regression_md(result: dict, session_dir: Path):
    tonight = result.get("tonight_rate", 0)
    prev = result.get("previous_rate")
    delta = result.get("delta")
    trend = result.get("trend", "unknown")

    def rate_str(r):
        return f"{r:.1%}" if r is not None else "N/A"

    lines = [
        "# Regression Report\n",
        f"**Tonight:** {rate_str(tonight)}",
    ]
    if prev is not None:
        delta_str = f"{delta:+.1%}" if delta is not None else "N/A"
        symbol = "🔴" if trend == "regression" else "🟢" if trend == "improvement" else "🟡"
        lines.append(f"**Previous night:** {rate_str(prev)}")
        lines.append(f"**Delta:** {delta_str} {symbol}")
        lines.append(f"**7-day avg:** {rate_str(result.get('seven_day_avg'))}")
        lines.append(f"**Trend:** {trend}")

    lines.append("")

    if result.get("category_regression"):
        lines.append("## Category Regressions\n")
        lines.append("| Category | Tonight | Previous | Change |")
        lines.append("|----------|---------|----------|--------|")
        for cr in result["category_regression"]:
            lines.append(
                f"| {cr['category']} | {cr['tonight_failures']} fails "
                f"| {cr['prev_failures']} fails | {cr['change']:+d} |"
            )
        lines.append("")

    if result.get("history"):
        lines.append("## History\n")
        lines.append("| Session | Pass Rate |")
        lines.append("|---------|-----------|")
        for h in result["history"]:
            lines.append(f"| {h['session']} | {rate_str(h.get('rate'))} |")

    (session_dir / "regression.md").write_text("\n".join(lines))
