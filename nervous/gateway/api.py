#!/usr/bin/env python3
"""Agent API Gateway — FastAPI on port 8888.
Exposes workspace capabilities as a local REST API.
"""
import os
import sys
from pathlib import Path

WORKSPACE = Path(os.environ.get('WORKSPACE', Path.home() / 'SuneelWorkSpace'))
sys.path.insert(0, str(WORKSPACE / 'gateway'))

try:
    from fastapi import FastAPI, HTTPException, Depends, Query
    from fastapi.middleware.cors import CORSMiddleware
    from fastapi.responses import JSONResponse
    from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
    import uvicorn
except ImportError:
    print("ERROR: FastAPI/uvicorn not installed.")
    print("Run: pip3 install fastapi uvicorn --break-system-packages")
    sys.exit(1)

from auth import get_or_create_token, verify_token
import json
import subprocess

app = FastAPI(
    title="SuneelWorkSpace Agent Gateway",
    description="Local REST API for workspace capabilities",
    version="1.0.0"
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:*", "http://127.0.0.1:*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

security = HTTPBearer()


def auth_check(credentials: HTTPAuthorizationCredentials = Depends(security)):
    if not verify_token(credentials.credentials):
        raise HTTPException(status_code=401, detail="Invalid token")
    return credentials.credentials


def read_file_safe(path: Path) -> str:
    try:
        return path.read_text()
    except Exception as e:
        return f"Error reading file: {e}"


# ─── Health ────────────────────────────────────────────────────────────────

@app.get("/health")
def health(_token: str = Depends(auth_check)):
    health_file = WORKSPACE / 'spine/state/WORKSPACE_HEALTH.json'
    if health_file.exists():
        with open(health_file) as f:
            data = json.load(f)
    else:
        data = {"status": "unknown"}
    return {"gateway": "ok", "workspace": data}


# ─── Memory ────────────────────────────────────────────────────────────────

@app.get("/memory/facts")
def memory_facts(_token: str = Depends(auth_check)):
    content = read_file_safe(WORKSPACE / 'brain/memory/MEMORY.md')
    return {"content": content}


@app.get("/memory/decisions")
def memory_decisions(_token: str = Depends(auth_check)):
    content = read_file_safe(WORKSPACE / 'brain/memory/DECISIONS.md')
    return {"content": content}


@app.get("/memory/search")
def memory_search(
    q: str = Query(..., description="Search query"),
    k: int = Query(5, description="Number of results"),
    _token: str = Depends(auth_check)
):
    try:
        result = subprocess.run(
            ["python3", str(WORKSPACE / 'brain/memory/vector/semantic_search.py'), q, str(k)],
            capture_output=True, text=True, timeout=30
        )
        return {"query": q, "results": result.stdout, "error": result.stderr if result.returncode != 0 else None}
    except subprocess.TimeoutExpired:
        return {"query": q, "results": "", "error": "Search timed out"}
    except FileNotFoundError:
        return {"query": q, "results": "", "error": "Semantic search not available"}


# ─── Goals ─────────────────────────────────────────────────────────────────

@app.get("/goals/active")
def goals_active(_token: str = Depends(auth_check)):
    goals_file = WORKSPACE / 'brain/memory/goals/active_goals.md'
    if not goals_file.exists():
        goals_file = WORKSPACE / 'heart/tasks/ACTIVE_TASKS.md'
    content = read_file_safe(goals_file)
    return {"content": content}


@app.post("/goals/create")
def goals_create(description: str, confirm: bool = False, _token: str = Depends(auth_check)):
    if not confirm:
        return {"status": "preview", "message": f"Would create goal: {description}", "confirm_with": "?confirm=true"}
    goals_file = WORKSPACE / 'brain/memory/goals/active_goals.md'
    goals_file.parent.mkdir(parents=True, exist_ok=True)
    from datetime import datetime
    entry = f"\n## {datetime.now():%Y-%m-%d} — {description}\n- Status: pending\n"
    with open(goals_file, 'a') as f:
        f.write(entry)
    return {"status": "created", "description": description}


# ─── Workflows ─────────────────────────────────────────────────────────────

@app.get("/workflows/list")
def workflows_list(_token: str = Depends(auth_check)):
    wf_dir = WORKSPACE / 'brain/workflows/generated'
    if not wf_dir.exists():
        return {"workflows": []}
    workflows = [f.name for f in wf_dir.glob('*.json') if f.is_file()]
    return {"workflows": workflows, "count": len(workflows)}


@app.post("/workflows/execute")
def workflows_execute(name: str, _token: str = Depends(auth_check)):
    wf_file = WORKSPACE / 'brain/workflows/generated' / f"{name}.json"
    if not wf_file.exists():
        raise HTTPException(status_code=404, detail=f"Workflow '{name}' not found")
    with open(wf_file) as f:
        data = json.load(f)
    level = data.get('execution_level', 'CONTROLLED')
    if level == 'RESTRICTED':
        raise HTTPException(status_code=403, detail="RESTRICTED workflows cannot be executed via API")
    return {"status": "queued", "workflow": name, "level": level, "note": "Manual execution required for CONTROLLED workflows"}


# ─── Anticipation ──────────────────────────────────────────────────────────

@app.get("/brain/anticipation/suggestions")
def anticipation_suggestions(_token: str = Depends(auth_check)):
    suggestions_file = WORKSPACE / 'brain/anticipation/action_suggestions.md'
    content = read_file_safe(suggestions_file)
    return {"content": content}


@app.post("/brain/anticipation/record")
def anticipation_record(command: str, _token: str = Depends(auth_check)):
    log_file = WORKSPACE / 'blood/logs/command_history.log'
    from datetime import datetime
    with open(log_file, 'a') as f:
        f.write(f"{datetime.now().isoformat()} {command}\n")
    return {"status": "recorded", "command": command}


# ─── Research ──────────────────────────────────────────────────────────────

@app.get("/research/decisions")
def research_decisions(_token: str = Depends(auth_check)):
    decisions_dir = WORKSPACE / 'brain/memory/memory'
    files = [f.name for f in decisions_dir.glob('*.md') if f.is_file()]
    return {"files": files}


@app.post("/research/arxiv")
def research_arxiv(query: str, _token: str = Depends(auth_check)):
    result = subprocess.run(
        ["bash", str(WORKSPACE / 'bin/arxiv-mcp'), query],
        capture_output=True, text=True, timeout=30, input=""
    )
    return {"query": query, "output": result.stdout, "error": result.stderr if result.returncode != 0 else None}


if __name__ == '__main__':
    token = get_or_create_token()
    print(f"\n🚀 Agent API Gateway starting on http://localhost:8888")
    print(f"   Token: {token[:8]}... (run: gateway-token for full)")
    print(f"   Docs:  http://localhost:8888/docs\n")
    uvicorn.run(app, host="127.0.0.1", port=8888, log_level="warning")
