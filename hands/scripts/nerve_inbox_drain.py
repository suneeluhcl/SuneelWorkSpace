#!/usr/bin/env python3
"""Periodically drain organ nerve_inbox/ queues, logging a one-line summary per organ.

Doesn't build per-organ reaction logic -- just prevents unbounded accumulation
while keeping the notify-on-change mechanism usable for future consumers.
"""
import sys
from collections import Counter
from pathlib import Path
from datetime import datetime, timezone

WORKSPACE = Path(__file__).resolve().parent.parent.parent
sys.path.insert(0, str(WORKSPACE / "nervous"))

from nerve_propagator import check_inbox, clear_inbox  # noqa: E402

ORGANS = ["brain", "heart", "eyes", "ears", "nervous", "skeleton",
          "blood", "hands", "mouth", "dna", "lab", "spine"]

LOG_PATH = WORKSPACE / "blood" / "logs" / "MAINTENANCE_LOG.md"


def main() -> None:
    lines = []
    total = 0
    for organ in ORGANS:
        events = check_inbox(organ)
        if not events:
            continue
        by_source = Counter(e.get("source_organ", "?") for e in events)
        summary = ", ".join(f"{src}:{n}" for src, n in by_source.most_common())
        cleared = clear_inbox(organ)
        total += cleared
        lines.append(f"- nerve_inbox drained for {organ}: {cleared} events ({summary})")

    if lines:
        now = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
        with open(LOG_PATH, "a") as f:
            f.write(f"\n## {now} nerve-inbox-drain\n")
            for line in lines:
                f.write(line + "\n")
    print(f"Drained {total} total nerve_inbox events across {len(lines)} organ(s).")


if __name__ == "__main__":
    main()
