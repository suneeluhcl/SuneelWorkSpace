"""
nerve_healer.py
Monitors all nerve connections between organs.
When a connection breaks, uses Ollama to diagnose and repair it.
Runs continuously as a background daemon.
"""

import asyncio
import json
import os
import re
import urllib.request
from datetime import datetime, timezone

REGISTRY_PATH = "nervous/nerve_registry.json"
HEALER_LOG = "blood/logs/nerve_healer.jsonl"
HEAL_INTERVAL_SECONDS = 1800  # Check every 30 minutes
OLLAMA_BASE = "http://localhost:11434"

ORGANS = ["brain", "heart", "eyes", "ears", "nervous", "skeleton",
          "blood", "hands", "mouth", "dna", "lab", "spine"]


def ask_ollama(prompt: str, timeout: int = 60) -> str:
    payload = json.dumps({
        "model": "suneelworkspace",
        "prompt": prompt,
        "stream": False,
        "options": {"temperature": 0.1, "num_ctx": 2048}
    }).encode()
    req = urllib.request.Request(
        f"{OLLAMA_BASE}/api/generate",
        data=payload,
        headers={"Content-Type": "application/json"},
        method="POST"
    )
    try:
        with urllib.request.urlopen(req, timeout=timeout) as r:
            return json.loads(r.read()).get("response", "").strip()
    except Exception:
        return ""


def check_all_connections() -> list:
    """Check all nerve connections and return list of broken ones."""
    if not os.path.exists(REGISTRY_PATH):
        return []

    registry = json.load(open(REGISTRY_PATH))
    broken = []

    for organ, config in registry.get("organs", {}).items():
        # Check organ path exists
        organ_path = config.get("path", f"{organ}/")
        if not os.path.exists(organ_path):
            broken.append({
                "organ": organ,
                "type": "organ_missing",
                "path": organ_path,
                "severity": "critical",
            })
            continue

        # Check nerve.json exists
        nerve_path = f"{organ}/nerve.json"
        if not os.path.exists(nerve_path):
            broken.append({
                "organ": organ,
                "type": "nerve_json_missing",
                "path": nerve_path,
                "severity": "high",
            })

        # Check provides paths
        for key, path in config.get("provides", {}).items():
            if path and not path.startswith("http") and not os.path.exists(path):
                broken.append({
                    "organ": organ,
                    "type": "broken_provides",
                    "key": key,
                    "path": path,
                    "severity": "medium",
                })

        # Check needs paths
        for key, path in config.get("needs", {}).items():
            if path and not path.startswith("http") and not os.path.exists(path):
                broken.append({
                    "organ": organ,
                    "type": "broken_needs",
                    "key": key,
                    "path": path,
                    "severity": "low",
                })

    return broken


def diagnose_and_heal(broken_connection: dict) -> bool:
    """Use Ollama to diagnose a broken connection and apply fix."""
    organ = broken_connection.get("organ", "?")
    conn_type = broken_connection.get("type", "?")
    path = broken_connection.get("path", "?")
    key = broken_connection.get("key", "")

    prompt = f"""A nerve connection in SuneelWorkSpace is broken and needs repair.

Organ: {organ}
Connection type: {conn_type}
Broken path: {path}
Key: {key}

SuneelWorkSpace has 12 organs: brain, heart, eyes, ears, nervous, skeleton, blood, hands, mouth, dna, lab, spine

Diagnose this broken connection and provide the fix.

Respond in JSON only:
{{
  "diagnosis": "why this is broken",
  "fix_type": "create_dir|create_file|update_path|create_symlink|skip",
  "fix_command": "exact shell command to fix it",
  "is_safe": true,
  "explanation": "what the fix does"
}}"""

    response = ask_ollama(prompt)
    if not response:
        return False

    try:
        match = re.search(r'\{.*\}', response, re.DOTALL)
        if not match:
            return False

        fix = json.loads(match.group())

        if not fix.get("is_safe", False):
            _log_heal(organ, conn_type, path, "skipped_unsafe", fix.get("explanation", ""))
            return False

        fix_type = fix.get("fix_type", "skip")

        if fix_type == "skip" or not fix_type:
            return False

        if fix_type == "create_dir":
            os.makedirs(path, exist_ok=True)
            _log_heal(organ, conn_type, path, "healed_mkdir", fix.get("explanation", ""))
            print(f"  Healed: created directory {path}")
            return True

        elif fix_type == "create_file":
            if path.endswith(".json"):
                os.makedirs(os.path.dirname(path) or ".", exist_ok=True)
                json.dump({}, open(path, "w"), indent=2)
                _log_heal(organ, conn_type, path, "healed_create_json", fix.get("explanation", ""))
                print(f"  Healed: created {path}")
                return True
            elif path.endswith(".md"):
                os.makedirs(os.path.dirname(path) or ".", exist_ok=True)
                open(path, "w").write(f"# {os.path.basename(path)}\n\n*Created by nerve healer*\n")
                _log_heal(organ, conn_type, path, "healed_create_md", fix.get("explanation", ""))
                print(f"  Healed: created {path}")
                return True

        elif fix_type == "update_path":
            if os.path.exists(REGISTRY_PATH):
                registry = json.load(open(REGISTRY_PATH))
                filename = os.path.basename(path)
                actual = None
                for root, dirs, files in os.walk("."):
                    dirs[:] = [d for d in dirs if not d.startswith(".") and d != "spine/backups"]
                    if filename in files:
                        actual = os.path.join(root, filename)
                        break
                if actual:
                    organ_config = registry.get("organs", {}).get(organ, {})
                    if key and key in organ_config.get("provides", {}):
                        registry["organs"][organ]["provides"][key] = actual
                    elif key and key in organ_config.get("needs", {}):
                        registry["organs"][organ]["needs"][key] = actual
                    json.dump(registry, open(REGISTRY_PATH, "w"), indent=2)
                    _log_heal(organ, conn_type, path, "healed_path_update", f"Updated to {actual}")
                    print(f"  Healed: updated path {path} -> {actual}")
                    return True

    except Exception as e:
        _log_heal(organ, conn_type, path, "heal_failed", str(e))

    return False


def _log_heal(organ: str, conn_type: str, path: str, outcome: str, detail: str):
    entry = {
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "organ": organ,
        "connection_type": conn_type,
        "path": path,
        "outcome": outcome,
        "detail": detail,
    }
    os.makedirs(os.path.dirname(HEALER_LOG), exist_ok=True)
    with open(HEALER_LOG, "a") as f:
        f.write(json.dumps(entry) + "\n")


async def healer_loop():
    """Main nerve healer loop."""
    print(f"Nerve Healer started — checking every {HEAL_INTERVAL_SECONDS//60} minutes")

    while True:
        print(f"\nNerve health check — {datetime.now().strftime('%H:%M:%S')}")

        broken = check_all_connections()
        if not broken:
            print(f"  All nerve connections healthy")
        else:
            print(f"  Found {len(broken)} broken connections")
            healed = 0
            for conn in broken:
                print(f"  Healing: {conn['organ']} {conn['type']} — {conn['path']}")
                if diagnose_and_heal(conn):
                    healed += 1
            print(f"  Healed: {healed}/{len(broken)}")

        await asyncio.sleep(HEAL_INTERVAL_SECONDS)


if __name__ == "__main__":
    import sys
    if "--check" in sys.argv:
        broken = check_all_connections()
        print(f"Broken connections: {len(broken)}")
        for b in broken:
            print(f"  [{b['severity']}] {b['organ']}: {b['type']} — {b['path']}")
    else:
        asyncio.run(healer_loop())
