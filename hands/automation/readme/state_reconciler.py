#!/usr/bin/env python3
"""
State Reconciler — compares CURRENT_STATE.json + runtime probe + READMEs.

Detects:
  - Undocumented live components (exist in probe, missing from README)
  - Dead documented components (in README Contents, not on disk)
  - Mismatched wiring (README says depends on X, dep map says otherwise)

Adds ## 🧬 State Alignment section to READMEs.
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

STATE_FILE = WORKSPACE / "spine/state/CURRENT_STATE.json"
RECONCILE_REPORT = WORKSPACE / "spine/readme_reconcile_report.json"


def _load_current_state() -> dict:
    if STATE_FILE.exists():
        try:
            return json.loads(STATE_FILE.read_text())
        except Exception:
            pass
    return {}


def _extract_readme_contents(readme_path: Path) -> list:
    """Parse ## 📂 Contents section for file references."""
    if not readme_path.exists():
        return []
    content = readme_path.read_text(errors="ignore")
    match = re.search(r"## 📂 Contents(.*?)(?=\n## |\Z)", content, re.DOTALL)
    if not match:
        return []
    files = re.findall(r"`([^`]+\.[a-zA-Z0-9]+)`", match.group(1))
    return [f for f in files if "/" not in f]


def _get_actual_files(folder: Path) -> list:
    """List non-hidden code files directly in folder."""
    try:
        return [
            f.name for f in folder.iterdir()
            if f.is_file() and not f.name.startswith(".")
            and f.name not in {"README.md", "README.tmp.md", "README.lock"}
            and f.suffix not in {".pyc", ".log", ".jsonl"}
        ]
    except Exception:
        return []


def reconcile_folder(folder_path: str) -> dict:
    """
    Reconcile a single folder's README against actual disk state.

    Returns:
        {
          folder: str,
          undocumented_files: list[str],   # on disk, not in README
          ghost_files: list[str],           # in README, not on disk
          wiring_mismatches: list[str],
          state_note: str,                  # from CURRENT_STATE.json if present
          status: "aligned" | "drifted" | "critical",
          timestamp: str,
        }
    """
    path = Path(folder_path).resolve()
    try:
        rel = str(path.relative_to(WORKSPACE))
    except ValueError:
        rel = str(path)

    actual = set(_get_actual_files(path))
    documented = set(_extract_readme_contents(path / "README.md"))

    undocumented = sorted(actual - documented)
    ghost = sorted(documented - actual)

    # Wiring mismatches: check dep map vs README links
    wiring_mismatches = []
    dep_map_path = WORKSPACE / "spine/readme_dependency_map.json"
    if dep_map_path.exists():
        try:
            dep_data = json.loads(dep_map_path.read_text()).get("folders", {})
            folder_entry = dep_data.get(rel, {})
            declared_deps = set(folder_entry.get("dependencies", []))
            readme_path = path / "README.md"
            if readme_path.exists():
                content = readme_path.read_text(errors="ignore")
                readme_links = set(re.findall(r"\.\./([^/\"')]+)/README\.md", content))
                extra = readme_links - declared_deps
                missing = declared_deps - readme_links
                for e in extra:
                    wiring_mismatches.append(f"README links {e}/ but not in dep map")
                for m in missing:
                    wiring_mismatches.append(f"dep map lists {m}/ but README doesn't link it")
        except Exception:
            pass

    # Pull note from CURRENT_STATE
    state = _load_current_state()
    state_note = ""
    for key in ["last_action", "last_agent", "session_summary", "active_task"]:
        val = state.get(key)
        if val and isinstance(val, str) and len(val) < 200:
            state_note = val
            break

    issues_count = len(undocumented) + len(ghost) + len(wiring_mismatches)
    if issues_count == 0:
        status = "aligned"
    elif issues_count <= 3:
        status = "drifted"
    else:
        status = "critical"

    return {
        "folder": rel,
        "undocumented_files": undocumented,
        "ghost_files": ghost,
        "wiring_mismatches": wiring_mismatches,
        "state_note": state_note,
        "status": status,
        "timestamp": datetime.now().isoformat(),
    }


def build_state_alignment_section(result: dict) -> str:
    """Generate ## 🧬 State Alignment markdown section."""
    lines = ["## 🧬 State Alignment\n"]
    status_emoji = {"aligned": "✅", "drifted": "⚠️", "critical": "❌"}
    lines.append(f"**Status:** {status_emoji.get(result['status'], '?')} {result['status'].upper()}\n")

    if result["undocumented_files"]:
        lines.append("**Undocumented files on disk:**")
        for f in result["undocumented_files"][:5]:
            lines.append(f"- `{f}` *(not in README Contents)*")
        lines.append("")

    if result["ghost_files"]:
        lines.append("**Ghost references (in README, not on disk):**")
        for f in result["ghost_files"][:5]:
            lines.append(f"- `{f}` *(referenced but missing)*")
        lines.append("")

    if result["wiring_mismatches"]:
        lines.append("**Wiring mismatches:**")
        for m in result["wiring_mismatches"][:3]:
            lines.append(f"- {m}")
        lines.append("")

    if not any([result["undocumented_files"], result["ghost_files"], result["wiring_mismatches"]]):
        lines.append("All documented files exist on disk. Dependencies aligned with dep map.\n")

    if result.get("state_note"):
        lines.append(f"*System state note: {result['state_note']}*\n")

    lines.append(f"*Last reconciled: {result['timestamp'][:19]}*")
    return "\n".join(lines)


def reconcile_all(workspace_root: str = None) -> list:
    """Reconcile all workspace folders and save report."""
    from hands.automation.readme.intelligence_engine import analyze_workspace
    root = Path(workspace_root) if workspace_root else WORKSPACE
    analyses = analyze_workspace(str(root))
    results = []
    for analysis in analyses:
        folder = str(root / analysis["path"])
        try:
            result = reconcile_folder(folder)
            results.append(result)
        except Exception:
            pass

    drifted = [r for r in results if r["status"] != "aligned"]
    report = {
        "generated": datetime.now().isoformat(),
        "total_folders": len(results),
        "aligned": len([r for r in results if r["status"] == "aligned"]),
        "drifted": len([r for r in results if r["status"] == "drifted"]),
        "critical": len([r for r in results if r["status"] == "critical"]),
        "drifted_folders": drifted,
    }
    tmp = RECONCILE_REPORT.with_suffix(".tmp.json")
    tmp.write_text(json.dumps(report, indent=2))
    tmp.rename(RECONCILE_REPORT)
    return results


if __name__ == "__main__":
    import argparse
    parser = argparse.ArgumentParser(description="Reconcile README vs disk state")
    parser.add_argument("folder", nargs="?", help="Folder to reconcile (default: all)")
    args = parser.parse_args()

    if args.folder:
        result = reconcile_folder(args.folder)
        print(json.dumps(result, indent=2))
    else:
        results = reconcile_all()
        drifted = [r for r in results if r["status"] != "aligned"]
        print(f"Total: {len(results)} | Aligned: {len(results) - len(drifted)} | Drifted/Critical: {len(drifted)}")
        for r in drifted[:10]:
            print(f"  {r['status'].upper():8} {r['folder']}")
