#!/usr/bin/env python3
"""
brain/vault/vault_sync.py
Bidirectional sync between SuneelWorkSpace state and the Obsidian vault.

Forward  (workspace → vault):
  Generates/refreshes brain/vault/organs/{organ}.md for all 12 organs.
  Frontmatter includes: live health, active tasks, diagnostic warnings.

Reverse  (vault → workspace):
  Watches brain/vault/organs/ for edits.
  - Checked task boxes  → update heart/tasks/ACTIVE_TASKS.md
  - Command triggers    → run the named CLI command
"""

import json
import os
import re
import subprocess
import sys
import threading
import time
from datetime import datetime, timezone
from pathlib import Path

WORKSPACE = Path(os.path.expanduser("~/SuneelWorkSpace"))
VAULT_ORGANS = WORKSPACE / "brain/vault/organs"
ACTIVE_TASKS = WORKSPACE / "heart/tasks/ACTIVE_TASKS.md"
HEALTH_FILE = WORKSPACE / "spine/state/WORKSPACE_HEALTH.json"

ORGANS = [
    "brain", "heart", "eyes", "ears", "nervous",
    "skeleton", "blood", "hands", "mouth", "dna", "lab", "spine",
]

# Commands the vault reverse-watcher is allowed to trigger.
_SAFE_COMMANDS = frozenset([
    "agent-doctor", "nerve-heal", "nerve-check", "nerve-status",
    "memory-curate", "memory-reindex", "run-tests", "readme-sync",
    "ollama-stack-status", "model-health",
])

_VENV_PY = str(WORKSPACE / ".venv/bin/python3")
PYTHON = _VENV_PY if os.path.exists(_VENV_PY) else sys.executable


# ── helpers ────────────────────────────────────────────────────────────────────

def _read(path: Path, max_chars: int = 2000) -> str:
    try:
        return path.read_text(errors="ignore")[:max_chars]
    except FileNotFoundError:
        return ""


def _load_health() -> dict:
    try:
        return json.loads(HEALTH_FILE.read_text())
    except Exception:
        return {}


def _load_active_tasks() -> list[str]:
    raw = _read(ACTIVE_TASKS, 4000)
    return [ln.strip() for ln in raw.splitlines() if ln.strip()]


def _notify(organ: str, event: str, detail: str) -> None:
    try:
        sys.path.insert(0, str(WORKSPACE))
        from nervous.nerve_propagator import notify_change
        notify_change(organ, event, detail)
    except Exception:
        pass


# ── forward sync: workspace → vault ────────────────────────────────────────────

def _organ_issues(health: dict, organ: str) -> list[str]:
    issues = health.get("issues", [])
    return [i["message"] for i in issues if i.get("organ") == organ or organ in i.get("message", "")]


def generate_organ_note(organ: str) -> str:
    """Build a fresh Obsidian Markdown note for one organ."""
    health = _load_health()
    tasks = _load_active_tasks()
    issues = _organ_issues(health, organ)
    health_score = health.get("health_score", "?")
    ts = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M UTC")

    nerve_path = WORKSPACE / organ / "nerve.json"
    nerve: dict = {}
    try:
        nerve = json.loads(nerve_path.read_text())
    except Exception:
        pass

    provides = ", ".join(nerve.get("provides", []))
    needs = ", ".join(nerve.get("needs", []))
    cli_cmds = ", ".join(nerve.get("cli_commands", []))

    # YAML frontmatter
    frontmatter_lines = [
        "---",
        f'organ: "{organ}"',
        f'workspace_health: {health_score}',
        f'last_sync: "{ts}"',
        f'issues: {len(issues)}',
        "tags:",
        f'  - organ/{organ}',
        "  - workspace/suneelworkspace",
        "---",
    ]

    # Body
    body_lines = [
        f"# {organ}",
        "",
        f"> Synced from SuneelWorkSpace — {ts}",
        "",
        "## Capabilities",
        f"**Provides**: {provides or '_none_'}",
        f"**Needs**: {needs or '_none_'}",
        f"**CLI**: `{cli_cmds or 'none'}`",
        "",
    ]

    body_lines += ["## Active Tasks", ""]
    organ_tasks = [t for t in tasks if organ in t.lower() or t.startswith("-")][:10]
    if organ_tasks:
        for t in organ_tasks:
            body_lines.append(f"- [ ] {t.lstrip('-').strip()}")
    else:
        body_lines.append("_No organ-specific tasks_")
    body_lines.append("")

    body_lines += ["## Diagnostic Warnings", ""]
    if issues:
        for issue in issues:
            body_lines.append(f"- ⚠️ {issue}")
    else:
        body_lines.append("✅ No issues")
    body_lines.append("")

    body_lines += [
        "## Commands",
        "",
        f"Run `agent-doctor` to refresh health → `- [ ] agent-doctor`",
        f"Run nerve heal → `- [ ] nerve-heal`",
        "",
        "---",
        "_Edit task checkboxes to sync back to ACTIVE_TASKS.md._",
        "_Add `- [ ] <cli-command>` and check it to trigger that command._",
    ]

    return "\n".join(frontmatter_lines) + "\n" + "\n".join(body_lines) + "\n"


