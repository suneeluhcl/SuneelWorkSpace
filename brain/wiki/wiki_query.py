#!/usr/bin/env python3
"""
brain/wiki/wiki_query.py

Compounding query engine for brain/vault/wiki/.

Given a natural-language query:
  1. Scans brain/vault/wiki/index.md to select the top-5 most relevant notes
     (keyword overlap + workspace RAG FTS5 as a secondary scorer).
  2. Reads the selected note files in full.
  3. Feeds the combined content to the local suneelworkspace Ollama model to
     generate a synthesised markdown answer.
  4. If the query is comparative ("compare X and Y", "X vs Y", "difference
     between X and Y") — saves the synthesis as:
       brain/vault/wiki/synthesis-<timestamp>.md
     and appends a link row to brain/vault/wiki/index.md.

CLI:
    python3 brain/wiki/wiki_query.py "How does the nervous system work?"
    python3 brain/wiki/wiki_query.py "compare vault_sync and vault_graph"
    python3 brain/wiki/wiki_query.py --top-k 3 "what is workspace RAG?"
"""

import json
import os
import re
import sys
import urllib.request
from datetime import datetime, timezone
from pathlib import Path

WORKSPACE   = Path(os.path.expanduser("~/SuneelWorkSpace"))
sys.path.insert(0, str(WORKSPACE))
os.chdir(WORKSPACE)

WIKI_DIR    = WORKSPACE / "brain/vault/wiki"
INDEX_PATH  = WIKI_DIR / "index.md"

OLLAMA_BASE  = "http://localhost:11434"
OLLAMA_MODEL = "suneelworkspace"
SIDECAR_URL  = "http://127.0.0.1:11435"

_COMPARATIVE_RE = re.compile(
    r"\b(compare|versus|vs\.?|difference\s+between|contrast|similarities|trade.?off)\b",
    re.IGNORECASE,
)


# ── scoring helpers ───────────────────────────────────────────────────────────

def _tokenise(text: str) -> set[str]:
    return {w.lower() for w in re.findall(r"[a-zA-Z]{3,}", text)}


def _keyword_score(query_tokens: set[str], note_text: str) -> float:
    """Jaccard-like overlap of query tokens against note content."""
    note_tokens = _tokenise(note_text)
    if not note_tokens:
        return 0.0
    hits = query_tokens & note_tokens
    return len(hits) / (len(query_tokens) + 1)


def _rag_scores(query: str, note_slugs: list[str]) -> dict[str, float]:
    """
    Use workspace_rag FTS5 to rank notes by semantic relevance.
    Returns {slug: rank_score} (lower rank = better in FTS5 BM25).
    """
    scores: dict[str, float] = {}
    try:
        import importlib.util
        spec = importlib.util.spec_from_file_location(
            "workspace_rag", WORKSPACE / "brain/research/workspace_rag.py"
        )
        mod = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(mod)
        results = mod.search(query, top_k=10, source_types=["vault"])
        for i, r in enumerate(results):
            path = r.get("path", "")
            # Match path basename to note slug
            slug = Path(path).stem.lower()
            if slug in note_slugs:
                scores[slug] = 1.0 / (i + 1)   # higher = more relevant
    except Exception:
        pass
    return scores


# ── note selection ─────────────────────────────────────────────────────────────

def _read_index() -> list[dict]:
    """Parse index.md and return list of {slug, type, updated}."""
    if not INDEX_PATH.exists():
        return []
    entries: list[dict] = []
    for line in INDEX_PATH.read_text(encoding="utf-8", errors="ignore").splitlines():
        m = re.search(r"\[\[(.+?)\]\].*?\|\s*(\S+)\s*\|\s*(\S+)\s*\|", line)
        if m:
            entries.append({
                "slug":    m.group(1).lower(),
                "type":    m.group(2),
                "updated": m.group(3),
            })
    return entries


def select_notes(query: str, top_k: int = 5) -> list[Path]:
    """Return up to top_k note paths ranked by relevance to query."""
    index = _read_index()
    if not index:
        # Fallback: list all notes directly
        all_notes = [p for p in sorted(WIKI_DIR.glob("*.md"))
                     if p.name not in {"index.md", "log.md", "Wiki Health.md",
                                       "Wiki-Health.md"}]
        return all_notes[:top_k]

    slugs = [e["slug"] for e in index]
    query_tokens = _tokenise(query)

    # Read notes for keyword scoring
    note_texts: dict[str, str] = {}
    for e in index:
        p = WIKI_DIR / f"{e['slug']}.md"
        if p.exists():
            try:
                note_texts[e["slug"]] = p.read_text(encoding="utf-8", errors="ignore")
            except Exception:
                pass

    rag = _rag_scores(query, slugs)

    # Combined score
    scored: list[tuple[float, str]] = []
    for e in index:
        slug = e["slug"]
        kw = _keyword_score(query_tokens, note_texts.get(slug, ""))
        r = rag.get(slug, 0.0)
        combined = kw * 0.6 + r * 0.4
        scored.append((combined, slug))

    scored.sort(reverse=True)
    results = []
    for _, slug in scored[:top_k]:
        p = WIKI_DIR / f"{slug}.md"
        if p.exists():
            results.append(p)
    return results


# ── LLM helpers ───────────────────────────────────────────────────────────────

def _sidecar_up() -> bool:
    try:
        urllib.request.urlopen(f"{SIDECAR_URL}/health", timeout=2)
        return True
    except Exception:
        return False


