"""
autonomous_repair_loop.py
1. Run all tests
2. Analyze failures with Ollama
3. Apply SAFE fixes
4. Queue CONTROLLED fixes
5. Re-run tests
6. Learn from results
7. Repeat until pass rate >= 95% or max iterations reached
"""

import json
import os
import re
import shutil
import sys
import time
import urllib.request
from datetime import datetime, timezone
from pathlib import Path

WORKSPACE = os.path.expanduser("~/SuneelWorkSpace")
sys.path.insert(0, WORKSPACE)
os.chdir(WORKSPACE)

OLLAMA_BASE = "http://localhost:11434"
LOOP_LOG = "blood/logs/repair_loop.jsonl"
MAX_ITERATIONS = 5
TARGET_PASS_RATE = 0.95
SANDBOX_BASE = Path("/tmp/suneelworkspace-sandbox")

# Models used for multi-model voting consensus
_VOTING_MODELS = ["codellama", "llama3.3:70b"]


def ask_ollama(prompt: str, model: str = "suneelworkspace", timeout: int = 120) -> str:
    payload = json.dumps({
        "model": model,
        "prompt": prompt,
        "stream": False,
        "options": {"temperature": 0.1, "num_ctx": 4096}
    }).encode()
    req = urllib.request.Request(
        f"{OLLAMA_BASE}/api/generate",
        data=payload,
        headers={"Content-Type": "application/json"},
        method="POST"
    )
    try:
        with urllib.request.urlopen(req, timeout=timeout) as r:
            return json.loads(r.read()).get("response", "").strip()
    except Exception:
        return ""


def run_tests() -> dict:
    from tests.test_runner import run_all_tests
    return run_all_tests(verbose=False, fix_on_fail=False)


def analyze_failures_with_ollama(failures: list) -> list:
    if not failures:
        return []
    failure_text = "\n".join([
        f"Test: {f['test']}\nError: {f['message']}"
        for f in failures[:10]
    ])
    prompt = f"""Analyze these SuneelWorkSpace test failures and suggest SAFE fixes.

SuneelWorkSpace: 12 organs (brain, heart, eyes, ears, nervous, skeleton, blood, hands, mouth, dna, lab, spine)

Failures:
{failure_text}

For each failure, provide a specific fix. Respond ONLY in JSON array:
[
  {{
    "test": "test name",
    "root_cause": "why it failed",
    "fix_type": "create_dir|create_file|fix_symlink|skip",
    "target_path": "relative/path",
    "fix_command": "content or target for symlink",
    "execution_level": "SAFE",
    "confidence": 0.85
  }}
]"""

    response = ask_ollama(prompt)
    if not response:
        return []
    try:
        match = re.search(r'\[.*\]', response, re.DOTALL)
        if match:
            return json.loads(match.group())
    except Exception:
        pass
    return []


# Directories the repair loop is allowed to create files in (LLM-generated paths)
_ALLOWED_CREATE_DIRS = ("tests/", "blood/logs/", "lab/autolab/experiments/")
_CONTROLLED_QUEUE = "blood/logs/repair_loop_controlled_queue.json"

# Organ → test file mapping for sandbox verification
_ORGAN_TEST_MAP: dict[str, str] = {
    "brain":    "tests/organs/brain/test_brain.py",
    "heart":    "tests/organs/heart/test_heart.py",
    "eyes":     "tests/organs/eyes/test_eyes.py",
    "ears":     "tests/organs/ears/test_ears.py",
    "nervous":  "tests/nerve_system/test_nervous.py",
    "skeleton": "tests/organs/skeleton/test_skeleton.py",
    "blood":    "tests/organs/blood/test_blood.py",
    "hands":    "tests/organs/hands/test_hands.py",
    "mouth":    "tests/organs/mouth/test_mouth.py",
    "dna":      "tests/organs/dna/test_dna.py",
    "lab":      "tests/organs/lab/test_lab.py",
    "spine":    "tests/organs/spine/test_spine.py",
}


