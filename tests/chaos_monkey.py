#!/usr/bin/env python3
"""
tests/chaos_monkey.py

Overnight chaos-engineering injector for SuneelWorkSpace.

Injects one safe anomaly per run cycle, verifies that the health score drops
(or test count increases), triggers the autonomous repair loop, then verifies
that the system healed.  Every anomaly is reversible; the monkey always cleans
up after itself regardless of whether healing succeeded.

Usage:
    python3 tests/chaos_monkey.py [--dry-run] [--chaos-type <type>]

Chaos types:
    break_symlink   — rename the target of a non-essential hands/bin symlink
    corrupt_json    — inject an invalid key into a regeneratable JSON cache
    delete_cache    — delete a regeneratable cache file
    bad_test_syntax — write a temp test file with a deliberate SyntaxError

Wired into hands/automation/dag/pipelines/night_shift.yaml as 'chaos_test'.
"""

import json
import os
import random
import shutil
import subprocess
import sys
import tempfile
import time
from datetime import datetime, timezone
from pathlib import Path

WORKSPACE = Path(os.path.expanduser("~/SuneelWorkSpace"))
sys.path.insert(0, str(WORKSPACE))
os.chdir(WORKSPACE)

LOG_PATH = WORKSPACE / "blood/logs/chaos_monkey.jsonl"

# ── safe chaos targets ─────────────────────────────────────────────────────────

# Non-critical symlinks that can be temporarily broken without affecting startup
_SYMLINK_CANDIDATES = [
    "hands/bin/vault-sync",
    "hands/bin/log-learn",
    "hands/bin/daily-evolve",
    "hands/bin/sidecar-start",
]

# Regeneratable JSON files safe to corrupt
_JSON_CACHE_CANDIDATES = [
    "spine/readme_health_cache.json",
    "spine/state/readme_health_cache.json",
    "brain/anticipation/prediction_memory.json",
]

# Regeneratable cache files safe to delete
_CACHE_FILE_CANDIDATES = [
    "brain/anticipation/prediction_memory.json",
    "spine/readme_health_cache.json",
]

# Temp test file that chaos monkey will create and then remove
_BAD_TEST_FILE = WORKSPACE / "tests/chaos_test_temp.py"


# ── utilities ─────────────────────────────────────────────────────────────────

def _log(record: dict) -> None:
    LOG_PATH.parent.mkdir(parents=True, exist_ok=True)
    with LOG_PATH.open("a") as f:
        f.write(json.dumps(record) + "\n")


def _run(cmd: list[str], timeout: int = 120) -> tuple[int, str]:
    r = subprocess.run(cmd, cwd=WORKSPACE, capture_output=True, text=True, timeout=timeout)
    return r.returncode, (r.stdout + r.stderr).strip()


def _read_health() -> dict:
    p = WORKSPACE / "spine/state/WORKSPACE_HEALTH.json"
    try:
        return json.loads(p.read_text())
    except Exception:
        return {}


def _read_test_summary() -> dict:
    """Run the full test suite and return a summary dict."""
    rc, output = _run(
        [sys.executable, "-m", "pytest", "tests/", "-q", "--tb=no", "--no-header"],
        timeout=180,
    )
    lines = output.splitlines()
    summary_line = next((l for l in reversed(lines) if "passed" in l or "failed" in l), "")
    return {"returncode": rc, "summary": summary_line, "output": output[-2000:]}


# ── chaos injectors ───────────────────────────────────────────────────────────

def _inject_break_symlink(dry_run: bool) -> dict | None:
    """Break a non-essential bin symlink by renaming its target."""
    for candidate in _SYMLINK_CANDIDATES:
        p = WORKSPACE / candidate
        if p.is_symlink():
            real = p.resolve(strict=False)
            if real.exists():
                broken_name = real.with_suffix(".chaos_backup")
                if not dry_run:
                    real.rename(broken_name)
                return {
                    "chaos_type": "break_symlink",
                    "symlink": candidate,
                    "original_target": str(real),
                    "backup_name": str(broken_name),
                }
    return None


