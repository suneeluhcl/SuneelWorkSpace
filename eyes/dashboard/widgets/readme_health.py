"""
README Health Dashboard Widget — workspace-wide README health, trends, priority, and repair status.
Reads from spine/ cache files populated by the README update pipeline.
"""
import json
import os
from pathlib import Path

WORKSPACE = Path(os.environ.get("WORKSPACE", Path(__file__).resolve().parents[3]))
CACHE_PATH = WORKSPACE / "spine/readme_health_cache.json"
PRIORITY_PATH = WORKSPACE / "spine/readme_priority_queue.json"
HISTORY_PATH = WORKSPACE / "spine/readme_metrics_history.json"
REFLECTION_PATH = WORKSPACE / "spine/readme_self_reflection.json"
RECONCILE_PATH = WORKSPACE / "spine/readme_reconcile_report.json"
REPAIR_PATH = WORKSPACE / "spine/readme_repair_report.json"


def get_readme_health() -> dict:
    result = {
        "overall_score": None,
        "total_folders": 0,
        "healthy_count": 0,
        "warning_count": 0,
        "critical_count": 0,
        "low_health_count": 0,
        "critical_folders": [],
        "last_updated": "",
        "status": "unknown",
        # Phase 3 additions
        "trend": None,
        "trend_delta": None,
        "top_priority": [],
        "system_accuracy": None,
        "drifted_folders": 0,
        "pending_repairs": 0,
    }

    if not CACHE_PATH.exists():
        result["status"] = "cache_missing"
        return result

    try:
        cache = json.loads(CACHE_PATH.read_text())
    except Exception:
        result["status"] = "cache_error"
        return result

    entries = {k: v for k, v in cache.items() if isinstance(v, dict) and "health_score" in v}
    if not entries:
        result["status"] = "no_scores"
        return result

    scores = [v["health_score"] for v in entries.values()]
    result["total_folders"] = len(scores)
    result["overall_score"] = round(sum(scores) / len(scores))
    result["healthy_count"] = sum(1 for s in scores if s >= 80)
    result["warning_count"] = sum(1 for s in scores if 60 <= s < 80)
    result["critical_count"] = sum(1 for s in scores if s < 60)
    result["low_health_count"] = result["critical_count"]

    critical = [
        {"path": k, "score": v["health_score"], "updated": v.get("updated", "")}
        for k, v in entries.items()
        if v.get("health_score", 100) < 60
    ]
    result["critical_folders"] = sorted(critical, key=lambda x: x["score"])[:8]

    timestamps = [v.get("updated", "") for v in entries.values() if v.get("updated")]
    result["last_updated"] = max(timestamps) if timestamps else ""

    overall = result["overall_score"]
    result["status"] = "healthy" if overall >= 80 else ("warning" if overall >= 60 else "critical")

    # Phase 3: Trend data
    if HISTORY_PATH.exists():
        try:
            history = json.loads(HISTORY_PATH.read_text())
            snapshots = history.get("snapshots", [])
            if len(snapshots) >= 2:
                first = snapshots[-7]["overall_score"] if len(snapshots) >= 7 else snapshots[0]["overall_score"]
                last = snapshots[-1]["overall_score"]
                delta = round(last - first, 1)
                result["trend"] = "improving" if delta > 2 else ("degrading" if delta < -2 else "stable")
                result["trend_delta"] = delta
        except Exception:
            pass

    # Phase 3: Priority queue top items
    if PRIORITY_PATH.exists():
        try:
            pq = json.loads(PRIORITY_PATH.read_text())
            queue = pq.get("queue", [])
            result["top_priority"] = [
                {"folder": e["folder"], "priority": e["priority"], "score": e["health_score"]}
                for e in queue[:5] if e.get("priority_score", 0) > 20
            ]
        except Exception:
            pass

    # Phase 3: System accuracy
    if REFLECTION_PATH.exists():
        try:
            reflection = json.loads(REFLECTION_PATH.read_text())
            result["system_accuracy"] = reflection.get("latest_accuracy")
        except Exception:
            pass

    # Phase 3: Drifted folders from reconciler
    if RECONCILE_PATH.exists():
        try:
            reconcile = json.loads(RECONCILE_PATH.read_text())
            result["drifted_folders"] = reconcile.get("drifted", 0) + reconcile.get("critical", 0)
        except Exception:
            pass

    # Phase 3: Pending repairs
    if REPAIR_PATH.exists():
        try:
            repair = json.loads(REPAIR_PATH.read_text())
            result["pending_repairs"] = repair.get("total_repairs_skipped", 0)
        except Exception:
            pass

    return result


def get_readme_priority() -> dict:
    """Return priority queue summary for dashboard."""
    if not PRIORITY_PATH.exists():
        return {"error": "priority queue not built yet — run: readme-priority --rebuild"}
    try:
        data = json.loads(PRIORITY_PATH.read_text())
        return {
            "generated": data.get("generated", ""),
            "total": data.get("total", 0),
            "p0_count": data.get("p0_count", 0),
            "p1_count": data.get("p1_count", 0),
            "p2_count": data.get("p2_count", 0),
            "top_10": data.get("queue", [])[:10],
        }
    except Exception as e:
        return {"error": str(e)}


def get_readme_trends() -> dict:
    """Return trend analytics for dashboard."""
    if not HISTORY_PATH.exists():
        return {"error": "no trend data — run: readme-trends --record"}
    try:
        data = json.loads(HISTORY_PATH.read_text())
        snapshots = data.get("snapshots", [])
        return {
            "updated": data.get("updated", ""),
            "snapshot_count": len(snapshots),
            "last_30_days": snapshots[-30:],
        }
    except Exception as e:
        return {"error": str(e)}


if __name__ == "__main__":
    print(json.dumps(get_readme_health(), indent=2))
