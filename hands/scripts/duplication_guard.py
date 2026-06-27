#!/usr/bin/env python3
"""Duplication Guard: Protects workspace against file duplication, drift, and misplacement."""

from __future__ import annotations

import argparse
import json
import os
import sys
from pathlib import Path
from typing import Any

ROOT = Path(os.environ.get("SUNEEL_WORKSPACE", Path.home() / "SuneelWorkSpace")).resolve()

# List of subsystem directories
SUBSYSTEM_DIRS = {
    "agent-system",
    "anticipation",
    "autolab",
    "automation",
    "comms",
    "codex",
    "docs",
    "goal-engine",
    "identity",
    "mcp",
    "obsidian-vault",
    "orchestrator",
    "projects",
    "research-engine",
    "scripts",
    "system-context",
    "tools",
    "testing",
    "dashboard",
    "gateway",
}


def rel(path: Path) -> str:
    try:
        return str(path.relative_to(ROOT))
    except ValueError:
        return str(path)

def load_json(path: Path) -> Any:
    if not path.exists():
        return {}
    try:
        return json.loads(path.read_text())
    except Exception:
        return {}

def check_canonical_location(proposed_path: Path) -> tuple[bool, str]:
    """Phase 2: Enforce canonical location rules."""
    abs_path = proposed_path.resolve()
    
    # Try to make relative to ROOT
    try:
        rel_path = abs_path.relative_to(ROOT)
    except ValueError:
        return False, f"Path '{proposed_path}' is outside the workspace root '{ROOT}'."
    
    parts = rel_path.parts
    if not parts:
        return True, ""
        
    top_dir = parts[0]
    filename = parts[-1]
    ext = Path(filename).suffix.lower()
    
    # Rule 1: bin/ must only contain symlinks
    if top_dir == "bin" and len(parts) > 1:
        # If the file doesn't exist yet, we check if it is being proposed as a symlink
        # Note: At runtime we check if the user is attempting to write a regular file here.
        return True, "WARNING: All additions to bin/ must be created as symlinks to subsystem scripts."
        
    # Rule 2: scripts must live in subsystem directories (not root or bin/ as raw files)
    if (ext in (".sh", ".py", ".bash", ".zsh") or not ext) and top_dir not in SUBSYSTEM_DIRS and top_dir != "bin" and top_dir != "scripts":
        suggested_sub = "scripts" if top_dir == "root" else top_dir
        return False, (
            f"Misplaced Script Rejected: Scripts must live inside a valid subsystem scripts directory (e.g. 'heart/goals/scripts/', 'heart/orchestrator/scripts/').\n"
            f"Proposed path: {rel_path}\n"
            f"Suggested action: Move to subsystem folder, then create a symlink in bin/ if it's a CLI entrypoint."
        )

    # Rule 3: configs must stay in subsystem/config/ or correct config directories
    is_config_ext = ext in (".json", ".yaml", ".yml", ".toml")
    is_config_name = "config" in filename.lower() or "policy" in filename.lower() or "weights" in filename.lower()
    if (is_config_ext and is_config_name) or filename == "opencode.json":
        # Check if it lives in a subsystem/config or nervous/nervous/nervous/mcp/server/config or heart/orchestrator/router
        in_config_dir = False
        for part in parts:
            if part in ("config", "router", "adaptive", "settings"):
                in_config_dir = True
                break
        if not in_config_dir and top_dir not in (".agents", ".claude", ".gstack", ".rtk", ".serena") and filename != "opencode.json":
            return False, (
                f"Misplaced Config Rejected: Configuration files must stay in subsystem/config/ directories.\n"
                f"Proposed path: {rel_path}\n"
                f"Suggested action: Place config in 'subsystem/config/' (e.g., 'mouth/mouth/mouth/comms/config/{filename}')."
            )
            
    return True, ""