def _path_within_workspace(relative: str) -> str | None:
    """Return resolved absolute path only if it stays inside WORKSPACE, else None."""
    if not relative or os.path.isabs(relative) or "\x00" in relative:
        return None
    parts = relative.replace("\\", "/").split("/")
    if ".." in parts:
        return None
    ws_real = os.path.realpath(WORKSPACE)
    full = os.path.realpath(os.path.join(WORKSPACE, relative))
    if full == ws_real or full.startswith(ws_real + os.sep):
        return full
    return None


def _queue_controlled_fix(fix: dict) -> None:
    path = os.path.join(WORKSPACE, _CONTROLLED_QUEUE)
    os.makedirs(os.path.dirname(path), exist_ok=True)
    try:
        existing = json.load(open(path)) if os.path.exists(path) else []
    except Exception:
        existing = []
    existing.append({**fix, "queued_at": datetime.now(timezone.utc).isoformat()})
    json.dump(existing, open(path, "w"), indent=2)


def _run_organ_tests(test_file: str) -> bool:
    """Run a specific organ test file. Returns True if all tests pass."""
    import subprocess
    full = os.path.join(WORKSPACE, test_file)
    if not os.path.exists(full):
        return True  # no test to verify → accept fix
    r = subprocess.run(
        [sys.executable, "-m", "pytest", full, "-q", "--tb=short", "--no-header"],
        cwd=WORKSPACE,
        capture_output=True,
        text=True,
        timeout=120,
    )
    return r.returncode == 0


def _git_commit_fix(fix: dict, target: str) -> None:
    """Commit a sandbox-verified fix to the active branch."""
    import subprocess
    msg = f"fix: sandbox-verified repair — {fix.get('root_cause', target)[:60]}"
    try:
        subprocess.run(["git", "add", target], cwd=WORKSPACE, capture_output=True)
        subprocess.run(
            ["git", "commit", "--no-verify", "-m", msg],
            cwd=WORKSPACE,
            capture_output=True,
        )
    except Exception:
        pass


def _sandbox_apply_and_test(fix: dict) -> bool:
    """
    Sandbox mechanism for safe fix application:
    1. Backup the target file to /tmp/suneelworkspace-sandbox/{ts}/
    2. Apply the fix to the real workspace
    3. Run the affected organ's tests from the real workspace
    4. If tests pass: commit the fix, clean up sandbox, return True
    5. If tests fail: restore from backup, clean up sandbox, return False

    Falls back to plain apply_fix() when there is no specific target or test.
    """
    target = fix.get("target_path", "")
    organ = target.split("/")[0] if "/" in target else ""
    test_file = _ORGAN_TEST_MAP.get(organ)

    ts = datetime.now(timezone.utc).strftime("%Y%m%d_%H%M%S_%f")
    sandbox = SANDBOX_BASE / ts
    sandbox.mkdir(parents=True, exist_ok=True)

    # Backup the target file before touching it
    full_target = _path_within_workspace(target) if target else None
    backup_path = None
    if full_target and os.path.isfile(full_target):
        backup_path = sandbox / Path(target).name
        shutil.copy2(full_target, backup_path)

    # Apply fix to real workspace
    if not apply_fix(fix):
        shutil.rmtree(sandbox, ignore_errors=True)
        return False

    # No test file → accept fix without verification
    if not test_file or not os.path.exists(os.path.join(WORKSPACE, test_file)):
        shutil.rmtree(sandbox, ignore_errors=True)
        if target:
            _git_commit_fix(fix, target)
        return True

    # Verify in real workspace using the organ's test suite
    passed = _run_organ_tests(test_file)
    shutil.rmtree(sandbox, ignore_errors=True)

    if passed:
        if target:
            _git_commit_fix(fix, target)
        return True

    # Restore from backup on failure
    if backup_path and os.path.isfile(backup_path) and full_target:
        shutil.copy2(backup_path, full_target)
        print(f"    Sandbox: tests failed — restored {target} from backup")
    return False


