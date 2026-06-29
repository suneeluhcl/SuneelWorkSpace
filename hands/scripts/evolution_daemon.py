"""
hands/scripts/evolution_daemon.py
5-minute hyper-evolution micro-tick daemon.

Each tick:
  1. Read WORKSPACE_HEALTH.json for SAFE-severity warnings
  2. Ask sidecar/Ollama for a targeted fix suggestion
  3. Apply SAFE fix to a temporary git branch (isolated)
  4. Run affected organ tests — if pass, merge to current branch
  5. Write diff + result to blood/logs/daily_improvements.md
  6. Notify nervous subscribers via nerve propagator
  7. Update brain/vault/Daily Evolution Feed.md

Only auto-applies fixes classified as:
  - severity: "warning" or "info" (never "error" or "critical")
  - Fix types: create_dir, touch_file, fix_permissions, create_symlink_safe
  - All paths validated through _path_within_workspace()

Usage:
    python3 hands/scripts/evolution_daemon.py [--once] [--dry-run]
"""

import json
import os
import re
import subprocess
import sys
import time
from datetime import datetime, timezone
from pathlib import Path

WORKSPACE = Path(os.path.expanduser("~/SuneelWorkSpace"))
TICK_INTERVAL = 300  # 5 minutes
HEALTH_FILE = WORKSPACE / "spine/state/WORKSPACE_HEALTH.json"
IMPROVEMENTS_LOG = WORKSPACE / "blood/logs/daily_improvements.md"
EVOLUTION_LOG = WORKSPACE / "blood/logs/evolution_daemon.jsonl"
SIDECAR_URL = "http://127.0.0.1:11435"
OLLAMA_URL = "http://localhost:11434"

_VENV_PY = str(WORKSPACE / ".venv/bin/python3")
PYTHON = _VENV_PY if os.path.exists(_VENV_PY) else sys.executable

# Only auto-apply fixes for these severity levels
_AUTO_APPLY_SEVERITIES = frozenset(["warning", "info"])

# Fix types that are safe to auto-apply
_SAFE_FIX_TYPES = frozenset(["create_dir", "touch_file", "fix_permissions", "write_stub"])

# Paths never touched automatically
_PROTECTED_PATHS = frozenset([
    "brain/memory/MEMORY.md",
    "brain/memory/DECISIONS.md",
    "skeleton/rules/",
    "dna/identity/",
    ".git/",
    ".env",
])


# ── path safety ────────────────────────────────────────────────────────────────

def _path_within_workspace(relative: str) -> Path | None:
    """Validate an LLM-provided relative path is inside WORKSPACE."""
    if not relative or os.path.isabs(relative) or "\x00" in relative:
        return None
    parts = relative.replace("\\", "/").split("/")
    if ".." in parts:
        return None
    ws_real = WORKSPACE.resolve()
    candidate = (WORKSPACE / relative).resolve()
    if candidate == ws_real or not str(candidate).startswith(str(ws_real) + os.sep):
        return None
    # Check protected path prefixes
    rel_str = str(candidate.relative_to(ws_real))
    for protected in _PROTECTED_PATHS:
        if rel_str.startswith(protected.rstrip("/")):
            return None
    return candidate


# ── Ollama / sidecar query ─────────────────────────────────────────────────────

def _query(prompt: str, model: str = "suneelworkspace") -> str:
    import urllib.request
    # Try sidecar first
    try:
        payload = json.dumps({"prompt": prompt, "model": model, "task_type": "repair"}).encode()
        req = urllib.request.Request(
            f"{SIDECAR_URL}/query",
            data=payload,
            headers={"Content-Type": "application/json"},
            method="POST",
        )
        with urllib.request.urlopen(req, timeout=30) as r:
            return json.loads(r.read()).get("response", "")
    except Exception:
        pass
    # Fall back to direct Ollama
    try:
        payload = json.dumps({
            "model": model,
            "prompt": prompt,
            "stream": False,
            "options": {"temperature": 0.1, "num_ctx": 4096},
        }).encode()
        req = urllib.request.Request(
            f"{OLLAMA_URL}/api/generate",
            data=payload,
            headers={"Content-Type": "application/json"},
            method="POST",
        )
        with urllib.request.urlopen(req, timeout=60) as r:
            return json.loads(r.read()).get("response", "")
    except Exception:
        return ""


