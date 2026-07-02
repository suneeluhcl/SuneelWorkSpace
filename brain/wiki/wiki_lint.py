#!/usr/bin/env python3
"""
brain/wiki/wiki_lint.py

Wiki linter for brain/vault/wiki/.

Reads all .md files in the wiki directory and produces a health report at
brain/vault/wiki/Wiki Health.md covering:

  Broken links    — [[Target]] where Target.md does not exist
  Orphan pages    — notes with no incoming [[links]] from other wiki notes
  Conceptual gaps — noun phrases that appear 3+ times across the wiki but
                    have no corresponding note file

The report is also printed to stdout so it can be used in CI/night-shift.

CLI:
    python3 brain/wiki/wiki_lint.py
    python3 brain/wiki/wiki_lint.py --fix-stubs    # create stub notes for broken links
    python3 brain/wiki/wiki_lint.py --json          # output JSON instead of markdown
"""

import json
import os
import re
import sys
from collections import defaultdict
from datetime import datetime, timezone
from pathlib import Path

WORKSPACE  = Path(os.path.expanduser("~/SuneelWorkSpace"))
WIKI_DIR   = WORKSPACE / "brain/vault/wiki"
REPORT_PATH = WIKI_DIR / "Wiki Health.md"

# README.md is the auto-generated organ README (rewritten nightly by the README
# Intelligence System) — it is workspace machinery, not a wiki note.
_SKIP_FILES = {"index.md", "log.md", "Wiki Health.md", "README.md"}
_LINK_RE    = re.compile(r"\[\[([^\]|#]+?)(?:[|#][^\]]*?)?\]\]")

# Only slugs that are entirely safe single-path-components may become filenames.
# Rejects anything with slashes, dots sequences, null bytes, or unusual chars.
_SAFE_SLUG_RE = re.compile(r"^[a-z0-9][a-z0-9_-]{0,80}$")

# Minimum occurrences for a phrase to be flagged as a conceptual gap
_GAP_THRESHOLD = 3
# Minimum word length to be considered a gap candidate
_GAP_MIN_LEN   = 4

# Common stop-words that should not be flagged as gaps even if frequent
_STOP_WORDS = {
    "the", "and", "for", "with", "this", "that", "from", "have", "will", "been",
    "their", "about", "which", "when", "into", "there", "then", "than", "also",
    "should", "would", "could", "each", "some", "these", "those", "more", "like",
    "used", "using", "based", "note", "notes", "file", "files", "path", "workspace",
    "brain", "heart", "eyes", "ears", "spine", "blood", "hands", "mouth", "skeleton",
    "nervous", "vault", "wiki",
}


# ── scanner ───────────────────────────────────────────────────────────────────

def _slug(name: str) -> str:
    """
    Normalise a link target to a safe filename stem.

    Strips path-traversal sequences (..  /  \\  null bytes) and any char
    that is not alphanumeric, hyphen, or whitespace before collapsing spaces
    to hyphens.  Returns an empty string if the result would be unsafe.
    """
    s = name.strip().lower()
    s = s.replace("\x00", "")               # null bytes
    s = re.sub(r"[/\\]", "", s)             # forward and back slashes
    s = re.sub(r"\.{2,}", "", s)            # .. sequences
    s = re.sub(r"[^\w\s-]", "", s)          # non-word chars (keeps letters, digits, _, -)
    s = re.sub(r"\s+", "-", s).strip("-")
    return s


def _note_slug(path: Path) -> str:
    return path.stem.lower()


def _read_notes() -> dict[str, str]:
    """Return {slug: full_text} for all wiki .md files."""
    notes: dict[str, str] = {}
    if not WIKI_DIR.exists():
        return notes
    for p in WIKI_DIR.glob("*.md"):
        if p.name in _SKIP_FILES:
            continue
        try:
            notes[_note_slug(p)] = p.read_text(encoding="utf-8", errors="ignore")
        except Exception:
            pass
    return notes


def _extract_links(text: str) -> list[str]:
    """Return list of link targets from [[target]] patterns."""
    return [m.group(1).strip() for m in _LINK_RE.finditer(text)]


def _extract_plain_words(text: str) -> list[str]:
    """Return significant words from non-link, non-frontmatter text."""
    # Strip YAML frontmatter
    clean = re.sub(r"^---\n.*?\n---\n", "", text, flags=re.DOTALL)
    # Strip link syntax but keep inner text
    clean = _LINK_RE.sub(lambda m: m.group(1), clean)
    # Strip markdown headings, bullets, backticks
    clean = re.sub(r"[#*`_>|]", " ", clean)
    words = re.findall(r"\b[A-Za-z][a-zA-Z]{3,}\b", clean)
    return [w.lower() for w in words]


# ── analysis ──────────────────────────────────────────────────────────────────

