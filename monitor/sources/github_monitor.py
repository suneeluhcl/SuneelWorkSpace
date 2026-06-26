#!/usr/bin/env python3
"""Watch GitHub repos for new releases and issues."""

import json
import os
import sys
import urllib.request
from datetime import datetime, timezone
from pathlib import Path

CONFIG_PATH = Path(__file__).parent.parent / "config" / "monitor_config.json"
CACHE_DIR = Path(__file__).parent.parent / "cache"
GITHUB_API = "https://api.github.com"


def _gh_get(path: str) -> dict | list | None:
    token = os.environ.get("GITHUB_TOKEN", "")
    headers = {"Accept": "application/vnd.github+json", "User-Agent": "SuneelWorkSpace/1.0"}
    if token:
        headers["Authorization"] = f"Bearer {token}"
    try:
        req = urllib.request.Request(f"{GITHUB_API}{path}", headers=headers)
        with urllib.request.urlopen(req, timeout=15) as resp:
            return json.loads(resp.read())
    except Exception as e:
        print(f"  GitHub API error [{path}]: {e}", file=sys.stderr)
        return None


def _fetch_releases(repo: str, label: str) -> list[dict]:
    data = _gh_get(f"/repos/{repo}/releases?per_page=3")
    if not data:
        return []
    items = []
    for r in data:
        items.append({
            "title": f"[{label}] Release: {r.get('tag_name', '')} — {r.get('name', '')}",
            "url": r.get("html_url", ""),
            "published": r.get("published_at", ""),
            "summary": (r.get("body", "") or "")[:300],
            "source": f"github:{repo}",
            "tags": ["github", "release"],
            "fetched_at": datetime.now(timezone.utc).isoformat(),
        })
    return items


def _fetch_issues(repo: str, label: str) -> list[dict]:
    data = _gh_get(f"/repos/{repo}/issues?per_page=3&state=open&sort=created")
    if not data:
        return []
    items = []
    for r in (data if isinstance(data, list) else []):
        if "pull_request" in r:
            continue
        items.append({
            "title": f"[{label}] Issue: {r.get('title', '')}",
            "url": r.get("html_url", ""),
            "published": r.get("created_at", ""),
            "summary": (r.get("body", "") or "")[:300],
            "source": f"github:{repo}",
            "tags": ["github", "issue"],
            "fetched_at": datetime.now(timezone.utc).isoformat(),
        })
    return items


def run(dry_run: bool = False) -> list[dict]:
    config = json.loads(CONFIG_PATH.read_text())
    all_items = []

    for entry in config.get("github_repos", []):
        repo = entry["repo"]
        label = entry.get("label", repo)
        watch = entry.get("watch", ["releases"])
        print(f"  [GitHub] {label} ...", end=" ", flush=True)
        if dry_run:
            print("(dry-run skip)")
            continue
        items = []
        if "releases" in watch:
            items.extend(_fetch_releases(repo, label))
        if "issues" in watch:
            items.extend(_fetch_issues(repo, label))
        print(f"{len(items)} items")
        all_items.extend(items)

    if not dry_run:
        CACHE_DIR.mkdir(parents=True, exist_ok=True)
        date = datetime.now().strftime("%Y-%m-%d")
        out = CACHE_DIR / f"github_{date}.json"
        out.write_text(json.dumps(all_items, indent=2))
        print(f"  saved → {out}")

    return all_items


if __name__ == "__main__":
    run(dry_run="--dry-run" in sys.argv)
