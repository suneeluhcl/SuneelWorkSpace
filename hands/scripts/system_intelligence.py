#!/usr/bin/env python3
"""Local-first system audit, capability, and recommendation generator."""

from __future__ import annotations

import argparse
import json
import os
import platform
import shutil
import sqlite3
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


ROOT = Path(os.environ.get("SUNEEL_WORKSPACE", Path.home() / "SuneelWorkSpace")).resolve()
NOW = datetime.now(timezone.utc).astimezone()

EXPECTED_SUBSYSTEMS = [
    "agent-system",
    "mcp",
    "orchestrator",
    "goal-engine",
    "autolab",
    "comms",
    "bin",
    "scripts",
    "configs",
    "docs",
]

SAFE_CLI_TOOLS = [
    "rtk",
    "git",
    "gh",
    "python3",
    "pip3",
    "node",
    "npm",
    "pnpm",
    "uv",
    "brew",
    "codex",
    "claude",
    "gemini",
    "opencode",
    "rg",
    "jq",
    "sqlite3",
    "osascript",
    "shortcuts",
    "mdfind",
]

REPORT_RESOURCES = {
    "workspace://spine/audit/system": "spine/audit/system_audit.md",
    "workspace://spine/audit/gaps": "spine/audit/gap_analysis.md",
    "workspace://spine/audit/improvement-plan": "spine/audit/improvement_plan.md",
    "workspace://system/profile": "spine/system-context/system_profile.json",
    "workspace://spine/tools/inventory": "spine/tools/tool_inventory.json",
    "workspace://spine/tools/recommendations": "spine/tools/recommendations.md",
    "workspace://research/index": "brain/research/ideas/index.json",
    "workspace://research/decisions": "brain/research/decisions/README.md",
    "workspace://memory/patterns": "brain/memory/PATTERNS.md",
    "workspace://memory/insights": "brain/memory/INSIGHTS.md",
    "workspace://policy/bounded-self-upgrade": "skeleton/rules/BOUNDED_SELF_UPGRADE.md",
    "workspace://heart/orchestrator/system-intelligence-policy": "heart/orchestrator/router/system_intelligence_policy.md",
    "workspace://goals/idea-pipeline": "heart/goals/planner/idea_execution_pipeline.md",
    "workspace://lab/autolab/system-improvement-strategy": "lab/autolab/meta/system_improvement_strategy.md",
}


def rel(path: Path) -> str:
    try:
        return str(path.relative_to(ROOT))
    except ValueError:
        return str(path)


def read_json(path: Path, default: Any) -> Any:
    try:
        return json.loads(path.read_text())
    except Exception:
        return default


def write_json(path: Path, data: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(data, indent=2, sort_keys=True) + "\n")


def run_short(argv: list[str], timeout: float = 3.0) -> str | None:
    exe = shutil.which(argv[0])
    if not exe:
        return None
    try:
        out = subprocess.run(
            [exe, *argv[1:]],
            check=False,
            capture_output=True,
            text=True,
            timeout=timeout,
        )
    except Exception:
        return None
    text = (out.stdout or out.stderr or "").strip().splitlines()
    return text[0][:160] if text else None


def top_level_home_dirs() -> list[str]:
    home = Path.home()
    ignored = {".Trash", "Library"}
    names: list[str] = []
    for path in home.iterdir():
        if path.name in ignored:
            continue
        if path.is_dir():
            names.append(path.name)
    return sorted(names)


def installed_apps() -> list[dict[str, str]]:
    apps: list[dict[str, str]] = []
    for base in [Path("/Applications"), Path.home() / "Applications"]:
        if not base.exists():
            continue
        for path in sorted(base.glob("*.app"))[:200]:
            apps.append({"name": path.stem, "location": str(base)})
    return apps


def disk_summary() -> dict[str, Any]:
    usage = shutil.disk_usage(str(Path.home()))
    return {
        "home_total_gb": round(usage.total / 1024**3, 1),
        "home_used_gb": round(usage.used / 1024**3, 1),
        "home_free_gb": round(usage.free / 1024**3, 1),
    }