def analyse() -> dict:
    """
    Returns:
    {
      "broken_links":     [(source_slug, target_slug), …],
      "orphans":          [slug, …],
      "conceptual_gaps":  [(word, count), …],
      "note_count":       int,
      "link_count":       int,
    }
    """
    notes = _read_notes()
    note_slugs: set[str] = set(notes.keys())

    # Build outgoing and incoming link maps
    outgoing: dict[str, list[str]] = defaultdict(list)
    incoming: dict[str, list[str]] = defaultdict(list)

    for slug, text in notes.items():
        links = _extract_links(text)
        for link in links:
            target = _slug(link)
            outgoing[slug].append(target)
            incoming[target].append(slug)

    # ── Broken links ─────────────────────────────────────────────────────────
    broken: list[tuple[str, str]] = []
    for src, targets in outgoing.items():
        for tgt in targets:
            if tgt not in note_slugs:
                broken.append((src, tgt))

    # ── Orphan pages ─────────────────────────────────────────────────────────
    orphans: list[str] = [s for s in note_slugs if not incoming.get(s)]

    # ── Conceptual gaps ───────────────────────────────────────────────────────
    word_counts: dict[str, int] = defaultdict(int)
    all_text = "\n".join(notes.values())
    for word in _extract_plain_words(all_text):
        if word not in _STOP_WORDS and len(word) >= _GAP_MIN_LEN:
            word_counts[word] += 1

    # Gap candidates: mentioned frequently but no note exists
    gaps: list[tuple[str, int]] = [
        (word, count)
        for word, count in word_counts.items()
        if count >= _GAP_THRESHOLD and word not in note_slugs
    ]
    gaps.sort(key=lambda x: x[1], reverse=True)

    return {
        "broken_links":    broken,
        "orphans":         orphans,
        "conceptual_gaps": gaps[:20],
        "note_count":      len(notes),
        "link_count":      sum(len(v) for v in outgoing.values()),
    }


# ── report writer ─────────────────────────────────────────────────────────────

def write_report(result: dict) -> Path:
    """Write Wiki Health.md and return the path."""
    WIKI_DIR.mkdir(parents=True, exist_ok=True)
    ts = datetime.now(timezone.utc).isoformat()
    broken    = result["broken_links"]
    orphans   = result["orphans"]
    gaps      = result["conceptual_gaps"]
    n_notes   = result["note_count"]
    n_links   = result["link_count"]

    score = 100
    score -= min(40, len(broken)  * 5)
    score -= min(30, len(orphans) * 3)
    score -= min(20, len(gaps)    * 1)

    icon = "🟢" if score >= 80 else ("🟡" if score >= 50 else "🔴")

    lines = [
        "# Wiki Health Report",
        "",
        f"> Generated: {ts}",
        "",
        f"## Summary  {icon} {score}/100",
        "",
        f"| Metric | Value |",
        f"|--------|-------|",
        f"| Notes | {n_notes} |",
        f"| Links | {n_links} |",
        f"| Broken links | {len(broken)} |",
        f"| Orphan pages | {len(orphans)} |",
        f"| Conceptual gaps | {len(gaps)} |",
        "",
    ]

    if broken:
        lines += ["## ❌ Broken Links", ""]
        for src, tgt in broken:
            lines.append(f"- `[[{tgt}]]` referenced in [[{src}]] — target note missing")
        lines.append("")

    if orphans:
        lines += ["## 🏝️ Orphan Pages", "",
                  "*These notes have no incoming links from other wiki notes.*", ""]
        for slug in sorted(orphans):
            lines.append(f"- [[{slug}]]")
        lines.append("")

    if gaps:
        lines += ["## 💡 Conceptual Gaps", "",
                  f"*Terms mentioned ≥{_GAP_THRESHOLD}× across the wiki but lacking their own note.*", ""]
        for word, count in gaps[:15]:
            lines.append(f"- `{word}` ({count} mentions)")
        lines.append("")

    if not broken and not orphans and not gaps:
        lines += ["## ✅ All checks passed — wiki is healthy!", ""]

    REPORT_PATH.write_text("\n".join(lines), encoding="utf-8")
    return REPORT_PATH


def create_stubs(broken_links: list[tuple[str, str]]) -> int:
    """
    Create stub notes for broken link targets.

    Each target slug is validated with _SAFE_SLUG_RE and confirmed to resolve
    inside WIKI_DIR before any file is written, preventing path traversal.
    """
    wiki_real = WIKI_DIR.resolve()
    created = 0
    for _, target in broken_links:
        # Reject slugs that don't match the safe single-component pattern
        if not _SAFE_SLUG_RE.match(target):
            continue
        stub_path = (WIKI_DIR / f"{target}.md").resolve()
        # Double-check the resolved path stays inside the wiki directory
        try:
            stub_path.relative_to(wiki_real)
        except ValueError:
            continue  # resolved outside WIKI_DIR — skip
        if stub_path.exists():
            continue
        entity_name = target.replace("-", " ").title()
        stub_path.write_text(
            f"---\nentity: {entity_name}\ntype: concept\n"
            f"created: {datetime.now(timezone.utc).isoformat()}\n---\n\n"
            f"# {entity_name}\n\n*Stub — expand via `wiki-ingest`.*\n\n"
            "## Facts\n\n## Backlinks\n",
            encoding="utf-8",
        )
        created += 1
    return created


# ── CLI ────────────────────────────────────────────────────────────────────────

def main() -> None:
    import argparse
    parser = argparse.ArgumentParser(description="Wiki linter — finds broken links, orphans, and gaps")
    parser.add_argument("--fix-stubs", action="store_true",
                        help="Create empty stub notes for broken link targets")
    parser.add_argument("--json", action="store_true",
                        help="Print JSON result to stdout instead of markdown report")
    args = parser.parse_args()

    result = analyse()
    broken  = result["broken_links"]
    orphans = result["orphans"]
    gaps    = result["conceptual_gaps"]

    if args.json:
        print(json.dumps(result, indent=2))
        return

    report_path = write_report(result)
    print(f"[wiki-lint] {result['note_count']} notes | "
          f"{len(broken)} broken | {len(orphans)} orphans | {len(gaps)} gaps")
    print(f"[wiki-lint] Report: {report_path}")

    if args.fix_stubs and broken:
        n = create_stubs(broken)
        print(f"[wiki-lint] Created {n} stub notes for broken links")

    # Exit code: 0 = healthy, 1 = issues found
    sys.exit(1 if (broken or orphans) else 0)


if __name__ == "__main__":
    main()
