#!/usr/bin/env python3
"""
validate_telegram_bridge.py — Static validator for the Adwi Telegram bridge.

Loads bot.py and the Safe Command API server.py, runs structural integrity
checks, prints PASS/FAIL per check, exits 0 only if all checks pass.

Checks:
  1.  bot.py loads without exception
  2.  TELEGRAM_COMMANDS dict present and non-empty
  3.  All command keys start with "/"
  4.  server.py (Safe Command API) loads without exception
  5.  Every Safe API route in TELEGRAM_COMMANDS exists in ALLOWED_COMMANDS
  6.  No forbidden mutation routes exposed via TELEGRAM_COMMANDS
  7.  All local (route=None) commands are dispatched in _handle_local_cmd or _TEST_JOBS
  8.  _TEST_JOBS contains the four expected test commands
  9.  _TEST_JOBS argv lists contain no pytest-only flags
  10. Required runtime paths exist (VENV_PY, ADWI_CLI, job_runner.py, smoke scripts)
  11. HELP_TEXT includes the dynamic command count
  12. MENU_TEXT includes the dynamic command count

Usage:
  python3 adwi/scripts/validate_telegram_bridge.py
"""
from __future__ import annotations

import importlib.util
import inspect
import sys
from pathlib import Path

WORKSPACE    = Path(__file__).resolve().parent.parent.parent
BOT_PATH      = WORKSPACE / "adwi" / "services" / "telegram-bridge" / "bot.py"
SERVER_PATH   = WORKSPACE / "adwi" / "services" / "command-api" / "server.py"
JR_PATH       = WORKSPACE / "adwi" / "services" / "telegram-bridge" / "job_runner.py"
SMOKE_PATH    = WORKSPACE / "adwi" / "scripts" / "smoke_telegram_jobs.py"
E2E_LOOP_PATH = WORKSPACE / "adwi" / "e2e_auto_loop.py"
E2E_SUMM_PATH = WORKSPACE / "adwi" / "scripts" / "telegram_e2e_summary.py"
E2E_STAT_PATH = WORKSPACE / "adwi" / "bin" / "adwi-e2e-status-reader"

_EXPECTED_TEST_JOBS = {"/test_quick", "/test_nlu", "/test_obsidian", "/test_all"}
_PYTEST_ONLY_FLAGS  = ("--tb=", "--cov=", "--cov-report", "--cache-show",
                       "--lf", "--ff", "--sw", "--randomly")
_FORBIDDEN_PATTERNS = (
    "run-bash", "run-python", "patch-adwi", "self-heal", "nightly-run",
    "git-commit", "git-push", "gmail-send", "gmail-confirm",
    "implement-idea", "notify", "file-write", "obsidian-write", "backup-now",
    "e2e-auto-loop-start",
)


# ── Helpers ───────────────────────────────────────────────────────────────────

def _load_module(name: str, path: Path):
    spec = importlib.util.spec_from_file_location(name, path)
    mod  = importlib.util.module_from_spec(spec)   # type: ignore[arg-type]
    spec.loader.exec_module(mod)                    # type: ignore[union-attr]
    return mod


_pass_count = 0
_fail_count = 0


def _check(label: str, cond: bool, detail: str = "") -> bool:
    global _pass_count, _fail_count
    status = "PASS" if cond else "FAIL"
    suffix = f"  ({detail})" if detail else ""
    print(f"  {status}  {label}{suffix}")
    if cond:
        _pass_count += 1
    else:
        _fail_count += 1
    return cond


def _sub(label: str, cond: bool, detail: str = "") -> bool:
    suffix = f"  ({detail})" if detail else ""
    mark   = "  ✓" if cond else "  ✗"
    print(f"      {mark}  {label}{suffix}")
    return cond


# ── Main ──────────────────────────────────────────────────────────────────────

