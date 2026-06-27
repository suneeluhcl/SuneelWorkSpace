#!/usr/bin/env python3
import os
import json
import re

SUGGESTIONS_FILE = "/Users/MAC/SuneelWorkSpace/brain/anticipation/action_suggestions.md"

def get_suggestions():
    if not os.path.exists(SUGGESTIONS_FILE):
        return []
        
    with open(SUGGESTIONS_FILE, 'r', encoding='utf-8') as f:
        content = f.read()
        
    suggestions = []
    
    # Match patterns like:
    # 1. [HIGH | CONTROLLED | 0.95]
    #    Based on repeated workflow: run daily-evolve
    pattern = re.compile(r"^\d+\.\s+\[([^\]]+)\]\s*\n\s*(.*?)(?=\n\s*\d+\.\s+\[|\n\n|\Z)", re.DOTALL | re.MULTILINE)
    matches = pattern.findall(content)
    
    for match in matches:
        meta_str = match[0]
        desc = match[1].strip()
        
        # Split meta details
        parts = [p.strip() for p in meta_str.split("|")]
        priority = parts[0] if len(parts) > 0 else "medium"
        tier = parts[1] if len(parts) > 1 else "SAFE"
        score = parts[2] if len(parts) > 2 else "0.5"
        
        # Clean desc lines
        desc_lines = [l.strip() for l in desc.splitlines() if l.strip() and not l.strip().startswith("→")]
        desc_clean = " ".join(desc_lines)
        
        suggestions.append({
            "priority": priority,
            "tier": tier,
            "score": score,
            "description": desc_clean
        })
        
    return suggestions

if __name__ == "__main__":
    print(json.dumps(get_suggestions(), indent=2))
