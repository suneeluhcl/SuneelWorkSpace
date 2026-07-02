#!/usr/bin/env python3
"""Auto-generated orchestrated MCP workflow wrapper for: Code Improvement Workflow"""

import sys
import os
import pathlib

ROOT = pathlib.Path("/Users/MAC/SuneelWorkSpace")
sys.path.append(str(ROOT / "hands" / "scripts"))

try:
    from mcp_orchestrator import parse_and_run_md_workflow
except ImportError:
    # Fallback to local import
    sys.path.append(os.path.dirname(os.path.abspath(__file__)))
    from mcp_orchestrator import parse_and_run_md_workflow

def main():
    source_note = pathlib.Path("/Users/MAC/SuneelWorkSpace/brain/workflows/code_improvement_workflow.md")
    print(f"🎬 Starting Orchestrated MCP Pipeline Workflow: Code Improvement Workflow")
    success = parse_and_run_md_workflow(source_note)
    if success:
        sys.exit(0)
    else:
        sys.exit(1)

if __name__ == "__main__":
    main()
