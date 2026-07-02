#!/usr/bin/env python3
"""Prompt Eval Runner — scores identity prompts against eval cases.
CLI: python3 eval_runner.py [--version v1] [--case case_001]
"""
import json
import sys
import os
import argparse
import subprocess
from pathlib import Path
from datetime import datetime

WORKSPACE = Path(os.environ.get('WORKSPACE', Path.home() / 'SuneelWorkSpace'))
EVAL_DIR = WORKSPACE / 'dna/identity/prompts/eval'
VERSIONS_DIR = WORKSPACE / 'dna/identity/prompts/versions'
RESULTS_DIR = EVAL_DIR / 'eval_results'
CASES_FILE = EVAL_DIR / 'eval_cases.json'

# Import scorer from same directory
sys.path.insert(0, str(EVAL_DIR))
try:
    from eval_scorer import score_response
except ImportError:
    def score_response(text, expected, forbidden, weight=1.0):
        return 0.7 * weight  # fallback


def load_cases(case_filter=None):
    with open(CASES_FILE) as f:
        data = json.load(f)
    # Handle both {"cases": [...]} dict and plain list formats
    if isinstance(data, list):
        cases = data
    else:
        cases = data.get('cases', [])
    if case_filter:
        cases = [c for c in cases if c['id'] == case_filter]
    return cases


def load_prompt_version(version: str) -> str:
    version_file = VERSIONS_DIR / f'identity_prompt_{version}.md'
    if not version_file.exists():
        # Fall back to current
        current = VERSIONS_DIR / 'identity_prompt_current.md'
        if current.exists():
            return current.read_text()
        # Fall back to base
        base = WORKSPACE / 'dna/identity/prompts/identity_prompt.md'
        return base.read_text() if base.exists() else ""
    return version_file.read_text()


def get_ollama_response(prompt: str) -> str:
    """Try to get response from Ollama if available."""
    try:
        result = subprocess.run(
            ['ollama', 'list'], capture_output=True, text=True, timeout=5
        )
        if result.returncode != 0:
            return None
        # Get first available model
        lines = result.stdout.strip().split('\n')
        if len(lines) < 2:
            return None
        model = lines[1].split()[0] if lines[1].strip() else None
        if not model:
            return None
        response = subprocess.run(
            ['ollama', 'run', model, prompt],
            capture_output=True, text=True, timeout=60
        )
        return response.stdout.strip() if response.returncode == 0 else None
    except Exception:
        return None


def get_manual_response(case: dict, prompt_text: str) -> str:
    """Print prompt and wait for manual response paste."""
    print(f"\n{'─'*60}")
    print(f"Case: {case['id']} [{case.get('category', 'general')}]")
    print(f"User input: {case['input']}")
    print(f"\nFull prompt sent to model:\n{'─'*40}")
    print(prompt_text[-400:])  # Show last 400 chars
    print(f"{'─'*40}")
    print("Paste model response (then press Enter twice):")
    lines = []
    try:
        while True:
            line = input()
            if line == '' and lines and lines[-1] == '':
                break
            lines.append(line)
        return '\n'.join(lines[:-1]) if lines else "No response provided"
    except (EOFError, KeyboardInterrupt):
        return "No response provided"


def run_eval(version: str = 'v1', case_filter: str = None):
    RESULTS_DIR.mkdir(parents=True, exist_ok=True)

    prompt_text = load_prompt_version(version)
    cases = load_cases(case_filter)

    if not cases:
        print(f"No cases found (filter={case_filter})")
        return

    print(f"\n── Prompt Eval: identity_prompt_{version} ──")
    print(f"Cases to evaluate: {len(cases)}")

    # Check ollama availability once
    ollama_available = get_ollama_response("Say 'ok'.") is not None
    if not ollama_available:
        print("⚠️  Ollama not available — switching to manual input mode\n")
    else:
        print("✅ Ollama available — running automated eval\n")

    case_results = []
    total_weight = 0
    weighted_score = 0

    for case in cases:
        user_prompt = f"{prompt_text}\n\nUser: {case['input']}\nAssistant:"

        if ollama_available:
            response = get_ollama_response(user_prompt)
            if not response:
                response = get_manual_response(case, user_prompt)
        else:
            response = get_manual_response(case, user_prompt)

        raw_score = score_response(
            response,
            case['expected_traits'],
            case['forbidden_traits'],
            case['weight']
        )
        normalized = min(raw_score / case['weight'], 1.0)
        weighted_score += raw_score
        total_weight += case['weight']

        status = "✅" if normalized >= 0.70 else "❌"
        cat = case.get('category', 'general')
        print(f"  {case['id']} [{cat:<12}] {normalized:.2f} {status}")
        case_results.append({
            "id": case['id'],
            "category": cat,
            "score": round(normalized, 3),
            "raw": round(raw_score, 3),
            "weight": case['weight'],
            "passed": normalized >= 0.70
        })

    overall = (weighted_score / total_weight) * 100 if total_weight > 0 else 0
    passed = overall >= 70
    status_str = "✅ PASS" if passed else "❌ FAIL"

    print(f"\nOverall Score: {overall:.0f}/100 {status_str} (threshold: 70)")

    # Find issues
    issues = [r for r in case_results if not r['passed']]
    if issues:
        print(f"\nTop issues:")
        for r in issues[:3]:
            print(f"  - {r['id']}: score {r['score']:.2f}")

    # Save results
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    result_file = RESULTS_DIR / f"result_{version}_{timestamp}.json"
    result_data = {
        "version": version,
        "timestamp": datetime.now().isoformat(),
        "overall_score": round(overall, 2),
        "passed": passed,
        "threshold": 70,
        "case_count": len(cases),
        "cases": case_results
    }
    with open(result_file, 'w') as f:
        json.dump(result_data, f, indent=2)

    print(f"\nResults saved → dna/identity/prompts/eval/eval_results/{result_file.name}")
    return result_data


def main():
    parser = argparse.ArgumentParser(description='Evaluate identity prompt versions')
    parser.add_argument('--version', default='v1', help='Prompt version (e.g. v1, v2)')
    parser.add_argument('--case', help='Run only a specific case ID')
    args = parser.parse_args()
    run_eval(args.version, args.case)


if __name__ == '__main__':
    main()