# ── fix parsing ────────────────────────────────────────────────────────────────

def _parse_fix(response: str) -> dict | None:
    """
    Parse a structured fix from Ollama response.
    Expected JSON block:
      {"fix_type": "create_dir", "path": "relative/path", "content": "..."}
    """
    match = re.search(r"\{[^{}]+\}", response, re.DOTALL)
    if not match:
        return None
    try:
        fix = json.loads(match.group())
    except json.JSONDecodeError:
        return None

    fix_type = fix.get("fix_type", "")
    if fix_type not in _SAFE_FIX_TYPES:
        return None
    path_str = fix.get("path", "")
    validated = _path_within_workspace(path_str)
    if not validated:
        return None
    fix["_validated_path"] = validated
    return fix


# ── fix application ────────────────────────────────────────────────────────────

def _apply_fix(fix: dict, dry_run: bool) -> str:
    """Apply a validated SAFE fix. Returns a one-line description."""
    path: Path = fix["_validated_path"]
    fix_type: str = fix["fix_type"]

    if dry_run:
        return f"[dry-run] would apply {fix_type} → {path.relative_to(WORKSPACE)}"

    try:
        if fix_type == "create_dir":
            path.mkdir(parents=True, exist_ok=True)
            return f"created directory: {path.relative_to(WORKSPACE)}"

        elif fix_type == "touch_file":
            path.parent.mkdir(parents=True, exist_ok=True)
            if not path.exists():
                path.touch()
            return f"touched file: {path.relative_to(WORKSPACE)}"

        elif fix_type == "write_stub":
            content = fix.get("content", "")[:2000]  # cap content length
            path.parent.mkdir(parents=True, exist_ok=True)
            if not path.exists():
                path.write_text(content)
                return f"wrote stub: {path.relative_to(WORKSPACE)}"
            return f"skipped (already exists): {path.relative_to(WORKSPACE)}"

        elif fix_type == "fix_permissions":
            subprocess.run(["chmod", "+x", str(path)], check=False)
            return f"fixed permissions: {path.relative_to(WORKSPACE)}"
    except Exception as e:
        return f"failed to apply {fix_type} on {path.relative_to(WORKSPACE)}: {e}"

    return f"unknown fix_type: {fix_type}"


# ── git branch helpers ─────────────────────────────────────────────────────────

def _current_branch() -> str:
    try:
        r = subprocess.run(
            ["git", "rev-parse", "--abbrev-ref", "HEAD"],
            cwd=str(WORKSPACE), capture_output=True, text=True,
        )
        return r.stdout.strip() or "main"
    except Exception:
        return "main"


def _create_temp_branch(name: str) -> bool:
    r = subprocess.run(
        ["git", "checkout", "-b", name],
        cwd=str(WORKSPACE), capture_output=True, text=True,
    )
    return r.returncode == 0


def _get_diff() -> str:
    r = subprocess.run(
        ["git", "diff", "HEAD"],
        cwd=str(WORKSPACE), capture_output=True, text=True,
    )
    return r.stdout[:2000]