def find_duplicates(proposed_path: Path, intent: str | None) -> list[dict[str, Any]]:
    """Phase 1: Scan file_graph.json and find similar files or intents."""
    graph_path = ROOT / "spine/spine/audit/file_graph.json"
    graph = load_json(graph_path)
    
    proposed_rel = rel(proposed_path)
    proposed_name = proposed_path.name.lower()
    # Normalize proposed base name for fuzzy comparison
    proposed_base = proposed_path.stem.lower()
    
    matches = []
    
    # 1. Check exact name matches or stem matches in the file graph
    files = graph.get("files", [])
    for f in files:
        fpath = f.get("path", "")
        if fpath == proposed_rel:
            continue
        
        fpath_obj = Path(fpath)
        fname = fpath_obj.name.lower()
        fstem = fpath_obj.stem.lower()
        
        score = 0
        reasons = []
        
        # Name matches exactly (e.g. goal-create in another place)
        if fname == proposed_name:
            score += 90
            reasons.append("Exact filename match")
        elif fstem == proposed_base:
            score += 80
            reasons.append("Stem filename match")
        elif proposed_base in fstem or fstem in proposed_base:
            # Overlapping names
            score += 50
            reasons.append(f"Filename overlapping stem ('{fstem}' vs '{proposed_base}')")
            
        # 2. Compare intent if provided
        if intent:
            intent_words = set(intent.lower().split())
            fpath_words = set(fpath.lower().replace("/", " ").replace("_", " ").replace("-", " ").split())
            common_words = intent_words.intersection(fpath_words)
            # Remove boring words
            common_words = {w for w in common_words if w not in {"the", "a", "an", "and", "or", "in", "on", "at", "to", "for", "of", "script", "py", "sh"}}
            if len(common_words) >= 2:
                score += len(common_words) * 15
                reasons.append(f"Overlap in description keywords: {', '.join(common_words)}")
                
        if score >= 50:
            matches.append({
                "path": fpath,
                "score": score,
                "reasons": reasons,
                "subsystem": f.get("subsystem", "unknown")
            })
            
    # Sort matches by score descending
    matches.sort(key=lambda x: -x["score"])
    return matches

def main() -> int:
    parser = argparse.ArgumentParser(description="Duplication Guard")
    parser.add_argument("path", help="Proposed file path to create/modify")
    parser.add_argument("--intent", "-i", help="Description of the file's purpose/intent", default=None)
    parser.add_argument("--force", "-f", action="store_true", help="Bypass duplication warning")
    args = parser.parse_args()
    
    proposed = Path(args.path).resolve()
    
    # 1. Enforce Canonical Location (Phase 2)
    ok, error_msg = check_canonical_location(proposed)
    if not ok:
        print("="*60, file=sys.stderr)
        print("❌ CANONICAL LOCATION ENFORCEMENT FAILURE", file=sys.stderr)
        print("="*60, file=sys.stderr)
        print(error_msg, file=sys.stderr)
        return 2
        
    # 2. Check Duplication (Phase 1 & 3)
    matches = find_duplicates(proposed, args.intent)
    if matches and not args.force:
        print("="*60, file=sys.stderr)
        print("⚠️  DUPLICATION WARNING: Similar functionality already exists", file=sys.stderr)
        print("="*60, file=sys.stderr)
        print(f"Proposed: {rel(proposed)}", file=sys.stderr)
        if args.intent:
            print(f"Intent:   {args.intent}", file=sys.stderr)
        print("\nSimilar files found:", file=sys.stderr)
        for idx, m in enumerate(matches[:3], 1):
            print(f"  {idx}. {m['path']} (Confidence: {m['score']}% - Subsystem: {m['subsystem']})", file=sys.stderr)
            for r in m["reasons"]:
                print(f"     → {r}", file=sys.stderr)
        print("\nOptions:", file=sys.stderr)
        print("  1. Extend existing system instead of creating a new file.", file=sys.stderr)
        print("  2. Intentionally fork/create (Run command with '--force' to proceed).", file=sys.stderr)
        print("="*60, file=sys.stderr)
        return 1
        
    if ok and not matches:
        print(f"✓ Path verification passed: {rel(proposed)}")
    elif args.force:
        print(f"✓ Warning bypassed with --force: {rel(proposed)}")
        
    return 0

if __name__ == "__main__":
    sys.exit(main())