def hardware_summary() -> dict[str, Any]:
    summary: dict[str, Any] = {
        "platform": platform.platform(),
        "machine": platform.machine(),
        "processor": platform.processor(),
        "cpu_count": os.cpu_count(),
    }
    for key, command in {
        "mac_model": ["sysctl", "-n", "hw.model"],
        "memory_bytes": ["sysctl", "-n", "hw.memsize"],
    }.items():
        value = run_short(command)
        if value:
            summary[key] = int(value) if value.isdigit() else value
    if isinstance(summary.get("memory_bytes"), int):
        summary["memory_gb"] = round(summary["memory_bytes"] / 1024**3, 1)
    return summary


def workspace_snapshot() -> dict[str, Any]:
    dirs = sorted(
        p.name for p in ROOT.iterdir() if p.is_dir() and not p.name.startswith(".git")
    )
    files_by_subsystem: dict[str, int] = {}
    for name in EXPECTED_SUBSYSTEMS:
        base = ROOT / name
        if base.exists():
            files_by_subsystem[name] = sum(1 for p in base.rglob("*") if p.is_file())
        else:
            files_by_subsystem[name] = 0
    bin_commands = sorted(p.name for p in (ROOT / "bin").glob("*") if p.is_file())
    executable_issues = [
        rel(p)
        for p in (ROOT / "bin").glob("*")
        if p.is_file() and not os.access(p, os.X_OK)
    ]
    return {
        "root": str(ROOT),
        "top_level_directories": dirs,
        "expected_subsystems_present": {
            name: (ROOT / name).exists() for name in EXPECTED_SUBSYSTEMS
        },
        "files_by_subsystem": files_by_subsystem,
        "bin_command_count": len(bin_commands),
        "bin_commands": bin_commands,
        "non_executable_bin_files": executable_issues,
    }


def capability_profile() -> dict[str, Any]:
    cli_tools: list[dict[str, Any]] = []
    for name in SAFE_CLI_TOOLS:
        path = shutil.which(name)
        version = None
        if path:
            if name in {"python3", "node", "npm", "pnpm", "git", "gh", "rtk", "uv"}:
                version = run_short([name, "--version"])
            elif name in {"codex", "claude", "gemini", "opencode"}:
                version = run_short([name, "--version"])
        cli_tools.append(
            {"name": name, "available": bool(path), "path": path, "version": version}
        )

    profile = {
        "generated_at": NOW.isoformat(),
        "safety_scope": {
            "home_directory": "top-level directory names only",
            "applications": "top-level .app bundle names only",
            "private_file_contents": "not scanned",
            "external_installs": "not performed",
        },
        "workspace": workspace_snapshot(),
        "home_top_level_directories": top_level_home_dirs(),
        "installed_applications": installed_apps(),
        "development_environments": cli_tools,
        "hardware": hardware_summary(),
        "disk": disk_summary(),
    }
    write_json(ROOT / "spine/system-context/system_profile.json", profile)
    return profile


def tool_inventory(profile: dict[str, Any] | None = None) -> dict[str, Any]:
    if profile is None:
        profile = read_json(ROOT / "spine/system-context/system_profile.json", {}) or capability_profile()

    tools: list[dict[str, Any]] = []
    for command in profile.get("workspace", {}).get("bin_commands", []):
        tools.append(
            {
                "name": command,
                "purpose": "Workspace command",
                "install_location": str(ROOT / "bin" / command),
                "integration_potential": "Can be routed through agent workflows and maintenance checks.",
                "safe_to_integrate": True,
            }
        )
    for tool in profile.get("development_environments", []):
        if tool.get("available"):
            tools.append(
                {
                    "name": tool["name"],
                    "purpose": "CLI or development capability",
                    "install_location": tool.get("path"),
                    "integration_potential": integration_potential(tool["name"]),
                    "safe_to_integrate": tool["name"] not in {"brew"},
                }
            )
    for app in profile.get("installed_applications", [])[:80]:
        tools.append(
            {
                "name": app["name"],
                "purpose": "Installed macOS application",
                "install_location": app["location"],
                "integration_potential": "Potential AppleScript/Shortcuts/manual workflow support; requires explicit approval before automation.",
                "safe_to_integrate": False,
            }
        )
    inventory = {"generated_at": NOW.isoformat(), "tools": tools}
    write_json(ROOT / "spine/tools/tool_inventory.json", inventory)
    return inventory


