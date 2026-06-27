#!/usr/bin/env python3
"""Workspace CI — Automated test suite for pre-change validation.
Runs duplication/integrity guards, health checks, and MCP status.
Exits with 0 (all pass) or 1 (any fail).
"""
import os
import sys
import subprocess
import json
from pathlib import Path
from datetime import datetime

WORKSPACE = Path(os.environ.get('WORKSPACE', Path.home() / 'SuneelWorkSpace'))
HEALTH_FILE = WORKSPACE / 'spine/state/WORKSPACE_HEALTH.json'

PASS = "✅ PASS"
FAIL = "❌ FAIL"
WARN = "⚠️  WARN"

results = []


def run(cmd: list, timeout: int = 30) -> subprocess.CompletedProcess:
    try:
        return subprocess.run(
            cmd, capture_output=True, text=True, timeout=timeout,
            cwd=str(WORKSPACE)
        )
    except subprocess.TimeoutExpired:
        r = subprocess.CompletedProcess(cmd, returncode=1)
        r.stdout = ""
        r.stderr = "TIMEOUT"
        return r
    except FileNotFoundError:
        r = subprocess.CompletedProcess(cmd, returncode=1)
        r.stdout = ""
        r.stderr = f"Command not found: {cmd[0]}"
        return r


def check(name: str, passed: bool, detail: str = ""):
    status = PASS if passed else FAIL
    print(f"  {status}  {name}")
    if detail:
        for line in detail.strip().split('\n')[:3]:
            print(f"         {line}")
    results.append({"check": name, "passed": passed})
    return passed


def check_health_score():
    if not HEALTH_FILE.exists():
        check("Workspace health check", False, "WORKSPACE_HEALTH.json not found")
        return
    try:
        with open(HEALTH_FILE) as f:
            data = json.load(f)
        # Real health json uses issue_count and error_count
        errors = int(data.get('error_count', 0))
        issues = int(data.get('issue_count', 0))
        # Compute a synthetic score: 100 - 20*errors - 5*issues
        score = max(0, 100 - errors * 20 - issues * 5)
        # Try direct score fields too
        if 'health_score' in data:
            score = float(data['health_score'])
        elif 'score' in data:
            score = float(data['score'])
        check(f"Workspace health (errors={errors}, issues={issues}, score≈{score:.0f})", score >= 70 or errors == 0)
    except Exception as e:
        check("Workspace health check", False, str(e))



def check_python_files():
    # Get recently modified Python files (last 50 by mtime)
    py_files = sorted(WORKSPACE.rglob('*.py'), key=lambda f: f.stat().st_mtime, reverse=True)[:10]
    errors = []
    for f in py_files:
        if any(skip in f.parts for skip in ['__pycache__', '.git', 'sandboxes', '.hf_cache']):
            continue
        r = run([sys.executable, '-m', 'py_compile', str(f)])
        if r.returncode != 0:
            errors.append(f"{f.name}: {r.stderr.strip()[:80]}")
    check("Python syntax check (recent files)", len(errors) == 0, '\n'.join(errors[:3]))


def check_mcp_status():
    r = run(['bash', str(WORKSPACE / 'bin/mcp-status')], timeout=15)
    check("MCP server indexable", r.returncode == 0, r.stderr[:100] if r.returncode != 0 else "")


def check_doctor():
    r = run(['bash', str(WORKSPACE / 'bin/agent-doctor')], timeout=20)
    check("agent-doctor passes", r.returncode == 0, r.stdout[-200:] if r.returncode != 0 else "")


def check_key_files():
    required = [
        'skeleton/rules/AGENT_SYSTEM.md',
        'brain/memory/MEMORY.md',
        'heart/tasks/ACTIVE_TASKS.md',
        'heart/heart/heart/orchestrator/mesh/agent_registry.json',
        'brain/graph/build_graph.py',
        'nervous/nervous/gateway/api.py',
    ]
    missing = [f for f in required if not (WORKSPACE / f).exists()]
    check("Key files exist", len(missing) == 0, '\n'.join(missing))


def check_bin_executables():
    key_bins = ['agent-start', 'agent-finish', 'agent-doctor', 'next',
                'mesh-status', 'brain-graph-build', 'gateway-start']
    not_exec = []
    for b in key_bins:
        p = WORKSPACE / 'bin' / b
        if p.exists() and not os.access(p, os.X_OK):
            not_exec.append(b)
    check("Key bin/ commands are executable", len(not_exec) == 0, ', '.join(not_exec))


def main():
    print(f"\n{'='*55}")
    print(f"  Workspace CI — {datetime.now():%Y-%m-%d %H:%M:%S}")
    print(f"{'='*55}\n")

    check_key_files()
    check_health_score()
    check_python_files()
    check_bin_executables()
    check_doctor()
    check_mcp_status()

    passed = sum(1 for r in results if r['passed'])
    total = len(results)
    all_passed = passed == total

    print(f"\n{'='*55}")
    print(f"  Result: {passed}/{total} checks passed")
    print(f"  Status: {'✅ ALL PASS' if all_passed else '❌ SOME FAILED'}")
    print(f"{'='*55}\n")

    sys.exit(0 if all_passed else 1)


if __name__ == '__main__':
    main()
