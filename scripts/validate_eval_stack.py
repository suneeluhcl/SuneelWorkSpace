#!/usr/bin/env python3
"""
validate_eval_stack.py
Validates that all eval stack components are installed and reachable.
Run after install_eval_stack.sh or on a new machine.

Exit codes:
  0 = all checks passed
  1 = warnings only (non-fatal)
  2 = fatal errors
"""

import importlib.util
import json
import os
import shutil
import subprocess
import sys
import urllib.request
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
VENV_PY = REPO_ROOT / "adwi" / ".venv" / "bin" / "python3"
PY = str(VENV_PY) if VENV_PY.exists() else sys.executable

RED = "\033[91m"
GREEN = "\033[92m"
YELLOW = "\033[93m"
RESET = "\033[0m"
BOLD = "\033[1m"

warnings = []
errors = []


def ok(msg: str):
    print(f"  {GREEN}✅{RESET} {msg}")


def warn(msg: str):
    print(f"  {YELLOW}⚠️ {RESET} {msg}")
    warnings.append(msg)


def err(msg: str):
    print(f"  {RED}❌{RESET} {msg}")
    errors.append(msg)


def section(title: str):
    print(f"\n{BOLD}{'─' * 55}{RESET}")
    print(f"{BOLD}  {title}{RESET}")
    print(f"{BOLD}{'─' * 55}{RESET}")


def check_http(url: str, timeout: int = 5) -> bool:
    try:
        urllib.request.urlopen(url, timeout=timeout)
        return True
    except Exception:
        return False


def check_py_import(module: str) -> bool:
    result = subprocess.run(
        [PY, "-c", f"import {module}; print({module}.__version__ if hasattr({module}, '__version__') else 'ok')"],
        capture_output=True, text=True
    )
    return result.returncode == 0, result.stdout.strip()


# ---------------------------------------------------------------------------
# 1. Directory structure
# ---------------------------------------------------------------------------
section("1. Directory Structure")

required_dirs = [
    "eval/nightly",
    "eval/scenarios/seeds",
    "eval/scenarios/generated",
    "eval/promptfoo",
    "eval/deepeval",
    "eval/giskard",
    "eval/playwright/tests",
    "eval/k6",
    "config/eval",
    "config/launchagents",
    "logs/nightly",
]

for d in required_dirs:
    path = REPO_ROOT / d
    if path.exists():
        ok(f"{d}/")
    else:
        err(f"Missing directory: {d}/")

# ---------------------------------------------------------------------------
# 2. Core Python files
# ---------------------------------------------------------------------------
section("2. Eval Python Modules")

required_files = [
    "eval/nightly/orchestrator.py",
    "eval/nightly/scenario_generator.py",
    "eval/nightly/grader.py",
    "eval/nightly/failure_cluster.py",
    "eval/nightly/regression_compare.py",
    "eval/nightly/report_publisher.py",
    "eval/nightly/phoenix_tracer.py",
    "eval/giskard/adversarial_scan.py",
    "eval/deepeval/test_nlu.py",
    "config/eval/nightly.yaml",
]

for f in required_files:
    path = REPO_ROOT / f
    if path.exists():
        ok(f"{f}")
    else:
        err(f"Missing: {f}")

# ---------------------------------------------------------------------------
# 3. Seed scenarios
# ---------------------------------------------------------------------------
section("3. Seed Scenarios")

seeds_dir = REPO_ROOT / "eval" / "scenarios" / "seeds"
seed_files = list(seeds_dir.glob("*.jsonl"))
total_seeds = 0
for sf in seed_files:
    count = sum(1 for line in sf.open() if line.strip())
    total_seeds += count
    ok(f"{sf.name}: {count} seeds")

if total_seeds == 0:
    err("No seed scenarios found in eval/scenarios/seeds/")
elif total_seeds < 50:
    warn(f"Only {total_seeds} seeds found — consider adding more for better coverage")
else:
    ok(f"Total: {total_seeds} seed scenarios")

# ---------------------------------------------------------------------------
# 4. Python packages
# ---------------------------------------------------------------------------
section("4. Python Packages")

py_checks = [
    ("yaml", "pyyaml (config loading)"),
    ("pandas", "pandas (Giskard dependency)"),
    ("deepeval", "deepeval (semantic quality metrics)"),
    ("giskard", "giskard (adversarial scan)"),
    ("pytest", "pytest (test runner)"),
]

for module, label in py_checks:
    ok_flag, version = check_py_import(module)
    if ok_flag:
        ok(f"{label} — {version}")
    else:
        if module in ("deepeval", "giskard", "pandas"):
            warn(f"{label} not installed — run: {PY} -m pip install {module}")
        else:
            err(f"{label} not installed — run: {PY} -m pip install pyyaml")