def integration_potential(name: str) -> str:
    potentials = {
        "rtk": "Default shell output filter for agent commands.",
        "gh": "GitHub PR, issue, and CI inspection with explicit confirmation for writes.",
        "python3": "Local automation scripts and structured report generation.",
        "node": "Frontend/dev tooling and MCP helpers when project-local.",
        "osascript": "Bounded macOS automation for Mail, Messages, and app workflows.",
        "shortcuts": "User-approved local workflow automations.",
        "mdfind": "Metadata-only search for user-approved file organization tasks.",
        "rg": "Fast workspace search without broad private indexing.",
        "sqlite3": "Inspectable local indexes for MCP and research metadata.",
    }
    return potentials.get(name, "Useful when explicitly routed by a workspace command.")


def gap_items() -> list[dict[str, str]]:
    profile_exists = (ROOT / "spine/system-context/system_profile.json").exists()
    research_exists = (ROOT / "research-engine").exists()
    inventory_exists = (ROOT / "spine/tools/tool_inventory.json").exists()
    return [
        {
            "category": "architecture",
            "gap": "System-wide audit artifacts were missing or not first-class.",
            "impact": "Agents could inspect files ad hoc, but there was no durable overview for future sessions.",
            "fix": "Create audit reports, gap analysis, improvement plan, and MCP resources.",
            "priority": "P0",
        },
        {
            "category": "automation",
            "gap": "Health checks did not summarize spine/audit/gap/research/tool readiness.",
            "impact": "Maintenance could report green while intelligence coverage was incomplete.",
            "fix": "Add system-intelligence status and health update hooks.",
            "priority": "P0",
        },
        {
            "category": "intelligence",
            "gap": "Ideas, comparisons, and decisions had no dedicated pipeline.",
            "impact": "Research outcomes could remain in chat instead of becoming durable shared brain context.",
            "fix": "Add a local research engine with capture, research, analyze, decide, and bootstrap scripts.",
            "priority": "P0" if not research_exists else "P1",
        },
        {
            "category": "research",
            "gap": "Tool discovery was not summarized into an inspectable inventory.",
            "impact": "Agents had to rediscover installed CLIs, apps, and integration candidates.",
            "fix": "Generate spine/tools/tool_inventory.json and recommendations.md.",
            "priority": "P1" if inventory_exists else "P0",
        },
        {
            "category": "workflow",
            "gap": "Email, messaging, downloads, and file organization support existed only as scattered commands.",
            "impact": "Daily workflows lacked a unified route from capture to execution to memory.",
            "fix": "Route workflow ideas through idea-start/idea-run and record decisions in shared brain.",
            "priority": "P1",
        },
        {
            "category": "usability",
            "gap": "There was no single command for capabilities, gaps, recommendations, or bounded self-upgrade.",
            "impact": "Suneel had to know internal paths and command names.",
            "fix": "Add system-audit, system-gaps, system-capabilities, system-recommend, and improve-system.",
            "priority": "P0",
        },
        {
            "category": "architecture",
            "gap": "MCP resource coverage did not include audit, research, profile, and tool artifacts.",
            "impact": "Connected agents could miss the new intelligence surfaces.",
            "fix": "Register new resources in nervous/mcp/server/config/resource_map.json.",
            "priority": "P1",
        },
        {
            "category": "automation",
            "gap": "Autolab evaluates improvements, but weak-area discovery was not tied to system gaps.",
            "impact": "Self-improvement can optimize local prompt/docs while missing architecture-level needs.",
            "fix": "Add an autolab strategy note that consumes gap_analysis.md and recommendations.md.",
            "priority": "P1",
        },
    ]


