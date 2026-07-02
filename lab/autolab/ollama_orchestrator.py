"""
ollama_orchestrator.py
Master coordinator for all Ollama-powered engines.
Runs engines on intelligent schedules based on:
- Time of day (night = more aggressive)
- Workspace health score
- Last run time per engine
- Available Ollama models
Coordinates: repair, learning, code review, nerve healing, memory curation, security scan
"""

import asyncio
import json
import os
import subprocess
import urllib.request
from datetime import datetime, timezone, timedelta

OLLAMA_BASE = "http://localhost:11434"
ORCHESTRATOR_LOG = "blood/logs/ollama_orchestrator.jsonl"
STATE_PATH = "lab/autolab/orchestrator_state.json"

ENGINES = {
    "ollama_repair": {
        "command": "python3 lab/autolab/ollama_repair_engine.py",
        "interval_day_hours": 4,
        "interval_night_hours": 1,
        "priority": 1,
        "description": "Analyzes anomalies and applies SAFE fixes",
        "requires_model": "llama3.1",
    },
    "nerve_healer": {
        "command": "python3 nervous/nerve_healer.py --check",
        "interval_day_hours": 2,
        "interval_night_hours": 0.5,
        "priority": 2,
        "description": "Checks and heals broken nerve connections",
        "requires_model": "suneelworkspace",
    },
    "memory_curator": {
        "command": "python3 brain/memory/memory_curator.py",
        "interval_day_hours": 12,
        "interval_night_hours": 6,
        "priority": 3,
        "description": "Curates brain/memory/ files",
        "requires_model": "llama3.1",
    },
    "ollama_learn": {
        "command": "python3 lab/autolab/ollama_learning_engine.py",
        "interval_day_hours": 8,
        "interval_night_hours": 2,
        "priority": 4,
        "description": "Learns from nerve events and generates skills",
        "requires_model": "llama3.1",
    },
    "code_review": {
        "command": "python3 lab/autolab/code_review_engine.py",
        "interval_day_hours": 24,
        "interval_night_hours": 8,
        "priority": 5,
        "description": "Reviews Python files with codellama",
        "requires_model": "codellama",
    },
    "security_scan": {
        "command": "python3 lab/autolab/security_scanner.py",
        "interval_day_hours": 24,
        "interval_night_hours": 12,
        "priority": 6,
        "description": "Scans for security issues",
        "requires_model": None,
    },
    "experiment_skills": {
        "command": "python3 lab/autolab/experiment_skill_generator.py",
        "interval_day_hours": 6,
        "interval_night_hours": 2,
        "priority": 7,
        "description": "Generates skills from completed experiments",
        "requires_model": "suneelworkspace",
    },
    "suggestion_consumer": {
        "command": "python3 lab/autolab/suggestion_consumer.py",
        "interval_day_hours": 2,
        "interval_night_hours": 1,
        "priority": 2,
        "description": "Closes the output→action loop: converts suggestions into tasks",
        "requires_model": None,
    },
    "rebuild_context": {
        "command": "python3 dna/agents/hermes/ollama_models/build_modelfile.py --apply",
        "interval_day_hours": 168,
        "interval_night_hours": 168,
        "priority": 8,
        "description": "Rebuilds suneelworkspace Modelfile with fresh context (weekly)",
        "requires_model": None,
    },
}

NIGHT_HOURS = list(range(22, 24)) + list(range(0, 8))


def is_night_mode() -> bool:
    return datetime.now().hour in NIGHT_HOURS


def is_ollama_running() -> bool:
    try:
        urllib.request.urlopen(f"{OLLAMA_BASE}/api/tags", timeout=3)
        return True
    except Exception:
        return False


def get_available_models() -> list:
    try:
        with urllib.request.urlopen(f"{OLLAMA_BASE}/api/tags", timeout=5) as r:
            data = json.loads(r.read())
            return [m["name"].split(":")[0] for m in data.get("models", [])]
    except Exception:
        return []


def load_state() -> dict:
    if os.path.exists(STATE_PATH):
        try:
            return json.load(open(STATE_PATH))
        except Exception:
            pass
    return {"last_run": {}}


def save_state(state: dict):
    os.makedirs(os.path.dirname(STATE_PATH), exist_ok=True)
    json.dump(state, open(STATE_PATH, "w"), indent=2)


