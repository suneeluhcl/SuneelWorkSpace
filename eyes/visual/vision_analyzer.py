"""
vision_analyzer.py
Analyzes dashboard screenshots and workspace state for visual issues and
improvement opportunities. Returns structured issue/improvement lists.
"""
import json
import os
import sys
from datetime import datetime, timezone
from pathlib import Path

_HERE = Path(__file__).parent
WORKSPACE = _HERE.parent


def analyze_screenshot(screenshot_path: str = None, context: dict = None) -> dict:
    """
    Analyze a screenshot (and workspace state) for issues and improvements.
    Returns a dict with 'issues' and 'improvements' lists.
    """
    issues: list[dict] = []
    improvements: list[dict] = []

    # ── Workspace health ────────────────────────────────────────────────────
    try:
        health_path = WORKSPACE / "spine/state/WORKSPACE_HEALTH.json"
        if health_path.exists():
            health = json.loads(health_path.read_text())
            score = health.get("health_score", 100)
            errors = health.get("error_count", 0)
            if score < 80:
                issues.append({
                    "id": "score_low",
                    "description": f"Workspace health score is {score}% (target ≥80%)",
                    "severity": "warning",
                    "auto_fix": True,
                })
            if errors > 0:
                issues.append({
                    "id": "workspace_errors",
                    "description": f"{errors} workspace error(s) detected by agent-doctor",
                    "severity": "error",
                    "auto_fix": True,
                })
    except Exception:
        pass

    # ── Evolution engine ────────────────────────────────────────────────────
    try:
        evo_log = WORKSPACE / "lab/evolution/evolution_log.jsonl"
        if not evo_log.exists() or evo_log.stat().st_size == 0:
            improvements.append({
                "id": "no_evolution",
                "title": "Evolution engine not yet started",
                "description": "Start evolution-start to enable continuous improvement",
                "priority": "medium",
            })
    except Exception:
        pass

    # ── Autolab queue ───────────────────────────────────────────────────────
    try:
        queue_md = WORKSPACE / "lab/autolab/experiment_queue.md"
        if queue_md.exists():
            lines = queue_md.read_text().splitlines()
            hypotheses = [l for l in lines if l.startswith("## ")]
            if not hypotheses:
                improvements.append({
                    "id": "empty_autolab_queue",
                    "title": "Autolab experiment queue is empty",
                    "description": "Run hypothesis-generate to populate the queue",
                    "priority": "low",
                })
    except Exception:
        pass

    # ── Gap analysis freshness ──────────────────────────────────────────────
    try:
        gap_path = WORKSPACE / "brain/system/gap_analysis_latest.json"
        if not gap_path.exists():
            improvements.append({
                "id": "no_gap_analysis",
                "title": "No gap analysis found",
                "description": "Run gap_finder.py to scan for capability gaps",
                "priority": "low",
            })
        else:
            data = json.loads(gap_path.read_text())
            age_hours = (datetime.now().timestamp() - gap_path.stat().st_mtime) / 3600
            if age_hours > 24:
                improvements.append({
                    "id": "stale_gap_analysis",
                    "title": f"Gap analysis is {age_hours:.0f}h old",
                    "description": "Re-run gap scan to get fresh capability coverage data",
                    "priority": "low",
                })
    except Exception:
        pass

    # ── Screenshot notes ────────────────────────────────────────────────────
    if screenshot_path and not os.path.exists(screenshot_path):
        issues.append({
            "id": "screenshot_missing",
            "description": f"Referenced screenshot not found: {screenshot_path}",
            "severity": "info",
            "auto_fix": False,
        })

    result = {
        "analyzed_at": datetime.now(timezone.utc).isoformat(),
        "screenshot_path": screenshot_path,
        "issues": issues,
        "improvements": improvements,
        "total_issues": len(issues),
        "total_improvements": len(improvements),
    }

    # Update visual state
    try:
        state_path = WORKSPACE / "eyes/visual/visual_state.json"
        state: dict = {}
        if state_path.exists():
            state = json.loads(state_path.read_text())
        state["last_analysis_at"] = result["analyzed_at"]
        state["issues_found"] = result["total_issues"]
        state_path.write_text(json.dumps(state, indent=2))
    except Exception:
        pass

    return result


if __name__ == "__main__":
    import json as _json
    path = sys.argv[1] if len(sys.argv) > 1 else None
    result = analyze_screenshot(path)
    print(f"Issues: {result['total_issues']}  |  Improvements: {result['total_improvements']}")
    print(_json.dumps(result, indent=2))