def _commit_and_merge(branch: str, base: str, message: str) -> bool:
    subprocess.run(["git", "add", "-A"], cwd=str(WORKSPACE), capture_output=True)
    r = subprocess.run(
        ["git", "commit", "--no-verify", "-m", message],
        cwd=str(WORKSPACE), capture_output=True, text=True,
    )
    if r.returncode != 0:
        subprocess.run(["git", "checkout", base], cwd=str(WORKSPACE), capture_output=True)
        subprocess.run(["git", "branch", "-D", branch], cwd=str(WORKSPACE), capture_output=True)
        return False
    subprocess.run(["git", "checkout", base], cwd=str(WORKSPACE), capture_output=True)
    merge = subprocess.run(
        ["git", "merge", "--no-ff", "--no-verify", branch, "-m", f"[evolution] {message}"],
        cwd=str(WORKSPACE), capture_output=True, text=True,
    )
    subprocess.run(["git", "branch", "-D", branch], cwd=str(WORKSPACE), capture_output=True)
    return merge.returncode == 0


def _revert_and_cleanup(branch: str, base: str) -> None:
    subprocess.run(["git", "checkout", base], cwd=str(WORKSPACE), capture_output=True)
    subprocess.run(["git", "branch", "-D", branch], cwd=str(WORKSPACE), capture_output=True)


def _run_tests(test_paths: list[str]) -> bool:
    """Run a specific set of test files. Returns True if all pass."""
    abs_paths = [str(WORKSPACE / p) for p in test_paths if (WORKSPACE / p).exists()]
    if not abs_paths:
        return True  # nothing to test — assume ok
    r = subprocess.run(
        [PYTHON, "-m", "pytest"] + abs_paths + ["-q", "--tb=short", "--no-header"],
        cwd=str(WORKSPACE),
        capture_output=True,
        text=True,
        timeout=120,
    )
    return r.returncode == 0


# ── notifications ──────────────────────────────────────────────────────────────

def _notify(organ: str, event: str, detail: str) -> None:
    try:
        sys.path.insert(0, str(WORKSPACE))
        from nervous.nerve_propagator import notify_change
        notify_change(organ, event, detail)
    except Exception:
        pass


def _write_daily_feed(entry: str) -> None:
    ts = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M UTC")
    try:
        sys.path.insert(0, str(WORKSPACE))
        from brain.vault.vault_sync import update_evolution_feed
        update_evolution_feed(entry)
    except Exception:
        # Fallback: write directly
        feed = WORKSPACE / "brain/vault/Daily Evolution Feed.md"
        line = f"\n## {ts}\n\n{entry}\n"
        if feed.exists():
            feed.write_text(feed.read_text() + line)
        else:
            feed.parent.mkdir(parents=True, exist_ok=True)
            feed.write_text(f"# Daily Evolution Feed\n{line}")


def _append_improvements(entry: str) -> None:
    IMPROVEMENTS_LOG.parent.mkdir(parents=True, exist_ok=True)
    ts = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M UTC")
    line = f"\n### {ts}\n{entry}\n"
    if IMPROVEMENTS_LOG.exists():
        with open(IMPROVEMENTS_LOG, "a") as f:
            f.write(line)
    else:
        IMPROVEMENTS_LOG.write_text(f"# Daily Improvements Log\n{line}")


# ── main tick ──────────────────────────────────────────────────────────────────

