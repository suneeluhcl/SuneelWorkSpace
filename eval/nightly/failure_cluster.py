"""
Failure Clustering
Groups tonight's failures by semantic similarity using nomic-embed-text via Ollama.
Falls back to keyword-based clustering if embeddings fail.
"""

import json
import math
import random
from collections import defaultdict
from pathlib import Path
from typing import Optional

REPO_ROOT = Path(__file__).resolve().parent.parent.parent


def _embed(text: str, ollama_base: str = "http://localhost:11434") -> Optional[list[float]]:
    import urllib.request
    import json as _json
    try:
        payload = _json.dumps({"model": "nomic-embed-text", "prompt": text}).encode()
        req = urllib.request.Request(
            f"{ollama_base}/api/embeddings",
            data=payload,
            headers={"Content-Type": "application/json"},
        )
        with urllib.request.urlopen(req, timeout=15) as resp:
            return _json.loads(resp.read()).get("embedding")
    except Exception:
        return None


def _cosine(a: list[float], b: list[float]) -> float:
    dot = sum(x * y for x, y in zip(a, b))
    norm_a = math.sqrt(sum(x * x for x in a))
    norm_b = math.sqrt(sum(x * x for x in b))
    if norm_a == 0 or norm_b == 0:
        return 0.0
    return dot / (norm_a * norm_b)


def _kmeans_cluster(
    items: list[dict],
    embeddings: list[list[float]],
    k: int,
    iterations: int = 10,
) -> list[int]:
    """Simple k-means clustering on embeddings."""
    if len(items) <= k:
        return list(range(len(items)))

    rng = random.Random(42)
    # Initialise centroids
    centroid_indices = rng.sample(range(len(embeddings)), k)
    centroids = [embeddings[i][:] for i in centroid_indices]

    assignments = [0] * len(embeddings)
    for _ in range(iterations):
        # Assign
        for i, emb in enumerate(embeddings):
            best_k = max(range(k), key=lambda ki: _cosine(emb, centroids[ki]))
            assignments[i] = best_k
        # Update centroids
        new_centroids = [[0.0] * len(centroids[0]) for _ in range(k)]
        counts = [0] * k
        for i, emb in enumerate(embeddings):
            ki = assignments[i]
            counts[ki] += 1
            for d in range(len(emb)):
                new_centroids[ki][d] += emb[d]
        for ki in range(k):
            if counts[ki] > 0:
                centroids[ki] = [v / counts[ki] for v in new_centroids[ki]]
    return assignments


def _keyword_cluster(failures: list[dict]) -> list[int]:
    """Fallback: group by expected_intent."""
    intent_to_id: dict[str, int] = {}
    assignments = []
    for row in failures:
        intent = row.get("expected_intent", row.get("expected", "unknown"))
        if intent not in intent_to_id:
            intent_to_id[intent] = len(intent_to_id)
        assignments.append(intent_to_id[intent])
    return assignments


def _label_cluster(failures_in_cluster: list[dict]) -> str:
    """Generate a short label for a cluster."""
    intents = [r.get("expected_intent", r.get("expected", "?")) for r in failures_in_cluster]
    predicted = [r.get("predicted_intent", r.get("got", "?")) for r in failures_in_cluster]

    # Most common expected intent
    from collections import Counter
    top_expected = Counter(intents).most_common(1)[0][0]
    top_predicted = Counter(predicted).most_common(1)[0][0]

    if top_expected == top_predicted:
        return f"{top_expected} (internal confusion)"
    return f"{top_expected} → {top_predicted}"


def cluster_failures(
    config: dict,
    nlu_results_path: str,
    session_dir_str: str,
) -> dict:
    session_dir = Path(session_dir_str)
    ollama_base = config.get("ollama_base", "http://localhost:11434")
    k = config.get("cluster_k", 8)

    # Load failures
    failures = []
    results_path = Path(nlu_results_path)
    if not results_path.exists():
        return {"error": "results file not found"}

    with open(results_path) as f:
        for line in f:
            try:
                row = json.loads(line)
                if row.get("result") != "pass":
                    failures.append(row)
            except json.JSONDecodeError:
                continue

    if not failures:
        return {"num_clusters": 0, "failures": 0}

    # Try embedding-based clustering
    embeddings = []
    embed_failed = False
    for row in failures[:200]:  # cap for speed
        emb = _embed(row.get("prompt", ""), ollama_base)
        if emb is None:
            embed_failed = True
            break
        embeddings.append(emb)

    if embed_failed or len(embeddings) < len(failures[:200]):
        assignments = _keyword_cluster(failures[:200])
        method = "keyword"
    else:
        actual_k = min(k, len(failures))
        assignments = _kmeans_cluster(failures[:200], embeddings, actual_k)
        method = "embedding"

    # Group
    cluster_map: dict[int, list[dict]] = defaultdict(list)
    for row, cluster_id in zip(failures[:200], assignments):
        cluster_map[cluster_id].append(row)

    clusters = []
    for cluster_id, rows in sorted(cluster_map.items(), key=lambda x: -len(x[1])):
        label = _label_cluster(rows)
        sample_prompts = [r.get("prompt", "") for r in rows[:5]]
        mis_routes = defaultdict(int)
        for r in rows:
            got = r.get("predicted_intent", r.get("got", "?"))
            expected = r.get("expected_intent", r.get("expected", "?"))
            mis_routes[f"{expected} → {got}"] += 1
        clusters.append({
            "cluster_id": cluster_id,
            "label": label,
            "size": len(rows),
            "sample_prompts": sample_prompts,
            "top_misroutes": dict(sorted(mis_routes.items(), key=lambda x: -x[1])[:5]),
        })

    # Derive repair priorities
    repair_hints = []
    for c in clusters[:5]:  # top 5 clusters
        label = c["label"]
        top_mr = list(c["top_misroutes"].items())[:1]
        if top_mr:
            expected, got = top_mr[0][0].split(" → ")
            repair_hints.append({
                "cluster_label": label,
                "expected": expected,
                "most_confused_with": got,
                "affected_count": c["size"],
                "suggested_action": _suggest_repair(expected, got),
            })

    result = {
        "num_clusters": len(clusters),
        "failures": len(failures),
        "method": method,
        "clusters": clusters,
        "repair_hints": repair_hints,
    }

    (session_dir / "failure_clusters.json").write_text(json.dumps(result, indent=2))
    return result


def _suggest_repair(expected: str, got: str) -> str:
    """Generate a human-readable repair suggestion."""
    if got == "chat":
        return f"Add regex anchor for '{expected}' before fallback-to-chat path"
    if got == "file_search":
        return f"Add synonym patterns for '{expected}' BEFORE file_search in _REGEX_INTENTS"
    if got == "doctor":
        return f"Add generic '{expected}' patterns (doctor fires too broadly)"
    if got == "status":
        return f"Tighten status regex; add '{expected}' patterns that beat status"
    if got == "__none__":
        return f"'{expected}' intent is being over-blocked — check if path is on safe list"
    return f"Review _REGEX_INTENTS ordering: '{expected}' lost to '{got}'"
