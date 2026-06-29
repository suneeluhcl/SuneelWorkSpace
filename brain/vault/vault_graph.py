#!/usr/bin/env python3
"""
brain/vault/vault_graph.py

Two-pass Obsidian graph engine for SuneelWorkSpace.

Pass 1 — autolink_notes():
    Scan all .md files in brain/vault/ and insert [[organ]] backlinks wherever
    organ names are mentioned in plain text (skips frontmatter, code blocks,
    already-linked text, and headings-as-tags).

Pass 2 — generate_canvas():
    Regenerate brain/vault/Workspace Map.canvas with 12 organ nodes laid out in
    a 4×3 grid.  Node color reflects live health status from
    spine/state/WORKSPACE_HEALTH.json:
      green ("4") — no issues for this organ
      yellow ("3") — warning-severity issues
      red ("1")   — error/critical issues

    Edges are drawn from each organ's nerve.json `listens_from` entries,
    reflecting the real event-subscription topology.

Called automatically at the end of brain/vault/vault_sync.py and via CLI:
    python3 brain/vault/vault_graph.py [--autolink-only | --canvas-only]
"""

import json
import os
import re
import sys
from datetime import datetime, timezone
from pathlib import Path

WORKSPACE = Path(os.path.expanduser("~/SuneelWorkSpace"))
VAULT = WORKSPACE / "brain/vault"
CANVAS_PATH = VAULT / "Workspace Map.canvas"
HEALTH_PATH = WORKSPACE / "spine/state/WORKSPACE_HEALTH.json"

ORGANS = [
    "brain", "heart", "eyes", "ears", "nervous",
    "skeleton", "blood", "hands", "mouth", "dna", "lab", "spine",
]

# Organ display labels (with subtitle)
_ORGAN_LABELS = {
    "brain":    "🧠 brain\nmemory · search · RAG",
    "heart":    "❤️ heart\ntasks · routing · goals",
    "eyes":     "👁️ eyes\ndashboard · port 7777",
    "ears":     "👂 ears\nRSS · GitHub monitors",
    "nervous":  "⚡ nervous\ngateway · nerve propagator",
    "skeleton": "🦴 skeleton\nrules · safety boundaries",
    "blood":    "🩸 blood\nSQLite · logs · telemetry",
    "hands":    "🙌 hands\nscripts · bin · CI runner",
    "mouth":    "💬 mouth\nmail · iMessage dispatcher",
    "dna":      "🧬 dna\nidentity · voice · adapt",
    "lab":      "🔬 lab\nautolab · Ollama engines",
    "spine":    "🦴 spine\nhealth · state · index",
}

# 4-column × 3-row grid layout (x, y) — 240px col spacing, 220px row spacing
_ORGAN_POSITIONS = {
    "brain":    (-360, -220),
    "heart":    (-120, -220),
    "eyes":     (120,  -220),
    "ears":     (360,  -220),
    "nervous":  (-360, 0),
    "skeleton": (-120, 0),
    "blood":    (120,  0),
    "hands":    (360,  0),
    "mouth":    (-360, 220),
    "dna":      (-120, 220),
    "lab":      (120,  220),
    "spine":    (360,  220),
}

NODE_W = 180
NODE_H = 80

# ── health helpers ─────────────────────────────────────────────────────────────

def _load_health() -> dict:
    try:
        return json.loads(HEALTH_PATH.read_text())
    except Exception:
        return {}


def _organ_color(organ: str, health: dict) -> str:
    """Return Obsidian canvas color string: '1'=red, '3'=yellow, '4'=green."""
    issues = health.get("issues", [])
    severities: set[str] = set()
    for issue in issues:
        path = issue.get("path", "") + issue.get("message", "") + issue.get("code", "")
        if organ in path.lower():
            severities.add(issue.get("severity", "info"))
    if "error" in severities or "critical" in severities:
        return "1"
    if "warning" in severities:
        return "3"
    return "4"


# ── Pass 1: autolinker ─────────────────────────────────────────────────────────

def _split_blocks(text: str) -> list[tuple[str, bool]]:
    """
    Split markdown text into (block, is_protected) pairs.
    Protected blocks: YAML frontmatter, fenced code blocks.
    """
    blocks: list[tuple[str, bool]] = []
    lines = text.splitlines(keepends=True)
    in_frontmatter = False
    in_code = False
    frontmatter_opened = False
    buf: list[str] = []
    protected = False

    def _flush():
        if buf:
            blocks.append(("".join(buf), protected))
            buf.clear()

    for i, line in enumerate(lines):
        stripped = line.rstrip()
        if i == 0 and stripped == "---":
            _flush()
            in_frontmatter = True
            frontmatter_opened = True
            protected = True
            buf.append(line)
            continue
        if in_frontmatter and stripped == "---" and frontmatter_opened:
            buf.append(line)
            in_frontmatter = False
            _flush()
            protected = False
            continue
        if not in_frontmatter and stripped.startswith("```"):
            if not in_code:
                _flush()
                in_code = True
                protected = True
                buf.append(line)
            else:
                buf.append(line)
                in_code = False
                _flush()
                protected = False
            continue
        buf.append(line)

    _flush()
    return blocks


