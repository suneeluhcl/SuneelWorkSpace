#!/usr/bin/env python3
"""
Evolution Feedback Loop — reads lab/autolab/results and injects outcomes into READMEs.

Reads completed lab challenges for a folder and adds:
  ## 🧪 Evolution Outcomes

Outcome types tracked:
  - Completed experiments (success/failure)
  - Health improvements triggered by evolution
  - Hypotheses validated
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

LAB_CHALLENGES_DIR = WORKSPACE / "lab/autolab/challenges"
LAB_RESULTS_DIR = WORKSPACE / "lab/autolab/results"


def _load_challenge_files(folder_rel: str) -> list:
    """Find challenge JSON files for a specific folder."""
    challenges = []
    safe_name = folder_rel.replace("/", "_").replace(".", "_")

    for search_dir in [LAB_CHALLENGES_DIR, LAB_RESULTS_DIR]:
        if not search_dir.exists():
            continue
        for f in search_dir.glob(f"*{safe_name}*.json"):
            try:
                data = json.loads(f.read_text())
                data["_source_file"] = f.name
                data["_is_result"] = search_dir == LAB_RESULTS_DIR
                challenges.append(data)
            except Exception:
                pass

    # Also search by organ
    organ = folder_rel.split("/")[0]
    for search_dir in [LAB_CHALLENGES_DIR, LAB_RESULTS_DIR]:
        if not search_dir.exists():
            continue
        for f in search_dir.glob(f"*{organ}*.json"):
            try:
                data = json.loads(f.read_text())
                if data not in challenges:
                    data["_source_file"] = f.name
                    data["_is_result"] = search_dir == LAB_RESULTS_DIR
                    challenges.append(data)
            except Exception:
                pass

    return challenges


def get_evolution_outcomes(folder_path: str) -> dict:
    """
    Get evolution outcomes for a folder.

    Returns:
        {
          folder: str,
          pending_challenges: list[dict],
          completed_results: list[dict],
          net_health_change: int,
          last_experiment: str,
          has_outcomes: bool,
          timestamp: str,
        }
    """
    path = Path(folder_path).resolve()
    try:
        rel = str(path.relative_to(WORKSPACE))
    except ValueError:
        rel = str(path)

    all_files = _load_challenge_files(rel)
    pending = [f for f in all_files if not f.get("_is_result")]
    completed = [f for f in all_files if f.get("_is_result")]

    # Estimate health change from completed results
    net_change = 0
    for result in completed:
        before = result.get("health_before", result.get("health_score", 0))
        after = result.get("health_after", 0)
        if before and after:
            net_change += after - before

    last_exp = ""
    if completed:
        completed.sort(key=lambda x: x.get("completed", x.get("created", "")), reverse=True)
        last_exp = completed[0].get("completed", completed[0].get("created", ""))[:10]
    elif pending:
        pending.sort(key=lambda x: x.get("created", ""), reverse=True)
        last_exp = f"pending ({pending[0].get('created', '')[:10]})"

    return {
        "folder": rel,
        "pending_challenges": pending[:5],
        "completed_results": completed[:5],
        "net_health_change": net_change,
        "last_experiment": last_exp,
        "has_outcomes": bool(pending or completed),
        "timestamp": datetime.now().isoformat(),
    }


def build_evolution_section(result: dict) -> str:
    """Generate ## 🧪 Evolution Outcomes markdown section."""
    lines = ["## 🧪 Evolution Outcomes\n"]

    if not result["has_outcomes"]:
        lines.append("No evolution experiments recorded for this folder.\n")
        lines.append(f"*Checked: {result['timestamp'][:19]}*")
        return "\n".join(lines)

    if result["net_health_change"] != 0:
        arrow = "📈" if result["net_health_change"] > 0 else "📉"
        sign = "+" if result["net_health_change"] > 0 else ""
        lines.append(f"**Net health change:** {arrow} {sign}{result['net_health_change']} points\n")

    if result["completed_results"]:
        lines.append(f"**Completed experiments ({len(result['completed_results'])}):**")
        for r in result["completed_results"][:3]:
            status = r.get("status", r.get("outcome", "unknown"))
            exp_type = r.get("type", "experiment")
            created = r.get("created", "")[:10]
            lines.append(f"- `{exp_type}` — {status} ({created})")
            if r.get("instructions"):
                lines.append(f"  *{r['instructions'][:80]}*")
        lines.append("")

    if result["pending_challenges"]:
        lines.append(f"**Pending challenges ({len(result['pending_challenges'])}):**")
        for p in result["pending_challenges"][:3]:
            priority = p.get("priority", "medium")
            exp_type = p.get("type", "challenge")
            lines.append(f"- `{exp_type}` [{priority}] — {p.get('instructions', '')[:60]}")
        lines.append("")

    if result["last_experiment"]:
        lines.append(f"*Last experiment: {result['last_experiment']}*")

    return "\n".join(lines)


def inject_evolution_into_readme(folder_path: str) -> bool:
    """Read existing README and inject/update evolution section."""
    path = Path(folder_path).resolve()
    readme = path / "README.md"
    if not readme.exists():
        return False

    result = get_evolution_outcomes(str(path))
    if not result["has_outcomes"]:
        return False

    section = build_evolution_section(result)
    content = readme.read_text(errors="ignore")

    # Replace existing section or append
    if "## 🧪 Evolution Outcomes" in content:
        content = re.sub(
            r"## 🧪 Evolution Outcomes.*?(?=\n## |\Z)",
            section + "\n\n",
            content,
            flags=re.DOTALL,
        )
    else:
        content = content.rstrip() + f"\n\n{section}\n"

    try:
        tmp = path / "README.tmp.md"
        tmp.write_text(content)
        tmp.rename(readme)
        return True
    except Exception:
        return False


if __name__ == "__main__":
    import argparse
    parser = argparse.ArgumentParser(description="Read lab evolution results and update READMEs")
    parser.add_argument("folder", nargs="?", help="Folder to update (default: all with lab results)")
    parser.add_argument("--dry-run", action="store_true", help="Show outcomes without writing")
    args = parser.parse_args()

    if args.folder:
        result = get_evolution_outcomes(args.folder)
        print(json.dumps(result, indent=2))
        if not args.dry_run and result["has_outcomes"]:
            ok = inject_evolution_into_readme(args.folder)
            print(f"README updated: {ok}")
    else:
        # Scan all folders with lab results
        count = 0
        if LAB_RESULTS_DIR.exists():
            for f in LAB_RESULTS_DIR.glob("*.json"):
                try:
                    data = json.loads(f.read_text())
                    target = data.get("target_folder")
                    if target:
                        folder = str(WORKSPACE / target)
                        if not args.dry_run:
                            ok = inject_evolution_into_readme(folder)
                            if ok:
                                count += 1
                                print(f"  ✅ Updated {target}")
                except Exception:
                    pass
        print(f"Updated {count} READMEs with evolution outcomes")
