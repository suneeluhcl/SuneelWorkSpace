"""
vision_implementer.py
Given a description (and optionally a screenshot), implement UI or
workspace changes autonomously. Routes to the appropriate subsystem.
"""
import json
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path

_HERE = Path(__file__).parent
WORKSPACE = _HERE.parent


def analyze_and_implement(
    description: str,
    screenshot_path: str = None,
    dry_run: bool = False,
) -> dict:
    """
    Parse the description and route to the correct subsystem action.
    Returns a result dict with 'applied', 'actions', and optional 'error'.
    """
    result: dict = {
        "description": description,
        "screenshot_path": screenshot_path,
        "analyzed_at": datetime.now(timezone.utc).isoformat(),
        "actions": [],
        "applied": False,
        "dry_run": dry_run,
    }

    desc = description.lower()

    # ── Route by keywords ───────────────────────────────────────────────────
    if any(k in desc for k in ("health", "repair", "fix", "score", "error")):
        result["actions"].append({
            "type": "health_repair",
            "note": "Triggering 8-stage health repair pipeline",
        })
        if not dry_run:
            try:
                import asyncio
                sys.path.insert(0, str(WORKSPACE / "dashboard"))
                from execution.health_repair_pipeline import run_health_repair
                asyncio.run(run_health_repair(lambda l, c: None, "vision_impl"))
                result["applied"] = True
            except Exception as e:
                result["error"] = str(e)[:200]

    elif any(k in desc for k in ("hypothesis", "experiment", "autolab", "idea")):
        result["actions"].append({
            "type": "generate_hypotheses",
            "note": "Triggering hypothesis generator",
        })
        if not dry_run:
            r = subprocess.run(
                [sys.executable, "lab/autolab/hypothesis_generator.py"],
                capture_output=True, text=True, timeout=60, cwd=str(WORKSPACE),
            )
            result["applied"] = r.returncode == 0
            if not result["applied"]:
                result["error"] = r.stderr[:200]

    elif any(k in desc for k in ("evolution", "evolve", "gap", "capability")):
        result["actions"].append({
            "type": "gap_scan",
            "note": "Running gap analysis + challenge generation",
        })
        if not dry_run:
            r = subprocess.run(
                [sys.executable, "lab/evolution/gap_finder.py"],
                capture_output=True, text=True, timeout=60, cwd=str(WORKSPACE),
            )
            result["applied"] = r.returncode == 0

    elif any(k in desc for k in ("screenshot", "visual", "monitor", "ui")):
        result["actions"].append({
            "type": "screenshot",
            "note": "Taking a fresh dashboard screenshot and analyzing it",
        })
        if not dry_run:
            sys.path.insert(0, str(WORKSPACE))
            from eyes.visual.screenshot_manager import take_screenshot
            from eyes.visual.vision_analyzer import analyze_screenshot
            from eyes.visual.visual_repair_agent import enqueue_from_analysis, process_repair_queue
            path = take_screenshot(label="vision_impl")
            analysis = analyze_screenshot(path)
            added = enqueue_from_analysis(analysis)
            summary = process_repair_queue()
            result["actions"][-1]["detail"] = {
                "screenshot": path,
                "issues": analysis["total_issues"],
                "enqueued": added,
                "processed": summary,
            }
            result["applied"] = True

    elif any(k in desc for k in ("model", "router", "fallback", "token")):
        result["actions"].append({
            "type": "model_status",
            "note": "Checking model health and quota status",
        })
        if not dry_run:
            sys.path.insert(0, str(WORKSPACE))
            from heart.model_router.quota_tracker import get_status
            result["actions"][-1]["detail"] = get_status()
            result["applied"] = True

    else:
        result["actions"].append({
            "type": "log",
            "note": f"No automatic action mapped for: {description[:100]}",
        })
        result["applied"] = False

    return result


if __name__ == "__main__":
    desc = " ".join(sys.argv[1:]) if len(sys.argv) > 1 else "repair workspace health"
    out = analyze_and_implement(desc)
    print(json.dumps(out, indent=2))
