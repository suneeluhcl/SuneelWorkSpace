#!/usr/bin/env python3
"""
brain/research/workspace_rag.py

Lightweight local RAG using SQLite FTS5 full-text search.
No external vector libraries required — pure stdlib + sqlite3.

Indexes:
  • Python source files across all 12 organs
  • Markdown rules in skeleton/rules/
  • Memory + decision files in brain/memory/
  • Recent log lines from blood/logs/ (last 200 lines per file)
  • Decisions and ideas from brain/

Search:
  Given a natural-language prompt, returns the top-k most relevant
  file excerpts ranked by FTS5 BM25 relevance.

CLI:
    python3 brain/research/workspace_rag.py index          # rebuild index
    python3 brain/research/workspace_rag.py search "query" # search
    python3 brain/research/workspace_rag.py stats          # show index stats
"""

import json
import os
import re
import sqlite3
import sys
import time
from pathlib import Path
from datetime import datetime, timezone

WORKSPACE = Path(os.path.expanduser("~/SuneelWorkSpace"))
DB_PATH = WORKSPACE / "brain/research/rag_index.db"

# ── file inclusion rules ───────────────────────────────────────────────────────

# Directories to index (relative to WORKSPACE)
_INDEX_ROOTS: list[tuple[str, str]] = [
    # (glob_root, source_type)
    ("brain/memory",          "memory"),
    ("brain/research",        "research"),
    ("skeleton/rules",        "rules"),
    ("dna/identity",          "identity"),
    ("blood/logs",            "logs"),
    ("spine/state",           "state"),
    ("heart/tasks",           "tasks"),
    ("lab/autolab",           "code"),
    ("brain/vault",           "vault"),
    ("tests",                 "tests"),
]

# Index all 12 organ top-level Python files
_ORGAN_ROOTS = [
    "brain", "heart", "eyes", "ears", "nervous",
    "skeleton", "blood", "hands", "mouth", "dna", "lab", "spine",
]

_INCLUDE_EXTENSIONS = {".py", ".md", ".json", ".yaml", ".yml", ".txt"}
_EXCLUDE_DIRS = {
    ".git", ".venv", "__pycache__", "node_modules",
    ".obsidian", "archives", "daily-notes",
}
_MAX_FILE_BYTES = 100_000   # skip files larger than 100 KB
_LOG_TAIL_LINES = 200       # only index the last N lines of log files


# ── database ───────────────────────────────────────────────────────────────────

def _get_db() -> sqlite3.Connection:
    DB_PATH.parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(DB_PATH)
    conn.execute("PRAGMA journal_mode=WAL")
    conn.execute("""
        CREATE TABLE IF NOT EXISTS file_meta (
            path TEXT PRIMARY KEY,
            mtime REAL,
            source_type TEXT
        )
    """)
    conn.execute("""
        CREATE VIRTUAL TABLE IF NOT EXISTS docs
        USING fts5(path UNINDEXED, source_type UNINDEXED, content, tokenize='porter ascii')
    """)
    conn.commit()
    return conn


def _truncate_content(path: Path, source_type: str) -> str:
    """Read and prepare file content for indexing."""
    try:
        if path.stat().st_size > _MAX_FILE_BYTES:
            return ""
        text = path.read_text(encoding="utf-8", errors="ignore")
    except Exception:
        return ""

    if source_type == "logs":
        lines = text.splitlines()[-_LOG_TAIL_LINES:]
        text = "\n".join(lines)

    # Strip YAML frontmatter for markdown files
    if path.suffix == ".md":
        text = re.sub(r"^---\n.*?\n---\n", "", text, flags=re.DOTALL)

    return text.strip()


# ── indexing ───────────────────────────────────────────────────────────────────

def _iter_files() -> list[tuple[Path, str]]:
    """Yield (path, source_type) tuples for all indexable files."""
    seen: set[Path] = set()
    results: list[tuple[Path, str]] = []

    def _scan(root: Path, source_type: str) -> None:
        if not root.exists():
            return
        for p in root.rglob("*"):
            if not p.is_file():
                continue
            if any(part in _EXCLUDE_DIRS for part in p.parts):
                continue
            if p.suffix not in _INCLUDE_EXTENSIONS:
                continue
            if p not in seen:
                seen.add(p)
                results.append((p, source_type))

    for rel_root, source_type in _INDEX_ROOTS:
        _scan(WORKSPACE / rel_root, source_type)

    for organ in _ORGAN_ROOTS:
        organ_root = WORKSPACE / organ
        if organ_root.exists():
            for p in organ_root.glob("*.py"):
                if p not in seen:
                    seen.add(p)
                    results.append((p, "code"))

    return results


