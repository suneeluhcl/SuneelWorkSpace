#!/usr/bin/env python3
"""Autolab Runner — safe gated execution of workspace experiments.
CLI: python3 lab/autolab/runner.py [--experiment exp_001] [--dry-run] [--safe-only]
"""
import json
import os
import sys
import shutil
import subprocess
import argparse
from pathlib import Path
from datetime import datetime

WORKSPACE = Path(os.environ.get('WORKSPACE', Path.home() / 'SuneelWorkSpace'))
ACTIVE_DIR = WORKSPACE / 'lab/autolab/experiments/active'
ROLLBACK_DIR = WORKSPACE / 'lab/autolab/experiments/rollback'
LOG_FILE = WORKSPACE / 'blood/logs/autolab_runner.log'


def log(msg: str):
    timestamp = datetime.now().isoformat()
    line = f"[{timestamp}] {msg}"
    print(line)
    LOG_FILE.parent.mkdir(parents=True, exist_ok=True)
    with open(LOG_FILE, 'a') as f:
        f.write(line + '\n')


def load_experiment(path: Path) -> dict:
    with open(path) as f:
        return json.load(f)


def save_experiment(exp: dict, path: Path):
    with open(path, 'w') as f:
        json.dump(exp, f, indent=2)


def run_command(cmd: str, dry_run: bool = False) -> tuple[int, str]:
    """Run a shell command; return (returncode, output)."""
    if dry_run:
        return 0, f"[DRY RUN] {cmd}"
    try:
        result = subprocess.run(
            cmd, shell=True, capture_output=True, text=True,
            timeout=120, cwd=str(WORKSPACE)
        )
        output = (result.stdout + result.stderr).strip()
        return result.returncode, output
    except subprocess.TimeoutExpired:
        return 1, "TIMEOUT after 120s"
    except Exception as e:
        return 1, str(e)


def measure_baseline(exp: dict, dry_run: bool = False) -> str:
    cmd = exp.get('measurement_command', '')
    if not cmd or cmd == 'echo \'manual_review_required\'':
        return 'manual_review_required'
    rc, output = run_command(cmd, dry_run=dry_run)
    return output.strip() if rc == 0 else 'measurement_failed'


def take_snapshot(exp: dict, dry_run: bool = False):
    """Copy target files to rollback directory."""
    exp_id = exp['experiment_id']
    rollback_path = ROLLBACK_DIR / exp_id
    if dry_run:
        print(f"    [DRY RUN] Would snapshot to {rollback_path}")
        return str(rollback_path)

    rollback_path.mkdir(parents=True, exist_ok=True)

    for action in exp.get('actions', []):
        target = action.get('target', '')
        if not target:
            continue
        src = WORKSPACE / target
        if src.is_file():
            dst = rollback_path / Path(target).name
            shutil.copy2(src, dst)
            log(f"  Snapshot: {target} → {dst}")
        elif src.is_dir():
            dst = rollback_path / Path(target).name
            if dst.exists():
                shutil.rmtree(dst)
            shutil.copytree(src, dst)
            log(f"  Snapshot dir: {target} → {dst}")

    return str(rollback_path)


def execute_experiment(exp: dict, exp_path: Path, dry_run: bool = False) -> bool:
    """Execute all actions in an experiment. Returns True on success."""
    exp_id = exp['experiment_id']
    name = exp['name']

    log(f"▶ Running SAFE experiment: {name}")
    print(f"\n{'─'*60}")
    print(f"Experiment: {name}")
    print(f"Hypothesis: {exp.get('hypothesis', 'N/A')[:100]}")
    print(f"Actions: {len(exp.get('actions', []))}")

    # Take snapshot
    rollback_path = take_snapshot(exp, dry_run)

    # Record baseline
    baseline = measure_baseline(exp, dry_run)
    print(f"Baseline: {baseline}")
    exp['baseline_value'] = baseline
    exp['started_at'] = datetime.now().isoformat()
    exp['rollback_path'] = rollback_path

    # Execute each action
    for i, action in enumerate(exp.get('actions', []), 1):
        cmd = action.get('command', '')
        desc = action.get('description', cmd[:60])
        print(f"\n  [{i}] {desc}")
        print(f"      $ {cmd[:80]}")

        rc, output = run_command(cmd, dry_run)
        if rc != 0:
            log(f"  ❌ Action failed: {cmd} → {output[:200]}")
            exp['status'] = 'failed'
            if not dry_run:
                save_experiment(exp, exp_path)
            return False

        if output:
            print(f"      → {output[:200]}")
        log(f"  ✅ Action {i} complete: {desc[:60]}")

    exp['status'] = 'evaluating'
    if not dry_run:
        save_experiment(exp, exp_path)

    # Call evaluator
    log(f"Calling evaluator for {exp_id}...")
    rc, output = run_command(
        f"python3 {WORKSPACE}/lab/autolab/evaluator.py --experiment {exp_id}",
        dry_run
    )
    if output:
        print(f"\n{output}")

    return True