# ---------------------------------------------------------------------------
# 5. System tools
# ---------------------------------------------------------------------------
section("5. System Tools")

tools = [
    ("k6", "k6 (perf testing)", False),
    ("npx", "npx (promptfoo + Playwright)", False),
    ("node", "Node.js", False),
    ("docker", "Docker (for Phoenix, n8n, etc.)", False),
]

for cmd, label, required in tools:
    if shutil.which(cmd):
        try:
            ver = subprocess.check_output([cmd, "--version"], text=True, stderr=subprocess.STDOUT).strip().split("\n")[0]
        except Exception:
            ver = "found"
        ok(f"{label} — {ver}")
    else:
        if required:
            err(f"{label} not found")
        else:
            warn(f"{label} not found — some nightly layers will be skipped")

# ---------------------------------------------------------------------------
# 6. Services
# ---------------------------------------------------------------------------
section("6. Services")

services = [
    ("http://localhost:11434/api/tags", "Ollama", True),
    ("http://localhost:6333/", "Qdrant", False),
    ("http://localhost:6006/", "Phoenix", False),
    ("http://localhost:3000/", "Open WebUI", False),
    ("http://localhost:5055/health", "Safe Command API", False),
    ("http://localhost:5056/", "Obsidian Bridge", False),
    ("http://localhost:8888/", "SearXNG", False),
    ("http://localhost:5678/", "n8n", False),
]

for url, name, required in services:
    if check_http(url):
        ok(f"{name} reachable at {url}")
    else:
        if required:
            err(f"{name} not reachable — NLU eval requires Ollama")
        else:
            warn(f"{name} not reachable at {url} — some eval layers will be skipped")

# ---------------------------------------------------------------------------
# 7. Config files
# ---------------------------------------------------------------------------
section("7. Configuration")

config_files = [
    ("config/eval/nightly.yaml", True),
    ("eval/promptfoo/promptfooconfig.yaml", False),
    ("eval/playwright/playwright.config.ts", False),
    ("eval/k6/api_load.js", False),
    ("config/launchagents/com.suneel.adwi-nightly-eval.plist.template", False),
]

for f, required in config_files:
    path = REPO_ROOT / f
    if path.exists():
        ok(f"{f}")
    else:
        if required:
            err(f"Missing required config: {f}")
        else:
            warn(f"Missing optional config: {f}")

# ---------------------------------------------------------------------------
# 8. LaunchAgent
# ---------------------------------------------------------------------------
section("8. LaunchAgent")

plist = Path.home() / "Library" / "LaunchAgents" / "com.suneel.adwi-nightly-eval.plist"
if plist.exists():
    ok(f"LaunchAgent installed at {plist}")
    result = subprocess.run(
        ["launchctl", "list", "com.suneel.adwi-nightly-eval"],
        capture_output=True, text=True
    )
    if result.returncode == 0:
        ok("LaunchAgent is loaded and active")
    else:
        warn("LaunchAgent file exists but is not loaded — run: launchctl load " + str(plist))
else:
    warn(f"LaunchAgent not installed — run: scripts/install_eval_stack.sh")

# ---------------------------------------------------------------------------
# 9. Logs directory
# ---------------------------------------------------------------------------
section("9. Logs")

logs_dir = REPO_ROOT / "logs" / "nightly"
if logs_dir.exists():
    sessions = [d for d in logs_dir.iterdir() if d.is_dir() and d.name != "latest"]
    ok(f"logs/nightly/ exists — {len(sessions)} prior sessions")
    if sessions:
        latest_brief = logs_dir / "latest" / "00_morning_brief.md"
        if latest_brief.exists():
            ok(f"Latest morning brief found: logs/nightly/latest/00_morning_brief.md")
        else:
            warn("No latest morning brief — run orchestrator to generate first report")
else:
    warn("logs/nightly/ does not exist — will be created on first run")

# ---------------------------------------------------------------------------
# Summary
# ---------------------------------------------------------------------------
print(f"\n{'═' * 55}")
print(f"{BOLD}  Validation Summary{RESET}")
print(f"{'═' * 55}")
print(f"  {GREEN}Passed:   {55 - len(warnings) - len(errors)}{RESET}")
print(f"  {YELLOW}Warnings: {len(warnings)}{RESET}")
print(f"  {RED}Errors:   {len(errors)}{RESET}")

if errors:
    print(f"\n{RED}Fatal errors:{RESET}")
    for e in errors:
        print(f"  • {e}")
    sys.exit(2)
elif warnings:
    print(f"\n{YELLOW}Warnings (non-fatal):{RESET}")
    for w in warnings:
        print(f"  • {w}")
    sys.exit(1)
else:
    print(f"\n{GREEN}All checks passed — eval stack ready!{RESET}")
    sys.exit(0)