def _insert_links(text: str, organ_names: list[str]) -> str:
    """
    Replace first occurrence of each unlinked organ name per file with [[organ]].
    Skips already-linked text (`[[...]]`) and inline code (`code`).
    """
    linked: set[str] = set()

    # Find already-linked organs
    for m in re.finditer(r"\[\[([^\]]+)\]\]", text):
        target = m.group(1).split("|")[0].split("#")[0].lower().strip()
        linked.add(target)

    def _replacer(organ: str):
        def replace(m: re.Match) -> str:
            if organ in linked:
                return m.group(0)
            # Don't link inside inline code
            start = m.start()
            # naive check: count backticks before this position on the same line
            line_start = text.rfind("\n", 0, start) + 1
            line_before = text[line_start:start]
            if line_before.count("`") % 2 == 1:
                return m.group(0)
            linked.add(organ)
            return f"[[{organ}]]"
        return replace

    for organ in organ_names:
        # Word boundary, not preceded by [[ or |, not followed by ]]
        pattern = rf"(?<!\[\[)(?<!\|)\b({re.escape(organ)})\b(?!\]\])"
        text = re.sub(pattern, _replacer(organ), text, flags=re.IGNORECASE, count=1)

    return text


def autolink_notes(vault_root: Path | None = None) -> dict:
    """Insert [[organ]] backlinks in all unprotected .md files under brain/vault/."""
    root = vault_root or VAULT
    modified = 0
    skipped = 0

    for md_path in root.rglob("*.md"):
        try:
            original = md_path.read_text(encoding="utf-8")
        except Exception:
            skipped += 1
            continue

        blocks = _split_blocks(original)
        new_blocks: list[str] = []
        changed = False

        for block_text, is_protected in blocks:
            if is_protected:
                new_blocks.append(block_text)
            else:
                linked = _insert_links(block_text, ORGANS)
                if linked != block_text:
                    changed = True
                new_blocks.append(linked)

        if changed:
            md_path.write_text("".join(new_blocks), encoding="utf-8")
            modified += 1

    return {"modified": modified, "skipped": skipped}


# ── Pass 2: canvas generator ───────────────────────────────────────────────────

def _load_nerve(organ: str) -> dict:
    """Read organ's nerve.json. Returns {} on any error."""
    p = WORKSPACE / organ / "nerve.json"
    try:
        return json.loads(p.read_text())
    except Exception:
        return {}


def generate_canvas(health: dict | None = None) -> dict:
    """
    Regenerate brain/vault/Workspace Map.canvas with organ nodes colored by
    live health status and edges from nerve.json listens_from entries.
    """
    if health is None:
        health = _load_health()

    nodes: list[dict] = []
    edges: list[dict] = []
    organ_ids: dict[str, str] = {organ: f"organ_{organ}" for organ in ORGANS}

    ts_label = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M UTC")

    # Title node
    nodes.append({
        "id": "title",
        "type": "text",
        "text": f"# SuneelWorkSpace Neural Map\nLast updated: {ts_label}",
        "x": -60,
        "y": -380,
        "width": 340,
        "height": 60,
        "color": "6",
    })

    # Organ nodes
    for organ in ORGANS:
        x, y = _ORGAN_POSITIONS[organ]
        color = _organ_color(organ, health)
        nodes.append({
            "id": organ_ids[organ],
            "type": "text",
            "text": _ORGAN_LABELS[organ],
            "x": x - NODE_W // 2,
            "y": y - NODE_H // 2,
            "width": NODE_W,
            "height": NODE_H,
            "color": color,
        })

    # Edges from nerve.json listens_from
    edge_set: set[tuple[str, str]] = set()
    for organ in ORGANS:
        nerve = _load_nerve(organ)
        sources = nerve.get("listens_from", [])
        if isinstance(sources, str):
            sources = [sources]
        for src in sources:
            src = src.lower()
            if src in organ_ids and src != organ:
                key = (src, organ)
                if key not in edge_set:
                    edge_set.add(key)
                    edges.append({
                        "id": f"edge_{src}_{organ}",
                        "fromNode": organ_ids[src],
                        "toNode": organ_ids[organ],
                        "fromSide": "right",
                        "toSide": "left",
                    })

    canvas = {"nodes": nodes, "edges": edges}
    CANVAS_PATH.parent.mkdir(parents=True, exist_ok=True)
    CANVAS_PATH.write_text(json.dumps(canvas, indent=2, ensure_ascii=False))
    return {
        "nodes": len(nodes),
        "edges": len(edges),
        "canvas_path": str(CANVAS_PATH),
    }


# ── entry point ────────────────────────────────────────────────────────────────

def run() -> dict:
    """Run both passes. Called by vault_sync.py and directly."""
    health = _load_health()
    link_result = autolink_notes()
    canvas_result = generate_canvas(health)
    return {
        "autolink": link_result,
        "canvas": canvas_result,
        "ts": datetime.now(timezone.utc).isoformat(),
    }


def main() -> None:
    import argparse
    parser = argparse.ArgumentParser(description="Obsidian autolinker and canvas generator")
    parser.add_argument("--autolink-only", action="store_true")
    parser.add_argument("--canvas-only", action="store_true")
    args = parser.parse_args()

    if args.autolink_only:
        r = autolink_notes()
        print(f"[vault-graph] autolink: {r['modified']} notes updated")
    elif args.canvas_only:
        r = generate_canvas()
        print(f"[vault-graph] canvas: {r['nodes']} nodes, {r['edges']} edges → {r['canvas_path']}")
    else:
        r = run()
        print(f"[vault-graph] autolink: {r['autolink']['modified']} notes updated | "
              f"canvas: {r['canvas']['nodes']} nodes, {r['canvas']['edges']} edges")


if __name__ == "__main__":
    main()
