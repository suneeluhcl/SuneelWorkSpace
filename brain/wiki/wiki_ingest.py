#!/usr/bin/env python3
"""
brain/wiki/wiki_ingest.py

LLM-Wiki ingest pipeline for SuneelWorkSpace.

Reads a source file (markdown, text, code) from brain/vault/sources/ or any
path, uses the local reasoning sidecar (port 11435) or Ollama directly to
extract named entities + facts, and writes/updates note files in
brain/vault/wiki/.

Each wiki note:
  brain/vault/wiki/{EntityName}.md
  ─ YAML frontmatter (entity, type, created, updated, source)
  ─ ## Facts  (deduplicated bullet list)
  ─ ## Backlinks  ([[source-slug]] list)

Index card appended/updated in:  brain/vault/wiki/index.md
Ingest log line appended to:      brain/vault/wiki/log.md

CLI:
    python3 brain/wiki/wiki_ingest.py <path-or-glob>
    python3 brain/wiki/wiki_ingest.py brain/vault/sources/intro.md
    python3 brain/wiki/wiki_ingest.py --reindex    # rebuild index.md from existing notes
"""

import json
import os
import re
import sys
import urllib.request
from datetime import datetime, timezone
from pathlib import Path

WORKSPACE = Path(os.path.expanduser("~/SuneelWorkSpace"))
sys.path.insert(0, str(WORKSPACE))
os.chdir(WORKSPACE)

WIKI_DIR    = WORKSPACE / "brain/vault/wiki"
LOG_PATH    = WIKI_DIR / "log.md"
INDEX_PATH  = WIKI_DIR / "index.md"

SIDECAR_URL  = "http://127.0.0.1:11435"
OLLAMA_BASE  = "http://127.0.0.1:11434"
OLLAMA_MODEL = "suneelworkspace"

_VENV_PY = str(WORKSPACE / ".venv/bin/python3")

ENTITY_SYSTEM = (
    "You are an entity extractor. Given a document, identify all important named "
    "entities (concepts, tools, systems, metrics, people, decisions). For each, list "
    "2-5 concise factual statements drawn ONLY from the text. "
    "Respond ONLY with a JSON array — no prose:\n"
    '[{"entity":"Name","type":"concept|tool|system|person|metric|decision",'
    '"facts":["fact one","fact two"]}]'
)

# ── LLM helpers ───────────────────────────────────────────────────────────────

def _call_sidecar(prompt: str) -> str:
    payload = json.dumps({"prompt": prompt, "task_type": "learning"}).encode()
    req = urllib.request.Request(
        f"{SIDECAR_URL}/query", data=payload,
        headers={"Content-Type": "application/json"}, method="POST",
    )
    try:
        with urllib.request.urlopen(req, timeout=60) as r:
            return json.loads(r.read()).get("response", "").strip()
    except Exception:
        return ""


def _call_ollama(prompt: str) -> str:
    payload = json.dumps({
        "model": OLLAMA_MODEL,
        "system": ENTITY_SYSTEM,
        "prompt": prompt,
        "stream": False,
        "options": {"temperature": 0.1, "num_ctx": 6144},
    }).encode()
    req = urllib.request.Request(
        f"{OLLAMA_BASE}/api/generate", data=payload,
        headers={"Content-Type": "application/json"}, method="POST",
    )
    try:
        with urllib.request.urlopen(req, timeout=180) as r:
            return json.loads(r.read()).get("response", "").strip()
    except Exception as e:
        return f"[ollama error: {e}]"


def _sidecar_up() -> bool:
    try:
        urllib.request.urlopen(f"{SIDECAR_URL}/health", timeout=2)
        return True
    except Exception:
        return False


def _extract_entities(text: str, source_name: str) -> list[dict]:
    """Ask sidecar/Ollama to extract entities from text. Returns list of dicts."""
    truncated = text[:3000]
    prompt = (
        f"Document: {source_name}\n\n"
        f"{truncated}\n\n"
        "Extract entities and facts as JSON array."
    )
    response = _call_ollama(prompt)
    if not response or response.startswith("[ollama error"):
        print(f"      [DEBUG] ollama call returned: {response}", file=sys.stderr)
        return []
    try:
        match = re.search(r"\[.*?\]", response, re.DOTALL)
        if match:
            return json.loads(match.group())
        else:
            print(f"      [DEBUG] No JSON bracket match in response: {response}", file=sys.stderr)
    except Exception as e:
        print(f"      [DEBUG] JSON parse error: {e}. Raw response: {response}", file=sys.stderr)
    return []


