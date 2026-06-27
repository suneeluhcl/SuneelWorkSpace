#!/usr/bin/env python3
"""Autolab Promotion Gate — promotes or rolls back experiments.
CLI:
  python3 lab/autolab/promotion_gate.py --promote <exp_id>
  python3 lab/autolab/promotion_gate.py --rollback <exp_id>
  python3 lab/autolab/promotion_gate.py --status
"""
import json
import os
import sys
import shutil
import argparse
from pathlib import Path
from datetime import datetime

WORKSPACE = Path(os.environ.get('WORKSPACE', Path.home() / 'SuneelWorkSpace'))
ACTIVE_DIR = WORKSPACE / 'lab/autolab/experiments/active'
COMPLETED_DIR = WORKSPACE / 'lab/autolab/experiments/completed'
ROLLBACK_DIR = WORKSPACE / 'lab/autolab/experiments/rollback'
LOG_FILE = WORKSPACE / 'blood/logs/autolab_runner.log'


def log(msg: str):
    timestamp = datetime.now().isoformat()
    line = f"[{timestamp}] {msg}"
    LOG_FILE.parent.mkdir(parents=True, exist_ok=True)
    with open(LOG_FILE, 'a') as f:
        f.write(line + '\n')


def find_experiment(exp_id: str) -> tuple[dict, Path] | tuple[None, None]:
    for search_dir in [COMPLETED_DIR, ACTIVE_DIR]:
        for f in search_dir.glob('*.json'):
            try:
                data = json.loads(f.read_text())
                if data.get('experiment_id') == exp_id or f.stem == exp_id:
                    return data, f
            except Exception:
                pass
    return None, None


def promote(exp_id: str):
    exp, exp_path = find_experiment(exp_id)
    if exp is None:
        print(f"❌ Experiment '{exp_id}' not found")
        sys.exit(1)

    name = exp['name']
    delta = exp.get('score_delta', 0)
    level = exp.get('execution_level', 'CONTROLLED')

    if delta < 0:
        print(f"❌ Cannot promote {name} — score delta is negative ({delta:.2f})")
        sys.exit(1)

    if level == 'SAFE':
        # Auto-promote
        rollback_path = ROLLBACK_DIR / exp_id
        if rollback_path.exists():
            shutil.rmtree(rollback_path)
        exp['status'] = 'promoted'
        exp['promoted_at'] = datetime.now().isoformat()
        with open(exp_path, 'w') as f:
            json.dump(exp, f, indent=2)
        log(f"Auto-promoted SAFE experiment: {name} (delta: +{delta:.2f})")
        print(f"✅ Experiment '{name}' promoted automatically (SAFE + positive delta: +{delta:.2f})")

    else:
        # CONTROLLED — ask for confirmation
        print(f"\nPromote experiment '{name}' (delta: +{delta:.2f})?")
        try:
            reply = input("(y/n): ").strip().lower()
        except (EOFError, KeyboardInterrupt):
            reply = 'n'

        if reply == 'y':
            rollback_path = ROLLBACK_DIR / exp_id
            if rollback_path.exists():
                shutil.rmtree(rollback_path)
            exp['status'] = 'promoted'
            exp['promoted_at'] = datetime.now().isoformat()
            with open(exp_path, 'w') as f:
                json.dump(exp, f, indent=2)
            log(f"User-promoted CONTROLLED experiment: {name} (delta: +{delta:.2f})")
            print(f"✅ Promoted: {name}")
        else:
            print("Promotion declined — keeping rollback snapshot")
            log(f"User declined promotion of {name}")


def rollback(exp_id: str):
    exp, exp_path = find_experiment(exp_id)
    if exp is None:
        print(f"❌ Experiment '{exp_id}' not found")
        sys.exit(1)

    name = exp['name']
    rollback_path = Path(exp.get('rollback_path', str(ROLLBACK_DIR / exp_id)))

    if not rollback_path.exists():
        print(f"❌ No rollback snapshot found at: {rollback_path}")
        sys.exit(1)

    print(f"Rolling back: {name}")
    print(f"Snapshot: {rollback_path}")

    # Restore files from snapshot
    restored = 0
    for action in exp.get('actions', []):
        target = action.get('target', '')
        if not target:
            continue
        src_backup = rollback_path / Path(target).name
        dst = WORKSPACE / target

        if src_backup.is_file():
            dst.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(src_backup, dst)
            print(f"  Restored: {target}")
            restored += 1
        elif src_backup.is_dir():
            if dst.exists():
                shutil.rmtree(dst)
            shutil.copytree(src_backup, dst)
            print(f"  Restored dir: {target}")
            restored += 1

    exp['status'] = 'rolled_back'
    exp['rolled_back_at'] = datetime.now().isoformat()
    with open(exp_path, 'w') as f:
        json.dump(exp, f, indent=2)

    log(f"Rolled back experiment: {name} | restored {restored} targets")
    print(f"\n↩️  Experiment '{name}' rolled back successfully ({restored} files restored)")

    # Clean up rollback snapshot
    shutil.rmtree(rollback_path, ignore_errors=True)


def status():
    print(f"\n{'='*60}")
    print(f"  Autolab Experiment Status — {datetime.now():%Y-%m-%d %H:%M}")
    print(f"{'='*60}")

    all_experiments = []
    for search_dir, label in [(ACTIVE_DIR, 'ACTIVE'), (COMPLETED_DIR, 'COMPLETED')]:
        if not search_dir.exists():
            continue
        for f in sorted(search_dir.glob('*.json')):
            try:
                exp = json.loads(f.read_text())
                all_experiments.append((label, exp))
            except Exception:
                pass

    if not all_experiments:
        print("  No experiments found.")
        return

    for label, exp in all_experiments:
        exp_id = exp.get('experiment_id', '?')
        name = exp.get('name', '?')[:45]
        status_val = exp.get('status', '?')
        level = exp.get('execution_level', '?')
        delta = exp.get('score_delta')
        delta_str = f" Δ{delta:+.2f}" if delta is not None else ""

        icon = {
            'queued': '⏳',
            'evaluating': '🔄',
            'completed_positive': '✅',
            'completed_negative': '❌',
            'promoted': '🚀',
            'rolled_back': '↩️ ',
            'skipped': '⏭️ ',
            'failed': '💥',
        }.get(status_val, '❓')

        print(f"  {icon} [{level:<12}] {exp_id:<10} {name:<45} {status_val}{delta_str}")

    print()


def main():
    parser = argparse.ArgumentParser(description='Autolab promotion gate')
    parser.add_argument('--promote', metavar='EXP_ID', help='Promote a completed experiment')
    parser.add_argument('--rollback', metavar='EXP_ID', help='Roll back an experiment')
    parser.add_argument('--status', action='store_true', help='Show all experiment status')
    args = parser.parse_args()

    if args.promote:
        promote(args.promote)
    elif args.rollback:
        rollback(args.rollback)
    elif args.status:
        status()
    else:
        parser.print_help()


if __name__ == '__main__':
    main()
