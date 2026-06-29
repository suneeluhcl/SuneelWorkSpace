#!/usr/bin/env python3
"""
lab/autolab/ollama_reasoning_sidecar.py
Lightweight context-cache sidecar on port 11435.

Pre-loads identity profiles, decisions, and system rules into memory.
Provides a REST API for fast workspace-aware queries, avoiding Ollama
bootstrap delays on repeated calls from shell utilities and scripts.

Endpoints:
    GET  /context        → cached workspace context (JSON)
    POST /query          → {prompt, model?, task_type?} → {response}
    POST /invalidate     → clear context cache
    GET  /health         → sidecar health check

The context_injector.py routes through this sidecar when it is running,
falling back to direct Ollama if sidecar is unavailable.
"""

import json
import os
import sys
import threading
import time
import urllib.request
from datetime import datetime, timezone
from http.server import BaseHTTPRequestHandler, HTTPServer
from pathlib import Path

WORKSPACE = Path(os.path.expanduser("~/SuneelWorkSpace"))
PORT = 11435
OLLAMA_BASE = "http://localhost:11434"
CACHE_TTL = 300  # 5 minutes

sys.path.insert(0, str(WORKSPACE))

# ── in-memory context store ────────────────────────────────────────────────────

_store: dict = {
    "context": {},   # task_type → {text, ts}
    "lock": threading.Lock(),
}


def _read(path: Path, max_chars: int = 2000) -> str:
    try:
        return path.read_text(errors="ignore")[:max_chars]
    except FileNotFoundError:
        return ""


def _build_context(task_type: str = "general") -> str:
    """Build workspace context — cached for CACHE_TTL seconds."""
    with _store["lock"]:
        cached = _store["context"].get(task_type, {})
        if cached and (time.time() - cached.get("ts", 0)) < CACHE_TTL:
            return cached["text"]

    sections: list[str] = []

    # Identity (pre-loaded on startup — these rarely change)
    identity = _read(WORKSPACE / "dna/identity/profile/identity_profile.md", 800)
    tone = _read(WORKSPACE / "dna/identity/profile/tone_profile.md", 400)
    if identity:
        sections.append(f"## Identity\n{identity}")
    if tone:
        sections.append(f"## Tone\n{tone}")

    # Architecture summary (static)
    sections.append(
        "## Workspace Architecture\n"
        "SuneelWorkSpace — 12-organ AI workspace (macOS M4 Max, 64 GB RAM).\n"
        "Organs: brain memory/search, heart tasks/routing, eyes dashboard/7777, "
        "ears monitors, nervous propagator, skeleton rules, blood logs, "
        "hands 194-CLI, mouth comms, dna identity, lab 9-Ollama-engines, spine health.\n"
        "Symlinks in hands/bin/. Events via nervous/nerve_propagator.py.\n"
        "Ollama models: suneelworkspace(llama3.3:70b), codellama, llama3.1, "
        "mistral, llama3.2."
    )

    # Live state — refresh on every build
    try:
        health = json.loads((WORKSPACE / "spine/state/WORKSPACE_HEALTH.json").read_text())
        score = health.get("health_score", "?")
        issues = len(health.get("issues", []))
        sections.append(f"## Current Health\nScore: {score}/100 | Open issues: {issues}")
    except Exception:
        pass

    memory = _read(WORKSPACE / "brain/memory/MEMORY.md", 1200)
    if memory:
        sections.append(f"## Workspace Memory\n{memory}")

    tasks = _read(WORKSPACE / "heart/tasks/ACTIVE_TASKS.md", 500)
    if tasks:
        sections.append(f"## Active Tasks\n{tasks}")

    if task_type in ("repair", "general", "architecture"):
        decisions = _read(WORKSPACE / "brain/memory/DECISIONS.md", 600)
        if decisions:
            sections.append(f"## Key Decisions\n{decisions}")

    if task_type in ("repair", "learning"):
        patterns = _read(WORKSPACE / "brain/memory/PATTERNS.md", 400)
        if patterns:
            sections.append(f"## Patterns\n{patterns}")

    ctx = "\n\n".join(sections)[:4000]

    with _store["lock"]:
        _store["context"][task_type] = {"text": ctx, "ts": time.time()}

    return ctx


