#!/usr/bin/env python3
"""Plain-file research engine for idea capture, analysis, and decisions."""

from __future__ import annotations

import argparse
import json
import os
import re
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


ROOT = Path(os.environ.get("SUNEEL_WORKSPACE", Path.home() / "SuneelWorkSpace")).resolve()
ENGINE = ROOT / "research-engine"
IDEAS = ENGINE / "ideas"
PLANS = ENGINE / "plans"
ANALYSES = ENGINE / "analyses"
DECISIONS = ENGINE / "decisions"
SHARED_DECISIONS = ROOT / "brain/memory/DECISIONS.md"
SHARED_MEMORY = ROOT / "brain/memory/MEMORY.md"
NOW = datetime.now(timezone.utc).astimezone()


def slugify(text: str) -> str:
    slug = re.sub(r"[^a-zA-Z0-9]+", "-", text.lower()).strip("-")
    return slug[:60] or "idea"


def read_json(path: Path, default: Any) -> Any:
    try:
        return json.loads(path.read_text())
    except Exception:
        return default


def write_json(path: Path, data: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(data, indent=2, sort_keys=True) + "\n")


def bootstrap() -> None:
    for path in [IDEAS, PLANS, ANALYSES, DECISIONS]:
        path.mkdir(parents=True, exist_ok=True)
    index = IDEAS / "index.json"
    if not index.exists():
        write_json(index, {"generated_at": NOW.isoformat(), "ideas": []})
    readme = ENGINE / "README.md"
    if not readme.exists():
        readme.write_text(
            "\n".join(
                [
                    "# Research Engine",
                    "",
                    "A local-first pipeline for turning ideas into plans, comparisons, and decisions.",
                    "",
                    "## Commands",
                    "",
                    "- `idea-capture`: store a raw idea as a Markdown file and index entry.",
                    "- `idea-research`: create a research plan for an idea.",
                    "- `idea-analyze`: create a solution comparison and risk review.",
                    "- `idea-decide`: record a decision and promote it into shared memory.",
                    "- `idea-bootstrap`: repair/create the directory structure.",
                    "- `idea-start` and `idea-run`: user-facing wrappers in `bin/`.",
                    "",
                    "## Safety",
                    "",
                    "This engine stores plain files inside `~/SuneelWorkSpace/research-engine` and does not install tools, spend money, or scan private folders by itself.",
                ]
            )
            + "\n"
        )
    dec_readme = DECISIONS / "README.md"
    if not dec_readme.exists():
        dec_readme.write_text(
            "# Research Decisions\n\nDecision records created by `idea-decide` and draft decisions created by `idea-run`.\n"
        )


def update_index(entry: dict[str, Any]) -> None:
    bootstrap()
    index_path = IDEAS / "index.json"
    data = read_json(index_path, {"ideas": []})
    ideas = data.setdefault("ideas", [])
    ideas = [item for item in ideas if item.get("id") != entry["id"]]
    ideas.append(entry)
    data["ideas"] = sorted(ideas, key=lambda item: item.get("created_at", ""))
    data["generated_at"] = NOW.isoformat()
    write_json(index_path, data)


def find_idea(identifier: str) -> dict[str, Any]:
    data = read_json(IDEAS / "index.json", {"ideas": []})
    matches = [
        item
        for item in data.get("ideas", [])
        if item.get("id") == identifier or identifier.lower() in item.get("title", "").lower()
    ]
    if not matches:
        raise SystemExit(f"No idea found for: {identifier}")
    return matches[-1]


def capture(title: str, body: str = "") -> dict[str, Any]:
    bootstrap()
    idea_id = f"{NOW.strftime('%Y%m%d-%H%M%S')}-{slugify(title)}"
    path = IDEAS / f"{idea_id}.md"
    content = [
        f"# {title}",
        "",
        f"- ID: `{idea_id}`",
        f"- Captured: {NOW.isoformat()}",
        "- Status: captured",
        "",
        "## Raw Idea",
        "",
        body.strip() or title,
        "",
        "## Next",
        "",
        "- Run `idea-research {id}`.",
        "- Run `idea-analyze {id}`.",
        "- Run `idea-decide {id} \"decision\"` when a choice is ready.",
    ]
    path.write_text("\n".join(content).replace("{id}", idea_id) + "\n")
    entry = {
        "id": idea_id,
        "title": title,
        "created_at": NOW.isoformat(),
        "status": "captured",
        "idea_path": str(path.relative_to(ROOT)),
    }
    update_index(entry)
    print(path)
    return entry