def write_markdown_reports(profile: dict[str, Any], inventory: dict[str, Any]) -> None:
    audit_dir = ROOT / "spine" / "audit"
    audit_dir.mkdir(parents=True, exist_ok=True)
    subsystems = profile["workspace"]["expected_subsystems_present"]
    file_counts = profile["workspace"]["files_by_subsystem"]
    gaps = gap_items()

    strengths = [
        "Shared agent state is file-based and inspectable.",
        "Autolab already has evaluator, frontier, reports, rollback notes, and safety policy files.",
        "MCP server has local storage, resource maps, tool policies, and doctor/reindex scripts.",
        "Goal engine and orchestrator already expose planning, routing, history, and report surfaces.",
        "Comms commands exist for mail/message workflow primitives.",
    ]
    fragile = [
        "Several subsystems are connected by conventions and scripts rather than a central capability registry.",
        "Logs, backups, quarantine, and snapshots can grow without a user-facing retention summary.",
        "Daily workflow support needs more routeable playbooks before it feels like an operating system.",
        "Research decisions need explicit promotion into MEMORY.md, DECISIONS.md, patterns, and insights.",
        "Mac app automation should remain opt-in because Mail, Messages, downloads, and files are private surfaces.",
    ]

    audit = [
        "# System Audit",
        "",
        f"Generated: {NOW.isoformat()}",
        "",
        "## Scope",
        "",
        "Inspected workspace metadata, subsystem structure, command surfaces, MCP configuration, autolab state, orchestration files, goal-engine files, comms files, docs, logs, and state files under `~/SuneelWorkSpace`.",
        "",
        "No private home-directory file contents were ingested. Home awareness is limited to top-level directory names and system/application metadata.",
        "",
        "## Current Architecture",
        "",
    ]
    for name in EXPECTED_SUBSYSTEMS:
        status = "present" if subsystems.get(name) else "missing"
        audit.append(f"- `{name}`: {status}; files observed: {file_counts.get(name, 0)}")
    audit.extend(["", "## Strengths", ""])
    audit.extend(f"- {item}" for item in strengths)
    audit.extend(["", "## Fragile Areas", ""])
    audit.extend(f"- {item}" for item in fragile)
    audit.extend(["", "## Missing Or Incomplete Subsystems", ""])
    for item in gaps:
        audit.append(f"- [{item['priority']}] {item['category']}: {item['gap']} Impact: {item['impact']}")
    audit.extend(
        [
            "",
            "## Command Surface",
            "",
            f"- Workspace commands found: {profile['workspace']['bin_command_count']}",
            f"- Non-executable bin files: {len(profile['workspace']['non_executable_bin_files'])}",
            f"- Tool inventory entries: {len(inventory.get('tools', []))}",
            "",
            "## System Introspection",
            "",
            f"- CPU count: {profile['hardware'].get('cpu_count')}",
            f"- Memory GB: {profile['hardware'].get('memory_gb', 'unknown')}",
            f"- Home disk free GB: {profile['disk'].get('home_free_gb')}",
            f"- Installed application names captured: {len(profile.get('installed_applications', []))}",
            f"- Home top-level directory names captured: {len(profile.get('home_top_level_directories', []))}",
            "",
            "## Upgrade Direction",
            "",
            "The correct upgrade is not a rebuild. Keep the existing agent-system, MCP, orchestrator, goal-engine, comms, and autolab structure, then add a system intelligence layer that can audit, profile, recommend, and route ideas into research/decision artifacts.",
        ]
    )
    (audit_dir / "system_audit.md").write_text("\n".join(audit) + "\n")

    gap_doc = [
        "# Gap Analysis",
        "",
        f"Generated: {NOW.isoformat()}",
        "",
        "| Category | Priority | Gap | Impact | Suggested Fix |",
        "|---|---:|---|---|---|",
    ]
    for item in gaps:
        gap_doc.append(
            f"| {item['category']} | {item['priority']} | {item['gap']} | {item['impact']} | {item['fix']} |"
        )
    (audit_dir / "gap_analysis.md").write_text("\n".join(gap_doc) + "\n")

    plan = [
        "# Improvement Plan",
        "",
        f"Generated: {NOW.isoformat()}",
        "",
        "| Rank | Improvement | Effort | Expected Impact |",
        "|---:|---|---|---|",
        "| 1 | Keep system-audit and system-capabilities in regular maintenance. | Low | Agents start with current evidence instead of stale assumptions. |",
        "| 2 | Promote research decisions into DECISIONS.md and MEMORY.md after each idea-run. | Low | Durable learning improves future sessions. |",
        "| 3 | Add retention reporting for logs, snapshots, backups, and quarantine. | Medium | Prevents silent workspace bloat. |",
        "| 4 | Add explicit workflow playbooks for email, messaging, downloads, and file organization. | Medium | Turns scattered commands into repeatable daily workflows. |",
        "| 5 | Extend MCP resource map whenever new durable knowledge surfaces are added. | Low | Keeps connected agents aligned. |",
        "| 6 | Add opt-in macOS Shortcuts/AppleScript automations for approved apps. | Medium | Better daily assistance without broad private data access. |",
        "| 7 | Add recommendation review queue before installing external tools. | Low | Preserves safety while improving capability discovery. |",
        "| 8 | Let autolab consume gap_analysis.md as a weak-area input. | Medium | Self-improvement focuses on real system gaps. |",
        "| 9 | Add command-level smoke tests for all bin scripts. | Medium | Faster detection of broken or unused scripts. |",
        "| 10 | Create a lightweight knowledge index over approved workspace docs only. | Medium | Improves research and recall without scanning private folders. |",
    ]
    (audit_dir / "improvement_plan.md").write_text("\n".join(plan) + "\n")


