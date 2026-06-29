#!/usr/bin/env python3
"""
tests/scenario_runner.py

Stress-test scenario simulator for SuneelWorkSpace.

Injects controlled faults that target different layers of the workspace,
then verifies:
  1. The nerve system fires appropriate alerts (health score drops or
     test failures appear).
  2. The autonomous repair loop successfully heals the workspace.

All faults are 100% reversible — cleanup runs in a finally block
regardless of test outcome.

Scenarios:
  corrupt_state_json      — write invalid JSON to spine/state/CURRENT_STATE.json
  bad_code_stub           — inject a SyntaxError into a temp lab/autolab/ file
  remove_exec_permissions — chmod 644 on a hands/scripts/*.sh file
  mock_telemetry_error    — append a CRITICAL error record to blood/logs/

CLI:
    python3 tests/scenario_runner.py                          # run all
    python3 tests/scenario_runner.py --scenario corrupt_state_json
    python3 tests/scenario_runner.py --list
    python3 tests/scenario_runner.py --dry-run
"""

import json
import os
import stat
import subprocess
import sys
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Callable

WORKSPACE = Path(os.path.expanduser("~/SuneelWorkSpace"))
sys.path.insert(0, str(WORKSPACE))
os.chdir(WORKSPACE)

LOG_PATH = WORKSPACE / "blood/logs/scenario_runner.jsonl"
_VENV_PY = str(WORKSPACE / ".venv/bin/python3")
PYTHON = _VENV_PY if os.path.exists(_VENV_PY) else sys.executable


# ── scenario base ──────────────────────────────────────────────────────────────

class Scenario:
    name: str = "base"
    description: str = ""

    def inject(self) -> dict:
        """Apply the fault. Return a state dict for restore()."""
        raise NotImplementedError

    def restore(self, state: dict) -> None:
        """Always-called cleanup. Undo inject() using the state dict."""
        raise NotImplementedError


# ── scenario 1: corrupt state JSON ────────────────────────────────────────────

class CorruptStateJson(Scenario):
    name = "corrupt_state_json"
    description = "Write invalid JSON to spine/state/CURRENT_STATE.json — breaks health readers"

    TARGET = WORKSPACE / "spine/state/CURRENT_STATE.json"

    def inject(self) -> dict:
        original = self.TARGET.read_text() if self.TARGET.exists() else None
        self.TARGET.parent.mkdir(parents=True, exist_ok=True)
        self.TARGET.write_text(
            '{"health_score": "NOT_A_NUMBER", "issues": [{"bad": true,}\n\n'
        )
        return {"original": original}

    def restore(self, state: dict) -> None:
        if state.get("original") is not None:
            self.TARGET.write_text(state["original"])
        elif self.TARGET.exists():
            self.TARGET.unlink()


# ── scenario 2: bad code stub ──────────────────────────────────────────────────

class BadCodeStub(Scenario):
    name = "bad_code_stub"
    description = "Create a Python file with a deliberate SyntaxError in lab/autolab/"

    TARGET = WORKSPACE / "lab/autolab/scenario_stub_temp.py"

    def inject(self) -> dict:
        self.TARGET.write_text(
            "# scenario_runner temp stub — deleted after repair cycle\n"
            "def broken_function(\n"
            "    # Unclosed paren — deliberate SyntaxError for stress test\n"
        )
        return {"path": str(self.TARGET)}

    def restore(self, state: dict) -> None:
        p = Path(state.get("path", ""))
        if p.exists():
            p.unlink()


# ── scenario 3: remove executable permissions ──────────────────────────────────

class RemoveExecPermissions(Scenario):
    name = "remove_exec_permissions"
    description = "chmod 644 a hands/scripts/*.sh file — breaks direct execution"

    def _find_target(self) -> Path | None:
        scripts = sorted((WORKSPACE / "hands/scripts").glob("*.sh"))
        for s in scripts:
            # Skip anything safety-critical
            if "agent-finish" in s.name or "night-shift" in s.name:
                continue
            if os.access(s, os.X_OK):
                return s
        return None

    def inject(self) -> dict:
        target = self._find_target()
        if target is None:
            return {"target": None}
        original_mode = oct(target.stat().st_mode)
        target.chmod(0o644)
        return {"target": str(target), "original_mode": original_mode}

    def restore(self, state: dict) -> None:
        if not state.get("target"):
            return
        p = Path(state["target"])
        if p.exists():
            # Restore to original or safe executable mode
            try:
                original = int(state.get("original_mode", "0o755"), 8)
            except Exception:
                original = 0o755
            p.chmod(original)


# ── scenario 4: mock telemetry error ──────────────────────────────────────────

class MockTelemetryError(Scenario):
    name = "mock_telemetry_error"
    description = "Append a CRITICAL error record to blood/logs/anomaly_log.jsonl"

    TARGET = WORKSPACE / "blood/logs/anomaly_log.jsonl"

    def inject(self) -> dict:
        self.TARGET.parent.mkdir(parents=True, exist_ok=True)
        # Remember byte offset so we can trim this exact record
        offset = self.TARGET.stat().st_size if self.TARGET.exists() else 0
        record = {
            "ts": datetime.now(timezone.utc).isoformat(),
            "severity": "critical",
            "organ": "blood",
            "code": "scenario_mock_critical",
            "message": "Simulated CRITICAL telemetry anomaly from scenario_runner",
        }
        with self.TARGET.open("a") as f:
            f.write(json.dumps(record) + "\n")
        return {"offset": offset}

    def restore(self, state: dict) -> None:
        offset = state.get("offset", 0)
        if self.TARGET.exists() and self.TARGET.stat().st_size > offset:
            with self.TARGET.open("rb+") as f:
                f.truncate(offset)


