#!/usr/bin/env python3
"""
Failure Cascade Engine — extends change_impact_engine with failure propagation.

Maps: "If this folder fails → what else breaks?"

Uses:
  - spine/readme_dependency_map.json (reverse_dependencies)
  - Runtime probe health data
  - Health cache scores

Adds ## 🌐 Failure Impact Map section to READMEs.
"""
import json
import os
import subprocess
import sys
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Set

sys.path.insert(0, str(Path(__file__).resolve().parents[3]))

WORKSPACE = Path(subprocess.check_output(
    ["git", "rev-parse", "--show-toplevel"], text=True,
    cwd=os.path.dirname(os.path.abspath(__file__))
).strip())

DEP_MAP_PATH = WORKSPACE / "spine/readme_dependency_map.json"
CACHE_PATH = WORKSPACE / "spine/readme_health_cache.json"

SEVERITY_THRESHOLDS = {"critical": 40, "high": 60, "medium": 80}


def _load_dep_map() -> dict:
    if DEP_MAP_PATH.exists():
        try:
            return json.loads(DEP_MAP_PATH.read_text()).get("folders", {})
        except Exception:
            pass
    return {}


def _load_cache() -> dict:
    if CACHE_PATH.exists():
        try:
            return json.loads(CACHE_PATH.read_text())
        except Exception:
            pass
    return {}


def _get_downstream(folder_rel: str, dep_map: dict, visited: Set[str] = None, depth: int = 0) -> List[dict]:
    """Recursively find all folders that depend on folder_rel."""
    if visited is None:
        visited = set()
    if folder_rel in visited or depth > 4:
        return []
    visited.add(folder_rel)

    results = []
    rdeps = dep_map.get(folder_rel, {}).get("reverse_dependencies", [])
    for rdep in rdeps:
        results.append({"path": rdep, "depth": depth + 1})
        results.extend(_get_downstream(rdep, dep_map, visited, depth + 1))
    return results


def compute_failure_impact(folder_path: str) -> dict:
    """
    Compute failure impact for a folder.

    Returns:
        {
          folder: str,
          direct_dependents: list[str],
          cascade_dependents: list[{path, depth}],
          blast_radius: int,
          severity: "critical" | "high" | "medium" | "low",
          at_risk_folders: list[str],  # dependents with low health scores
          timestamp: str,
        }
    """
    path = Path(folder_path).resolve()
    try:
        rel = str(path.relative_to(WORKSPACE))
    except ValueError:
        rel = str(path)

    dep_map = _load_dep_map()
    cache = _load_cache()

    direct = dep_map.get(rel, {}).get("reverse_dependencies", [])
    all_downstream = _get_downstream(rel, dep_map)

    # Deduplicate by path, keep shallowest depth
    seen: Dict[str, int] = {}
    for item in all_downstream:
        p = item["path"]
        if p not in seen or item["depth"] < seen[p]:
            seen[p] = item["depth"]

    cascade = [{"path": p, "depth": d} for p, d in sorted(seen.items(), key=lambda x: x[1])]
    blast_radius = len(cascade)

    # Find at-risk folders (dependents with health < 70)
    at_risk = []
    for item in cascade:
        score = cache.get(item["path"], {}).get("health_score", 100)
        if score < 70:
            at_risk.append(f"{item['path']} (score: {score})")

    # Severity based on blast radius
    if blast_radius >= 10:
        severity = "critical"
    elif blast_radius >= 5:
        severity = "high"
    elif blast_radius >= 2:
        severity = "medium"
    else:
        severity = "low"

    return {
        "folder": rel,
        "direct_dependents": direct,
        "cascade_dependents": cascade[:20],
        "blast_radius": blast_radius,
        "severity": severity,
        "at_risk_folders": at_risk[:5],
        "timestamp": datetime.now().isoformat(),
    }


def build_failure_impact_section(result: dict) -> str:
    """Generate ## 🌐 Failure Impact Map markdown section."""
    lines = ["## 🌐 Failure Impact Map\n"]
    sev_emoji = {"critical": "🔴", "high": "🟠", "medium": "🟡", "low": "🟢"}
    lines.append(f"**Blast Radius:** {sev_emoji.get(result['severity'], '⚪')} {result['blast_radius']} folders affected if this fails\n")

    if result["direct_dependents"]:
        lines.append("**Direct dependents:**")
        for dep in result["direct_dependents"][:5]:
            lines.append(f"- `{dep}/`")
        lines.append("")

    if result["cascade_dependents"]:
        lines.append(f"**Cascade (depth 1-{max(c['depth'] for c in result['cascade_dependents'])}):**")
        by_depth: Dict[int, List[str]] = {}
        for item in result["cascade_dependents"][:10]:
            by_depth.setdefault(item["depth"], []).append(item["path"])
        for depth, paths in sorted(by_depth.items()):
            lines.append(f"- Depth {depth}: {', '.join(f'`{p}`' for p in paths[:3])}")
        lines.append("")

    if result["at_risk_folders"]:
        lines.append("**⚠️ At-risk dependents (low health):**")
        for r in result["at_risk_folders"]:
            lines.append(f"- {r}")
        lines.append("")

    if result["blast_radius"] == 0:
        lines.append("No downstream dependents. Failure is isolated.\n")

    lines.append(f"*Computed: {result['timestamp'][:19]}*")
    return "\n".join(lines)


def compute_workspace_blast_map(workspace_root: str = None) -> dict:
    """Compute failure impact for all folders, return sorted by blast radius."""
    from hands.automation.readme.intelligence_engine import analyze_workspace
    root = Path(workspace_root) if workspace_root else WORKSPACE
    analyses = analyze_workspace(str(root))
    results = []
    for analysis in analyses:
        folder = str(root / analysis["path"])
        try:
            result = compute_failure_impact(folder)
            results.append(result)
        except Exception:
            pass
    return sorted(results, key=lambda x: x["blast_radius"], reverse=True)


if __name__ == "__main__":
    import argparse
    parser = argparse.ArgumentParser(description="Compute failure cascade impact")
    parser.add_argument("folder", nargs="?", help="Folder to analyze (default: top 10 by blast radius)")
    args = parser.parse_args()

    if args.folder:
        result = compute_failure_impact(args.folder)
        print(json.dumps(result, indent=2))
    else:
        results = compute_workspace_blast_map()
        print(f"{'Severity':10} {'Blast':6} {'Folder'}")
        print("-" * 50)
        for r in results[:15]:
            if r["blast_radius"] > 0:
                print(f"{r['severity']:10} {r['blast_radius']:6}   {r['folder']}")
