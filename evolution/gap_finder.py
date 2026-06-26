"""
gap_finder.py
Scans the workspace for missing capabilities and knowledge gaps.
Outputs a structured gap report to brain/system/gap_analysis_latest.json.
"""
import json
import sys
from datetime import datetime, timezone
from pathlib import Path

_HERE = Path(__file__).parent
WORKSPACE = _HERE.parent
GAP_OUTPUT = WORKSPACE / "brain/system/gap_analysis_latest.json"

EXPECTED_CAPABILITIES = [
    {"id": "model_router",     "path": "agent_system/model_router/router.py",               "desc": "Multi-model routing with fallback"},
    {"id": "visual_monitor",   "path": "visual/screenshot_manager.py",                       "desc": "Visual monitoring + screenshot manager"},
    {"id": "vision_analyzer",  "path": "visual/vision_analyzer.py",                          "desc": "AI vision analysis of screenshots"},
    {"id": "visual_repair",    "path": "visual/visual_repair_agent.py",                      "desc": "Visual repair agent"},
    {"id": "vision_impl",      "path": "visual/vision_implementer.py",                       "desc": "Vision-to-implementation bridge"},
    {"id": "evolution_engine", "path": "evolution/engine.py",                                "desc": "Autonomous evolution engine"},
    {"id": "night_shift",      "path": "orchestrator/dag/pipelines/night_shift.yaml",        "desc": "Night shift scheduler"},
    {"id": "health_repair",    "path": "dashboard/execution/health_repair_pipeline.py",      "desc": "Health repair pipeline"},
    {"id": "autolab",          "path": "autolab/runner.py",                                  "desc": "Autolab experiment runner"},
    {"id": "memory_vector",    "path": "agent-system/memory/vector/chroma_store",            "desc": "Vector memory store"},
    {"id": "mcp_server",       "path": "mcp/server/main.py",                                 "desc": "MCP server"},
    {"id": "orchestrator",     "path": "orchestrator/router/router.py",                      "desc": "Task orchestrator"},
    {"id": "goal_engine",      "path": "goal-engine/goal_tracker.py",                        "desc": "Goal tracking"},
    {"id": "challenger",       "path": "evolution/challenger.py",                            "desc": "Self-challenge generator"},
    {"id": "gap_finder",       "path": "evolution/gap_finder.py",                            "desc": "Gap finder (this file)"},
]


def scan_for_gaps() -> dict:
    """Scan workspace for missing capabilities and knowledge gaps."""
    gaps: list[dict] = []
    present: list[str] = []

    for cap in EXPECTED_CAPABILITIES:
        full = WORKSPACE / cap["path"]
        if full.exists():
            present.append(cap["id"])
        else:
            gaps.append({**cap, "status": "missing", "priority": "high"})

    # Check for stale memory files
    stale: list[dict] = []
    check_files = [
        "agent-system/memory/MEMORY.md",
        "agent-system/memory/SESSION_HANDOFF.md",
    ]
    for rel in check_files:
        p = WORKSPACE / rel
        if p.exists():
            age_days = (datetime.now().timestamp() - p.stat().st_mtime) / 86400
            if age_days > 7:
                stale.append({"path": rel, "age_days": round(age_days, 1)})

    result = {
        "scanned_at": datetime.now(timezone.utc).isoformat(),
        "total_capabilities": len(EXPECTED_CAPABILITIES),
        "present": len(present),
        "present_ids": present,
        "gaps": gaps,
        "stale_files": stale,
        "gap_count": len(gaps),
        "health_pct": round(len(present) / len(EXPECTED_CAPABILITIES) * 100, 1),
    }

    try:
        GAP_OUTPUT.parent.mkdir(parents=True, exist_ok=True)
        GAP_OUTPUT.write_text(json.dumps(result, indent=2))
    except Exception:
        pass

    return result


if __name__ == "__main__":
    result = scan_for_gaps()
    print(f"Capability health: {result['health_pct']}%  ({result['present']}/{result['total_capabilities']} present, {result['gap_count']} gaps)")
    if result["gaps"]:
        print(f"\nGaps ({result['gap_count']}):")
        for g in result["gaps"]:
            print(f"  ✗  {g['id']:<24}  {g['desc']}")
    if result["stale_files"]:
        print(f"\nStale files:")
        for s in result["stale_files"]:
            print(f"  ⚠  {s['path']}  ({s['age_days']}d old)")