def write_recommendations(profile: dict[str, Any], inventory: dict[str, Any]) -> None:
    lines = [
        "# Tool And Workflow Recommendations",
        "",
        f"Generated: {NOW.isoformat()}",
        "",
        "No external tools were installed. These are proposals for explicit future approval.",
        "",
        "## 1. Communication",
        "",
        "- Build opt-in Mail and Messages playbooks around existing `mail-*`, `imessage-*`, and `comms-*` commands.",
        "- Add approval gates for sending, deleting, archiving, forwarding, and contacting people.",
        "- Add digest generation that stores summaries, not private message bodies, unless explicitly requested.",
        "",
        "## 2. Research",
        "",
        "- Use `research-engine` for idea capture, planning, comparison, and decision records.",
        "- Add web research only when explicitly requested or when freshness materially matters.",
        "- Promote accepted decisions into `brain/memory/DECISIONS.md`.",
        "",
        "## 3. Automation",
        "",
        "- Connect `improve-system` to scheduled maintenance only after several manual runs are trusted.",
        "- Add bounded AppleScript/Shortcuts integrations per app, one workflow at a time.",
        "- Keep writes reversible with timestamped backups for important files.",
        "",
        "## 4. Development",
        "",
        "- Add smoke tests for every workspace command and report failures in `agent-doctor`.",
        "- Keep RTK as the default output filter for shell-heavy sessions.",
        "- Use `gh` for GitHub inspection and require explicit approval for publishing changes.",
        "",
        "## 5. System Management",
        "",
        "- Add retention summaries for `.agent-backups`, `snapshots`, `lab/autolab/quarantine`, and logs.",
        "- Keep system awareness metadata-only unless Suneel explicitly asks for deeper indexing.",
        "",
        "## 6. Data Organization",
        "",
        "- Start with metadata-only download/file triage: names, extensions, sizes, and dates.",
        "- Add move/rename actions only after preview and explicit approval.",
        "",
        "## 7. Assistant Intelligence",
        "",
        "- Treat `spine/audit/gap_analysis.md` as an input to autolab and goal planning.",
        "- Register new durable knowledge files in MCP resource maps.",
        "- Use `idea-run` to transform rough ideas into plans, tradeoffs, and decisions.",
        "",
        "## Inventory Summary",
        "",
        f"- Tool entries discovered: {len(inventory.get('tools', []))}",
        f"- CLI tools available: {sum(1 for t in profile.get('development_environments', []) if t.get('available'))}",
        f"- Installed app names captured: {len(profile.get('installed_applications', []))}",
    ]
    path = ROOT / "spine/tools/recommendations.md"
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text("\n".join(lines) + "\n")


