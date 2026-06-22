#!/usr/bin/env python3
"""
telegram_e2e_summary.py — Compact E2E auto-loop summary for Telegram.

Reads adwi/notes/e2e-auto-loop/status.json and the most recent cycle or
final report. Prints a short human-readable summary (no secrets, no tokens).
Exits 0 even when no loop has run.

Usage: python3 adwi/scripts/telegram_e2e_summary.py
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

HOME     = Path.home()
LOOP_DIR = HOME / "SuneelWorkSpace" / "adwi" / "notes" / "e2e-auto-loop"
STATUS_F = LOOP_DIR / "status.json"


def _fmt_pct(v) -> str:
    if v is None:
        return "—"
    try:
        return f"{float(v):.1f}%"
    except (TypeError, ValueError):
        return str(v)


def _best_report(job_id: str) -> dict:
    """Return the most detailed report dict available for this job_id."""
    if not job_id or job_id == "?":
        return {}
    job_dir = LOOP_DIR / job_id
    final_f = job_dir / "final-report.json"
    if final_f.exists():
        try:
            return json.loads(final_f.read_text(encoding="utf-8"))
        except Exception:
            pass
    cycle_reports = sorted(job_dir.glob("cycle-*-report.json"))
    if cycle_reports:
        try:
            return json.loads(cycle_reports[-1].read_text(encoding="utf-8"))
        except Exception:
            pass
    return {}


def main() -> int:
    if not STATUS_F.exists():
        print("No E2E auto loop has run on this machine.")
        print("Start one with: /e2e_plan analyze")
        return 0

    try:
        status = json.loads(STATUS_F.read_text(encoding="utf-8"))
    except Exception as exc:
        print(f"[error] Cannot read status.json: {exc}")
        return 0

    job_id = status.get("job_id", "?")
    state  = status.get("status", "?")
    target = status.get("target")

    lines = [f"E2E Loop — {job_id}"]
    lines.append(f"  Status: {state}  Target: {_fmt_pct(target)}")

    report = _best_report(job_id)
    if report:
        combined = report.get("combined_pct") or report.get("final_combined_pct")
        cycle    = report.get("cycle") or report.get("total_cycles")
        reason   = (report.get("stop_reason") or report.get("reason") or "")[:120]
        unfixed  = report.get("unfixed_clusters") or []

        if combined is not None:
            lines.append(f"  Combined: {_fmt_pct(combined)}")
        if cycle is not None:
            lines.append(f"  Cycle:    {cycle}")
        if reason:
            lines.append(f"  Reason:   {reason}")
        if unfixed:
            lines.append(f"  Unfixed:  {', '.join(str(u) for u in unfixed[:3])}")
    else:
        start = (status.get("started_at") or "")[:16]
        if start:
            lines.append(f"  Started:  {start}")
        msg = (status.get("message") or status.get("detail") or "")[:120]
        if msg:
            lines.append(f"  Info:     {msg}")

    cancel_f = LOOP_DIR / "cancel"
    if cancel_f.exists():
        lines.append("  [cancel sentinel present — loop will stop soon]")

    lines.append("")
    lines.append("Details: /e2e_report  •  Full log: /jobs  •  Cancel: /e2e_cancel_plan")

    print("\n".join(lines))
    return 0


if __name__ == "__main__":
    sys.exit(main())
