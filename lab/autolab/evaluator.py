#!/usr/bin/env python3
"""Autolab Evaluator — scores experiments by before/after metric comparison.
CLI: python3 lab/autolab/evaluator.py --experiment <exp_id>
"""
import json
import os
import sys
import subprocess
import argparse
from pathlib import Path
from datetime import datetime

WORKSPACE = Path(os.environ.get('WORKSPACE', Path.home() / 'SuneelWorkSpace'))
ACTIVE_DIR = WORKSPACE / 'lab/autolab/experiments/active'
COMPLETED_DIR = WORKSPACE / 'lab/autolab/experiments/completed'
LOG_FILE = WORKSPACE / 'blood/logs/autolab_runner.log'
IMPROVEMENTS_FILE = WORKSPACE / 'brain/system/daily_improvements.md'


def log(msg: str):
    timestamp = datetime.now().isoformat()
    line = f"[{timestamp}] {msg}"
    LOG_FILE.parent.mkdir(parents=True, exist_ok=True)
    with open(LOG_FILE, 'a') as f:
        f.write(line + '\n')


def find_experiment(exp_id: str) -> tuple[dict, Path] | tuple[None, None]:
    for search_dir in [ACTIVE_DIR, COMPLETED_DIR]:
        for f in search_dir.glob('*.json'):
            try:
                data = json.loads(f.read_text())
                if data.get('experiment_id') == exp_id or f.stem == exp_id:
                    return data, f
            except Exception:
                pass
    return None, None


def run_measurement(cmd: str) -> str:
    if not cmd or 'manual_review_required' in cmd:
        return 'manual_review_required'
    try:
        result = subprocess.run(
            cmd, shell=True, capture_output=True, text=True,
            timeout=60, cwd=str(WORKSPACE)
        )
        return (result.stdout + result.stderr).strip()
    except Exception as e:
        return f'error: {e}'


def parse_numeric(value: str) -> float | None:
    if not value:
        return None
    try:
        return float(value.strip().split('\n')[-1])
    except (ValueError, AttributeError):
        return None


def get_manual_score() -> float:
    """Prompt user for a manual quality score 1-10."""
    print("\n📋 Manual review required.")
    print("   Rate the experiment outcome from 1-10:")
    print("   1-3 = regression, 4-6 = neutral, 7-10 = improvement")
    try:
        raw = input("Score (1-10): ").strip()
        score = float(raw)
        score = max(1.0, min(10.0, score))
        # Normalize to delta: 5.5 = 0 delta baseline
        return score - 5.5
    except (ValueError, EOFError, KeyboardInterrupt):
        print("Using neutral score (0 delta)")
        return 0.0


def append_improvement_log(exp: dict, delta: float):
    """Append experiment summary to daily_improvements.md."""
    IMPROVEMENTS_FILE.parent.mkdir(parents=True, exist_ok=True)
    today = datetime.now().strftime("%Y-%m-%d")
    status = "✅ improved" if delta >= 0 else "❌ regression"
    entry = (
        f"\n### [{today}] {exp['name']}\n"
        f"- Hypothesis: {exp.get('hypothesis', 'N/A')[:100]}\n"
        f"- Baseline: {exp.get('baseline_value', 'N/A')}\n"
        f"- Result: {exp.get('result_value', 'N/A')}\n"
        f"- Delta: {delta:+.2f} — {status}\n"
        f"- Status: {exp.get('status', '?')}\n"
    )
    with open(IMPROVEMENTS_FILE, 'a') as f:
        f.write(entry)


def main():
    parser = argparse.ArgumentParser(description='Autolab experiment evaluator')
    parser.add_argument('--experiment', required=True, help='Experiment ID to evaluate')
    parser.add_argument('--rollback', action='store_true', help='Rollback this experiment')
    args = parser.parse_args()

    exp, exp_path = find_experiment(args.experiment)
    if exp is None:
        print(f"❌ Experiment '{args.experiment}' not found")
        sys.exit(1)

    exp_id = exp['experiment_id']
    name = exp['name']

    print(f"\n📊 Evaluating: {name}")

    # Run measurement command to get result
    measurement_cmd = exp.get('measurement_command', '')
    result_raw = run_measurement(measurement_cmd)
    print(f"   Measurement result: {result_raw[:100]}")

    # Compute score delta
    if result_raw == 'manual_review_required':
        delta = get_manual_score()
        result_value = f"manual:{delta+5.5:.1f}/10"
    else:
        baseline_raw = exp.get('baseline_value', '')
        baseline_num = parse_numeric(str(baseline_raw))
        result_num = parse_numeric(result_raw)

        if baseline_num is not None and result_num is not None:
            delta = result_num - baseline_num
            result_value = result_raw
        else:
            # Can't compute numerically — treat as neutral
            delta = 0.0
            result_value = result_raw
            print("   ⚠️  Could not parse numeric values — using neutral delta")

    exp['result_value'] = result_value
    exp['score_delta'] = round(delta, 4)
    exp['completed_at'] = datetime.now().isoformat()

    if delta >= 0:
        exp['status'] = 'completed_positive'
        print(f"   ✅ Positive result (delta: {delta:+.2f})")
        log(f"Experiment {exp_id} completed positively (delta: {delta:+.2f})")
    else:
        exp['status'] = 'completed_negative'
        print(f"   ⚠️  Experiment {name} shows regression (delta: {delta:.2f})")
        log(f"Experiment {exp_id} completed with regression (delta: {delta:.2f})")

        try:
            reply = input(f"Rollback? (y/n): ").strip().lower()
        except (EOFError, KeyboardInterrupt):
            reply = 'n'

        if reply == 'y':
            rc = os.system(
                f"python3 {WORKSPACE}/lab/autolab/promotion_gate.py --rollback {exp_id}"
            )
            if rc == 0:
                print(f"   ↩️  Rolled back successfully")
            else:
                print(f"   ❌ Rollback failed")
        else:
            print("   Keeping result, moving to completed/ with negative flag")
            log(f"Kept negative result for {exp_id} (user declined rollback)")

    # Move to completed/
    COMPLETED_DIR.mkdir(parents=True, exist_ok=True)
    completed_path = COMPLETED_DIR / exp_path.name
    with open(completed_path, 'w') as f:
        json.dump(exp, f, indent=2)

    # Remove from active if still there
    if exp_path.parent == ACTIVE_DIR and exp_path.exists():
        exp_path.unlink()

    # Append to daily improvements
    append_improvement_log(exp, delta)

    print(f"\n   Archived → lab/autolab/experiments/completed/{exp_path.name}")
    print(f"   Logged → brain/system/daily_improvements.md")

    # Auto-promote if SAFE + positive
    if exp.get('execution_level') == 'SAFE' and delta >= 0:
        os.system(
            f"python3 {WORKSPACE}/lab/autolab/promotion_gate.py --promote {exp_id} 2>/dev/null || true"
        )


if __name__ == '__main__':
    main()
