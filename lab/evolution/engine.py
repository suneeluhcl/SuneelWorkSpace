#!/usr/bin/env python3
"""
engine.py
Autonomous Evolution Engine — orchestrates continuous workspace improvement
by cycling through gap scanning, challenge generation, and experiment runs.
"""
import json
import logging
import signal
import sys
import time
from datetime import datetime, timezone
from pathlib import Path

_HERE = Path(__file__).parent
WORKSPACE = _HERE.parent.parent
EVO_LOG    = _HERE / "evolution_log.jsonl"
STATE_FILE = _HERE / "engine_state.json"

def load_config() -> dict:
    config_path = _HERE / "evolution_config.json"
    default = {
        "night_hours": [22, 6],
        "day_interval_minutes": 45,
        "night_interval_minutes": 30
    }
    if not config_path.exists():
        return default
    try:
        return json.loads(config_path.read_text())
    except Exception:
        return default


def get_night_hours() -> tuple[int, int]:
    cfg = load_config()
    hours = cfg.get("night_hours", [22, 6])
    return tuple(hours[:2])


# ── Public helpers ────────────────────────────────────────────────────────────

def is_night_mode() -> bool:
    """Return True if the current local hour is in the night-shift window."""
    hour = datetime.now().hour
    start, end = get_night_hours()
    if start > end:        # wraps midnight
        return hour >= start or hour < end
    return start <= hour < end


# ── Internal helpers ──────────────────────────────────────────────────────────

def _log_event(event_type: str, data: dict = None) -> None:
    EVO_LOG.parent.mkdir(parents=True, exist_ok=True)
    entry = {
        "ts": datetime.now(timezone.utc).isoformat(),
        "type": event_type,
        "night_mode": is_night_mode(),
        **(data or {}),
    }
    with open(EVO_LOG, "a") as f:
        f.write(json.dumps(entry) + "\n")


def _save_state(state: dict) -> None:
    STATE_FILE.write_text(json.dumps(state, indent=2))


def _load_state() -> dict:
    try:
        return json.loads(STATE_FILE.read_text())
    except Exception:
        return {"status": "stopped", "started_at": None, "cycles": 0}


# ── Evolution cycle ───────────────────────────────────────────────────────────

def run_evolution_cycle() -> dict:
    """Run one full evolution cycle: gap scan → challenges → log."""
    _log_event("cycle_start")
    results: dict = {}

    # Gap scan
    try:
        sys.path.insert(0, str(WORKSPACE))
        from lab.evolution.gap_finder import scan_for_gaps
        gaps = scan_for_gaps()
        results["gaps"] = {"count": gaps["gap_count"], "health_pct": gaps["health_pct"]}
        _log_event("gap_scan_complete", results["gaps"])
    except Exception as e:
        results["gaps"] = {"error": str(e)[:100]}
        _log_event("gap_scan_error", {"error": str(e)[:100]})

    # Generate challenges
    try:
        from lab.evolution.challenger import generate_challenges
        challenges = generate_challenges(3)
        results["challenges"] = len(challenges)
        _log_event("challenges_generated", {"count": len(challenges)})
    except Exception as e:
        results["challenges"] = {"error": str(e)[:100]}

    _log_event("cycle_complete", results)
    return results


# ── Engine loop ───────────────────────────────────────────────────────────────

def start_engine(interval_minutes: int = 45) -> None:
    """Start the evolution engine daemon loop."""
    cfg = load_config()
    # prioritize command line interval argument if provided explicitly, otherwise config
    if len(sys.argv) > 2:
        interval_minutes = int(sys.argv[2])
    else:
        interval_minutes = cfg.get("day_interval_minutes", 45)

    state = {
        "status": "running",
        "started_at": datetime.now(timezone.utc).isoformat(),
        "cycles": 0,
        "interval_minutes": interval_minutes,
    }
    _save_state(state)
    _log_event("engine_start", {"interval_minutes": interval_minutes})
    print(f"🧬 Evolution engine started (interval: {interval_minutes}m, night boost: {cfg.get('night_interval_minutes', 30)}m)")

    def _handle_stop(sig, frame):
        s = _load_state()
        s["status"] = "stopped"
        s["stopped_at"] = datetime.now(timezone.utc).isoformat()
        _save_state(s)
        _log_event("engine_stop", {"reason": "signal", "signal": sig})
        print("\n🛑 Evolution engine stopped.")
        sys.exit(0)

    signal.signal(signal.SIGINT, _handle_stop)
    signal.signal(signal.SIGTERM, _handle_stop)

    while True:
        s = _load_state()
        if s.get("status") != "running":
            print("Stop signal received.")
            break

        result = run_evolution_cycle()
        s["cycles"] = s.get("cycles", 0) + 1
        s["last_cycle"] = datetime.now(timezone.utc).isoformat()
        _save_state(s)

        cfg = load_config()
        night_int = cfg.get("night_interval_minutes", 30)
        day_int = s.get("interval_minutes", interval_minutes)
        sleep_secs = (night_int if is_night_mode() else day_int) * 60
        print(f"[{datetime.now().strftime('%H:%M')}] Cycle {s['cycles']} complete — "
              f"gaps: {result.get('gaps', {}).get('count', '?')} | "
              f"next in {sleep_secs // 60}m")
        time.sleep(sleep_secs)


# ── Entry point ───────────────────────────────────────────────────────────────

if __name__ == "__main__":
    cmd = sys.argv[1] if len(sys.argv) > 1 else "start"
    if cmd == "status":
        print(json.dumps(_load_state(), indent=2))
    elif cmd == "cycle":
        print(json.dumps(run_evolution_cycle(), indent=2))
    elif cmd == "night":
        print(f"Night mode: {is_night_mode()}")
    else:
        interval = int(sys.argv[2]) if len(sys.argv) > 2 else 45
        start_engine(interval)