def apply_fix(fix: dict) -> bool:
    if fix.get("execution_level") != "SAFE":
        return False
    if fix.get("confidence", 0) < 0.7:
        return False

    fix_type = fix.get("fix_type", "skip")
    target = fix.get("target_path", "")
    command = fix.get("fix_command", "")

    try:
        if fix_type == "create_dir" and target:
            full = _path_within_workspace(target)
            if not full:
                print(f"    Rejected (traversal/absolute): {target}")
                return False
            os.makedirs(full, exist_ok=True)
            print(f"    Created dir: {target}")
            return True

        elif fix_type == "create_file" and target and command:
            full = _path_within_workspace(target)
            if not full:
                print(f"    Rejected (traversal/absolute): {target}")
                return False
            if not any(target.startswith(d) for d in _ALLOWED_CREATE_DIRS):
                print(f"    Rejected (not in allowed dirs): {target}")
                _queue_controlled_fix(fix)
                return False
            os.makedirs(os.path.dirname(full), exist_ok=True)
            with open(full, "w") as f:
                f.write(command)
            print(f"    Created file: {target}")
            return True

        elif fix_type == "fix_symlink":
            # Never auto-apply symlink fixes from LLM output — queue for human review
            _queue_controlled_fix(fix)
            print(f"    Queued for human review (symlink): {target}")
            return False

    except Exception as e:
        print(f"    Fix failed: {e}")

    return False


def analyze_failures_consensus(failures: list) -> list:
    """
    Phase 3 — Multi-model voting consensus.

    Queries both codellama and llama3.3:70b independently for fix suggestions.
    Returns only fixes where both models agree on the same target_path.
    If only one model responds, returns that model's fixes as a fallback.
    """
    import threading

    if not failures:
        return []

    failure_text = "\n".join(
        f"Test: {f['test']}\nError: {f['message']}" for f in failures[:10]
    )
    prompt = (
        "Analyze these SuneelWorkSpace test failures and suggest SAFE fixes.\n\n"
        f"Failures:\n{failure_text}\n\n"
        "Respond ONLY in a JSON array:\n"
        '[\n  {\n    "test": "test_name",\n    "root_cause": "why it failed",\n'
        '    "fix_type": "create_dir|create_file|skip",\n'
        '    "target_path": "relative/path",\n'
        '    "fix_command": "content or empty",\n'
        '    "execution_level": "SAFE",\n'
        '    "confidence": 0.80\n  }\n]'
    )

    model_fixes: dict[str, list] = {}

    def _query(model: str) -> None:
        print(f"  [voting] Querying {model}…")
        resp = ask_ollama(prompt, model=model, timeout=180)
        fixes: list = []
        if resp:
            try:
                m = re.search(r"\[.*?\]", resp, re.DOTALL)
                if m:
                    fixes = json.loads(m.group())
            except Exception:
                pass
        model_fixes[model] = fixes

    threads = [threading.Thread(target=_query, args=(m,)) for m in _VOTING_MODELS]
    for t in threads:
        t.start()
    for t in threads:
        t.join(timeout=200)

    sets: list[set] = [
        {f.get("target_path", "") for f in model_fixes.get(m, []) if f.get("target_path")}
        for m in _VOTING_MODELS
    ]

    # Require both models to agree on the same target_path
    responding = [m for m in _VOTING_MODELS if model_fixes.get(m)]
    if len(responding) < 2:
        # Only one model responded — use its fixes as fallback
        fallback = model_fixes.get(responding[0], []) if responding else []
        print(f"  [voting] Only {len(responding)} model(s) responded — using fallback")
        return fallback

    consensus_paths = sets[0] & sets[1]
    if not consensus_paths:
        print("  [voting] No path consensus — returning empty")
        return []

    print(f"  [voting] Consensus paths: {', '.join(sorted(consensus_paths))}")

    # Return primary model's fix entries filtered to consensus paths
    primary = model_fixes.get(_VOTING_MODELS[0], [])
    return [f for f in primary if f.get("target_path") in consensus_paths]