def should_run_engine(engine_name: str, state: dict) -> bool:
    engine = ENGINES[engine_name]
    night = is_night_mode()
    interval_hours = engine["interval_night_hours"] if night else engine["interval_day_hours"]

    last_run_str = state.get("last_run", {}).get(engine_name)
    if not last_run_str:
        return True

    try:
        last_run = datetime.fromisoformat(last_run_str)
        if last_run.tzinfo is None:
            last_run = last_run.replace(tzinfo=timezone.utc)
        elapsed_hours = (datetime.now(timezone.utc) - last_run).total_seconds() / 3600
        return elapsed_hours >= interval_hours
    except Exception:
        return True


def is_model_available(model_name: str, available_models: list) -> bool:
    if model_name is None:
        return True
    return any(model_name in m for m in available_models)


async def run_engine(engine_name: str) -> bool:
    engine = ENGINES[engine_name]
    print(f"  Running: {engine_name} — {engine['description']}")

    try:
        proc = await asyncio.create_subprocess_shell(
            engine["command"],
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.STDOUT,
            cwd=os.path.expanduser("~/SuneelWorkSpace")
        )
        stdout, _ = await asyncio.wait_for(proc.communicate(), timeout=600)
        success = proc.returncode == 0

        entry = {
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "engine": engine_name,
            "success": success,
            "night_mode": is_night_mode(),
            "output_lines": len(stdout.decode(errors="ignore").split("\n")) if stdout else 0,
        }
        os.makedirs(os.path.dirname(ORCHESTRATOR_LOG), exist_ok=True)
        with open(ORCHESTRATOR_LOG, "a") as f:
            f.write(json.dumps(entry) + "\n")

        print(f"  {'OK' if success else 'WARN'} {engine_name} complete")
        return success

    except asyncio.TimeoutError:
        print(f"  {engine_name} timed out after 10 minutes")
        return False
    except Exception as e:
        print(f"  {engine_name} error: {e}")
        return False


async def orchestration_loop():
    print(f"Ollama Orchestration Brain started")
    print(f"   Engines: {len(ENGINES)}")
    print(f"   Tick interval: 5 minutes")

    while True:
        night = is_night_mode()
        mode_str = "NIGHT" if night else "DAY"
        print(f"\nOrchestration tick — {datetime.now().strftime('%H:%M:%S')} [{mode_str}]")

        if not is_ollama_running():
            print("  Ollama not running — attempting start...")
            subprocess.Popen(["ollama", "serve"],
                           stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
            await asyncio.sleep(5)

        available_models = get_available_models()
        state = load_state()

        engines_to_run = []
        for engine_name, engine in sorted(ENGINES.items(), key=lambda x: x[1]["priority"]):
            if not should_run_engine(engine_name, state):
                continue
            required_model = engine.get("requires_model")
            if not is_model_available(required_model, available_models):
                print(f"  Skipping {engine_name} — model {required_model} not available")
                continue
            engines_to_run.append(engine_name)

        if not engines_to_run:
            print(f"  All engines up to date — nothing to run")
        else:
            print(f"  Running {len(engines_to_run)} engines: {engines_to_run}")
            for engine_name in engines_to_run:
                success = await run_engine(engine_name)
                if success:
                    state.setdefault("last_run", {})[engine_name] = \
                        datetime.now(timezone.utc).isoformat()
                    save_state(state)
                await asyncio.sleep(2)

        await asyncio.sleep(300)


if __name__ == "__main__":
    import sys
    if "--status" in sys.argv:
        state = load_state()
        available = get_available_models()
        print(f"Ollama running: {is_ollama_running()}")
        print(f"Available models: {available}")
        print(f"Mode: {'Night' if is_night_mode() else 'Day'}")
        print(f"\nEngine status:")
        for name, engine in ENGINES.items():
            last = state.get("last_run", {}).get(name, "never")
            should = should_run_engine(name, state)
            model_ok = is_model_available(engine.get("requires_model"), available)
            status = "DUE" if should else "OK"
            model_status = "OK" if model_ok else "NO MODEL"
            print(f"  [{status}] {name} | model:{model_status} | last:{last}")
    else:
        asyncio.run(orchestration_loop())