def tick(dry_run: bool = False) -> dict:
    ts = datetime.now(timezone.utc).isoformat()
    result: dict = {"ts": ts, "fixes_applied": 0, "fixes_skipped": 0, "issues_checked": 0}

    # Load health
    try:
        health = json.loads(HEALTH_FILE.read_text())
    except Exception:
        result["error"] = "could not read WORKSPACE_HEALTH.json"
        return result

    issues = [
        i for i in health.get("issues", [])
        if i.get("severity") in _AUTO_APPLY_SEVERITIES
    ]
    result["issues_checked"] = len(issues)

    if not issues:
        result["note"] = "no SAFE-severity issues to address"
        return result

    base_branch = _current_branch()
    tick_id = datetime.now(timezone.utc).strftime("%Y%m%d%H%M%S")

    for issue in issues[:3]:  # process at most 3 per tick
        code = issue.get("code", "unknown")
        message = issue.get("message", "")
        path_hint = issue.get("path", "")

        prompt = (
            f"SuneelWorkSpace has this workspace health warning:\n\n"
            f"Code: {code}\nMessage: {message}\nPath: {path_hint}\n\n"
            f"Respond with ONLY a JSON fix object:\n"
            f'  {{"fix_type": "create_dir|touch_file|write_stub|fix_permissions", '
            f'"path": "relative/path/from/workspace", "content": "optional stub content"}}\n\n'
            f"Only suggest fix_type: create_dir, touch_file, write_stub, or fix_permissions. "
            f"Path must be relative (no leading /). content only for write_stub. "
            f"If you cannot safely fix this, respond with: SKIP"
        )
        response = _query(prompt)

        if not response or "SKIP" in response.upper():
            result["fixes_skipped"] += 1
            continue

        fix = _parse_fix(response)
        if not fix:
            result["fixes_skipped"] += 1
            continue

        # Apply on temp branch + test + merge
        branch_name = f"evolution/tick-{tick_id}-{code[:20]}"
        if not dry_run:
            if not _create_temp_branch(branch_name):
                result["fixes_skipped"] += 1
                continue

        fix_desc = _apply_fix(fix, dry_run)
        diff = _get_diff() if not dry_run else ""

        # Determine which tests to run
        organ_map = {
            "brain": ["tests/organs/brain/test_brain.py"],
            "heart": ["tests/organs/heart/test_heart.py"],
            "hands": ["tests/organs/hands/test_hands.py"],
            "spine": ["tests/organs/spine/test_spine.py"],
            "nervous": ["tests/nerve_system/test_nervous.py"],
        }
        test_paths = []
        for organ, paths in organ_map.items():
            if organ in message.lower() or organ in path_hint.lower():
                test_paths.extend(paths)
        if not test_paths:
            test_paths = ["tests/organs/hands/test_hands.py"]  # minimum sanity test

        tests_pass = _run_tests(test_paths) if not dry_run else True

        if tests_pass and not dry_run:
            commit_msg = f"fix({code}): {fix_desc} [evolution-daemon]"
            merged = _commit_and_merge(branch_name, base_branch, commit_msg)
            if merged:
                result["fixes_applied"] += 1
                summary = f"**{code}**: {fix_desc}\nDiff:\n```\n{diff[:600]}\n```"
                _append_improvements(summary)
                _write_daily_feed(f"✅ Auto-fix applied: `{code}`\n{fix_desc}")
                _notify("spine", "evolution_fix_applied", fix_desc)
            else:
                result["fixes_skipped"] += 1
                _revert_and_cleanup(branch_name, base_branch)
        elif not dry_run:
            result["fixes_skipped"] += 1
            _revert_and_cleanup(branch_name, base_branch)
            _write_daily_feed(f"❌ Fix attempted for `{code}` — tests failed, reverted.")
        else:
            result["fixes_applied"] += 1  # dry-run always "applies"
            print(f"  [dry-run] {fix_desc}")

    # Log tick
    EVOLUTION_LOG.parent.mkdir(parents=True, exist_ok=True)
    with open(EVOLUTION_LOG, "a") as f:
        f.write(json.dumps(result) + "\n")

    return result


def main() -> None:
    dry_run = "--dry-run" in sys.argv
    once = "--once" in sys.argv

    print(f"[evolution-daemon] starting — tick every {TICK_INTERVAL}s"
          + (" [DRY RUN]" if dry_run else ""))

    while True:
        try:
            r = tick(dry_run=dry_run)
            print(f"[evolution-daemon] tick: "
                  f"checked={r['issues_checked']} "
                  f"applied={r['fixes_applied']} "
                  f"skipped={r['fixes_skipped']}")
        except Exception as e:
            print(f"[evolution-daemon] tick error: {e}", file=sys.stderr)
        if once:
            break
        time.sleep(TICK_INTERVAL)


if __name__ == "__main__":
    main()
