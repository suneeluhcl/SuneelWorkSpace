#!/bin/sh

ROOT="${SUNEEL_WORKSPACE:-$HOME/SuneelWorkSpace}"
CANON="$ROOT/skeleton/rules/AGENT_SYSTEM.md"
BACKUP_ROOT="$ROOT/.agent-backups"
MAINT_LOG="$ROOT/blood/logs/MAINTENANCE_LOG.md"
SESSION_LOG="$ROOT/blood/logs/SESSION_LOG.md"
HEALTH_JSON="$ROOT/spine/state/WORKSPACE_HEALTH.json"
STATE_JSON="$ROOT/spine/state/CURRENT_STATE.json"
INDEX_JSON="$ROOT/spine/state/INDEX.json"
LAUNCHD_LABEL="com.suneelworkspace.maintenance"
LAUNCHD_WORKSPACE_PLIST="$ROOT/hands/automation/launchd/$LAUNCHD_LABEL.plist"
LAUNCHD_USER_PLIST="$HOME/Library/LaunchAgents/$LAUNCHD_LABEL.plist"

now_stamp() {
  date '+%Y-%m-%dT%H:%M:%S%z'
}

today() {
  date '+%Y-%m-%d'
}

ensure_core_dirs() {
  mkdir -p \
    "$BACKUP_ROOT" \
    "$ROOT/bin" \
    "$ROOT/brain/memory" \
    "$ROOT/brain/research" \
    "$ROOT/brain/anticipation" \
    "$ROOT/brain/graph" \
    "$ROOT/brain/injector" \
    "$ROOT/heart/tasks" \
    "$ROOT/heart/goals" \
    "$ROOT/heart/model_router" \
    "$ROOT/heart/orchestrator" \
    "$ROOT/eyes/dashboard" \
    "$ROOT/eyes/visual" \
    "$ROOT/ears/monitor" \
    "$ROOT/nervous/gateway" \
    "$ROOT/nervous/mcp" \
    "$ROOT/skeleton/rules" \
    "$ROOT/blood/telemetry" \
    "$ROOT/blood/logs" \
    "$ROOT/hands/bin" \
    "$ROOT/hands/scripts" \
    "$ROOT/hands/automation" \
    "$ROOT/mouth/dispatcher" \
    "$ROOT/mouth/comms" \
    "$ROOT/dna/identity" \
    "$ROOT/dna/feedback" \
    "$ROOT/lab/autolab" \
    "$ROOT/lab/evolution" \
    "$ROOT/spine/state" \
    "$ROOT/spine/tools" \
    "$ROOT/projects"
}

log_maintenance() {
  ensure_core_dirs
  printf '\n## %s\n\n- %s\n' "$(today)" "$*" >> "$MAINT_LOG"
}

log_session() {
  ensure_core_dirs
  printf '\n## %s\n\n- %s\n' "$(today)" "$*" >> "$SESSION_LOG"
}

backup_item() {
  item="$1"
  [ -e "$item" ] || [ -L "$item" ] || return 0
  ts="$(date '+%Y%m%d-%H%M%S')"
  dest="$BACKUP_ROOT/$ts/${item#$HOME/}"
  mkdir -p "$(dirname "$dest")"
  cp -a "$item" "$dest"
  printf '%s\n' "$dest"
}

# Delete .agent-backups/<timestamp> snapshot dirs older than N days (default 7).
# Age is parsed from the YYYYMMDD-HHMMSS directory name itself, not filesystem
# mtime — snapshot dir mtimes get touched after creation and don't reflect age.
# Only removes directories matching that naming pattern; leaves README.md and
# any other non-snapshot files untouched.
prune_backups() {
  retention_days="${1:-7}"
  [ -d "$BACKUP_ROOT" ] || return 0
  python3 - "$BACKUP_ROOT" "$retention_days" "$MAINT_LOG" <<'PY' || true
import sys, re, shutil
from pathlib import Path
from datetime import datetime, timedelta

root = Path(sys.argv[1])
retention_days = float(sys.argv[2])
log_path = Path(sys.argv[3])
cutoff = datetime.now() - timedelta(days=retention_days)
pattern = re.compile(r"^(\d{8})-(\d{6})$")

for entry in sorted(root.iterdir()):
    if not entry.is_dir():
        continue
    m = pattern.match(entry.name)
    if not m:
        continue
    try:
        created = datetime.strptime(entry.name, "%Y%m%d-%H%M%S")
    except ValueError:
        continue
    if created < cutoff:
        shutil.rmtree(entry, ignore_errors=True)
        with open(log_path, "a") as f:
            f.write(f"- Pruned backup snapshot older than {retention_days:g}d: {entry.name}\n")
PY
}

is_json_valid() {
  [ -f "$1" ] && python3 -m json.tool "$1" >/dev/null 2>&1
}

tool_path() {
  command -v "$1" 2>/dev/null || true
}