# ── registry ───────────────────────────────────────────────────────────────────

SCENARIOS: dict[str, Scenario] = {
    s.name: s
    for s in [
        CorruptStateJson(),
        BadCodeStub(),
        RemoveExecPermissions(),
        MockTelemetryError(),
    ]
}


# ── runner helpers ─────────────────────────────────────────────────────────────

def _log(record: dict) -> None:
    LOG_PATH.parent.mkdir(parents=True, exist_ok=True)
    with LOG_PATH.open("a") as f:
        f.write(json.dumps(record) + "\n")


def _run(cmd: list[str], timeout: int = 120) -> tuple[int, str]:
    r = subprocess.run(
        cmd, cwd=WORKSPACE, capture_output=True, text=True, timeout=timeout
    )
    return r.returncode, (r.stdout + r.stderr).strip()


def _read_health() -> dict:
    p = WORKSPACE / "spine/state/WORKSPACE_HEALTH.json"
    try:
        return json.loads(p.read_text())
    except Exception:
        return {}


def _run_test_suite() -> dict:
    rc, output = _run(
        [PYTHON, "-m", "pytest", "tests/", "-q", "--tb=no", "--no-header"],
        timeout=180,
    )
    lines = output.splitlines()
    summary = next((l for l in reversed(lines) if "passed" in l or "failed" in l or "error" in l), "")
    failures = sum(1 for l in lines if re.search(r"FAILED|ERROR", l))
    return {"returncode": rc, "summary": summary, "failures": failures}


def _run_repair_loop() -> tuple[int, str]:
    return _run([PYTHON, "tests/autonomous_repair_loop.py"], timeout=600)


# ── run one scenario ───────────────────────────────────────────────────────────

def run_scenario(scenario: Scenario, dry_run: bool = False) -> dict:
    ts = datetime.now(timezone.utc).isoformat()
    print(f"\n[scenario] {ts} — {scenario.name}")
    print(f"  {scenario.description}")
    print(f"  dry_run={dry_run}")

    # Baseline
    health_before = _read_health()
    score_before = health_before.get("health_score", 0)
    tests_before = _run_test_suite()
    print(f"  Baseline: health={score_before}/100 | tests={tests_before['summary']}")

    result: dict = {
        "ts": ts,
        "scenario": scenario.name,
        "dry_run": dry_run,
        "score_before": score_before,
        "tests_before": tests_before["summary"],
    }

    if dry_run:
        return result | {"status": "dry_run"}

    # Inject
    state: dict = {}
    try:
        print(f"  Injecting fault…")
        state = scenario.inject()
        print(f"  Fault injected: {state}")

        time.sleep(1)

        # Verify impact
        health_after = _read_health()
        score_after = health_after.get("health_score", 0)
        tests_after = _run_test_suite()
        impact = (
            score_after < score_before
            or tests_after["failures"] > tests_before["failures"]
            or tests_after["returncode"] != 0
        )
        print(f"  After inject: health={score_after}/100 | tests={tests_after['summary']}")
        print(f"  Impact confirmed: {impact}")

        result.update({
            "score_after_inject": score_after,
            "tests_after_inject": tests_after["summary"],
            "impact_confirmed": impact,
        })

        # Repair
        print(f"  Running repair loop…")
        repair_rc, repair_out = _run_repair_loop()
        print(f"  Repair exit={repair_rc} | {repair_out[-200:]}")

        # Verify healing
        health_healed = _read_health()
        score_healed = health_healed.get("health_score", 0)
        tests_healed = _run_test_suite()
        healed = (
            score_healed >= score_before - 5
            and tests_healed["returncode"] == 0
        )
        print(f"  After repair: health={score_healed}/100 | tests={tests_healed['summary']}")
        print(f"  Healed: {healed}")

        result.update({
            "repair_rc": repair_rc,
            "score_healed": score_healed,
            "tests_healed": tests_healed["summary"],
            "healed": healed,
        })

        status = "healed" if healed else ("impact_no_heal" if impact else "no_impact")
        result["status"] = status

    finally:
        # Always restore
        try:
            scenario.restore(state)
            result["restored"] = True
            print(f"  Fault restored.")
        except Exception as e:
            result["restored"] = False
            result["restore_error"] = str(e)
            print(f"  Restore error: {e}")

    _log(result)
    print(f"  [scenario] status={result.get('status')}")
    return result


def run_all(dry_run: bool = False) -> list[dict]:
    results = []
    for name, scenario in SCENARIOS.items():
        r = run_scenario(scenario, dry_run=dry_run)
        results.append(r)

    passed = sum(1 for r in results if r.get("status") in ("healed", "dry_run"))
    total = len(results)
    print(f"\n[scenario-runner] {passed}/{total} scenarios passed")
    return results


# ── CLI ────────────────────────────────────────────────────────────────────────

def main() -> None:
    import argparse
    parser = argparse.ArgumentParser(description="SuneelWorkSpace stress-test scenario runner")
    parser.add_argument("--scenario", choices=list(SCENARIOS.keys()), default=None)
    parser.add_argument("--dry-run", action="store_true")
    parser.add_argument("--list", action="store_true")
    args = parser.parse_args()

    if args.list:
        for name, s in SCENARIOS.items():
            print(f"  {name:35s} — {s.description}")
        return

    if args.scenario:
        r = run_scenario(SCENARIOS[args.scenario], dry_run=args.dry_run)
        sys.exit(0 if r.get("status") in ("healed", "dry_run", "no_impact") else 1)
    else:
        results = run_all(dry_run=args.dry_run)
        failed = [r for r in results if r.get("status") not in ("healed", "dry_run", "no_impact")]
        sys.exit(len(failed))


if __name__ == "__main__":
    main()