def research(identifier: str) -> Path:
    bootstrap()
    idea = find_idea(identifier)
    path = PLANS / f"{idea['id']}-research-plan.md"
    lines = [
        f"# Research Plan: {idea['title']}",
        "",
        f"- Idea ID: `{idea['id']}`",
        f"- Created: {NOW.isoformat()}",
        "- Status: plan",
        "",
        "## Questions",
        "",
        "- What problem is this trying to solve?",
        "- What current workspace capability already covers part of it?",
        "- What local-first implementation would be smallest and reversible?",
        "- What external tools or plugins are candidates, and what approvals would they need?",
        "- What risks exist around privacy, money actions, destructive file operations, or hidden state?",
        "",
        "## Evidence To Gather",
        "",
        "- Existing files and commands under `~/SuneelWorkSpace`.",
        "- Relevant MCP resources and shared memory entries.",
        "- Local CLI/app capabilities from `spine/tools/tool_inventory.json`.",
        "- Fresh web or vendor documentation only when explicitly requested or required for current facts.",
        "",
        "## Output",
        "",
        f"- Run `idea-analyze {idea['id']}` after evidence is gathered.",
    ]
    path.write_text("\n".join(lines) + "\n")
    print(path)
    return path


def analyze(identifier: str) -> Path:
    bootstrap()
    idea = find_idea(identifier)
    path = ANALYSES / f"{idea['id']}-analysis.md"
    lines = [
        f"# Solution Analysis: {idea['title']}",
        "",
        f"- Idea ID: `{idea['id']}`",
        f"- Created: {NOW.isoformat()}",
        "- Status: draft-analysis",
        "",
        "## Options",
        "",
        "| Option | Strength | Tradeoff | Safety Notes |",
        "|---|---|---|---|",
        "| Use existing workspace scripts | Fast, inspectable, reversible | May need small wrappers | Preferred first step |",
        "| Add a new local subsystem | Durable capability | More maintenance surface | Keep plain files and small scripts |",
        "| Integrate an external tool/plugin | Can unlock mature capability | Requires trust, install, auth, or cost review | Propose only until approved |",
        "",
        "## Recommended Default",
        "",
        "Prefer existing workspace commands and plain-file state. Add external integrations only after explicit approval and a rollback plan.",
        "",
        "## Decision Draft",
        "",
        f"Run `idea-decide {idea['id']} \"<decision>\"` when ready.",
    ]
    path.write_text("\n".join(lines) + "\n")
    print(path)
    return path


def decide(identifier: str, decision: str, promote: bool = True) -> Path:
    bootstrap()
    idea = find_idea(identifier)
    path = DECISIONS / f"{idea['id']}-decision.md"
    lines = [
        f"# Decision: {idea['title']}",
        "",
        f"- Idea ID: `{idea['id']}`",
        f"- Decided: {NOW.isoformat()}",
        "- Status: accepted",
        "",
        "## Decision",
        "",
        decision,
        "",
        "## Rationale",
        "",
        "Local-first, inspectable, reversible changes are preferred unless the user explicitly approves broader integration.",
        "",
        "## Follow-up",
        "",
        "- Update implementation tasks if work remains.",
        "- Update shared memory if this creates durable knowledge.",
    ]
    path.write_text("\n".join(lines) + "\n")
    if promote:
        snippet = f"\n## {NOW.strftime('%Y-%m-%d')} - Research decision: {idea['title']}\n\n- Decision: {decision}\n- Source: `{path.relative_to(ROOT)}`\n"
        if SHARED_DECISIONS.exists():
            SHARED_DECISIONS.write_text(SHARED_DECISIONS.read_text().rstrip() + snippet + "\n")
    print(path)
    return path


def run(title: str, body: str = "") -> None:
    entry = capture(title, body)
    research(entry["id"])
    analyze(entry["id"])
    draft = DECISIONS / f"{entry['id']}-decision-draft.md"
    draft.write_text(
        "\n".join(
            [
                f"# Decision Draft: {entry['title']}",
                "",
                f"- Idea ID: `{entry['id']}`",
                f"- Created: {NOW.isoformat()}",
                "- Status: proposed",
                "",
                "## Proposed Direction",
                "",
                "Use the smallest local-first implementation first. Defer external installs, account changes, and private data indexing until explicitly approved.",
                "",
                "## Next Command",
                "",
                f"`idea-decide {entry['id']} \"accepted decision text\"`",
            ]
        )
        + "\n"
    )
    print(draft)


def main() -> int:
    parser = argparse.ArgumentParser(description="Local research engine")
    sub = parser.add_subparsers(dest="command", required=True)
    sub.add_parser("bootstrap")

    capture_p = sub.add_parser("capture")
    capture_p.add_argument("title")
    capture_p.add_argument("body", nargs="*", default=[])

    research_p = sub.add_parser("research")
    research_p.add_argument("identifier")

    analyze_p = sub.add_parser("analyze")
    analyze_p.add_argument("identifier")

    decide_p = sub.add_parser("decide")
    decide_p.add_argument("identifier")
    decide_p.add_argument("decision", nargs="+")

    run_p = sub.add_parser("run")
    run_p.add_argument("title")
    run_p.add_argument("body", nargs="*", default=[])

    args = parser.parse_args()
    if args.command == "bootstrap":
        bootstrap()
        print(ENGINE)
    elif args.command == "capture":
        capture(args.title, " ".join(args.body))
    elif args.command == "research":
        research(args.identifier)
    elif args.command == "analyze":
        analyze(args.identifier)
    elif args.command == "decide":
        decide(args.identifier, " ".join(args.decision))
    elif args.command == "run":
        run(args.title, " ".join(args.body))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