def main() -> int:
    print("validate_telegram_bridge.py — Telegram bridge structural validator")
    print(f"  bot.py:      {BOT_PATH}")
    print(f"  server.py:   {SERVER_PATH}")
    print()

    # ── Check 1: bot.py loads ─────────────────────────────────────────────────
    bot_mod = None
    try:
        bot_mod = _load_module("validate_bot", BOT_PATH)
        _check("bot.py loads without exception", True)
    except Exception as exc:
        _check("bot.py loads without exception", False, detail=str(exc)[:120])
        print("\nFATAL: cannot continue without bot.py")
        return 1

    tg_cmds: dict = getattr(bot_mod, "TELEGRAM_COMMANDS", None) or {}

    # ── Check 2: TELEGRAM_COMMANDS present and non-empty ─────────────────────
    _check("TELEGRAM_COMMANDS dict present and non-empty",
           bool(tg_cmds), detail=f"{len(tg_cmds)} commands" if tg_cmds else "missing/empty")

    # ── Check 3: All keys start with "/" ──────────────────────────────────────
    bad_keys = [k for k in tg_cmds if not k.startswith("/")]
    _check("All command keys start with '/'",
           not bad_keys, detail=f"bad: {bad_keys}" if bad_keys else "")

    # ── Check 4: server.py loads ──────────────────────────────────────────────
    server_mod = None
    try:
        server_mod = _load_module("validate_server", SERVER_PATH)
        _check("server.py (Safe Command API) loads without exception", True)
    except Exception as exc:
        _check("server.py (Safe Command API) loads without exception",
               False, detail=str(exc)[:120])
        server_mod = None

    # ── Check 5: Safe API routes exist in ALLOWED_COMMANDS ───────────────────
    if server_mod is not None:
        allowed: dict = getattr(server_mod, "ALLOWED_COMMANDS", {})
        api_routes = {v for v in tg_cmds.values() if v is not None}
        missing = sorted(r for r in api_routes if r not in allowed)
        _check(
            "All Safe API routes exist in ALLOWED_COMMANDS",
            not missing,
            detail=f"missing: {missing}" if missing else f"{len(api_routes)} routes OK",
        )
        if missing:
            for r in missing:
                _sub(r, False, "not in server.py ALLOWED_COMMANDS")
    else:
        _check("All Safe API routes exist in ALLOWED_COMMANDS",
               False, detail="skipped — server.py failed to load")

    # ── Check 6: No forbidden routes exposed ─────────────────────────────────
    forbidden_found: list[tuple[str, str]] = []
    for tg_cmd, route in tg_cmds.items():
        check_in = (route or tg_cmd)
        for pat in _FORBIDDEN_PATTERNS:
            if pat in check_in:
                forbidden_found.append((tg_cmd, pat))
    _check(
        "No forbidden mutation routes exposed",
        not forbidden_found,
        detail=f"violations: {forbidden_found}" if forbidden_found else "",
    )

    # ── Check 7: Every local command is dispatched ────────────────────────────
    local_cmds = [c for c, r in tg_cmds.items() if r is None]
    test_jobs: dict = getattr(bot_mod, "_TEST_JOBS", {})

    try:
        dispatch_src = inspect.getsource(bot_mod._handle_local_cmd)
    except Exception:
        dispatch_src = ""

    undispatched = []
    for cmd in local_cmds:
        in_test_jobs     = cmd in test_jobs
        in_dispatch_src  = f'cmd == "{cmd}"' in dispatch_src
        if not in_test_jobs and not in_dispatch_src:
            undispatched.append(cmd)

    _check(
        "All local commands dispatched (_handle_local_cmd or _TEST_JOBS)",
        not undispatched,
        detail=f"undispatched: {undispatched}" if undispatched else f"{len(local_cmds)} local cmds OK",
    )

    # ── Check 8: _TEST_JOBS has the four expected entries ─────────────────────
    present_jobs = set(test_jobs.keys())
    missing_jobs = _EXPECTED_TEST_JOBS - present_jobs
    extra_keys   = present_jobs - _EXPECTED_TEST_JOBS
    _check(
        "_TEST_JOBS contains all four expected test commands",
        not missing_jobs,
        detail=(f"missing: {sorted(missing_jobs)}" if missing_jobs
                else f"{len(present_jobs)} entries OK"),
    )
    if extra_keys:
        print(f"      (note: additional _TEST_JOBS entries: {sorted(extra_keys)})")

    # ── Check 9: _TEST_JOBS argv has no pytest-only flags ────────────────────
    bad_argv: list[str] = []
    for cmd, (name, argv) in test_jobs.items():
        for arg in argv:
            for flag in _PYTEST_ONLY_FLAGS:
                if arg.startswith(flag):
                    bad_argv.append(f"{cmd}: {arg!r}")
    _check(
        "_TEST_JOBS argv contains no pytest-only flags",
        not bad_argv,
        detail=f"violations: {bad_argv}" if bad_argv else "",
    )

    # ── Check 10: Required paths exist ───────────────────────────────────────
    venv_py  = Path(getattr(bot_mod, "VENV_PY",  ""))
    adwi_cli = Path(getattr(bot_mod, "ADWI_CLI", ""))
    required = [
        ("VENV_PY",                       venv_py),
        ("ADWI_CLI",                      adwi_cli),
        ("job_runner.py",                 JR_PATH),
        ("smoke_telegram_jobs.py",        SMOKE_PATH),
        ("validate_telegram_bridge.py",   Path(__file__).resolve()),
        ("e2e_auto_loop.py",              E2E_LOOP_PATH),
        ("telegram_e2e_summary.py",       E2E_SUMM_PATH),
        ("adwi-e2e-status-reader",        E2E_STAT_PATH),
    ]
    missing_paths = [(lbl, p) for lbl, p in required if not p.exists()]
    _check(
        "Required runtime paths exist",
        not missing_paths,
        detail=(f"missing: {[lbl for lbl, _ in missing_paths]}" if missing_paths
                else f"{len(required)} paths OK"),
    )
    for lbl, p in missing_paths:
        _sub(lbl, False, str(p))

    # ── Check 11: HELP_TEXT contains dynamic count ────────────────────────────
    help_text: str = getattr(bot_mod, "HELP_TEXT", "")
    n = str(len(tg_cmds))
    _check(
        "HELP_TEXT includes dynamic command count",
        n in help_text,
        detail=f"expected {n!r} in HELP_TEXT",
    )

    # ── Check 12: MENU_TEXT contains dynamic count ────────────────────────────
    menu_text: str = getattr(bot_mod, "MENU_TEXT", "")
    _check(
        "MENU_TEXT includes dynamic command count",
        n in menu_text,
        detail=f"expected {n!r} in MENU_TEXT",
    )

    # ── Summary ───────────────────────────────────────────────────────────────
    total = _pass_count + _fail_count
    print(f"\n{_pass_count}/{total} checks passed")
    if _fail_count == 0:
        print("PASS")
        return 0
    print("FAIL")
    return 1


if __name__ == "__main__":
    sys.exit(main())
