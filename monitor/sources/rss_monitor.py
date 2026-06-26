#!/usr/bin/env python3
"""Fetch and parse RSS/Atom feeds defined in monitor_config.json.

Uses regex extraction instead of an XML parser — no XXE or billion-laughs
attack surface. Works on both RSS 2.0 (<item>) and Atom (<entry>) formats.
"""

import json
import re
import sys
import urllib.request
from datetime import datetime, timezone
from pathlib import Path

CONFIG_PATH = Path(__file__).parent.parent / "config" / "monitor_config.json"
CACHE_DIR = Path(__file__).parent.parent / "cache"


def _fetch(url: str) -> str | None:
    try:
        req = urllib.request.Request(url, headers={"User-Agent": "SuneelWorkSpace-Monitor/1.0"})
        with urllib.request.urlopen(req, timeout=15) as resp:
            return resp.read().decode("utf-8", errors="replace")
    except Exception as e:
        print(f"  RSS fetch failed [{url}]: {e}", file=sys.stderr)
        return None


def _tag(text: str, tag: str) -> str:
    """Extract first occurrence of <tag>…</tag>, stripping CDATA if present."""
    m = re.search(rf"<{tag}[^>]*>(.*?)</{tag}>", text, re.DOTALL | re.IGNORECASE)
    if not m:
        return ""
    val = m.group(1).strip()
    # unwrap CDATA
    cdata = re.match(r"<!\[CDATA\[(.*?)]]>", val, re.DOTALL)
    return (cdata.group(1) if cdata else val).strip()


def _attr(text: str, tag: str, attr: str) -> str:
    """Extract attribute value from first self-closing or opening <tag attr="...">."""
    m = re.search(rf"<{tag}[^>]+{attr}=['\"]([^'\"]*)['\"]", text, re.IGNORECASE)
    return m.group(1).strip() if m else ""


def _parse_feed(raw: str, label: str, tags: list[str]) -> list[dict]:
    now = datetime.now(timezone.utc).isoformat()
    items = []

    # RSS 2.0: split on <item>
    chunks = re.split(r"<item[\s>]", raw, flags=re.IGNORECASE)[1:]
    if not chunks:
        # Atom: split on <entry>
        chunks = re.split(r"<entry[\s>]", raw, flags=re.IGNORECASE)[1:]

    for chunk in chunks:
        title = _tag(chunk, "title") or _tag(chunk, "atom:title")
        if not title:
            continue
        # RSS link vs Atom <link href="...">
        link = _tag(chunk, "link") or _attr(chunk, "link", "href")
        pub = _tag(chunk, "pubDate") or _tag(chunk, "published") or _tag(chunk, "updated")
        summary = (_tag(chunk, "description") or _tag(chunk, "summary") or
                   _tag(chunk, "content") or _tag(chunk, "atom:summary"))[:300]
        items.append({
            "title": title[:200],
            "url": link,
            "published": pub,
            "summary": summary,
            "source": label,
            "tags": tags,
            "fetched_at": now,
        })

    return items


def run(dry_run: bool = False) -> list[dict]:
    config = json.loads(CONFIG_PATH.read_text())
    all_items = []

    for feed in config.get("rss_feeds", []):
        print(f"  [RSS] {feed['label']} ...", end=" ", flush=True)
        if dry_run:
            print("(dry-run skip)")
            continue
        raw = _fetch(feed["url"])
        if raw:
            items = _parse_feed(raw, feed["label"], feed.get("tags", []))
            print(f"{len(items)} items")
            all_items.extend(items)
        else:
            print("0 items (error)")

    if not dry_run:
        CACHE_DIR.mkdir(parents=True, exist_ok=True)
        date = datetime.now().strftime("%Y-%m-%d")
        out = CACHE_DIR / f"rss_{date}.json"
        out.write_text(json.dumps(all_items, indent=2))
        print(f"  saved → {out}")

    return all_items


if __name__ == "__main__":
    run(dry_run="--dry-run" in sys.argv)