# ── note helpers ───────────────────────────────────────────────────────────────

def _note_slug(name: str) -> str:
    """Convert entity name to a safe filename slug."""
    slug = re.sub(r"[^\w\s-]", "", name.strip()).strip()
    return re.sub(r"\s+", "-", slug)


def _read_note(path: Path) -> dict:
    """Parse an existing wiki note. Returns {facts, backlinks, type, created}."""
    if not path.exists():
        return {"facts": [], "backlinks": [], "type": "concept", "created": None}
    text = path.read_text(encoding="utf-8", errors="ignore")
    facts: list[str] = []
    backlinks: list[str] = []
    etype = "concept"
    created = None
    for line in text.splitlines():
        stripped = line.strip()
        if stripped.startswith("- ") and "## Facts" in text:
            # Collect facts after the Facts header
            pass  # parsed below
        if m := re.match(r"^type:\s*(.+)", stripped):
            etype = m.group(1).strip()
        if m := re.match(r"^created:\s*(.+)", stripped):
            created = m.group(1).strip()

    # Parse facts section
    in_facts = in_links = False
    for line in text.splitlines():
        if line.startswith("## Facts"):
            in_facts = True; in_links = False; continue
        if line.startswith("## Backlinks"):
            in_links = True; in_facts = False; continue
        if line.startswith("## ") and in_facts:
            in_facts = False
        if line.startswith("## ") and in_links:
            in_links = False
        if in_facts and line.strip().startswith("- "):
            facts.append(line.strip()[2:])
        if in_links and line.strip().startswith("- [["):
            m = re.search(r"\[\[(.+?)\]\]", line)
            if m:
                backlinks.append(m.group(1))
    return {"facts": facts, "backlinks": backlinks, "type": etype, "created": created}


def _write_note(entity: str, etype: str, facts: list[str],
                backlinks: list[str], source: str) -> Path:
    """Write or update brain/vault/wiki/{slug}.md. Deduplicates facts."""
    slug = _note_slug(entity)
    path = WIKI_DIR / f"{slug}.md"
    existing = _read_note(path)

    # Merge facts (deduplicate by normalised lowercase)
    seen = {f.lower().strip() for f in existing["facts"]}
    merged_facts = list(existing["facts"])
    for f in facts:
        if f.lower().strip() not in seen:
            merged_facts.append(f)
            seen.add(f.lower().strip())

    # Merge backlinks
    seen_links = set(existing["backlinks"])
    merged_links = list(existing["backlinks"])
    source_slug = _note_slug(Path(source).stem)
    if source_slug not in seen_links:
        merged_links.append(source_slug)

    now = datetime.now(timezone.utc).isoformat()
    created = existing.get("created") or now
    final_type = existing.get("type") or etype

    lines = [
        "---",
        f"entity: {entity}",
        f"type: {final_type}",
        f"created: {created}",
        f"updated: {now}",
        f"source: {source}",
        "---",
        "",
        f"# {entity}",
        "",
        "## Facts",
        "",
    ]
    for fact in merged_facts[:20]:      # cap at 20 facts per note
        lines.append(f"- {fact}")
    lines += ["", "## Backlinks", ""]
    for link in merged_links:
        lines.append(f"- [[{link}]]")
    lines.append("")

    path.write_text("\n".join(lines), encoding="utf-8")
    return path


# ── index helpers ──────────────────────────────────────────────────────────────

def _rebuild_index() -> None:
    """Regenerate index.md from all wiki notes."""
    notes = sorted(WIKI_DIR.glob("*.md"))
    rows: list[str] = []
    for note_path in notes:
        if note_path.name in ("index.md", "log.md", "Wiki Health.md"):
            continue
        text = note_path.read_text(encoding="utf-8", errors="ignore")
        etype = "?"
        entity = note_path.stem.replace("-", " ")
        updated = "?"
        for line in text.splitlines():
            if m := re.match(r"^type:\s*(.+)", line.strip()):
                etype = m.group(1).strip()
            if m := re.match(r"^entity:\s*(.+)", line.strip()):
                entity = m.group(1).strip()
            if m := re.match(r"^updated:\s*(.+)", line.strip()):
                updated = m.group(1)[:10]
        rows.append(f"| [[{note_path.stem}]] | {etype} | {updated} |")

    lines = [
        "# Wiki Index",
        "",
        f"> Auto-generated by `wiki_ingest.py` — {len(rows)} entries",
        "",
        "| Note | Type | Updated |",
        "|------|------|---------|",
    ] + rows + [""]
    INDEX_PATH.write_text("\n".join(lines), encoding="utf-8")


