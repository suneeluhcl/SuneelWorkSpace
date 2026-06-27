#!/usr/bin/env python3
"""Build a relevance-scored morning brief from today's monitor cache."""

import json
import re
import sys
from datetime import datetime
from pathlib import Path

CACHE_DIR = Path(__file__).parent.parent / "cache"
CONFIG_PATH = Path(__file__).parent.parent / "config" / "monitor_config.json"
ACTIVE_TASKS_PATH = Path(__file__).parent.parent.parent / "agent-system" / "tasks" / "ACTIVE_TASKS.md"
BRAIN_LOGS = Path(__file__).parent.parent.parent / "obsidian-vault" / "logs"


def _goal_keywords() -> set[str]:
    """Extract keywords from ACTIVE_TASKS.md for relevance scoring."""
    keywords: set[str] = set()
    if ACTIVE_TASKS_PATH.exists():
        text = ACTIVE_TASKS_PATH.read_text(encoding="utf-8", errors="ignore").lower()
        words = re.findall(r"\b[a-z]{4,}\b", text)
        # Keep words that appear >1 time (likely meaningful)
        from collections import Counter
        counts = Counter(words)
        keywords = {w for w, c in counts.items() if c > 1}
    # Always include workspace-relevant terms
    keywords.update({"claude", "llm", "agent", "workflow", "autolab", "telemetry",
                     "monitor", "prompt", "python", "mcp", "workspace"})
    return keywords


def _score(item: dict, keywords: set[str]) -> float:
    text = f"{item.get('title','')} {item.get('summary','')}".lower()
    hits = sum(1 for kw in keywords if kw in text)
    return min(hits / max(len(keywords), 1) * 10, 1.0)


def build(date_str: str | None = None) -> str:
    date_str = date_str or datetime.now().strftime("%Y-%m-%d")
    config = json.loads(CONFIG_PATH.read_text())
    threshold = config.get("relevance_threshold", 0.4)

    # Load all cache files for the date
    all_items: list[dict] = []
    for source in ("rss", "github", "arxiv"):
        cache_file = CACHE_DIR / f"{source}_{date_str}.json"
        if cache_file.exists():
            try:
                all_items.extend(json.loads(cache_file.read_text()))
            except Exception:
                pass

    keywords = _goal_keywords()

    # Score and filter
    scored = [(item, _score(item, keywords)) for item in all_items]
    scored = [(item, s) for item, s in scored if s >= threshold]
    scored.sort(key=lambda x: -x[1])

    # Deduplicate by URL
    seen_urls: set[str] = set()
    unique = []
    for item, score in scored:
        url = item.get("url", "")
        if url and url in seen_urls:
            continue
        seen_urls.add(url)
        unique.append((item, score))

    from ears.monitor.digest.digest_formatter import format_brief
    brief = format_brief(unique, date_str, len(all_items))

    BRAIN_LOGS.mkdir(parents=True, exist_ok=True)
    out = BRAIN_LOGS / f"morning_brief_{date_str}.md"
    out.write_text(brief)
    print(f"Brief written → {out} ({len(unique)} relevant / {len(all_items)} total items)")
    return brief


def main() -> None:
    date = sys.argv[1] if len(sys.argv) > 1 else None
    build(date)


if __name__ == "__main__":
    main()
