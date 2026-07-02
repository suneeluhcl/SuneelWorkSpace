#!/usr/bin/env python3
"""Mesh Monitor: Detects stalled tasks and re-routes to next-best agent."""
import json
import time
import sys
import os
from datetime import datetime, timedelta
from pathlib import Path

WORKSPACE = Path(os.environ.get('WORKSPACE', Path.home() / 'SuneelWorkSpace'))
QUEUE_FILE = WORKSPACE / 'heart/orchestrator/mesh/task_queue.json'
REGISTRY_FILE = WORKSPACE / 'heart/orchestrator/mesh/agent_registry.json'
LOG_FILE = WORKSPACE / 'blood/logs/mesh_monitor.log'


def log(msg):
    timestamp = datetime.now().isoformat()
    line = f"[{timestamp}] {msg}"
    print(line)
    LOG_FILE.parent.mkdir(parents=True, exist_ok=True)
    with open(LOG_FILE, 'a') as f:
        f.write(line + '\n')


def load_queue():
    if not QUEUE_FILE.exists():
        return {"queue": []}
    with open(QUEUE_FILE) as f:
        return json.load(f)


def save_queue(data):
    with open(QUEUE_FILE, 'w') as f:
        json.dump(data, f, indent=2)


def load_registry():
    if not REGISTRY_FILE.exists():
        return {"agents": {}}
    with open(REGISTRY_FILE) as f:
        return json.load(f)


def get_next_agent(current_agent, registry):
    agents = list(registry.get('agents', {}).keys())
    if current_agent in agents:
        idx = agents.index(current_agent)
        return agents[(idx + 1) % len(agents)]
    return agents[0] if agents else None


def check_stalled_tasks():
    data = load_queue()
    registry = load_registry()
    now = datetime.now()
    changed = False
    for task in data['queue']:
        if task.get('status') != 'in_progress':
            continue
        last_updated = task.get('last_updated')
        if not last_updated:
            continue
        try:
            last_dt = datetime.fromisoformat(last_updated)
        except Exception:
            continue
        threshold = task.get('stall_threshold_minutes', 30)
        if (now - last_dt) > timedelta(minutes=threshold):
            next_agent = get_next_agent(task.get('assigned_agent', ''), registry)
            log(f"STALL DETECTED: task={task['task_id']} was={task['assigned_agent']} rerouting={next_agent}")
            task['status'] = 'stalled'
            task['assigned_agent'] = next_agent
            task['last_updated'] = now.isoformat()
            changed = True
    if changed:
        save_queue(data)
    return data


def print_status():
    data = load_queue()
    registry = load_registry()
    print("\n=== MESH STATUS ===")
    agents = registry.get('agents', {})
    print(f"Registered agents: {', '.join(agents.keys())}")
    queue = data.get('queue', [])
    print(f"Tasks in queue: {len(queue)}")
    if queue:
        for t in queue:
            tid = t.get('task_id', '?')[:8]
            status = t.get('status', '?').upper()
            agent = t.get('assigned_agent', '?')
            desc = t.get('description', '')[:60]
            print(f"  [{status}] {tid}... | agent={agent} | {desc}")
    else:
        print("  (empty)")
    print()


def main():
    if '--status' in sys.argv:
        print_status()
        return
    log("Mesh monitor starting — checking every 5 minutes")
    while True:
        try:
            check_stalled_tasks()
        except Exception as e:
            log(f"ERROR: {e}")
        time.sleep(300)


if __name__ == '__main__':
    main()