def _append_index_row(slug: str, etype: str) -> None:
    """Append or update a single row in index.md."""
    if not INDEX_PATH.exists():
        _rebuild_index()
        return
    text = INDEX_PATH.read_text(encoding="utf-8", errors="ignore")
    tag = f"[[{slug}]]"
    today = datetime.now(timezone.utc).date().isoformat()
    row = f"| {tag} | {etype} | {today} |"
    if tag in text:
        text = re.sub(rf"\|.*{re.escape(tag)}.*\|", row, text)
    else:
        text = text.rstrip() + f"\n{row}\n"
    INDEX_PATH.write_text(text, encoding="utf-8")


def _log_ingest(source: str, created: int, updated: int) -> None:
    WIKI_DIR.mkdir(parents=True, exist_ok=True)
    ts = datetime.now(timezone.utc).isoformat()
    line = f"- `{ts}` ingested `{source}` — {created} created, {updated} updated\n"
    with LOG_PATH.open("a", encoding="utf-8") as f:
        if LOG_PATH.stat().st_size == 0:
            f.write("# Wiki Ingest Log\n\n")
        f.write(line)


# ── main ingest ────────────────────────────────────────────────────────────────

def ingest(source_path: Path) -> dict:
    """Ingest a single source file into the wiki."""
    if not source_path.exists():
        return {"status": "not_found", "source": str(source_path)}

    WIKI_DIR.mkdir(parents=True, exist_ok=True)
    text = source_path.read_text(encoding="utf-8", errors="ignore")
    print(f"  [wiki-ingest] Extracting entities from {source_path.name} ({len(text)} chars)…")

    entities = _extract_entities(text, source_path.name)
    if not entities:
        print("  [wiki-ingest] No entities extracted (model unavailable or empty response)")
        _log_ingest(str(source_path), 0, 0)
        return {"status": "no_entities", "source": str(source_path)}

    print(f"  [wiki-ingest] Extracted {len(entities)} entities")
    created_count = updated_count = 0

    for item in entities:
        entity = str(item.get("entity", "")).strip()
        etype  = str(item.get("type", "concept")).strip()
        facts  = [str(f) for f in item.get("facts", []) if str(f).strip()]
        if not entity or len(entity) < 2:
            continue
        slug = _note_slug(entity)
        note_path = WIKI_DIR / f"{slug}.md"
        is_new = not note_path.exists()
        _write_note(entity, etype, facts, [], str(source_path))
        _append_index_row(slug, etype)
        if is_new:
            created_count += 1
        else:
            updated_count += 1

    _log_ingest(str(source_path), created_count, updated_count)
    print(f"  [wiki-ingest] Done — {created_count} created, {updated_count} updated")
    return {
        "status": "ok",
        "source": str(source_path),
        "entities": len(entities),
        "created": created_count,
        "updated": updated_count,
    }


def ingest_dir(source_dir: Path) -> list[dict]:
    """Ingest all .md and .txt files in a directory."""
    results = []
    for p in sorted(source_dir.glob("*")):
        if p.suffix in (".md", ".txt", ".py") and p.is_file():
            results.append(ingest(p))
    return results


# ── CLI ────────────────────────────────────────────────────────────────────────

def main() -> None:
    import argparse
    parser = argparse.ArgumentParser(description="LLM-Wiki ingest pipeline")
    parser.add_argument("path", nargs="?", default=None,
                        help="Source file or directory to ingest (default: brain/vault/sources/)")
    parser.add_argument("--reindex", action="store_true",
                        help="Rebuild index.md from existing wiki notes")
    args = parser.parse_args()

    if args.reindex:
        _rebuild_index()
        count = len(list(WIKI_DIR.glob("*.md"))) - 3
        print(f"[wiki-ingest] Rebuilt index.md — {count} notes indexed")
        return

    target = Path(args.path) if args.path else WORKSPACE / "brain/vault/sources"
    if not target.exists():
        print(f"[wiki-ingest] Path not found: {target}")
        sys.exit(1)

    if target.is_dir():
        results = ingest_dir(target)
        ok = sum(1 for r in results if r.get("status") == "ok")
        print(f"\n[wiki-ingest] {ok}/{len(results)} files ingested successfully")
    else:
        result = ingest(target)
        sys.exit(0 if result.get("status") == "ok" else 1)


if __name__ == "__main__":
    main()
