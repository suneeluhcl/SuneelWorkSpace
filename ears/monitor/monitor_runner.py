#!/usr/bin/env python3
"""P3.6 — Orchestrate all monitor sources then build digest."""

import sys
from pathlib import Path

# Allow running from any directory
sys.path.insert(0, str(Path(__file__).parent.parent))

from ears.monitor.sources.rss_monitor import run as run_rss
from ears.monitor.sources.github_monitor import run as run_github
from ears.monitor.sources.arxiv_monitor import run as run_arxiv
from ears.monitor.digest.digest_builder import build as build_digest


def run(source: str | None = None, dry_run: bool = False, skip_digest: bool = False) -> None:
    sources = {
        "rss": run_rss,
        "github": run_github,
        "arxiv": run_arxiv,
    }

    if source and source not in sources:
        print(f"Unknown source '{source}'. Valid: {', '.join(sources)}")
        sys.exit(1)

    to_run = {source: sources[source]} if source else sources

    print(f"Running monitor ({', '.join(to_run)}) {'[dry-run]' if dry_run else ''}...")
    all_items = []
    for name, fn in to_run.items():
        items = fn(dry_run=dry_run)
        all_items.extend(items)

    print(f"\nTotal items fetched: {len(all_items)}")

    if not dry_run and not skip_digest:
        print("\nBuilding digest...")
        build_digest()


def main() -> None:
    import argparse
    parser = argparse.ArgumentParser(description="Run external world monitor")
    parser.add_argument("--source", choices=["rss", "github", "arxiv"], default=None)
    parser.add_argument("--dry-run", action="store_true")
    parser.add_argument("--no-digest", action="store_true")
    args = parser.parse_args()
    run(source=args.source, dry_run=args.dry_run, skip_digest=args.no_digest)


if __name__ == "__main__":
    main()
