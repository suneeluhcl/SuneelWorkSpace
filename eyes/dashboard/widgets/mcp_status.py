#!/usr/bin/env python3
import os
import json
import socket

MCP_STATE = "/Users/MAC/SuneelWorkSpace/nervous/mcp/server/state/mcp_state.json"
LAST_INDEX = "/Users/MAC/SuneelWorkSpace/nervous/mcp/server/state/last_index.json"

def get_mcp_status():
    status = {
        "server_status": "offline",
        "last_reindex": "",
        "total_resources": 0,
        "headroom_proxy": "offline"
    }
    
    # 1. Check if Headroom proxy is running on port 8787
    s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    s.settimeout(1.0)
    try:
        s.connect(("127.0.0.1", 8787))
        status["headroom_proxy"] = "online"
        s.close()
    except Exception:
        status["headroom_proxy"] = "offline"
        
    # 2. Read MCP server state
    if os.path.exists(MCP_STATE):
        try:
            with open(MCP_STATE, 'r', encoding='utf-8') as f:
                state_data = json.load(f)
            status["last_reindex"] = state_data.get("last_reindex", "")
            # Assume online if recently updated
            status["server_status"] = "online"
        except Exception:
            pass
            
    # 3. Read resource index count
    if os.path.exists(LAST_INDEX):
        try:
            with open(LAST_INDEX, 'r', encoding='utf-8') as f:
                index_data = json.load(f)
            status["total_resources"] = index_data.get("total_entries", 0)
        except Exception:
            pass
            
    return status

if __name__ == "__main__":
    print(json.dumps(get_mcp_status(), indent=2))