def _call_ollama(system: str, prompt: str, timeout: int = 120) -> str:
    payload = json.dumps({
        "model": OLLAMA_MODEL,
        "system": system,
        "prompt": prompt,
        "stream": False,
        "options": {"temperature": 0.3, "num_ctx": 8192},
    }).encode()
    req = urllib.request.Request(
        f"{OLLAMA_BASE}/api/generate", data=payload,
        headers={"Content-Type": "application/json"}, method="POST",
    )
    try:
        with urllib.request.urlopen(req, timeout=timeout) as r:
            return json.loads(r.read()).get("response", "").strip()
    except Exception as e:
        return f"[ollama error: {e}]"


def _call_sidecar(prompt: str) -> str:
    payload = json.dumps({"prompt": prompt, "task_type": "research"}).encode()
    req = urllib.request.Request(
        f"{SIDECAR_URL}/query", data=payload,
        headers={"Content-Type": "application/json"}, method="POST",
    )
    try:
        with urllib.request.urlopen(req, timeout=60) as r:
            return json.loads(r.read()).get("response", "").strip()
    except Exception:
        return ""


# ── query engine ──────────────────────────────────────────────────────────────

def _build_synthesis_prompt(query: str, notes: list[Path], is_comparative: bool) -> tuple[str, str]:
    """Return (system_prompt, user_prompt)."""
    system = (
        "You are a knowledge synthesis engine inside SuneelWorkSpace — a living, "
        "self-maintaining local AI workspace on macOS M4 Max 64 GB. "
        "Answer the query using ONLY the provided wiki notes. "
        "Be concise, structured, and link relevant concepts with [[wiki-links]]. "
        "Format the answer as clean markdown. "
        + ("Structure your answer as a comparison table followed by a summary paragraph."
           if is_comparative else "")
    )

    note_sections = []
    for p in notes:
        try:
            content = p.read_text(encoding="utf-8", errors="ignore")[:1200]
            note_sections.append(f"## Note: {p.stem}\n{content}")
        except Exception:
            pass

    joined = "\n\n---\n\n".join(note_sections)
    user = (
        f"Query: {query}\n\n"
        f"Wiki notes:\n\n{joined}\n\n"
        "Provide a synthesised answer:"
    )
    return system, user


def query(q: str, top_k: int = 5) -> dict:
    """Run the full query pipeline. Returns {answer, notes_used, synthesis_path?}."""
    if not q.strip():
        return {"answer": "", "notes_used": [], "error": "empty query"}

    notes = select_notes(q, top_k=top_k)
    if not notes:
        return {
            "answer": "No relevant wiki notes found. Try running `wiki-ingest` first.",
            "notes_used": [],
        }

    is_comparative = bool(_COMPARATIVE_RE.search(q))
    system, prompt = _build_synthesis_prompt(q, notes, is_comparative)

    print(f"  [wiki-query] Using {len(notes)} notes: "
          f"{', '.join(p.stem for p in notes)}")
    print(f"  [wiki-query] Synthesising ({'comparative' if is_comparative else 'factual'})…")

    if _sidecar_up():
        answer = _call_sidecar(prompt)
        if not answer:
            answer = _call_ollama(system, prompt)
    else:
        answer = _call_ollama(system, prompt)

    result: dict = {
        "answer": answer,
        "notes_used": [str(p.relative_to(WORKSPACE)) for p in notes],
    }

    # Save synthesis file for comparative queries
    if is_comparative and answer:
        ts = datetime.now(timezone.utc).strftime("%Y%m%d-%H%M%S")
        safe_q = re.sub(r"[^\w\s-]", "", q)[:40].strip().replace(" ", "-").lower()
        synth_path = WIKI_DIR / f"synthesis-{ts}-{safe_q}.md"

        lines = [
            f"# Synthesis: {q}",
            f"\n> Generated: {datetime.now(timezone.utc).isoformat()}",
            f"> Sources: {', '.join(f'[[{p.stem}]]' for p in notes)}",
            "\n---\n",
            answer,
            "\n---\n",
            "*Auto-generated by `wiki-query`. Review and promote to a permanent note if useful.*",
        ]
        synth_path.write_text("\n".join(lines), encoding="utf-8")

        # Append link to index.md
        slug = synth_path.stem.lower()
        today = datetime.now(timezone.utc).date().isoformat()
        row = f"| [[{slug}]] | synthesis | {today} |"
        if INDEX_PATH.exists():
            with INDEX_PATH.open("a", encoding="utf-8") as f:
                f.write(f"\n{row}\n")

        result["synthesis_path"] = str(synth_path.relative_to(WORKSPACE))
        print(f"  [wiki-query] Synthesis saved → {synth_path.name}")

    return result


# ── CLI ────────────────────────────────────────────────────────────────────────

def main() -> None:
    import argparse
    parser = argparse.ArgumentParser(description="Wiki compound query engine")
    parser.add_argument("query_text", nargs="+", help="Query string")
    parser.add_argument("--top-k", type=int, default=5,
                        help="Number of wiki notes to use (default 5)")
    args = parser.parse_args()

    q = " ".join(args.query_text)
    print(f"[wiki-query] Query: {q!r}")
    result = query(q, top_k=args.top_k)

    print("\n" + "─" * 60)
    print(result.get("answer", "No answer generated."))
    print("─" * 60)

    if sp := result.get("synthesis_path"):
        print(f"\nSynthesis saved → {sp}")

    sys.exit(0 if result.get("answer") else 1)


if __name__ == "__main__":
    main()
