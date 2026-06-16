"""
Phoenix Tracer
Pushes nightly eval traces to the local Arize Phoenix instance (:6006).
Phoenix is already running via Docker. This module uploads the night's
JSONL results as a Phoenix dataset for experiment tracking.

Does NOT require any external API keys — Phoenix is local-only.
"""

import json
from datetime import datetime
from pathlib import Path
from typing import Optional


PHOENIX_BASE = "http://localhost:6006"


def _check_phoenix(base: str = PHOENIX_BASE) -> bool:
    import urllib.request
    try:
        urllib.request.urlopen(f"{base}/healthz", timeout=5)
        return True
    except Exception:
        try:
            # Phoenix may not have /healthz — try root
            urllib.request.urlopen(base, timeout=5)
            return True
        except Exception:
            return False


def _phoenix_request(method: str, path: str, body: Optional[dict] = None, base: str = PHOENIX_BASE):
    import urllib.request
    import json as _json
    url = f"{base}{path}"
    data = _json.dumps(body).encode() if body else None
    req = urllib.request.Request(
        url,
        data=data,
        headers={"Content-Type": "application/json"},
        method=method,
    )
    with urllib.request.urlopen(req, timeout=30) as resp:
        return _json.loads(resp.read())


def push_to_phoenix(
    config: dict,
    nlu_results_path: str,
    session_dir: Path,
) -> dict:
    phoenix_base = config.get("phoenix_base", PHOENIX_BASE)
    session_name = session_dir.name

    if not _check_phoenix(phoenix_base):
        return {"skipped": True, "reason": "Phoenix not reachable at " + phoenix_base}

    results_path = Path(nlu_results_path)
    if not results_path.exists():
        return {"skipped": True, "reason": "nlu_results.jsonl not found"}

    # Load results
    rows = []
    with open(results_path) as f:
        for line in f:
            try:
                rows.append(json.loads(line))
            except json.JSONDecodeError:
                continue

    if not rows:
        return {"pushed": 0, "reason": "empty results"}

    # Convert to Phoenix dataset format
    # Phoenix ingest API: POST /v1/datasets or use the spans API
    dataset_name = f"adwi-nightly-{session_name}"

    try:
        # Try Phoenix v1 dataset API
        dataset_payload = {
            "name": dataset_name,
            "description": f"Adwi NLU nightly eval — session {session_name}",
            "examples": [
                {
                    "input": {"prompt": r.get("prompt", "")},
                    "output": {
                        "intent": r.get("predicted_intent", r.get("got", "")),
                        "confidence": r.get("confidence", 0.0),
                    },
                    "metadata": {
                        "expected_intent": r.get("expected_intent", r.get("expected", "")),
                        "result": r.get("result", "fail"),
                        "latency_ms": r.get("latency_ms", 0),
                        "category": r.get("category", "unknown"),
                        "scenario_type": r.get("scenario_type", "unknown"),
                    },
                }
                for r in rows[:500]  # Phoenix UI handles up to 500 well
            ],
        }

        response = _phoenix_request("POST", "/v1/datasets", dataset_payload, phoenix_base)
        dataset_id = response.get("data", {}).get("id") or response.get("id")

        result = {
            "pushed": len(dataset_payload["examples"]),
            "dataset_name": dataset_name,
            "dataset_id": dataset_id,
            "phoenix_url": f"{phoenix_base}/datasets/{dataset_id}" if dataset_id else phoenix_base,
        }
    except Exception as e:
        # Fallback: write a Phoenix-compatible JSONL for manual upload
        phoenix_jsonl = session_dir / "phoenix_upload.jsonl"
        with open(phoenix_jsonl, "w") as f:
            for r in rows:
                record = {
                    "input": r.get("prompt", ""),
                    "output": r.get("predicted_intent", r.get("got", "")),
                    "expected": r.get("expected_intent", r.get("expected", "")),
                    "score": 1.0 if r.get("result") == "pass" else 0.0,
                    "metadata": {
                        "latency_ms": r.get("latency_ms", 0),
                        "confidence": r.get("confidence", 0.0),
                        "category": r.get("category", ""),
                        "session": session_name,
                    },
                }
                f.write(json.dumps(record) + "\n")

        result = {
            "pushed": 0,
            "fallback_file": str(phoenix_jsonl),
            "note": f"Phoenix API unavailable ({e}). File ready for manual import at {phoenix_base}.",
        }

    (session_dir / "phoenix_trace.json").write_text(json.dumps(result, indent=2))
    return result
