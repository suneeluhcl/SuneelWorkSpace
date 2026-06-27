#!/usr/bin/env python3
"""
Auto Repair Engine — detects and fixes README + workspace issues automatically.

Repair Policy:
  SAFE       → auto-fix (no approval needed)
  CONTROLLED → log + require approval
  RESTRICTED → log only, never auto-fix

SAFE repairs:
  - Missing README (regenerate)
  - Outdated README (regenerate)
  - Missing required sections (inject)
  - Ghost file references (remove from Contents)
  - Stale README.tmp.md files (clean up)

CONTROLLED repairs (require --approve flag):
  - Python import path fixes (single-line, non-logic changes)
  - Missing __init__.py in Python packages

RESTRICTED (log only):
  - Logic bugs
  - Config schema mismatches
  - Anything affecting executable behavior
"""
import json
import os
import re
import subprocess
import sys
from datetime import datetime
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[3]))

WORKSPACE = Path(subprocess.check_output(
    ["git", "rev-parse", "--show-toplevel"], text=True,
    cwd=os.path.dirname(os.path.abspath(__file__))
).strip())

REPAIR_LOG = WORKSPACE / "blood/logs/auto_repair.log"
REPAIR_REPORT = WORKSPACE / "spine/readme_repair_report.json"

REQUIRED_SECTIONS = ["Purpose", "Contents", "Change Log"]


def _log(msg: str) -> None:
    ts = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    REPAIR_LOG.parent.mkdir(parents=True, exist_ok=True)
    with open(REPAIR_LOG, "a") as f:
        f.write(f"[{ts}] {msg}\n")


def _check_policy(repair_type: str, approved: bool) -> str:
    """Return 'execute' | 'skip' | 'log_only'."""
    safe = {
        "missing_readme", "outdated_readme", "inject_section",
        "remove_ghost_refs", "clean_tmp_files",
    }
    controlled = {"add_init_py", "fix_import_path"}
    if repair_type in safe:
        return "execute"
    if repair_type in controlled:
        return "execute" if approved else "skip"
    return "log_only"