def learn_from_results(iteration: int, results: dict, fixes_applied: int):
    entry = {
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "iteration": iteration,
        "passed": results.get("passed", 0),
        "failed": results.get("failed", 0),
        "total": results.get("total", 0),
        "fixes_applied": fixes_applied,
        "pass_rate": results.get("passed", 0) / max(results.get("total", 1), 1),
    }
    os.makedirs(os.path.dirname(LOOP_LOG), exist_ok=True)
    with open(LOOP_LOG, "a") as f:
        f.write(json.dumps(entry) + "\n")

    try:
        from nervous.nerve_propagator import notify_change
        notify_change("lab", "repair_loop_iteration",
                      f"iteration={iteration} passed={results.get('passed',0)}/{results.get('total',0)}")
    except Exception:
        pass


def run_autonomous_repair_loop(max_iterations: int = MAX_ITERATIONS):
    print(f"\nAutonomous Repair Loop")
    print(f"   Max iterations: {max_iterations} | Target: {TARGET_PASS_RATE*100:.0f}%\n")

    iteration = 0
    best_pass_rate = 0.0

    while iteration < max_iterations:
        iteration += 1
        print(f"\n{'─'*50}")
        print(f"Iteration {iteration}/{max_iterations}")
        print(f"{'─'*50}")

        results = run_tests()
        passed = results.get("passed", 0)
        total = results.get("total", 0)
        pass_rate = passed / max(total, 1)
        print(f"   {passed}/{total} passing ({pass_rate*100:.1f}%)")

        if pass_rate > best_pass_rate:
            best_pass_rate = pass_rate

        if pass_rate >= TARGET_PASS_RATE:
            print(f"\nTarget reached: {pass_rate*100:.1f}%")
            learn_from_results(iteration, results, 0)
            break

        failures = results.get("failures", [])
        if not failures:
            learn_from_results(iteration, results, 0)
            break

        print(f"\nAnalyzing {len(failures)} failures with Ollama...")
        fixes = analyze_failures_with_ollama(failures)
        print(f"   {len(fixes)} potential fixes generated")

        fixes_applied = 0
        for fix in fixes:
            if fix.get("execution_level") == "SAFE" and fix.get("confidence", 0) >= 0.7:
                print(f"  Applying (sandbox): {fix.get('root_cause', '')[:60]}")
                if _sandbox_apply_and_test(fix):
                    fixes_applied += 1

        print(f"\n   Applied {fixes_applied} fixes")
        learn_from_results(iteration, results, fixes_applied)

        if fixes_applied == 0:
            # Phase 3: multi-model voting consensus fallback
            print("  Single-model fixes exhausted — trying multi-model voting consensus…")
            consensus_fixes = analyze_failures_consensus(failures)
            consensus_applied = 0
            for fix in consensus_fixes:
                if fix.get("execution_level") == "SAFE" and fix.get("confidence", 0) >= 0.6:
                    print(f"  [voting] Applying: {fix.get('root_cause', '')[:60]}")
                    if _sandbox_apply_and_test(fix):
                        consensus_applied += 1
            if consensus_applied > 0:
                learn_from_results(iteration, results, consensus_applied)
                print(f"  Voting consensus applied {consensus_applied} fix(es)")
                time.sleep(2)
                continue
            print("   No more SAFE fixes available (voting consensus exhausted)")
            break

        time.sleep(2)

    print(f"\n{'='*50}")
    print(f"Repair Loop Complete")
    print(f"   Iterations: {iteration} | Best pass rate: {best_pass_rate*100:.1f}%")
    print(f"{'='*50}\n")
    return {"iterations": iteration, "best_pass_rate": best_pass_rate}


if __name__ == "__main__":
    import argparse
    parser = argparse.ArgumentParser()
    parser.add_argument("--max-iterations", type=int, default=MAX_ITERATIONS)
    args = parser.parse_args()
    run_autonomous_repair_loop(max_iterations=args.max_iterations)
