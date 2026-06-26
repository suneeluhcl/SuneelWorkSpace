#!/usr/bin/env python3
"""Search Arxiv topics matching active goals.

Uses regex extraction instead of an XML parser — no XXE or billion-laughs
attack surface. Arxiv returns Atom 1.0; we extract fields with targeted
regex patterns rather than a full parse tree.
"""

import json
import re
import sys
import urllib.parse
import urllib.request
from datetime import datetime, timezone
from pathlib import Path

CONFIG_PATH = Path(__file__).parent.parent / "config" / "monitor_config.json"
CACHE_DIR = Path(__file__).parent.parent / "cache"
ARXIV_API = "http://export.arxiv.org/api/query"


def _fetch(url: str) -> str | None:
    try:
        req = urllib.request.Request(url, headers={"User-Agent": "SuneelWorkSpace/1.0"})
        with urllib.request.urlopen(req, timeout=20) as resp:
            return resp.read().decode("utf-8", errors="replace")
    except Exception as e:
        print(f"  Arxiv fetch error: {e}", file=sys.stderr)
        return None


def _tag(chunk: str, tag: str) -> str:
    m = re.search(rf"<(?:[a-z]+:)?{tag}[^>]*>(.*?)</(?:[a-z]+:)?{tag}>",
                  chunk, re.DOTALL | re.IGNORECASE)
    if not m:
        return ""
    val = m.group(1).strip()
    cdata = re.match(r"<!\[CDATA\[(.*?)]]>", val, re.DOTALL)
    return (cdata.group(1) if cdata else val).strip()


def _attr(chunk: str, tag: str, attr: str) -> str:
    m = re.search(rf"<(?:[a-z]+:)?{tag}[^>]+{attr}=['\"]([^'\"]*)['\"]",
                  chunk, re.IGNORECASE)
    return m.group(1).strip() if m else ""


def _parse_entries(raw: str) -> list[dict]:
    now = datetime.now(timezone.utc).isoformat()
    entries = re.split(r"<entry[\s>]", raw, flags=re.IGNORECASE)[1:]
    items = []
    for chunk in entries:
        title = _tag(chunk, "title")
        if not title:
            continue
        # Arxiv ID link is in <id>; the abs URL is in <link href="..." rel="alternate">
        link = _attr(chunk, "link", "href") or _tag(chunk, "id")
        pub = _tag(chunk, "published") or _tag(chunk, "updated")
        summary = _tag(chunk, "summary")[:400]
        # Extract author names
        author_chunks = re.findall(r"<author[^>]*>(.*?)</author>", chunk,
                                   re.DOTALL | re.IGNORECASE)
        authors = [_tag(a, "name") for a in author_chunks[:3] if _tag(a, "name")]
        items.append({
            "title": title[:200],
            "url": link,
            "published": pub,
            "summary": summary,
            "authors": authors,
            "source": "arxiv",
            "tags": ["arxiv", "research"],
            "fetched_at": now,
        })
    return items


def _search(query: str, max_results: int = 5) -> list[dict]:
    params = urllib.parse.urlencode({
        "search_query": f"all:{query}",
        "start": 0,
        "max_results": max_results,
        "sortBy": "submittedDate",
        "sortOrder": "descending",
    })
    raw = _fetch(f"{ARXIV_API}?{params}")
    return _parse_entries(raw) if raw else []


def run(dry_run: bool = False) -> list[dict]:
    config = json.loads(CONFIG_PATH.read_text())
    all_items = []

    for topic in config.get("arxiv_topics", []):
        label = topic.get("label", topic["query"])
        max_r = topic.get("max_results", 5)
        print(f"  [Arxiv] {label} ...", end=" ", flush=True)
        if dry_run:
            print("(dry-run skip)")
            continue
        items = _search(topic["query"], max_r)
        print(f"{len(items)} papers")
        all_items.extend(items)

    if not dry_run:
        CACHE_DIR.mkdir(parents=True, exist_ok=True)
        date = datetime.now().strftime("%Y-%m-%d")
        out = CACHE_DIR / f"arxiv_{date}.json"
        out.write_text(json.dumps(all_items, indent=2))
        print(f"  saved → {out}")

    return all_items


if __name__ == "__main__":
    run(dry_run="--dry-run" in sys.argv)