def index(force: bool = False) -> dict:
    """
    Build or update the RAG index.
    Incremental by default (skips files with unchanged mtime).
    """
    conn = _get_db()
    files = _iter_files()
    added = updated = skipped = 0

    for fpath, source_type in files:
        try:
            mtime = fpath.stat().st_mtime
        except Exception:
            continue

        rel = str(fpath.relative_to(WORKSPACE))
        row = conn.execute(
            "SELECT mtime FROM file_meta WHERE path = ?", (rel,)
        ).fetchone()

        if not force and row and abs(row[0] - mtime) < 0.5:
            skipped += 1
            continue

        content = _truncate_content(fpath, source_type)
        if not content:
            skipped += 1
            continue

        conn.execute("DELETE FROM docs WHERE path = ?", (rel,))
        conn.execute(
            "INSERT INTO docs(path, source_type, content) VALUES (?, ?, ?)",
            (rel, source_type, content),
        )
        if row:
            conn.execute(
                "UPDATE file_meta SET mtime=?, source_type=? WHERE path=?",
                (mtime, source_type, rel),
            )
            updated += 1
        else:
            conn.execute(
                "INSERT INTO file_meta(path, mtime, source_type) VALUES (?,?,?)",
                (rel, mtime, source_type),
            )
            added += 1

    conn.commit()
    conn.close()
    return {
        "added": added,
        "updated": updated,
        "skipped": skipped,
        "total_files": len(files),
    }


# ── search ─────────────────────────────────────────────────────────────────────

def search(query: str, top_k: int = 5, source_types: list[str] | None = None) -> list[dict]:
    """
    Return the top-k most relevant documents for `query`.
    Each result: {path, source_type, snippet, rank}
    """
    if not query.strip():
        return []

    # Ensure index is warm (do a quick incremental refresh)
    index()

    conn = _get_db()

    # Build FTS5 query — escape special chars, fall back to OR across words
    clean = re.sub(r'[^\w\s]', ' ', query).strip()
    words = clean.split()
    if not words:
        conn.close()
        return []

    fts_query = " OR ".join(words)

    type_filter = ""
    params: list = [fts_query]
    if source_types:
        placeholders = ",".join("?" * len(source_types))
        type_filter = f" AND source_type IN ({placeholders})"
        params.extend(source_types)

    params.append(top_k)

    try:
        rows = conn.execute(
            f"""
            SELECT path, source_type,
                   snippet(docs, 2, '**', '**', '…', 30) AS snip,
                   rank
            FROM docs
            WHERE content MATCH ?{type_filter}
            ORDER BY rank
            LIMIT ?
            """,
            params,
        ).fetchall()
    except Exception:
        conn.close()
        return []

    conn.close()
    return [
        {"path": r[0], "source_type": r[1], "snippet": r[2], "rank": r[3]}
        for r in rows
    ]


def get_context_for_prompt(prompt: str, top_k: int = 5) -> str:
    """
    Return a formatted string of the top-k relevant file excerpts.
    Suitable for prepending to an Ollama system prompt.
    """
    results = search(prompt, top_k=top_k)
    if not results:
        return ""

    lines = ["## Relevant Workspace Context (RAG)"]
    for i, r in enumerate(results, 1):
        lines.append(f"\n### [{i}] `{r['path']}` ({r['source_type']})")
        lines.append(r["snippet"])

    return "\n".join(lines)


def stats() -> dict:
    """Return index statistics."""
    conn = _get_db()
    total = conn.execute("SELECT COUNT(*) FROM file_meta").fetchone()[0]
    by_type = conn.execute(
        "SELECT source_type, COUNT(*) FROM file_meta GROUP BY source_type ORDER BY COUNT(*) DESC"
    ).fetchall()
    conn.close()
    return {
        "total_indexed": total,
        "by_type": {r[0]: r[1] for r in by_type},
        "db_path": str(DB_PATH),
    }


# ── CLI ────────────────────────────────────────────────────────────────────────

def main() -> None:
    import argparse
    parser = argparse.ArgumentParser(description="Workspace RAG — FTS5 semantic search")
    sub = parser.add_subparsers(dest="cmd")

    p_index = sub.add_parser("index", help="Build or update the search index")
    p_index.add_argument("--force", action="store_true", help="Reindex all files")

    p_search = sub.add_parser("search", help="Search the index")
    p_search.add_argument("query", help="Search query")
    p_search.add_argument("-k", type=int, default=5)
    p_search.add_argument("--type", dest="source_type", default=None)

    sub.add_parser("stats", help="Show index statistics")

    args = parser.parse_args()

    if args.cmd == "index":
        t = time.monotonic()
        r = index(force=args.force)
        elapsed = round(time.monotonic() - t, 2)
        print(f"[rag] indexed in {elapsed}s — added={r['added']} updated={r['updated']} skipped={r['skipped']}")

    elif args.cmd == "search":
        types = [args.source_type] if args.source_type else None
        results = search(args.query, top_k=args.k, source_types=types)
        if not results:
            print("[rag] no results")
        for i, r in enumerate(results, 1):
            print(f"\n[{i}] {r['path']} ({r['source_type']})")
            print(f"     {r['snippet']}")

    elif args.cmd == "stats":
        s = stats()
        print(f"[rag] {s['total_indexed']} files indexed — {s['db_path']}")
        for t, n in s["by_type"].items():
            print(f"  {t:20s} {n}")

    else:
        parser.print_help()


if __name__ == "__main__":
    main()
