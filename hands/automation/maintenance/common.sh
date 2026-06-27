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
LAUNCHD_WORKSPACE_PLIST="$ROOT/automation/launchd/$LAUNCHD_LABEL.plist"
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
    "$ROOT/automation/doctor" \
    "$ROOT/automation/repair" \
    "$ROOT/automation/maintenance" \
    "$ROOT/automation/launchd" \
    "$ROOT/automation/hooks" \
    "$ROOT/automation/reports" \
    "$ROOT/brain/memory/shared" \
    "$ROOT/brain/memory/memory" \
    "$ROOT/brain/memory/tasks" \
    "$ROOT/brain/memory/logs" \
    "$ROOT/brain/memory/state" \
    "$ROOT/brain/memory/templates" \
    "$ROOT/brain/memory/docs" \
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

is_json_valid() {
  [ -f "$1" ] && python3 -m json.tool "$1" >/dev/null 2>&1
}

tool_path() {
  command -v "$1" 2>/dev/null || true
}
