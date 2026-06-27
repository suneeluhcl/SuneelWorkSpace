#!/usr/bin/env python3
"""Anticipation Cold Start Bootstrap.
Pre-loads 50 high-confidence behavior patterns from README command sequences.
Only adds patterns not already in prediction_memory.json. Idempotent.
"""
import json
import os
from pathlib import Path
from datetime import datetime

WORKSPACE = Path(os.environ.get('WORKSPACE', Path.home() / 'SuneelWorkSpace'))
MEMORY_FILE = WORKSPACE / 'brain/anticipation/prediction_memory.json'

BOOTSTRAP_PATTERNS = [
    # idea → goal → execute flow
    {"sequence": ["idea-start"], "next": "idea-run", "confidence": 0.72},
    {"sequence": ["idea-run"], "next": "goal-create", "confidence": 0.65},
    {"sequence": ["goal-create"], "next": "goal-execute", "confidence": 0.68},
    # research flow
    {"sequence": ["arxiv-mcp"], "next": "idea-start", "confidence": 0.60},
    {"sequence": ["memory-search"], "next": "idea-start", "confidence": 0.62},
    {"sequence": ["brain-graph-query"], "next": "memory-search", "confidence": 0.63},
    # maintenance flow
    {"sequence": ["agent-doctor"], "next": "agent-repair", "confidence": 0.75},
    {"sequence": ["agent-repair"], "next": "agent-doctor", "confidence": 0.70},
    {"sequence": ["workspace-backup"], "next": "agent-maintain", "confidence": 0.65},
    {"sequence": ["agent-maintain"], "next": "agent-doctor", "confidence": 0.68},
    # daily workflow
    {"sequence": ["agent-start"], "next": "next", "confidence": 0.80},
    {"sequence": ["next"], "next": "agent-finish", "confidence": 0.75},
    {"sequence": ["agent-finish"], "next": "agent-start", "confidence": 0.60},
    # development flow
    {"sequence": ["workspace-index"], "next": "memory-search", "confidence": 0.65},
    {"sequence": ["mcp-reindex"], "next": "mcp-status", "confidence": 0.78},
    {"sequence": ["mcp-status"], "next": "mcp-reindex", "confidence": 0.62},
    # spine/audit/improvement flow
    {"sequence": ["agent-doctor"], "next": "workspace-ci", "confidence": 0.70},
    {"sequence": ["workspace-ci"], "next": "agent-repair", "confidence": 0.65},
    {"sequence": ["duplication-guard"], "next": "integrity-guard", "confidence": 0.72},
    # dashboard flow
    {"sequence": ["workspace-dashboard"], "next": "next", "confidence": 0.65},
    # mesh operations
    {"sequence": ["mesh-status"], "next": "mesh-assign", "confidence": 0.62},
    {"sequence": ["mesh-monitor-start"], "next": "mesh-status", "confidence": 0.68},
    # graph operations
    {"sequence": ["brain-graph-build"], "next": "brain-graph-query", "confidence": 0.75},
    {"sequence": ["brain-graph-query"], "next": "idea-start", "confidence": 0.60},
    {"sequence": ["brain-graph-orphans"], "next": "brain-graph-build", "confidence": 0.65},
    # autolab flow
    {"sequence": ["autolab-run"], "next": "autolab-status", "confidence": 0.78},
    {"sequence": ["autolab-status"], "next": "autolab-run", "confidence": 0.65},
    {"sequence": ["autolab-promote"], "next": "agent-doctor", "confidence": 0.70},
    # gateway flow
    {"sequence": ["gateway-start"], "next": "gateway-status", "confidence": 0.72},
    {"sequence": ["gateway-status"], "next": "gateway-token", "confidence": 0.65},
    # git flow
    {"sequence": ["git-status"], "next": "git-commit", "confidence": 0.75},
    {"sequence": ["git-commit"], "next": "git-push", "confidence": 0.80},
    # evolution
    {"sequence": ["daily-evolve"], "next": "evolution-trend", "confidence": 0.70},
    {"sequence": ["evolution-trend"], "next": "agent-doctor", "confidence": 0.65},
    # training data
    {"sequence": ["build-training-data"], "next": "agent-finish", "confidence": 0.60},
    # MCP connectors
    {"sequence": ["ollama-mcp"], "next": "memory-search", "confidence": 0.60},
    {"sequence": ["arxiv-mcp"], "next": "brain-graph-build", "confidence": 0.60},
    # common pairs
    {"sequence": ["agent-start", "agent-doctor"], "next": "next", "confidence": 0.72},
    {"sequence": ["next", "goal-create"], "next": "goal-execute", "confidence": 0.68},
    {"sequence": ["idea-start", "idea-run"], "next": "goal-create", "confidence": 0.70},
    {"sequence": ["agent-doctor", "agent-repair"], "next": "mcp-reindex", "confidence": 0.65},
    {"sequence": ["mcp-reindex", "mcp-status"], "next": "next", "confidence": 0.68},
    {"sequence": ["workspace-backup", "agent-maintain"], "next": "agent-doctor", "confidence": 0.67},
    {"sequence": ["brain-graph-build", "brain-graph-query"], "next": "memory-search", "confidence": 0.63},
    {"sequence": ["autolab-run", "autolab-status"], "next": "autolab-promote", "confidence": 0.62},
    {"sequence": ["gateway-start", "gateway-status"], "next": "next", "confidence": 0.65},
    {"sequence": ["workspace-ci", "agent-doctor"], "next": "agent-finish", "confidence": 0.70},
    {"sequence": ["mesh-monitor-start", "mesh-status"], "next": "next", "confidence": 0.65},
    {"sequence": ["daily-evolve", "evolution-trend"], "next": "agent-finish", "confidence": 0.67},
]


def load_memory():
    if not MEMORY_FILE.exists():
        return {"patterns": [], "last_updated": None}
    with open(MEMORY_FILE) as f:
        return json.load(f)


def save_memory(data):
    MEMORY_FILE.parent.mkdir(parents=True, exist_ok=True)
    with open(MEMORY_FILE, 'w') as f:
        json.dump(data, f, indent=2)


def pattern_key(p):
    return tuple(p['sequence']) + (p['next'],)


def main():
    memory = load_memory()
    existing_keys = set(pattern_key(p) for p in memory.get('patterns', []))
    added = 0

    for bp in BOOTSTRAP_PATTERNS:
        key = pattern_key(bp)
        if key not in existing_keys:
            memory.setdefault('patterns', []).append({
                **bp,
                'source': 'bootstrap',
                'added_at': datetime.now().isoformat(),
                'uses': 0
            })
            existing_keys.add(key)
            added += 1

    memory['last_updated'] = datetime.now().isoformat()
    save_memory(memory)

    total = len(memory.get('patterns', []))
    print(f"✅ Bootstrap complete: {added} patterns added, {total} total in memory")
    print(f"   File: {MEMORY_FILE}")


if __name__ == '__main__':
    main()
