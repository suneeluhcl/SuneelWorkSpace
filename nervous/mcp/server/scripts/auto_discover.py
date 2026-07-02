#!/usr/bin/env python3
"""MCP Resource Map Auto-Discovery.
Scans workspace for files matching known patterns and compares to resource_map.json.
"""
import json
import os
import sys
from pathlib import Path
from datetime import datetime

WORKSPACE = Path(os.environ.get('WORKSPACE', Path.home() / 'SuneelWorkSpace'))
RESOURCE_MAP = WORKSPACE / 'nervous/mcp/server/config/resource_map.json'

SCAN_PATTERNS = [
    ('**/*.md', ['MEMORY', 'DECISIONS', 'SESSION_HANDOFF', 'ACTIVE_TASKS', 'MAINTENANCE', 'HANDOFF']),
    ('spine/state/*.json', None),
    ('brain/system/*.json', None),
    ('heart/orchestrator/mesh/*.json', None),
    ('brain/graph/knowledge_graph.json', None),
]

SKIP_DIRS = {
    '.git', '__pycache__', 'node_modules', '.hf_cache', 'chroma_store',
    'sandboxes', 'archive', 'backups', '.obsidian', 'brain/graph/reports'
}


def load_resource_map():
    if not RESOURCE_MAP.exists():
        return {"resources": [], "version": "1.0"}
    with open(RESOURCE_MAP) as f:
        return json.load(f)


def get_registered_paths(resource_map):
    registered = set()
    for resource in resource_map.get('resources', []):
        if 'file_path' in resource:
            registered.add(Path(resource['file_path']))
        if 'path' in resource:
            registered.add(Path(resource['path']))
    return registered


def discover_files():
    discovered = []
    for pattern, name_filters in SCAN_PATTERNS:
        for f in WORKSPACE.glob(pattern):
            if any(skip in f.parts for skip in SKIP_DIRS):
                continue
            if f.is_file():
                if name_filters is None or any(n in f.name for n in name_filters):
                    discovered.append(f)
    return discovered


def generate_uri(file_path: Path) -> str:
    rel = file_path.relative_to(WORKSPACE)
    parts = str(rel).replace('/', '_').replace('.', '_').lower()
    return f"workspace://{parts.replace('agent_system_', '').replace('brain_', 'brain/')}"


def main():
    propose = '--propose' in sys.argv
    apply = '--apply' in sys.argv

    resource_map = load_resource_map()
    registered = get_registered_paths(resource_map)
    discovered = discover_files()

    unregistered = [f for f in discovered if f not in registered and f.resolve() not in {r.resolve() for r in registered}]

    print(f"Scanning workspace for unregistered resources...")
    print(f"  Discovered: {len(discovered)} files")
    print(f"  Registered: {len(registered)} paths")
    print(f"  Unregistered: {len(unregistered)} files")

    if not unregistered:
        print("\n✅ All discovered files are registered in resource_map.json")
        return

    print("\nUnregistered files:")
    proposed = []
    for f in unregistered:
        rel = str(f.relative_to(WORKSPACE))
        uri = generate_uri(f)
        print(f"  {rel}")
        proposed.append({
            "uri": uri,
            "file_path": str(f),
            "description": f"Auto-discovered: {rel}",
            "discovered_at": datetime.now().isoformat(),
            "source": "auto_discover"
        })

    if propose or apply:
        print(f"\nProposed additions ({len(proposed)}):")
        for p in proposed:
            print(f"  {p['uri']} → {Path(p['file_path']).name}")

    if apply:
        print("\n⚠️  CONTROLLED: About to add to resource_map.json")
        reply = input("Confirm? (y/N) ").strip().lower()
        if reply == 'y':
            resource_map.setdefault('resources', []).extend(proposed)
            resource_map['last_updated'] = datetime.now().isoformat()
            with open(RESOURCE_MAP, 'w') as f:
                json.dump(resource_map, f, indent=2)
            print(f"✅ Added {len(proposed)} resources to resource_map.json")
        else:
            print("Cancelled.")
    elif not propose:
        print("\nRun with --propose to see suggested additions.")
        print("Run with --apply to apply them after review.")


if __name__ == '__main__':
    main()
