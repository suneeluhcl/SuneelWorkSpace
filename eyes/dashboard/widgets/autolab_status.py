#!/usr/bin/env python3
import os
import json
import re

REPORT_FILE = "/Users/MAC/SuneelWorkSpace/lab/autolab/reports/latest_report.md"

def get_autolab_status():
    status = {
        "score": "unknown",
        "gates": "unknown",
        "generated": "",
        "top_opportunity": "None"
    }
    
    if os.path.exists(REPORT_FILE):
        try:
            with open(REPORT_FILE, 'r', encoding='utf-8') as f:
                content = f.read()
                
            score_match = re.search(r"Score:\s*([^\n]+)", content)
            if score_match:
                status["score"] = score_match.group(1).strip()
                
            gates_match = re.search(r"Safety gates:\s*([^\n]+)", content)
            if gates_match:
                status["gates"] = gates_match.group(1).strip()
                
            gen_match = re.search(r"Generated:\s*([^\n]+)", content)
            if gen_match:
                status["generated"] = gen_match.group(1).strip()
        except Exception:
            pass
            
    return status

if __name__ == "__main__":
    print(json.dumps(get_autolab_status(), indent=2))
