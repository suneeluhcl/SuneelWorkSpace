"""Quota tracker — persists per-model token/call usage across sessions."""
import json
import os
import threading
from datetime import date, datetime, timezone
from pathlib import Path

STATE_PATH = Path(__file__).parent / "quota_state.json"
_lock = threading.Lock()

DAILY_LIMITS: dict = {
    "claude-sonnet-4-6": {"tokens": 1_000_000, "calls": 999_999_999},
    "claude-opus-4-8":   {"tokens":   500_000, "calls": 999_999_999},
    "gpt-4o":            {"tokens": 1_000_000, "calls": 999_999_999},
    "gemini-2.5-pro":    {"tokens": 1_000_000, "calls": 999_999_999},
}


def _load() -> dict:
    try:
        return json.loads(STATE_PATH.read_text())
    except Exception:
        return {"models": {}, "last_reset": None, "fallback_chain": list(DAILY_LIMITS)}


def _save(state: dict) -> None:
    STATE_PATH.write_text(json.dumps(state, indent=2))


def _maybe_reset(state: dict) -> dict:
    today = date.today().isoformat()
    if state.get("last_reset") != today:
        for m in state.get("models", {}).values():
            m["tokens_used_today"] = 0
            m["calls_today"] = 0
            m["errors_today"] = 0
            m["available"] = True
        state["last_reset"] = today
    return state


def record_usage(model_id: str, tokens: int = 0, error: bool = False) -> None:
    with _lock:
        state = _load()
        state = _maybe_reset(state)
        m = state["models"].setdefault(model_id, {
            "tokens_used_today": 0, "calls_today": 0,
            "errors_today": 0, "last_error": None, "available": True,
        })
        m["calls_today"] += 1
        m["tokens_used_today"] += tokens
        if error:
            m["errors_today"] += 1
            m["last_error"] = datetime.now(timezone.utc).isoformat()
        lim = DAILY_LIMITS.get(model_id, {})
        if m["tokens_used_today"] >= lim.get("tokens", 999_999_999):
            m["available"] = False
        _save(state)


def mark_unavailable(model_id: str, reason: str = "") -> None:
    with _lock:
        state = _load()
        entry = state["models"].setdefault(model_id, {"available": True})
        entry["available"] = False
        if reason:
            entry["last_error"] = reason
        _save(state)


def get_status() -> dict:
    with _lock:
        state = _load()
        state = _maybe_reset(state)
        _save(state)
    models_list = []
    for mid, m in state.get("models", {}).items():
        lim = DAILY_LIMITS.get(mid, {})
        models_list.append({
            "id": mid,
            "available": m.get("available", True),
            "tokens_used_today": m.get("tokens_used_today", 0),
            "tokens_limit": lim.get("tokens", 999_999_999),
            "calls_today": m.get("calls_today", 0),
            "errors_today": m.get("errors_today", 0),
            "last_error": m.get("last_error"),
        })
    return {
        "models": models_list,
        "last_reset": state.get("last_reset"),
        "fallback_chain": state.get("fallback_chain", []),
    }


if __name__ == "__main__":
    import json as _json
    print(_json.dumps(get_status(), indent=2))
