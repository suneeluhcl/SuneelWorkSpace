#!/usr/bin/env python3
import os
import json
import chromadb

WORKSPACE_HEALTH = "/Users/MAC/SuneelWorkSpace/spine/state/WORKSPACE_HEALTH.json"
CHROMA_DIR = "/Users/MAC/SuneelWorkSpace/brain/memory/vector/chroma_store"
COLLECTION_NAME = "workspace_memory"

def get_memory_health():
    stats = {
        "status": "unknown",
        "total_errors": 0,
        "total_warnings": 0,
        "vector_count": 0,
        "last_checked": ""
    }
    
    # Read workspace health
    if os.path.exists(WORKSPACE_HEALTH):
        try:
            with open(WORKSPACE_HEALTH, 'r', encoding='utf-8') as f:
                health_data = json.load(f)
            stats["status"] = health_data.get("status", "unknown")
            stats["total_errors"] = health_data.get("error_count", 0)
            stats["total_warnings"] = health_data.get("warning_count", 0)
            stats["last_checked"] = health_data.get("checked_at", "")
        except Exception:
            pass
            
    # Read Chroma DB count
    if os.path.exists(CHROMA_DIR):
        try:
            client = chromadb.PersistentClient(path=CHROMA_DIR)
            collection = client.get_collection(name=COLLECTION_NAME)
            stats["vector_count"] = collection.count()
        except Exception:
            pass
            
    return stats

if __name__ == "__main__":
    print(json.dumps(get_memory_health(), indent=2))
