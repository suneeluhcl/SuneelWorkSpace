#!/usr/bin/env python3
import os
import json
import re

SESSION_LOG = "/Users/MAC/SuneelWorkSpace/blood/logs/SESSION_LOG.md"
CURRENT_STATE = "/Users/MAC/SuneelWorkSpace/spine/state/CURRENT_STATE.json"

def get_agent_activity():
    activity = {
        "active_agent": "Unknown",
        "session_id": "None",
        "last_summary": "No logs recorded yet.",
        "last_update": "",
        "status": "idle"
    }
    
    # Read current state
    if os.path.exists(CURRENT_STATE):
        try:
            with open(CURRENT_STATE, 'r', encoding='utf-8') as f:
                state_data = json.load(f)
            activity["active_agent"] = state_data.get("active_agent", "Unknown")
            activity["session_id"] = state_data.get("active_session_id", "None") or "None"
            activity["last_update"] = state_data.get("last_activity_timestamp", "")
            activity["status"] = state_data.get("status", "idle")
        except Exception:
            pass
            
    # Read last log entry from SESSION_LOG.md
    if os.path.exists(SESSION_LOG):
        try:
            with open(SESSION_LOG, 'r', encoding='utf-8') as f:
                lines = f.readlines()
            
            # Search from bottom to top for log entries starting with "- "
            for line in reversed(lines):
                line_str = line.strip()
                if line_str.startswith("- "):
                    activity["last_summary"] = line_str[2:]
                    break
        except Exception:
            pass
            
    return activity

if __name__ == "__main__":
    print(json.dumps(get_agent_activity(), indent=2))
