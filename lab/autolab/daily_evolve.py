#!/usr/bin/env python3
"""
lab/autolab/daily_evolve.py
Daily evolution coordinator — runs all learning passes in sequence.
Called nightly by night_shift.yaml or manually via: python3 lab/autolab/daily_evolve.py

Passes:
  1. log_learn_engine     — extract successful repairs → training_data.jsonl
  2. memory_curator       — curate MEMORY.md / DECISIONS.md
  3. experiment_skills    — extract skills from autolab experiments
  4. vault_sync           — refresh Obsidian organ notes
"""

import json
import os
import subprocess
import sys
import time
from datetime import datetime, timezone
from pathlib import Path

WORKSPACE = Path(os.path.expanduser("~/SuneelWorkSpace"))
EVOLVE_LOG = WORKSPACE / "blood/logs/daily_evolve.jsonl"
COMPLETED_DIR = WORKSPACE / "lab/autolab/experiments/completed"
PROMPTED_JSON = WORKSPACE / "lab/autolab/meta/promotion_prompts.json"
TASK_QUEUE = WORKSPACE / "heart/tasks/TASK_QUEUE.md"
_VENV_PY = str(WORKSPACE / ".venv/bin/python3")
PYTHON = _VENV_PY if os.path.exists(_VENV_PY) else sys.executable


def _run_pass(label: str, module_path: str, args: list[str] | None = None) -> dict:
    """Run a Python module as a subprocess pass. Returns status dict."""
    cmd = [PYTHON, str(WORKSPACE / module_path)] + (args or [])
    start = time.monotonic()
    try:
        proc = subprocess.run(
            cmd,
            cwd=str(WORKSPACE),
            capture_output=True,
            text=True,
            timeout=300,
        )
        elapsed = time.monotonic() - start
        return {
            "pass": label,
            "status": "ok" if proc.returncode == 0 else "failed",
            "returncode": proc.returncode,
            "elapsed_s": round(elapsed, 2),
            "output": (proc.stdout + proc.stderr)[-500:],
        }
    except subprocess.TimeoutExpired:
        return {"pass": label, "status": "timeout", "elapsed_s": 300}
    except Exception as e:
        return {"pass": label, "status": "error", "error": str(e)}


def surface_promotion_candidates() -> int:
    """Queue a task for each completed experiment not yet surfaced, so Suneel is
    prompted to promote successful experimental skills to primary skills."""
    if not COMPLETED_DIR.exists():
        return 0
    prompted: set[str] = set()
    if PROMPTED_JSON.exists():
        try:
            prompted = set(json.loads(PROMPTED_JSON.read_text()).get("experiment_ids", []))
        except Exception:
            prompted = set()

    new_lines: list[str] = []
    for exp_file in sorted(COMPLETED_DIR.glob("*.json")):
        try:
            exp = json.loads(exp_file.read_text())
        except Exception:
            continue
        exp_id = exp.get("experiment_id", exp_file.stem)
        if exp_id in prompted:
            continue
        name = exp.get("name", exp_file.stem)
        new_lines.append(
            f"- [autolab] Promote completed experiment `{exp_id}` ({name}) "
            "to a primary skill if it earned its keep — review via `autolab-promote --status`."
        )
        prompted.add(exp_id)

    if not new_lines:
        return 0
    if TASK_QUEUE.exists():
        content = TASK_QUEUE.read_text().rstrip() + "\n" + "\n".join(new_lines) + "\n"
        TASK_QUEUE.write_text(content)
    PROMPTED_JSON.parent.mkdir(parents=True, exist_ok=True)
    PROMPTED_JSON.write_text(json.dumps(
        {"experiment_ids": sorted(prompted),
         "updated_at": datetime.now(timezone.utc).isoformat()}, indent=2))
    return len(new_lines)


def run() -> list[dict]:
    results: list[dict] = []

    print("[daily-evolve] starting evolution passes...")

    passes = [
        ("log_learn",       "lab/autolab/log_learn_engine.py"),
        ("memory_curate",   "brain/memory/memory_curator.py"),
        ("experiment_skills", "lab/autolab/experiment_skill_generator.py"),
        ("vault_sync",      "brain/vault/vault_sync.py"),
        ("autotrainer",     "dna/agents/hermes/ollama_models/autotrainer.py"),
        ("scenario_runner", "tests/scenario_runner.py", ["--dry-run"]),
    ]

    for entry in passes:
        label, path = entry[0], entry[1]
        extra_args = list(entry[2]) if len(entry) > 2 else []
        full = WORKSPACE / path
        if not full.exists():
            results.append({"pass": label, "status": "skipped", "reason": f"not found: {path}"})
            print(f"  [{label}] skipped — {path} not found")
            continue
        print(f"  [{label}] running...", end=" ", flush=True)
        r = _run_pass(label, path, args=extra_args)
        results.append(r)
        print(f"{r['status']} ({r.get('elapsed_s', '?')}s)")

    # Log results
    EVOLVE_LOG.parent.mkdir(parents=True, exist_ok=True)
    record = {
        "ts": datetime.now(timezone.utc).isoformat(),
        "passes": results,
        "ok": sum(1 for r in results if r["status"] == "ok"),
        "failed": sum(1 for r in results if r["status"] == "failed"),
    }
    with open(EVOLVE_LOG, "a") as f:
        f.write(json.dumps(record) + "\n")

    promoted = surface_promotion_candidates()
    if promoted:
        print(f"[daily-evolve] queued {promoted} promotion candidate(s) in TASK_QUEUE.md")

    ok = record["ok"]
    total = len([r for r in results if r["status"] != "skipped"])
    print(f"[daily-evolve] complete: {ok}/{total} passes succeeded")
    return results


if __name__ == "__main__":
    run()