def process_controlled(exp: dict, exp_path: Path, dry_run: bool = False) -> bool:
    """Show plan and ask for confirmation before running."""
    name = exp['name']
    print(f"\n{'='*60}")
    print(f"CONTROLLED Experiment: {name}")
    print(f"Hypothesis: {exp.get('hypothesis', '')[:120]}")
    print(f"\nActions:")
    for i, a in enumerate(exp.get('actions', []), 1):
        print(f"  {i}. {a.get('description', a.get('command', '?')[:60])}")

    if dry_run:
        print(f"\n[DRY RUN] Would prompt: Run this experiment? (y/n)")
        return False

    try:
        reply = input("\nRun this experiment? (y/n): ").strip().lower()
    except (EOFError, KeyboardInterrupt):
        reply = 'n'

    if reply == 'y':
        return execute_experiment(exp, exp_path, dry_run)
    else:
        exp['status'] = 'skipped'
        save_experiment(exp, exp_path)
        log(f"Skipped CONTROLLED experiment: {name}")
        print(f"Skipped: {name}")
        return False


def process_restricted(exp: dict, exp_path: Path, dry_run: bool = False) -> bool:
    """Require justification before running RESTRICTED experiments."""
    name = exp['name']
    print(f"\n{'='*60}")
    print(f"⛔ RESTRICTED experiment requires explicit justification: {name}")

    if dry_run:
        print("[DRY RUN] Would prompt for justification")
        return False

    try:
        justification = input("Provide justification or type 'skip': ").strip()
    except (EOFError, KeyboardInterrupt):
        justification = 'skip'

    if justification.lower() == 'skip' or not justification:
        exp['status'] = 'skipped'
        save_experiment(exp, exp_path)
        log(f"Skipped RESTRICTED experiment: {name}")
        return False

    log(f"RESTRICTED experiment justified: {name} | justification: {justification}")
    exp['notes'] = (exp.get('notes', '') + f"\nJustification: {justification}").strip()
    return process_controlled(exp, exp_path, dry_run)


def load_queue(experiment_filter=None, safe_only=False) -> list[tuple[dict, Path]]:
    """Load queued experiments from active/ directory."""
    if not ACTIVE_DIR.exists():
        return []

    experiments = []
    for exp_file in sorted(ACTIVE_DIR.glob('*.json')):
        try:
            exp = load_experiment(exp_file)
        except Exception as e:
            log(f"Could not load {exp_file.name}: {e}")
            continue

        if exp.get('status') != 'queued':
            continue

        if experiment_filter and exp.get('experiment_id') != experiment_filter:
            continue

        if safe_only and exp.get('execution_level') != 'SAFE':
            continue

        experiments.append((exp, exp_file))

    return experiments


def main():
    parser = argparse.ArgumentParser(description='Autolab experiment runner')
    parser.add_argument('--experiment', help='Run only a specific experiment ID')
    parser.add_argument('--dry-run', action='store_true', help='Preview without executing')
    parser.add_argument('--safe-only', action='store_true', help='Only run SAFE-level experiments')
    args = parser.parse_args()

    log(f"Runner started | dry_run={args.dry_run} safe_only={args.safe_only} filter={args.experiment}")

    queue = load_queue(args.experiment, args.safe_only)

    if not queue:
        print("No queued experiments found.")
        if args.experiment:
            print(f"  Experiment '{args.experiment}' not found or not queued.")
        elif args.safe_only:
            print("  No SAFE-level queued experiments.")
        return

    print(f"\n{'='*60}")
    print(f"  Autolab Runner — {datetime.now():%Y-%m-%d %H:%M:%S}")
    print(f"  Experiments to process: {len(queue)}")
    if args.dry_run:
        print("  MODE: DRY RUN (no changes)")
    print(f"{'='*60}")

    success_count = 0
    for exp, exp_path in queue:
        level = exp.get('execution_level', 'CONTROLLED')

        if level == 'SAFE':
            ok = execute_experiment(exp, exp_path, args.dry_run)
        elif level == 'CONTROLLED':
            ok = process_controlled(exp, exp_path, args.dry_run)
        elif level == 'RESTRICTED':
            ok = process_restricted(exp, exp_path, args.dry_run)
        else:
            log(f"Unknown execution level '{level}' for {exp['experiment_id']}")
            ok = False

        if ok:
            success_count += 1

    print(f"\n{'='*60}")
    print(f"  Processed: {len(queue)} | Succeeded: {success_count}")
    print(f"{'='*60}\n")
    log(f"Runner complete | processed={len(queue)} succeeded={success_count}")


if __name__ == '__main__':
    main()
