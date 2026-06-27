#!/usr/bin/env python3
"""P3.8 — Generate experiment hypotheses from telemetry anomalies, leaderboard gaps, and world monitor.

Appends to lab/autolab/experiment_queue.md in the format existing runner.py expects:
  category<TAB>hypothesis
"""

import json
import re
import sys
from datetime import datetime, timezone
from pathlib import Path

WORKSPACE = Path(__file__).parent.parent
ANOMALIES_PATH = WORKSPACE / "agent-system" / "telemetry" / "anomalies.json"
LEADERBOARD_PATH = WORKSPACE / "agent-system" / "telemetry" / "comparison" / "leaderboard.json"
BRAIN_LOGS = WORKSPACE / "brain" / "logs"
QUEUE_PATH = Path(__file__).parent / "experiment_queue.md"
HYPOTHESIS_LOG = Path(__file__).parent / "hypothesis_log.jsonl"


def _load_json(path: Path) -> dict | list | None:
    if not path.exists():
        return None
    try:
        return json.loads(path.read_text())
    except Exception:
        return None


def _latest_brief() -> str:
    if not BRAIN_LOGS.exists():
        return ""
    briefs = sorted(BRAIN_LOGS.glob("morning_brief_*.md"), reverse=True)
    if not briefs:
        return ""
    return briefs[0].read_text(encoding="utf-8", errors="ignore")[:3000]


def _from_anomalies(anomalies: list) -> list[tuple[str, str]]:
    hypotheses = []
    for a in anomalies:
        agent = a.get("agent", "")
        task_type = a.get("task_type", "")
        metric = a.get("metric", "")
        delta = a.get("delta_pct", 0)

        if metric == "duration_ms":
            hypotheses.append((
                "performance",
                f"{agent} latency degraded {delta}% on {task_type} — "
                f"hypothesis: reduce prompt verbosity or switch to faster model for {task_type}"
            ))
        elif metric == "success_rate":
            hypotheses.append((
                "repair",
                f"{agent} success rate dropped {delta}% on {task_type} — "
                f"hypothesis: add few-shot examples to {task_type} system prompt"
            ))
    return hypotheses


def _from_leaderboard(lb: dict) -> list[tuple[str, str]]:
    hypotheses = []
    for task_type, agents in lb.items():
        if len(agents) < 2:
            continue
        sorted_agents = sorted(agents.items(), key=lambda x: -x[1]["capability_score"])
        best_agent, best_stats = sorted_agents[0]
        worst_agent, worst_stats = sorted_agents[-1]
        gap = best_stats["capability_score"] - worst_stats["capability_score"]
        if gap > 0.15:
            hypotheses.append((
                "routing",
                f"{best_agent} outperforms {worst_agent} on {task_type} by "
                f"{int(gap*100)}% capability score — "
                f"hypothesis: route all {task_type} tasks to {best_agent} by default"
            ))
    return hypotheses


def _from_brief(brief_text: str) -> list[tuple[str, str]]:
    if not brief_text:
        return []
    hypotheses = []

    # Extract paper titles from Arxiv section
    arxiv_titles = re.findall(r"###\s+\[(.+?)\]", brief_text)
    for title in arxiv_titles[:3]:
        if any(kw in title.lower() for kw in
               ("prompt", "compress", "efficient", "fine-tun", "retriev", "agent", "chain")):
            hypotheses.append((
                "research",
                f"New paper: '{title[:100]}' — "
                f"hypothesis: review and apply technique to workspace prompt engineering"
            ))
    return hypotheses


def generate() -> list[tuple[str, str]]:
    all_hypotheses: list[tuple[str, str]] = []
    sources_used = []

    anomalies = _load_json(ANOMALIES_PATH)
    if isinstance(anomalies, list) and anomalies:
        h = _from_anomalies(anomalies)
        all_hypotheses.extend(h)
        if h:
            sources_used.append(f"anomalies ({len(h)})")

    lb = _load_json(LEADERBOARD_PATH)
    if isinstance(lb, dict) and lb:
        h = _from_leaderboard(lb)
        all_hypotheses.extend(h)
        if h:
            sources_used.append(f"leaderboard ({len(h)})")

    brief = _latest_brief()
    if brief:
        h = _from_brief(brief)
        all_hypotheses.extend(h)
        if h:
            sources_used.append(f"monitor ({len(h)})")

    if not all_hypotheses:
        print("No new hypotheses generated (no anomalies, gaps, or relevant monitor items).")
        return []

    # Append to experiment_queue.md
    with QUEUE_PATH.open("a") as f:
        for category, hypothesis in all_hypotheses:
            f.write(f"{category}\t{hypothesis}\n")

    # Log to hypothesis_log.jsonl
    ts = datetime.now(timezone.utc).isoformat()
    with HYPOTHESIS_LOG.open("a") as f:
        for category, hypothesis in all_hypotheses:
            f.write(json.dumps({
                "timestamp": ts,
                "category": category,
                "hypothesis": hypothesis,
                "status": "queued",
            }) + "\n")

    print(f"Generated {len(all_hypotheses)} hypothesis/es from: {', '.join(sources_used)}")
    print(f"Appended to {QUEUE_PATH}")
    return all_hypotheses


def show_log(n: int = 10) -> None:
    if not HYPOTHESIS_LOG.exists():
        print("No hypothesis log yet.")
        return
    lines = HYPOTHESIS_LOG.read_text().strip().splitlines()
    recent = lines[-n:]
    print(f"Last {len(recent)} hypotheses:\n")
    for line in recent:
        try:
            h = json.loads(line)
            ts = h["timestamp"][:10]
            print(f"  [{ts}] [{h['category']}] {h['hypothesis'][:120]}")
        except Exception:
            pass


def main() -> None:
    if len(sys.argv) > 1 and sys.argv[1] == "log":
        n = int(sys.argv[2]) if len(sys.argv) > 2 else 10
        show_log(n)
    else:
        generate()


if __name__ == "__main__":
    main()