def forward_sync(organs: list[str] | None = None) -> dict:
    """Write/refresh vault notes for all (or specified) organs, then run vault_graph."""
    VAULT_ORGANS.mkdir(parents=True, exist_ok=True)
    target = organs or ORGANS
    written = []
    for organ in target:
        note = generate_organ_note(organ)
        path = VAULT_ORGANS / f"{organ}.md"
        path.write_text(note)
        written.append(organ)
        _notify(organ, "vault_note_updated", str(path))

    # Run vault_graph: autolink + regenerate canvas after notes are refreshed
    try:
        from brain.vault.vault_graph import run as _graph_run
        graph_result = _graph_run()
    except Exception:
        try:
            import importlib.util, sys as _sys
            spec = importlib.util.spec_from_file_location(
                "vault_graph", WORKSPACE / "brain/vault/vault_graph.py"
            )
            mod = importlib.util.module_from_spec(spec)
            spec.loader.exec_module(mod)
            graph_result = mod.run()
        except Exception as e:
            graph_result = {"error": str(e)}

    return {
        "written": written,
        "ts": datetime.now(timezone.utc).isoformat(),
        "graph": graph_result,
    }


# ── daily evolution feed ────────────────────────────────────────────────────────

def update_evolution_feed(entry: str) -> None:
    feed = WORKSPACE / "brain/vault/Daily Evolution Feed.md"
    ts = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M UTC")
    header = f"\n## {ts}\n\n{entry}\n"
    if not feed.exists():
        feed.write_text(f"# Daily Evolution Feed\n\nAuto-generated evolution diary.\n{header}")
    else:
        existing = feed.read_text()
        feed.write_text(existing + header)


# ── reverse sync: vault → workspace ────────────────────────────────────────────

def _apply_checked_tasks(organ: str, prev_content: str, new_content: str) -> None:
    """Compare before/after — newly checked boxes sync to ACTIVE_TASKS.md or trigger CLI."""
    prev_checked = set(re.findall(r"- \[x\] (.+)", prev_content, re.IGNORECASE))
    new_checked = set(re.findall(r"- \[x\] (.+)", new_content, re.IGNORECASE))
    newly = new_checked - prev_checked

    for task_text in newly:
        task_text = task_text.strip()
        # Command trigger
        if task_text in _SAFE_COMMANDS:
            bin_cmd = str(WORKSPACE / "hands/bin" / task_text)
            subprocess.Popen(
                [bin_cmd],
                cwd=str(WORKSPACE),
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL,
            )
            _notify(organ, "vault_command_triggered", task_text)
            continue
        # Task sync → mark complete in ACTIVE_TASKS.md
        if ACTIVE_TASKS.exists():
            content = ACTIVE_TASKS.read_text()
            updated = re.sub(
                rf"(- )\[ \]( {re.escape(task_text)})",
                r"\1[x]\2",
                content,
            )
            if updated != content:
                ACTIVE_TASKS.write_text(updated)
                _notify("heart", "task_completed_via_vault", task_text)


class _ReverseWatcher:
    """Watches vault/organs/ for file edits and syncs changes back to workspace."""

    def __init__(self) -> None:
        self._snapshots: dict[str, str] = {}
        self._lock = threading.Lock()
        self._timer: threading.Timer | None = None

    def _snapshot(self) -> None:
        for path in VAULT_ORGANS.glob("*.md"):
            key = str(path)
            if key not in self._snapshots:
                try:
                    self._snapshots[key] = path.read_text(errors="ignore")
                except OSError:
                    pass

    def _check(self) -> None:
        for path in VAULT_ORGANS.glob("*.md"):
            key = str(path)
            organ = path.stem
            if organ not in ORGANS:
                continue
            try:
                current = path.read_text(errors="ignore")
            except OSError:
                continue
            prev = self._snapshots.get(key, current)
            if current != prev:
                with self._lock:
                    self._snapshots[key] = current
                _apply_checked_tasks(organ, prev, current)

    def run_polling(self, interval: float = 3.0) -> None:
        VAULT_ORGANS.mkdir(parents=True, exist_ok=True)
        self._snapshot()
        print(f"[vault-sync] reverse watcher polling every {interval}s")
        while True:
            try:
                self._check()
            except Exception as e:
                print(f"[vault-sync] reverse watch error: {e}", file=sys.stderr)
            time.sleep(interval)


# ── entry point ────────────────────────────────────────────────────────────────

def main() -> None:
    import argparse
    parser = argparse.ArgumentParser(description="Obsidian vault sync")
    parser.add_argument("--forward-only", action="store_true", help="One-shot forward sync then exit")
    parser.add_argument("--watch", action="store_true", help="Start reverse watcher (blocking)")
    args = parser.parse_args()

    if args.watch:
        watcher = _ReverseWatcher()
        print("[vault-sync] starting in watch mode (reverse + forward periodic)")
        def _periodic_forward():
            while True:
                time.sleep(300)  # refresh forward every 5 min
                forward_sync()
        t = threading.Thread(target=_periodic_forward, daemon=True)
        t.start()
        forward_sync()
        watcher.run_polling()
    else:
        result = forward_sync()
        print(f"[vault-sync] wrote {len(result['written'])} organ notes: {', '.join(result['written'])}")


if __name__ == "__main__":
    main()