def _ask_ollama(prompt: str, model: str, task_type: str, temperature: float, num_ctx: int) -> str:
    ctx = _build_context(task_type)
    system = (
        "You are an AI engine inside SuneelWorkSpace — a living, self-maintaining local AI workspace.\n\n"
        f"{ctx}\n\n"
        "Rules: be direct, concise, actionable. SAFE actions only. Match Suneel's tone: "
        "short, direct, casual, smart."
    )
    payload = json.dumps({
        "model": model,
        "system": system,
        "prompt": prompt,
        "stream": False,
        "options": {"temperature": temperature, "num_ctx": num_ctx},
    }).encode()
    req = urllib.request.Request(
        f"{OLLAMA_BASE}/api/generate",
        data=payload,
        headers={"Content-Type": "application/json"},
        method="POST",
    )
    try:
        with urllib.request.urlopen(req, timeout=120) as r:
            return json.loads(r.read()).get("response", "").strip()
    except Exception as e:
        return f"[ollama error: {e}]"


# ── HTTP handler ───────────────────────────────────────────────────────────────

class _Handler(BaseHTTPRequestHandler):
    def log_message(self, fmt, *args):
        pass  # suppress default access log

    def _send(self, status: int, body: dict) -> None:
        data = json.dumps(body).encode()
        self.send_response(status)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(data)))
        self.end_headers()
        self.wfile.write(data)

    def _read_body(self) -> dict:
        length = int(self.headers.get("Content-Length", 0))
        if length == 0:
            return {}
        try:
            return json.loads(self.rfile.read(length))
        except Exception:
            return {}

    def do_GET(self):
        if self.path == "/health":
            self._send(200, {
                "status": "ok",
                "port": PORT,
                "ts": datetime.now(timezone.utc).isoformat(),
                "cached_task_types": list(_store["context"].keys()),
            })
        elif self.path.startswith("/context"):
            task_type = "general"
            if "?" in self.path:
                qs = self.path.split("?", 1)[1]
                for part in qs.split("&"):
                    if part.startswith("task_type="):
                        task_type = part.split("=", 1)[1]
            ctx = _build_context(task_type)
            self._send(200, {"context": ctx, "task_type": task_type, "chars": len(ctx)})
        else:
            self._send(404, {"error": "not found"})

    def do_POST(self):
        body = self._read_body()

        if self.path == "/query":
            prompt = body.get("prompt", "").strip()
            if not prompt:
                self._send(400, {"error": "prompt required"})
                return
            model = body.get("model", "suneelworkspace")
            task_type = body.get("task_type", "general")
            temperature = float(body.get("temperature", 0.2))
            num_ctx = int(body.get("num_ctx", 8192))
            response = _ask_ollama(prompt, model, task_type, temperature, num_ctx)
            self._send(200, {
                "response": response,
                "model": model,
                "task_type": task_type,
                "ts": datetime.now(timezone.utc).isoformat(),
            })

        elif self.path == "/invalidate":
            with _store["lock"]:
                _store["context"].clear()
            self._send(200, {"invalidated": True})

        else:
            self._send(404, {"error": "not found"})


# ── cache prefetch thread ──────────────────────────────────────────────────────

def _prefetch_loop() -> None:
    """Pre-warm all common task_type contexts in background."""
    for task_type in ("general", "repair", "review", "security", "learning"):
        try:
            _build_context(task_type)
        except Exception:
            pass
        time.sleep(2)


def is_running(port: int = PORT) -> bool:
    try:
        req = urllib.request.Request(f"http://localhost:{port}/health", method="GET")
        urllib.request.urlopen(req, timeout=1)
        return True
    except Exception:
        return False


def main() -> None:
    # Prefetch in background
    t = threading.Thread(target=_prefetch_loop, daemon=True)
    t.start()

    server = HTTPServer(("127.0.0.1", PORT), _Handler)
    print(f"[reasoning-sidecar] listening on http://127.0.0.1:{PORT}")
    print(f"[reasoning-sidecar] context TTL: {CACHE_TTL}s | Ollama: {OLLAMA_BASE}")
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        pass
    finally:
        server.server_close()


if __name__ == "__main__":
    main()