def update_mcp_resource_map() -> None:
    path = ROOT / "nervous/mcp/server/config/resource_map.json"
    data = read_json(path, {})
    if "resources" in data and isinstance(data["resources"], dict):
        data["resources"].update(REPORT_RESOURCES)
    else:
        data.update(REPORT_RESOURCES)
    write_json(path, data)


def update_health() -> dict[str, Any]:
    health_path = ROOT / "spine/state/WORKSPACE_HEALTH.json"
    health = read_json(health_path, {})
    checks = {
        "system_audit": (ROOT / "spine/audit/system_audit.md").exists(),
        "gap_analysis": (ROOT / "spine/audit/gap_analysis.md").exists(),
        "improvement_plan": (ROOT / "spine/audit/improvement_plan.md").exists(),
        "system_profile": (ROOT / "spine/system-context/system_profile.json").exists(),
        "tool_inventory": (ROOT / "spine/tools/tool_inventory.json").exists(),
        "tool_recommendations": (ROOT / "spine/tools/recommendations.md").exists(),
        "research_engine": (ROOT / "research-engine").exists(),
        "mcp_resource_coverage": all(
            str(v) in json.dumps(read_json(ROOT / "nervous/mcp/server/config/resource_map.json", {}))
            for v in REPORT_RESOURCES.values()
        ),
    }
    health["system_intelligence"] = {
        "updated_at": NOW.isoformat(),
        "checks": checks,
        "ready": all(checks.values()),
    }
    health["state_updated_at"] = NOW.isoformat()
    write_json(health_path, health)
    return health


def status_text() -> str:
    health = read_json(ROOT / "spine/state/WORKSPACE_HEALTH.json", {})
    si = health.get("system_intelligence", {})
    checks = si.get("checks", {})
    ready = si.get("ready", False)
    lines = ["", "System Intelligence:"]
    lines.append(f"  ready: {ready}")
    for key in [
        "system_audit",
        "gap_analysis",
        "system_profile",
        "tool_inventory",
        "research_engine",
        "mcp_resource_coverage",
    ]:
        lines.append(f"  {key}: {checks.get(key, False)}")
    return "\n".join(lines)


def generate_all(update_resources: bool = True) -> None:
    profile = capability_profile()
    inventory = tool_inventory(profile)
    write_markdown_reports(profile, inventory)
    write_recommendations(profile, inventory)
    if update_resources:
        update_mcp_resource_map()
    update_health()


def main() -> int:
    parser = argparse.ArgumentParser(description="Workspace system intelligence")
    parser.add_argument(
        "command",
        choices=[
            "audit",
            "capabilities",
            "recommend",
            "gaps",
            "improve",
            "health-update",
            "status",
        ],
    )
    args = parser.parse_args()

    if args.command == "capabilities":
        capability_profile()
        print(ROOT / "spine/system-context/system_profile.json")
    elif args.command in {"audit", "gaps", "recommend", "improve"}:
        generate_all(update_resources=True)
        if args.command == "audit":
            print(ROOT / "spine/audit/system_audit.md")
        elif args.command == "gaps":
            print(ROOT / "spine/audit/gap_analysis.md")
        elif args.command == "recommend":
            print(ROOT / "spine/tools/recommendations.md")
        else:
            print("system intelligence refreshed")
    elif args.command == "health-update":
        update_health()
    elif args.command == "status":
        print(status_text())
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