def _restore_break_symlink(info: dict) -> None:
    backup = Path(info["backup_name"])
    original = Path(info["original_target"])
    if backup.exists():
        backup.rename(original)


def _inject_corrupt_json(dry_run: bool) -> dict | None:
    """Inject an invalid key into a regeneratable JSON cache file."""
    for candidate in _JSON_CACHE_CANDIDATES:
        p = WORKSPACE / candidate
        if p.exists():
            try:
                data = json.loads(p.read_text())
                original_text = p.read_text()
                data["__chaos_monkey__"] = "injected_bad_value_" + str(time.time())
                if not dry_run:
                    p.write_text(json.dumps(data, indent=2))
                return {
                    "chaos_type": "corrupt_json",
                    "file": candidate,
                    "original_text": original_text,
                }
            except Exception:
                continue
    return None


def _restore_corrupt_json(info: dict) -> None:
    p = WORKSPACE / info["file"]
    p.write_text(info["original_text"])


def _inject_delete_cache(dry_run: bool) -> dict | None:
    """Delete a regeneratable cache file."""
    for candidate in _CACHE_FILE_CANDIDATES:
        p = WORKSPACE / candidate
        if p.exists():
            original_text = p.read_text()
            if not dry_run:
                p.unlink()
            return {
                "chaos_type": "delete_cache",
                "file": candidate,
                "original_text": original_text,
            }
    return None


def _restore_delete_cache(info: dict) -> None:
    p = WORKSPACE / info["file"]
    if not p.exists():
        p.parent.mkdir(parents=True, exist_ok=True)
        p.write_text(info["original_text"])


def _inject_bad_test_syntax(dry_run: bool) -> dict | None:
    """Write a temp test file with a deliberate SyntaxError."""
    if not dry_run:
        _BAD_TEST_FILE.write_text(
            "# chaos_monkey temp file — deleted after repair cycle\n"
            "def test_chaos_syntax_error(\n"
            "    # Deliberate unclosed parenthesis — SyntaxError\n"
        )
    return {
        "chaos_type": "bad_test_syntax",
        "file": str(_BAD_TEST_FILE.relative_to(WORKSPACE)),
    }


def _restore_bad_test_syntax(info: dict) -> None:
    if _BAD_TEST_FILE.exists():
        _BAD_TEST_FILE.unlink()


# ── chaos type registry ───────────────────────────────────────────────────────

_CHAOS = {
    "break_symlink":   (_inject_break_symlink,   _restore_break_symlink),
    "corrupt_json":    (_inject_corrupt_json,     _restore_corrupt_json),
    "delete_cache":    (_inject_delete_cache,     _restore_delete_cache),
    "bad_test_syntax": (_inject_bad_test_syntax,  _restore_bad_test_syntax),
}


# ── main chaos cycle ──────────────────────────────────────────────────────────

