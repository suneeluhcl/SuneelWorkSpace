#!/usr/bin/env python3
"""
Priority Engine — ranks workspace README/health issues by severity and impact.

Produces: spine/readme_priority_queue.json

Priority factors:
  - Health score (lower = higher priority)
  - Blast radius (more dependents = higher priority)
  - Critical issues count
  - README missing (always P0)
  - Days since last update
"""
import json
import os
import subprocess
import sys
from datetime import datetime
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[3]))

WORKSPACE = Path(subprocess.check_output(
    ["git", "rev-parse", "--show-toplevel"], text=True,
    cwd=os.path.dirname(os.path.abspath(__file__))
).strip())

PRIORITY_QUEUE_PATH = WORKSPACE / "spine/readme_priority_queue.json"
CACHE_PATH = WORKSPACE / "spine/readme_health_cache.json"
DEP_MAP_PATH = WORKSPACE / "spine/readme_dependency_map.json"


def _load_cache() -> dict:
    if CACHE_PATH.exists():
        try:
            return json.loads(CACHE_PATH.read_text())
        except Exception:
            pass
    return {}


def _load_dep_map() -> dict:
    if DEP_MAP_PATH.exists():
        try:
            return json.loads(DEP_MAP_PATH.read_text()).get("folders", {})
        except Exception:
            pass
    return {}


def _blast_radius(folder_rel: str, dep_map: dict, visited=None, depth=0) -> int:
    if visited is None:
        visited = set()
    if folder_rel in visited or depth > 3:
        return 0
    visited.add(folder_rel)
    rdeps = dep_map.get(folder_rel, {}).get("reverse_dependencies", [])
    total = len(rdeps)
    for rdep in rdeps:
        total += _blast_radius(rdep, dep_map, visited, depth + 1)
    return total


def _days_since_update(folder_path: Path) -> int:
    readme = folder_path / "README.md"
    if not readme.exists():
        return 999
    try:
        import time
        mtime = readme.stat().st_mtime
        return int((time.time() - mtime) / 86400)
    except Exception:
        return 0


def _priority_label(score: int) -> str:
    if score >= 80:
        return "P0"
    elif score >= 60:
        return "P1"
    elif score >= 40:
        return "P2"
    else:
        return "P3"


def compute_priority_queue(workspace_root: str = None) -> list:
    """
    Compute prioritized issue queue for all folders.

    Each entry:
        {
          priority: "P0" | "P1" | "P2" | "P3",
          priority_score: int (higher = more urgent),
          folder: str,
          health_score: int,
          blast_radius: int,
          critical_issues: list[str],
          days_since_update: int,
          readme_missing: bool,
        }
    """
    root = Path(workspace_root) if workspace_root else WORKSPACE
    cache = _load_cache()
    dep_map = _load_dep_map()

    from hands.automation.readme.intelligence_engine import analyze_workspace
    analyses = analyze_workspace(str(root))

    entries = []
    for analysis in analyses:
        rel = analysis["path"]
        folder_path = root / rel

        cached = cache.get(rel, {})
        health = cached.get("health_score", -1)

        if health == -1:
            try:
                from hands.automation.readme.health_scorer import score_folder
                scored = score_folder(str(folder_path), analysis=analysis)
                health = scored["score"]
                critical_issues = scored["critical_issues"]
            except Exception:
                health = 50
                critical_issues = []
        else:
            critical_issues = cached.get("critical_issues", [])

        readme_missing = not (folder_path / "README.md").exists()
        blast = _blast_radius(rel, dep_map)
        days = _days_since_update(folder_path)

        # Priority score: lower health, higher blast, more issues = higher score
        priority_score = (
            (100 - health) * 2
            + blast * 3
            + len(critical_issues) * 5
            + min(days, 30)
            + (50 if readme_missing else 0)
        )

        entries.append({
            "priority": _priority_label(priority_score),
            "priority_score": priority_score,
            "folder": rel,
            "health_score": health,
            "blast_radius": blast,
            "critical_issues": critical_issues[:3],
            "days_since_update": days,
            "readme_missing": readme_missing,
        })

    entries.sort(key=lambda x: x["priority_score"], reverse=True)

    # Write queue
    queue = {
        "generated": datetime.now().isoformat(),
        "total": len(entries),
        "p0_count": len([e for e in entries if e["priority"] == "P0"]),
        "p1_count": len([e for e in entries if e["priority"] == "P1"]),
        "p2_count": len([e for e in entries if e["priority"] == "P2"]),
        "p3_count": len([e for e in entries if e["priority"] == "P3"]),
        "queue": entries[:100],
    }
    tmp = PRIORITY_QUEUE_PATH.with_suffix(".tmp.json")
    PRIORITY_QUEUE_PATH.parent.mkdir(parents=True, exist_ok=True)
    tmp.write_text(json.dumps(queue, indent=2))
    tmp.rename(PRIORITY_QUEUE_PATH)
    return entries


def get_top_priority(n: int = 10) -> list:
    """Get top N priority items from existing queue."""
    if PRIORITY_QUEUE_PATH.exists():
        try:
            data = json.loads(PRIORITY_QUEUE_PATH.read_text())
            return data.get("queue", [])[:n]
        except Exception:
            pass
    return compute_priority_queue()[:n]


if __name__ == "__main__":
    import argparse
    parser = argparse.ArgumentParser(description="Compute README issue priority queue")
    parser.add_argument("--top", type=int, default=20, help="Show top N issues")
    parser.add_argument("--rebuild", action="store_true", help="Rebuild queue from scratch")
    args = parser.parse_args()

    if args.rebuild:
        entries = compute_priority_queue()
        print(f"Built priority queue: {len(entries)} folders")
    else:
        entries = get_top_priority(args.top)

    print(f"\n{'Priority':10} {'Score':6} {'Health':7} {'Blast':6} {'Folder'}")
    print("-" * 65)
    for e in entries[:args.top]:
        if e["priority_score"] > 20:
            print(f"{e['priority']:10} {e['priority_score']:6} {e['health_score']:7} {e['blast_radius']:6}   {e['folder']}")
