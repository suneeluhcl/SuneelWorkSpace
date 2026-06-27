#!/usr/bin/env python3
"""Auto-repair extensions: latency check, log rotation, workflow restoring, and MCP re-indexing."""

import json
import os
import pathlib
import subprocess
import time
from datetime import datetime, timezone

ROOT = pathlib.Path(os.environ.get("SUNEEL_WORKSPACE", str(pathlib.Path.home() / "SuneelWorkSpace"))).resolve()
LOGS_DIR = ROOT / "brain/memory/logs"
MCP_LOGS_DIR = ROOT / "nervous/nervous/nervous/mcp/server/logs"

def log_event(message: str):
    stamp = datetime.now(timezone.utc).astimezone().isoformat()
    log_file = LOGS_DIR / "MAINTENANCE_LOG.md"
    entry = f"- [{stamp}] [AUTO-REPAIR-EXT] {message}\n"
    try:
        with open(log_file, "a") as f:
            f.write(entry)
    except Exception:
        pass
    print(f"🔧 [AUTO-REPAIR-EXT] {message}")

def check_performance():
    """Detect degraded performance via testing latency logs."""
    results_path = ROOT / "lab/testing/test_results.json"
    if not results_path.exists():
        return
    try:
        data = json.loads(results_path.read_text())
        history = data.get("history", [])
        if not history:
            return
        
        # Calculate recent average latencies
        recent_runs = history[-5:]
        total_lat = 0.0
        total_cnt = 0
        for run in recent_runs:
            for t in run.get("runs", []):
                total_lat += t.get("latency_seconds", 0.0)
                total_cnt += 1
                
        if total_cnt > 0:
            avg_lat = total_lat / total_cnt
            log_event(f"Performance Check: Avg test latency is {avg_lat:.2f}s across {total_cnt} checks.")
            if avg_lat > 2.0:
                log_event("⚠️ Degraded performance detected! Cleaning workspace temp files and cache to restore speed...")
                # Safe cleanup actions
                for tmp_file in ROOT.glob("**/__pycache__"):
                    if tmp_file.is_dir():
                        import shutil
                        shutil.rmtree(tmp_file, ignore_errors=True)
                log_event("✓ Pycache cleared to restore performance.")
    except Exception as e:
        log_event(f"Error checking performance: {e}")

def restore_workflows():
    """Verify context and goal engine consistency and restore if broken."""
    context_path = ROOT / "spine/state/ACTIVE_CONTEXT.json"
    if context_path.exists():
        try:
            ctx = json.loads(context_path.read_text())
            if ctx.get("status") == "active" and ctx.get("current_goal") is None:
                # Inconsistent active context without a goal
                ctx["current_intent"] = "maintenance"
                ctx["active_workflow"] = "system_improvement"
                ctx["last_updated"] = datetime.now(timezone.utc).astimezone().isoformat()
                context_path.write_text(json.dumps(ctx, indent=2) + "\n")
                log_event("✓ Restored inconsistent active context without a goal to maintenance default.")
        except Exception as e:
            log_event(f"Error checking active context: {e}")

def clean_logs():
    """Rotate and truncate logs exceeding 100KB or 500 lines to prevent context bloat."""
    for log_dir in [LOGS_DIR, MCP_LOGS_DIR]:
        if not log_dir.exists():
            continue
        for log_file in log_dir.glob("*.md"):
            # Skip templates or non-log files
            if log_file.stem in ["PATTERNS", "INSIGHTS", "DECISIONS", "MEMORY", "SESSION_HANDOFF"]:
                continue
            _rotate_file_if_large(log_file)
        for log_file in log_dir.glob("*.log"):
            _rotate_file_if_large(log_file)

def _rotate_file_if_large(filepath: pathlib.Path, max_bytes=100*1024):
    if not filepath.exists() or filepath.stat().st_size < max_bytes:
        return
    try:
        content = filepath.read_text(errors="replace")
        lines = content.splitlines()
        if len(lines) > 500:
            # Keep last 150 lines
            kept = lines[-150:]
            # Backup full file
            archive_dir = filepath.parent / "archive"
            archive_dir.mkdir(parents=True, exist_ok=True)
            stamp = datetime.now().strftime("%Y%m%d-%H%M%S")
            backup_path = archive_dir / f"{filepath.name}.{stamp}.bak"
            filepath.replace(backup_path)
            
            # Write back the kept lines
            header = "# Log Rotated\n\n" if filepath.suffix == ".md" else ""
            filepath.write_text(header + "\n".join(kept) + "\n")
            log_event(f"Rotated large log file '{filepath.name}' ({len(lines)} lines) -> Backup saved to archive/")
    except Exception as e:
        log_event(f"Error rotating log '{filepath.name}': {e}")

def reindex_mcp():
    """Re-index the workspace-brain MCP sqlite databases."""
    reindex_script = ROOT / "bin/mcp-reindex"
    if reindex_script.exists():
        try:
            # Runs quietly
            subprocess.run([str(reindex_script)], check=True, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
            log_event("✓ MCP Server memory index successfully rebuilt.")
        except Exception as e:
            log_event(f"Error re-indexing MCP: {e}")

def main():
    log_event("Running auto-repair extensions...")
    check_performance()
    restore_workflows()
    clean_logs()
    reindex_mcp()
    log_event("Auto-repair extensions execution finished.")

if __name__ == "__main__":
    main()