def run_chaos_cycle(chaos_type: str | None = None, dry_run: bool = False) -> dict:
    ts = datetime.now(timezone.utc).isoformat()
    if chaos_type is None:
        chaos_type = random.choice(list(_CHAOS.keys()))

    inject_fn, restore_fn = _CHAOS[chaos_type]
    print(f"\n[chaos-monkey] {ts}")
    print(f"  Chaos type : {chaos_type}")
    print(f"  Dry run    : {dry_run}")

    # ── 1. Baseline health ───────────────────────────────────────────────────
    health_before = _read_health()
    score_before = health_before.get("health_score", 0)
    issues_before = len(health_before.get("issues", []))
    test_before = _read_test_summary()
    print(f"  Health before: {score_before}/100 | issues={issues_before}")
    print(f"  Tests before : {test_before['summary']}")

    # ── 2. Inject anomaly ────────────────────────────────────────────────────
    print(f"\n  Injecting: {chaos_type}…")
    chaos_info = inject_fn(dry_run)
    if chaos_info is None:
        print("  No suitable target found — skipping chaos cycle")
        return {"status": "skipped", "chaos_type": chaos_type, "ts": ts}

    print(f"  Injected  : {chaos_info}")

    result: dict = {
        "ts": ts,
        "chaos_type": chaos_type,
        "chaos_info": {k: v for k, v in chaos_info.items() if k != "original_text"},
        "dry_run": dry_run,
        "score_before": score_before,
        "issues_before": issues_before,
    }

    if dry_run:
        print("  [dry-run] Skipping health check and repair loop")
        return result | {"status": "dry_run"}

    # Brief pause so filesystem settles
    time.sleep(1)

    # ── 3. Verify impact — health should drop or test failures should appear ─
    health_after_inject = _read_health()
    score_after_inject = health_after_inject.get("health_score", 0)
    issues_after_inject = len(health_after_inject.get("issues", []))
    test_after_inject = _read_test_summary()

    impact_confirmed = (
        score_after_inject < score_before
        or issues_after_inject > issues_before
        or test_after_inject["returncode"] != 0
    )
    print(f"\n  Health after inject: {score_after_inject}/100 | issues={issues_after_inject}")
    print(f"  Tests after inject : {test_after_inject['summary']}")
    print(f"  Impact confirmed   : {impact_confirmed}")

    result.update({
        "score_after_inject": score_after_inject,
        "issues_after_inject": issues_after_inject,
        "test_summary_after_inject": test_after_inject["summary"],
        "impact_confirmed": impact_confirmed,
    })

    # ── 4. Run autonomous repair loop ────────────────────────────────────────
    print("\n  Running autonomous repair loop…")
    repair_rc, repair_output = _run(
        [sys.executable, "tests/autonomous_repair_loop.py"],
        timeout=600,
    )
    print(f"  Repair loop exit: {repair_rc}")
    print(f"  Repair output   : {repair_output[-300:]}")

    # ── 5. Verify healing ────────────────────────────────────────────────────
    health_healed = _read_health()
    score_healed = health_healed.get("health_score", 0)
    issues_healed = len(health_healed.get("issues", []))
    test_healed = _read_test_summary()

    healed = (
        score_healed >= score_before - 5           # score recovered (±5 tolerance)
        and issues_healed <= issues_before + 2     # issue count recovered
        and test_healed["returncode"] == 0         # tests passing
    )
    print(f"\n  Health healed  : {score_healed}/100 | issues={issues_healed}")
    print(f"  Tests healed   : {test_healed['summary']}")
    print(f"  Healing success: {healed}")

    result.update({
        "repair_rc": repair_rc,
        "score_healed": score_healed,
        "issues_healed": issues_healed,
        "test_summary_healed": test_healed["summary"],
        "healed": healed,
    })

    # ── 6. Always restore anomaly regardless of healing outcome ──────────────
    print("\n  Restoring chaos anomaly…")
    try:
        restore_fn(chaos_info)
        result["restored"] = True
        print("  Anomaly restored.")
    except Exception as e:
        result["restored"] = False
        result["restore_error"] = str(e)
        print(f"  Restore error: {e}")

    # ── 7. Log result ─────────────────────────────────────────────────────────
    status = "healed" if healed else ("impact_no_heal" if impact_confirmed else "no_impact")
    result["status"] = status
    _log(result)

    print(f"\n  [chaos-monkey] Cycle complete — status={status}")
    return result


def main() -> None:
    import argparse

    parser = argparse.ArgumentParser(description="SuneelWorkSpace chaos engineering injector")
    parser.add_argument("--dry-run", action="store_true", help="Inject anomaly but skip repair + health check")
    parser.add_argument("--chaos-type", choices=list(_CHAOS.keys()), default=None,
                        help="Specific chaos type (default: random)")
    args = parser.parse_args()

    result = run_chaos_cycle(chaos_type=args.chaos_type, dry_run=args.dry_run)
    rc = 0 if result.get("status") in ("healed", "skipped", "dry_run") else 1
    sys.exit(rc)


if __name__ == "__main__":
    main()
