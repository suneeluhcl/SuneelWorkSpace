"""
challenger.py
Generates self-improvement challenges for the workspace.
Logs challenges to lab/evolution/challenges.jsonl.
"""
import json
import random
import sys
from datetime import datetime, timezone
from pathlib import Path

_HERE = Path(__file__).parent
WORKSPACE = _HERE.parent
CHALLENGES_LOG = _HERE / "challenges.jsonl"

CHALLENGE_TEMPLATES = [
    {"type": "performance",  "template": "Reduce {subsystem} latency by {pct}% by optimizing {target}"},
    {"type": "coverage",     "template": "Add {capability} capability to improve {area} coverage"},
    {"type": "reliability",  "template": "Add retry logic and fallback for {component} to reach {target_pct}% uptime"},
    {"type": "intelligence", "template": "Improve {agent} decision quality by training on {data_source}"},
    {"type": "automation",   "template": "Automate {manual_task} to save {time_estimate} per day"},
    {"type": "integration",  "template": "Connect {system_a} to {system_b} for {benefit}"},
]

SUBSYSTEMS  = ["model router", "visual monitor", "evolution engine", "autolab", "memory system", "orchestrator"]
COMPONENTS  = ["API calls", "WebSocket", "file I/O", "subprocess execution", "vector search"]
AGENTS      = ["orchestrator", "autolab runner", "model router", "visual monitor", "gap finder"]
DATA_SRCS   = ["execution history", "user feedback", "benchmark results", "repair logs"]
MANUAL_TASK = ["health checks", "log review", "model selection", "gap scanning", "approval queue review"]
BENEFITS    = ["better observability", "faster decisions", "automated recovery", "continuous learning"]


def generate_challenges(count: int = 5) -> list:
    """Generate a set of self-improvement challenges."""
    challenges: list[dict] = []
    ts = datetime.now(timezone.utc)

    for i in range(count):
        t = random.choice(CHALLENGE_TEMPLATES)
        ch = {
            "id": f"challenge_{ts.strftime('%Y%m%d_%H%M%S')}_{i}",
            "type": t["type"],
            "description": t["template"].format(
                subsystem=random.choice(SUBSYSTEMS),
                pct=random.choice([10, 20, 30, 50]),
                target=random.choice(COMPONENTS),
                capability=random.choice(["self-healing", "predictive", "adaptive", "multi-modal"]),
                area=random.choice(["observability", "automation", "intelligence", "reliability"]),
                component=random.choice(COMPONENTS),
                target_pct=random.choice([95, 99, 99.9]),
                agent=random.choice(AGENTS),
                data_source=random.choice(DATA_SRCS),
                manual_task=random.choice(MANUAL_TASK),
                time_estimate=random.choice(["10 minutes", "30 minutes", "1 hour"]),
                system_a=random.choice(SUBSYSTEMS[:3]),
                system_b=random.choice(SUBSYSTEMS[3:]),
                benefit=random.choice(BENEFITS),
            ),
            "generated_at": ts.isoformat(),
            "status": "open",
            "priority": random.choice(["low", "medium", "high"]),
        }
        challenges.append(ch)

    try:
        CHALLENGES_LOG.parent.mkdir(parents=True, exist_ok=True)
        with open(CHALLENGES_LOG, "a") as f:
            for c in challenges:
                f.write(json.dumps(c) + "\n")
    except Exception:
        pass

    return challenges


if __name__ == "__main__":
    count = int(sys.argv[1]) if len(sys.argv) > 1 else 5
    challenges = generate_challenges(count)
    print(f"Generated {len(challenges)} challenge(s):")
    for c in challenges:
        print(f"  [{c['priority'].upper():6}] {c['type']}: {c['description']}")
