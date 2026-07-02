#!/usr/bin/env python3
"""
visual_repair_agent.py
Processes the visual repair queue — auto-fixes safe issues, sends
errors/high-severity items to the approval queue for human review.
"""
import json
import logging
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path

_HERE = Path(__file__).parent
WORKSPACE = _HERE.parent

REPAIR_QUEUE    = _HERE / "visual_repair_queue.json"
APPROVAL_QUEUE  = _HERE / "visual_approval_queue.json"
REPAIR_LOG      = _HERE / "visual_repair_log.jsonl"


def _load_queue(path: Path) -> list:
    if not path.exists():
        return []
    try:
        return json.loads(path.read_text())
    except Exception:
        return []


def _save_queue(path: Path, queue: list) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(queue, indent=2))


def _log_event(event: str, data: dict = None) -> None:
    try:
        entry = {"ts": datetime.now(timezone.utc).isoformat(), "event": event, **(data or {})}
        with open(REPAIR_LOG, "a") as f:
            f.write(json.dumps(entry) + "\n")
    except Exception:
        pass


def _generate_and_apply_fix(issue: dict) -> dict:
    """Apply a known automatic fix for the given issue dict."""
    issue_id = issue.get("id", "unknown")
    result = {"issue_id": issue_id, "applied": False, "note": ""}

    if issue_id in ("score_low", "workspace_errors"):
        try:
            import asyncio
            sys.path.insert(0, str(WORKSPACE / "dashboard"))
            from execution.health_repair_pipeline import run_health_repair

            async def _run():
                await run_health_repair(lambda l, c: None, "visual_repair")

            asyncio.run(_run())
            result["applied"] = True
            result["note"] = "Health repair pipeline triggered"
        except Exception as e:
            result["note"] = f"Health repair error: {str(e)[:100]}"

    elif issue_id in ("empty_autolab_queue", "no_evolution"):
        r = subprocess.run(
            [sys.executable, "-c",
             "import sys; sys.path.insert(0, '.'); "
             "from lab.autolab.hypothesis_generator import generate_hypotheses; generate_hypotheses()"],
            capture_output=True, text=True, timeout=30, cwd=str(WORKSPACE),
        )
        result["applied"] = r.returncode == 0
        result["note"] = "Hypothesis generation triggered"

    elif issue_id in ("no_gap_analysis", "stale_gap_analysis"):
        r = subprocess.run(
            [sys.executable, "lab/evolution/gap_finder.py"],
            capture_output=True, text=True, timeout=60, cwd=str(WORKSPACE),
        )
        result["applied"] = r.returncode == 0
        result["note"] = "Gap scan triggered"

    else:
        result["note"] = f"No automatic fix registered for: {issue_id}"

    return result


def process_repair_queue() -> dict:
    """Process all pending items — auto-fix safe ones, queue errors for approval."""
    queue = _load_queue(REPAIR_QUEUE)
    approval_queue = _load_queue(APPROVAL_QUEUE)

    auto_fixed = 0
    queued_for_approval = 0
    processed = 0

    pending = [i for i in queue if i.get("status") == "pending"]

    for item in pending:
        issue = item.get("issue", item.get("improvement", {}))
        severity = issue.get("severity", "info")

        if issue.get("auto_fix") and severity in ("info", "warning"):
            fix_result = _generate_and_apply_fix(issue)
            item["status"] = "applied" if fix_result["applied"] else "failed"
            item["fix_result"] = fix_result
            item["processed_at"] = datetime.now(timezone.utc).isoformat()
            auto_fixed += 1
            _log_event("auto_fix", {"issue": issue, "result": fix_result})
        else:
            item["status"] = "awaiting_approval"
            approval_queue.append({
                **item,
                "queued_at": item.get("queued_at", datetime.now(timezone.utc).isoformat()),
            })
            queued_for_approval += 1
            _log_event("queued_for_approval", {"issue": issue})

        processed += 1

    _save_queue(REPAIR_QUEUE, queue)
    _save_queue(APPROVAL_QUEUE, approval_queue)

    summary = {
        "processed": processed,
        "auto_fixed": auto_fixed,
        "queued_for_approval": queued_for_approval,
        "remaining": len([i for i in queue if i.get("status") == "pending"]),
    }
    _log_event("queue_processed", summary)
    return summary


def enqueue_from_analysis(analysis: dict) -> int:
    """Add issues/improvements from a vision analysis to the repair queue."""
    queue = _load_queue(REPAIR_QUEUE)
    existing_ids = {
        (i.get("issue") or i.get("improvement") or {}).get("id")
        for i in queue if i.get("status") == "pending"
    }
    added = 0
    ts = datetime.now(timezone.utc).isoformat()

    for issue in analysis.get("issues", []):
        if issue.get("id") not in existing_ids:
            queue.append({"issue": issue, "status": "pending", "queued_at": ts})
            existing_ids.add(issue.get("id"))
            added += 1

    for improvement in analysis.get("improvements", []):
        if improvement.get("id") not in existing_ids:
            queue.append({"improvement": improvement, "status": "pending", "queued_at": ts})
            existing_ids.add(improvement.get("id"))
            added += 1

    _save_queue(REPAIR_QUEUE, queue)
    return added


if __name__ == "__main__":
    sys.path.insert(0, str(WORKSPACE))
    from eyes.visual.vision_analyzer import analyze_screenshot
    from eyes.visual.screenshot_manager import get_latest_screenshot

    shot = get_latest_screenshot()
    analysis = analyze_screenshot(shot["path"] if shot else None)
    added = enqueue_from_analysis(analysis)
    print(f"Enqueued {added} item(s) from analysis")
    result = process_repair_queue()
    print(json.dumps(result, indent=2))