def repair_folder(folder_path: str, approved: bool = False, dry_run: bool = False) -> dict:
    """
    Scan and repair a single folder.

    Returns:
        {
          folder: str,
          repairs_done: list[{type, description, policy}],
          repairs_skipped: list[{type, description, reason}],
          timestamp: str,
        }
    """
    path = Path(folder_path).resolve()
    try:
        rel = str(path.relative_to(WORKSPACE))
    except ValueError:
        rel = str(path)

    done = []
    skipped = []

    # 1. Clean stale tmp files (SAFE)
    tmp = path / "README.tmp.md"
    if tmp.exists():
        policy_action = _check_policy("clean_tmp_files", approved)
        if not dry_run and policy_action == "execute":
            try:
                tmp.unlink()
                done.append({"type": "clean_tmp_files", "description": "Removed README.tmp.md", "policy": "SAFE"})
                _log(f"SAFE  {rel}: Removed README.tmp.md")
            except Exception as e:
                skipped.append({"type": "clean_tmp_files", "description": str(e), "reason": "error"})
        else:
            skipped.append({"type": "clean_tmp_files", "description": "Would remove README.tmp.md", "reason": "dry_run"})

    # 2. Generate missing README (SAFE)
    readme = path / "README.md"
    if not readme.exists():
        policy_action = _check_policy("missing_readme", approved)
        if not dry_run and policy_action == "execute":
            try:
                from hands.automation.readme.readme_generator import update_readme_for_folder
                success = update_readme_for_folder(str(path), use_claude=False)
                if success:
                    done.append({"type": "missing_readme", "description": "Generated missing README.md", "policy": "SAFE"})
                    _log(f"SAFE  {rel}: Generated missing README.md")
                else:
                    skipped.append({"type": "missing_readme", "description": "Generation failed", "reason": "error"})
            except Exception as e:
                skipped.append({"type": "missing_readme", "description": str(e), "reason": "error"})
        else:
            skipped.append({"type": "missing_readme", "description": "Would generate README.md", "reason": "dry_run"})

    # 3. Fix outdated README (SAFE)
    elif readme.exists():
        content = readme.read_text(errors="ignore")

        # 3a. Inject missing required sections (SAFE)
        for section in REQUIRED_SECTIONS:
            if section.lower() not in content.lower():
                policy_action = _check_policy("inject_section", approved)
                inject_text = f"\n\n## {section}\n\n*Auto-generated placeholder — update with accurate content.*\n"
                if not dry_run and policy_action == "execute":
                    try:
                        new_content = content + inject_text
                        readme.write_text(new_content)
                        content = new_content
                        done.append({
                            "type": "inject_section",
                            "description": f"Injected missing ## {section} section",
                            "policy": "SAFE",
                        })
                        _log(f"SAFE  {rel}: Injected ## {section}")
                    except Exception as e:
                        skipped.append({"type": "inject_section", "description": str(e), "reason": "error"})
                else:
                    skipped.append({
                        "type": "inject_section",
                        "description": f"Would inject ## {section}",
                        "reason": "dry_run",
                    })

        # 3b. Remove ghost file references from Contents (SAFE)
        match = re.search(r"(## 📂 Contents\n)(.*?)(?=\n## |\Z)", content, re.DOTALL)
        if match:
            contents_block = match.group(2)
            refs = re.findall(r"`([^`]+\.[a-zA-Z0-9]+)`", contents_block)
            ghost_refs = [f for f in refs if not (path / f).exists() and "/" not in f]
            if ghost_refs:
                policy_action = _check_policy("remove_ghost_refs", approved)
                if not dry_run and policy_action == "execute":
                    try:
                        new_block = contents_block
                        for ghost in ghost_refs:
                            new_block = re.sub(rf"- `{re.escape(ghost)}`[^\n]*\n?", "", new_block)
                        new_content = content.replace(contents_block, new_block)
                        readme.write_text(new_content)
                        done.append({
                            "type": "remove_ghost_refs",
                            "description": f"Removed ghost refs: {ghost_refs}",
                            "policy": "SAFE",
                        })
                        _log(f"SAFE  {rel}: Removed ghost refs {ghost_refs}")
                    except Exception as e:
                        skipped.append({"type": "remove_ghost_refs", "description": str(e), "reason": "error"})
                else:
                    skipped.append({
                        "type": "remove_ghost_refs",
                        "description": f"Would remove ghost refs: {ghost_refs}",
                        "reason": "dry_run",
                    })

    # 4. Add missing __init__.py to Python packages (CONTROLLED)
    py_files = list(path.glob("*.py"))
    init_py = path / "__init__.py"
    has_non_init = [f for f in py_files if f.name != "__init__.py" and not f.name.startswith("_")]
    if has_non_init and not init_py.exists():
        policy_action = _check_policy("add_init_py", approved)
        if not dry_run and policy_action == "execute":
            try:
                init_py.write_text("")
                done.append({"type": "add_init_py", "description": "Created __init__.py", "policy": "CONTROLLED"})
                _log(f"CTRL  {rel}: Created __init__.py")
            except Exception as e:
                skipped.append({"type": "add_init_py", "description": str(e), "reason": "error"})
        elif policy_action == "skip":
            skipped.append({"type": "add_init_py", "description": "Would create __init__.py", "reason": "needs --approve"})
        else:
            skipped.append({"type": "add_init_py", "description": "Would create __init__.py", "reason": "dry_run"})

    return {
        "folder": rel,
        "repairs_done": done,
        "repairs_skipped": skipped,
        "timestamp": datetime.now().isoformat(),
    }


def repair_all(approved: bool = False, dry_run: bool = False) -> dict:
    """Repair all workspace folders. Returns summary."""
    from hands.automation.readme.intelligence_engine import analyze_workspace
    analyses = analyze_workspace()
    total_done = 0
    total_skipped = 0
    folder_results = []

    for analysis in analyses:
        folder = str(WORKSPACE / analysis["path"])
        try:
            result = repair_folder(folder, approved=approved, dry_run=dry_run)
            if result["repairs_done"] or result["repairs_skipped"]:
                folder_results.append(result)
            total_done += len(result["repairs_done"])
            total_skipped += len(result["repairs_skipped"])
        except Exception:
            pass

    summary = {
        "generated": datetime.now().isoformat(),
        "dry_run": dry_run,
        "approved": approved,
        "total_repairs_done": total_done,
        "total_repairs_skipped": total_skipped,
        "folders_with_repairs": len(folder_results),
        "results": folder_results[:50],
    }
    tmp = REPAIR_REPORT.with_suffix(".tmp.json")
    tmp.write_text(json.dumps(summary, indent=2))
    tmp.rename(REPAIR_REPORT)
    return summary


if __name__ == "__main__":
    import argparse
    parser = argparse.ArgumentParser(description="Auto-repair workspace README and structure issues")
    parser.add_argument("folder", nargs="?", help="Folder to repair (default: all)")
    parser.add_argument("--approve", action="store_true", help="Allow CONTROLLED repairs")
    parser.add_argument("--dry-run", action="store_true", help="Show what would be done without doing it")
    args = parser.parse_args()

    if args.folder:
        result = repair_folder(args.folder, approved=args.approve, dry_run=args.dry_run)
        print(json.dumps(result, indent=2))
    else:
        summary = repair_all(approved=args.approve, dry_run=args.dry_run)
        mode = "DRY RUN" if args.dry_run else "LIVE"
        print(f"[{mode}] Done: {summary['total_repairs_done']} | Skipped: {summary['total_repairs_skipped']}")
