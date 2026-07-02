#!/usr/bin/env python3
"""
hands/scripts/dev/spring_watch.py
Live-tails a Spring Boot log (file or stdin), detects stack traces, database
connectivity errors, and other anomalies, and writes suggestions to
blood/logs/dev/spring_anomalies.md. Optional --ollama asks the local
suneelworkspace/llama3.1 model for a fix suggestion per new anomaly type.

Usage:
  spring-watch app.log                 # follow a log file
  ./mvnw spring-boot:run | spring-watch -   # pipe console output
  spring-watch app.log --ollama        # add local-LLM suggestions
"""

import json
import os
import re
import sys
import time
import urllib.request
from datetime import datetime, timezone
from pathlib import Path

WORKSPACE = Path(os.path.expanduser("~/SuneelWorkSpace"))
REPORT = WORKSPACE / "blood/logs/dev/spring_anomalies.md"
OLLAMA_URL = "http://localhost:11434/api/generate"

PATTERNS = [
    ("db_connection", re.compile(
        r"Connection refused|HikariPool.*(timeout|exception)|CannotGetJdbcConnection"
        r"|Communications link failure|Connection is not available", re.I),
     "Database unreachable — check the container/service is up (`dev-stack status`), "
     "then verify spring.datasource.url, port, and credentials."),
    ("db_schema", re.compile(
        r"Table .* doesn't exist|relation .* does not exist|Unknown column"
        r"|FlywayException|liquibase.*(error|failed)", re.I),
     "Schema drift — run pending migrations (Flyway/Liquibase) or rebuild the dev DB."),
    ("port_conflict", re.compile(r"Port \d+ was already in use|Address already in use", re.I),
     "Port conflict — another process holds the port. `lsof -i :<port>` to find it."),
    ("out_of_memory", re.compile(r"OutOfMemoryError|GC overhead limit", re.I),
     "JVM out of memory — raise -Xmx or hunt the leak with a heap dump."),
    ("bean_wiring", re.compile(
        r"UnsatisfiedDependencyException|NoSuchBeanDefinitionException"
        r"|BeanCreationException", re.I),
     "Bean wiring failure — a dependency is missing or misconfigured; check the "
     "named bean and active profiles."),
    ("stack_trace", re.compile(r"^\s+at [\w.$]+\([\w.]+:\d+\)"),
     "Exception stack trace — read the first 'Caused by:' line for the root cause."),
]


def ask_ollama(anomaly_type: str, line: str) -> str:
    payload = {
        "model": "suneelworkspace",
        "prompt": (f"Spring Boot log anomaly ({anomaly_type}):\n{line[:500]}\n\n"
                   "In 2 short sentences: likely root cause and the fix."),
        "stream": False,
        "options": {"num_predict": 120},
    }
    try:
        req = urllib.request.Request(OLLAMA_URL, json.dumps(payload).encode(),
                                     {"Content-Type": "application/json"})
        with urllib.request.urlopen(req, timeout=60) as r:
            return json.loads(r.read()).get("response", "").strip()
    except Exception:
        return ""


def record(anomaly_type: str, line: str, suggestion: str, llm_note: str) -> None:
    REPORT.parent.mkdir(parents=True, exist_ok=True)
    is_new = not REPORT.exists()
    with open(REPORT, "a") as f:
        if is_new:
            f.write("# Spring Boot Anomalies\n\nDetected by `spring-watch`. Newest last.\n")
        f.write(f"\n## {datetime.now(timezone.utc).isoformat()} — {anomaly_type}\n\n")
        f.write(f"```\n{line.strip()[:400]}\n```\n\n- Suggestion: {suggestion}\n")
        if llm_note:
            f.write(f"- Local model: {llm_note}\n")


def follow(path: str):
    """Yield lines from a file as they are appended (tail -f) or from stdin."""
    if path == "-":
        yield from sys.stdin
        return
    with open(path, errors="ignore") as f:
        f.seek(0, os.SEEK_END)
        while True:
            line = f.readline()
            if line:
                yield line
            else:
                time.sleep(0.5)


def main() -> int:
    args = [a for a in sys.argv[1:] if a != "--ollama"]
    use_ollama = "--ollama" in sys.argv
    if not args:
        print(__doc__)
        return 2
    source = args[0]
    print(f"[spring-watch] watching {source} (report: {REPORT})")

    seen_types: set[str] = set()
    try:
        for line in follow(source):
            for anomaly_type, rx, suggestion in PATTERNS:
                if rx.search(line):
                    tee = "NEW" if anomaly_type not in seen_types else "again"
                    print(f"[spring-watch] {anomaly_type} ({tee}): {line.strip()[:140]}")
                    if anomaly_type not in seen_types:
                        llm = ask_ollama(anomaly_type, line) if use_ollama else ""
                        record(anomaly_type, line, suggestion, llm)
                        print(f"  → {suggestion}")
                        seen_types.add(anomaly_type)
                    break
    except KeyboardInterrupt:
        print(f"\n[spring-watch] stopped. {len(seen_types)} anomaly type(s) recorded.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
