#!/usr/bin/env python3
import os
import re

GOALS_FILE = "/Users/MAC/SuneelWorkSpace/heart/goals/goals/active_goals.md"

def get_active_goals():
    if not os.path.exists(GOALS_FILE):
        return []
        
    with open(GOALS_FILE, 'r', encoding='utf-8') as f:
        content = f.read()
        
    goals = []
    # Match headers like "## [GOAL_ID] Title"
    pattern = re.compile(r"^##\s+\[([^\]]+)\]\s+(.*?)$", re.MULTILINE)
    matches = list(pattern.finditer(content))
    
    for idx, match in enumerate(matches):
        goal_id = match.group(1)
        title = match.group(2).strip()
        
        # Get start/end indices for parsing properties
        start_idx = match.end()
        end_idx = matches[idx + 1].start() if idx + 1 < len(matches) else len(content)
        block = content[start_idx:end_idx]
        
        goal = {
            "id": goal_id,
            "title": title,
            "description": "",
            "priority": "medium",
            "status": "active",
            "created_at": ""
        }
        
        # Parse fields
        for line in block.splitlines():
            line = line.strip()
            if line.startswith("- **description**:"):
                goal["description"] = line.replace("- **description**:", "").strip()
            elif line.startswith("- **priority**:"):
                goal["priority"] = line.replace("- **priority**:", "").strip()
            elif line.startswith("- **status**:"):
                goal["status"] = line.replace("- **status**:", "").strip()
            elif line.startswith("- **created_at**:"):
                goal["created_at"] = line.replace("- **created_at**:", "").strip()
                
        goals.append(goal)
        
    return goals

if __name__ == "__main__":
    import json
    print(json.dumps(get_active_goals(), indent=2))
