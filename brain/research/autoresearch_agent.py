#!/usr/bin/env python3
"""
brain/research/autoresearch_agent.py

Karpathy-style autonomous research agent for SuneelWorkSpace.

Given an idea ID from brain/research/ideas/index.json, runs a full 5-phase
research-to-prototype loop:

  Phase 1 — Literature Search
    Query arXiv REST API (public, no key required) for papers related to the
    idea. Optionally supplement with the workspace MCP gateway's web_search
    if available on port 7778. Abstracts stored in
    brain/research/plans/<id>-literature.md.

  Phase 2 — Workspace RAG Query
    Call workspace_rag.search() to find existing code/decisions/patterns
    already present in the workspace that are relevant to the idea.

  Phase 3 — Synthesis & Code Prototyping
    Feed the idea text + literature abstracts + RAG snippets to the local
    suneelworkspace Ollama model and ask it to write a self-contained Python
    prototype script. Written to brain/research/scripts/temp_prototype_<id>.py.

  Phase 4 — Sandboxed Execution
    Copy the prototype to /tmp/suneelworkspace-sandbox/<ts>-<id>/.
    Run it with a 30-second timeout. On error, feed the traceback back to
    Ollama for a patch. Up to 3 repair iterations.

  Phase 5 — Decision Promotion
    Write a final report to brain/research/analyses/<id>-report.md.
    If the prototype ran successfully, append an architectural decision record
    to brain/memory/DECISIONS.md and update the idea status to "completed".

CLI:
    python3 brain/research/autoresearch_agent.py                  # first captured idea
    python3 brain/research/autoresearch_agent.py <idea-id>        # specific idea
    python3 brain/research/autoresearch_agent.py --list           # list available ideas
    python3 brain/research/autoresearch_agent.py --phase 1        # run a single phase
"""

import json
import os
import re
import shutil
import subprocess
import sys
import time
import urllib.parse
import urllib.request
# defusedxml prevents XXE and billion-laughs attacks from untrusted XML responses.
# Fallback strips DOCTYPE/ENTITY declarations manually so stdlib ET is also safe.
try:
    import defusedxml.ElementTree as ET
except ImportError:
    import xml.etree.ElementTree as _stdlib_ET  # noqa: N812
    import re as _re_xml

    class ET:  # type: ignore[no-redef]
        @staticmethod
        def fromstring(text: str):
            safe = _re_xml.sub(r"<!DOCTYPE[^>]*(?:\[.*?\])?>", "", text, flags=_re_xml.DOTALL)
            safe = _re_xml.sub(r"<!ENTITY[^>]*>", "", safe)
            return _stdlib_ET.fromstring(safe)
from datetime import datetime, timezone
from pathlib import Path

WORKSPACE = Path(os.path.expanduser("~/SuneelWorkSpace"))
sys.path.insert(0, str(WORKSPACE))
os.chdir(WORKSPACE)

# ── paths ──────────────────────────────────────────────────────────────────────
IDEAS_INDEX      = WORKSPACE / "brain/research/ideas/index.json"
PLANS_DIR        = WORKSPACE / "brain/research/plans"
SCRIPTS_DIR      = WORKSPACE / "brain/research/scripts"
ANALYSES_DIR     = WORKSPACE / "brain/research/analyses"
DECISIONS_FILE   = WORKSPACE / "brain/memory/DECISIONS.md"
SANDBOX_BASE     = Path("/tmp/suneelworkspace-sandbox")
LOG_PATH         = WORKSPACE / "blood/logs/autoresearch.jsonl"

OLLAMA_BASE      = "http://localhost:11434"
OLLAMA_MODEL     = "suneelworkspace"
MCP_GATEWAY_URL  = "http://localhost:7778"   # workspace MCP gateway (optional)

_VENV_PY = str(WORKSPACE / ".venv/bin/python3")
PYTHON = _VENV_PY if os.path.exists(_VENV_PY) else sys.executable


# ── helpers ───────────────────────────────────────────────────────────────────

def _log(record: dict) -> None:
    LOG_PATH.parent.mkdir(parents=True, exist_ok=True)
    with LOG_PATH.open("a") as f:
        f.write(json.dumps(record) + "\n")


def _ask_ollama(prompt: str, system: str = "", model: str = OLLAMA_MODEL,
                timeout: int = 120) -> str:
    payload = json.dumps({
        "model": model,
        "system": system or (
            "You are a research assistant inside SuneelWorkSpace, a living AI workspace "
            "on macOS. Be concise, precise, and actionable. When writing code, always write "
            "complete, self-contained Python scripts that can run standalone."
        ),
        "prompt": prompt,
        "stream": False,
        "options": {"temperature": 0.3, "num_ctx": 8192},
    }).encode()
    req = urllib.request.Request(
        f"{OLLAMA_BASE}/api/generate",
        data=payload,
        headers={"Content-Type": "application/json"},
        method="POST",
    )
    try:
        with urllib.request.urlopen(req, timeout=timeout) as r:
            return json.loads(r.read()).get("response", "").strip()
    except Exception as e:
        return f"[ollama error: {e}]"


def _ollama_available() -> bool:
    try:
        urllib.request.urlopen(f"{OLLAMA_BASE}/api/tags", timeout=3)
        return True
    except Exception:
        return False


# ── Phase 1: Literature Search ────────────────────────────────────────────────

_ARXIV_NS = {"a": "http://www.w3.org/2005/Atom"}


def _search_arxiv(query: str, max_results: int = 5) -> list[dict]:
    """Hit the arXiv Atom API and return list of {title, authors, abstract, url}."""
    encoded = urllib.parse.quote(query)
    url = (
        f"http://export.arxiv.org/api/query"
        f"?search_query=all:{encoded}&max_results={max_results}&sortBy=relevance"
    )
    try:
        req = urllib.request.Request(url, headers={"User-Agent": "SuneelWorkSpace-AutoResearch/1.0"})
        with urllib.request.urlopen(req, timeout=20) as r:
            xml_text = r.read().decode("utf-8", errors="ignore")
    except Exception as e:
        print(f"  [arxiv] request failed: {e}")
        return []

    results = []
    try:
        root = ET.fromstring(xml_text)
        for entry in root.findall("a:entry", _ARXIV_NS):
            title_el = entry.find("a:title", _ARXIV_NS)
            abstract_el = entry.find("a:summary", _ARXIV_NS)
            url_el = entry.find("a:id", _ARXIV_NS)
            authors = [
                a.find("a:name", _ARXIV_NS).text
                for a in entry.findall("a:author", _ARXIV_NS)
                if a.find("a:name", _ARXIV_NS) is not None
            ]
            results.append({
                "title":    (title_el.text or "").strip().replace("\n", " "),
                "authors":  ", ".join(authors[:3]) + (" et al." if len(authors) > 3 else ""),
                "abstract": (abstract_el.text or "").strip().replace("\n", " ")[:600],
                "url":      (url_el.text or "").strip(),
            })
    except Exception as e:
        print(f"  [arxiv] parse error: {e}")

    return results


def _search_mcp_web(query: str) -> list[dict]:
    """Try MCP gateway web_search (optional, fails silently if not running)."""
    try:
        payload = json.dumps({"query": query, "max_results": 3}).encode()
        req = urllib.request.Request(
            f"{MCP_GATEWAY_URL}/search/web",
            data=payload,
            headers={"Content-Type": "application/json"},
            method="POST",
        )
        with urllib.request.urlopen(req, timeout=5) as r:
            data = json.loads(r.read())
            return data.get("results", [])
    except Exception:
        return []


def phase1_literature_search(idea_id: str, idea_title: str, idea_text: str) -> dict:
    """Search arXiv + optional MCP web, write literature.md."""
    print("  [phase-1] Searching arXiv…")
    query = idea_title or idea_text[:80]
    papers = _search_arxiv(query, max_results=5)

    web_results = _search_mcp_web(query)
    if web_results:
        print(f"  [phase-1] MCP web_search returned {len(web_results)} results")

    # Write literature.md
    PLANS_DIR.mkdir(parents=True, exist_ok=True)
    lit_path = PLANS_DIR / f"{idea_id}-literature.md"
    lines = [
        f"# Literature Search: {idea_title}",
        f"\nQuery: `{query}`",
        f"\nGenerated: {datetime.now(timezone.utc).isoformat()}",
        "\n---\n",
    ]

    if papers:
        lines.append(f"## arXiv Papers ({len(papers)} results)\n")
        for i, p in enumerate(papers, 1):
            lines.append(f"### [{i}] {p['title']}")
            if p["authors"]:
                lines.append(f"*{p['authors']}*")
            lines.append(f"\n{p['abstract']}\n")
            lines.append(f"[{p['url']}]({p['url']})\n")
    else:
        lines.append("## arXiv Papers\n\n*No results returned — arXiv may be unreachable.*\n")

    if web_results:
        lines.append("\n## Web Search Results\n")
        for r in web_results:
            title = r.get("title", "")
            url = r.get("url", r.get("href", ""))
            snippet = r.get("snippet", r.get("description", ""))
            lines.append(f"- **{title}** — {snippet}\n  {url}\n")

    lit_path.write_text("\n".join(lines), encoding="utf-8")
    print(f"  [phase-1] Wrote {lit_path.name} ({len(papers)} papers)")
    return {"papers": papers, "web_results": web_results, "lit_path": str(lit_path)}


# ── Phase 2: Workspace RAG ────────────────────────────────────────────────────

def phase2_rag_query(idea_title: str, idea_text: str) -> dict:
    """Query workspace_rag for existing relevant solutions."""
    print("  [phase-2] Querying workspace RAG…")
    try:
        import importlib.util
        spec = importlib.util.spec_from_file_location(
            "workspace_rag", WORKSPACE / "brain/research/workspace_rag.py"
        )
        mod = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(mod)
        results = mod.search(idea_title + " " + idea_text[:100], top_k=5)
        ctx = mod.get_context_for_prompt(idea_title, top_k=5)
        print(f"  [phase-2] Found {len(results)} relevant workspace documents")
        return {"results": results, "context_text": ctx}
    except Exception as e:
        print(f"  [phase-2] RAG unavailable: {e}")
        return {"results": [], "context_text": ""}


# ── Phase 3: Synthesis & Prototyping ──────────────────────────────────────────

def _extract_code(text: str) -> str:
    """Extract the first Python code block from a markdown-formatted response."""
    match = re.search(r"```(?:python)?\n(.*?)```", text, re.DOTALL)
    if match:
        return match.group(1).strip()
    # If no code block, try to find lines that look like Python
    lines = text.splitlines()
    code_lines = [l for l in lines if l.startswith("    ") or l.startswith("import ")
                  or l.startswith("def ") or l.startswith("class ")]
    return "\n".join(code_lines) if len(code_lines) > 3 else text


def phase3_synthesize(idea_id: str, idea_title: str, idea_text: str,
                      lit_result: dict, rag_result: dict) -> dict:
    """Ask Ollama to synthesize findings and write a prototype script."""
    print("  [phase-3] Synthesizing with Ollama…")

    papers = lit_result.get("papers", [])
    paper_section = ""
    if papers:
        paper_section = "\n## Related Papers\n"
        for p in papers[:3]:
            paper_section += f"\n**{p['title']}** ({p['authors']})\n{p['abstract'][:300]}\n"

    rag_ctx = rag_result.get("context_text", "")[:800]

    prompt = f"""You are implementing a research prototype for SuneelWorkSpace.

## Idea
Title: {idea_title}
{idea_text[:400]}
{paper_section}
## Existing Workspace Code (RAG)
{rag_ctx or 'No relevant workspace code found.'}

## Task
Write a complete, self-contained Python script that:
1. Demonstrates or tests the core concept of the idea
2. Runs without any external dependencies beyond Python stdlib
3. Prints meaningful output showing the idea works
4. Is under 80 lines

Wrap the code in a single ```python ... ``` block. Nothing else."""

    response = _ask_ollama(prompt, timeout=180)
    code = _extract_code(response)

    if not code or len(code) < 20:
        code = (
            f"#!/usr/bin/env python3\n"
            f'"""Prototype for: {idea_title}"""\n\n'
            f"# Autogenerated stub — Ollama synthesis did not return usable code\n"
            f"print('Idea: {idea_title}')\n"
            f"print('Status: stub — Ollama response was not parseable as Python code')\n"
        )

    SCRIPTS_DIR.mkdir(parents=True, exist_ok=True)
    proto_path = SCRIPTS_DIR / f"temp_prototype_{idea_id}.py"
    proto_path.write_text(code, encoding="utf-8")
    print(f"  [phase-3] Wrote prototype: {proto_path.name} ({len(code)} chars)")
    return {"prototype_path": str(proto_path), "code": code, "raw_response": response[:500]}


# ── Phase 4: Sandboxed Execution ──────────────────────────────────────────────

def _run_in_sandbox(prototype_path: Path, sandbox_dir: Path, timeout: int = 30) -> dict:
    """Copy prototype into sandbox and execute it. Returns {success, stdout, stderr}."""
    sandbox_dir.mkdir(parents=True, exist_ok=True)
    sandbox_script = sandbox_dir / prototype_path.name
    shutil.copy2(prototype_path, sandbox_script)

    try:
        r = subprocess.run(
            [PYTHON, str(sandbox_script)],
            capture_output=True,
            text=True,
            timeout=timeout,
            cwd=str(sandbox_dir),
        )
        return {
            "success": r.returncode == 0,
            "returncode": r.returncode,
            "stdout": r.stdout[-2000:],
            "stderr": r.stderr[-1000:],
        }
    except subprocess.TimeoutExpired:
        return {"success": False, "returncode": -1, "stdout": "", "stderr": "Timeout after 30s"}
    except Exception as e:
        return {"success": False, "returncode": -1, "stdout": "", "stderr": str(e)}


def _patch_with_ollama(code: str, traceback: str, iteration: int) -> str:
    """Ask Ollama to patch failing code based on the traceback."""
    prompt = (
        f"This Python code failed (iteration {iteration}/3):\n\n"
        f"```python\n{code[:1500]}\n```\n\n"
        f"Error:\n```\n{traceback[:500]}\n```\n\n"
        "Write the corrected complete Python script. "
        "Only output a ```python ... ``` block."
    )
    response = _ask_ollama(prompt, timeout=120)
    patched = _extract_code(response)
    return patched if len(patched) > 20 else code


def phase4_sandbox_execute(idea_id: str, prototype_path: str) -> dict:
    """Execute prototype in sandbox with up to 3 Ollama-assisted repair iterations."""
    print("  [phase-4] Running prototype in sandbox…")
    ts = datetime.now(timezone.utc).strftime("%Y%m%d_%H%M%S")
    sandbox_dir = SANDBOX_BASE / f"{ts}-{idea_id[:30]}"
    proto = Path(prototype_path)

    code = proto.read_text(encoding="utf-8", errors="ignore")
    iterations = []
    final_result: dict = {}

    for attempt in range(1, 4):
        print(f"  [phase-4] Attempt {attempt}/3…")
        result = _run_in_sandbox(proto, sandbox_dir, timeout=30)
        iterations.append({"attempt": attempt, **result})

        if result["success"]:
            print(f"  [phase-4] ✅ Success on attempt {attempt}")
            final_result = result
            break

        print(f"  [phase-4] ❌ Failed (rc={result['returncode']}): {result['stderr'][:120]}")
        if attempt < 3 and _ollama_available():
            print(f"  [phase-4] Patching with Ollama…")
            code = _patch_with_ollama(code, result["stderr"] + result["stdout"], attempt)
            proto.write_text(code, encoding="utf-8")
        else:
            final_result = result
            break

    # Cleanup sandbox
    try:
        shutil.rmtree(sandbox_dir, ignore_errors=True)
    except Exception:
        pass

    return {
        "success": final_result.get("success", False),
        "stdout": final_result.get("stdout", ""),
        "stderr": final_result.get("stderr", ""),
        "iterations": iterations,
        "total_attempts": len(iterations),
    }


# ── Phase 5: Decision Promotion ───────────────────────────────────────────────

def phase5_promote(idea_id: str, idea_title: str, idea_text: str,
                   lit_result: dict, rag_result: dict,
                   sandbox_result: dict) -> dict:
    """Write analysis report and optionally promote to DECISIONS.md."""
    print("  [phase-5] Writing research report…")

    success = sandbox_result.get("success", False)
    papers = lit_result.get("papers", [])
    iterations = sandbox_result.get("total_attempts", 0)
    rag_hits = len(rag_result.get("results", []))

    # Build report
    ts = datetime.now(timezone.utc).isoformat()
    status_line = "✅ Prototype validated" if success else "⚠️ Prototype did not run cleanly"

    lines = [
        f"# Research Report: {idea_title}",
        f"\n**ID:** `{idea_id}`",
        f"**Generated:** {ts}",
        f"**Status:** {status_line}",
        "\n---\n",
        "## Summary",
        f"\n{idea_text[:400]}\n",
        f"## Literature ({len(papers)} papers found)",
    ]
    for p in papers[:5]:
        lines.append(f"\n- **{p['title']}** — {p['abstract'][:200]}")

    lines += [
        f"\n## Workspace RAG Hits: {rag_hits}",
    ]
    for r in rag_result.get("results", [])[:3]:
        lines.append(f"\n- `{r['path']}` ({r['source_type']}): {r['snippet'][:120]}")

    lines += [
        f"\n## Sandbox Execution",
        f"\nAttempts: {iterations}  |  Final success: {success}",
    ]
    if sandbox_result.get("stdout"):
        lines.append(f"\n```\n{sandbox_result['stdout'][:400]}\n```")
    if sandbox_result.get("stderr") and not success:
        lines.append(f"\n**Last error:**\n```\n{sandbox_result['stderr'][:300]}\n```")

    lines += ["\n## Conclusions\n"]
    if success:
        lines.append(
            f"The prototype for '{idea_title}' ran successfully after {iterations} attempt(s). "
            f"The concept is viable. See scripts/temp_prototype_{idea_id}.py for the validated code."
        )
    else:
        lines.append(
            f"The prototype for '{idea_title}' did not complete cleanly after {iterations} attempt(s). "
            "Manual review recommended. See the error trace above."
        )

    ANALYSES_DIR.mkdir(parents=True, exist_ok=True)
    report_path = ANALYSES_DIR / f"{idea_id}-report.md"
    report_path.write_text("\n".join(lines), encoding="utf-8")
    print(f"  [phase-5] Wrote report: {report_path.name}")

    # Promote to DECISIONS.md if successful
    promoted = False
    if success:
        decision = (
            f"\n\n## {idea_title} (auto-promoted {ts[:10]})\n\n"
            f"**Idea ID:** `{idea_id}`\n\n"
            f"**Summary:** {idea_text[:300]}\n\n"
            f"**Validation:** Prototype ran successfully in sandbox after {iterations} attempt(s). "
            f"{len(papers)} arXiv papers surveyed. {rag_hits} workspace RAG hits.\n\n"
            f"**Report:** `brain/research/analyses/{report_path.name}`\n"
        )
        DECISIONS_FILE.parent.mkdir(parents=True, exist_ok=True)
        with DECISIONS_FILE.open("a", encoding="utf-8") as f:
            f.write(decision)
        promoted = True
        print(f"  [phase-5] ✅ Decision promoted to DECISIONS.md")
    else:
        print(f"  [phase-5] Prototype did not pass — skipping DECISIONS.md promotion")

    return {
        "report_path": str(report_path),
        "promoted_to_decisions": promoted,
        "success": success,
    }


# ── idea management ───────────────────────────────────────────────────────────

def _load_ideas() -> list[dict]:
    if not IDEAS_INDEX.exists():
        return []
    try:
        return json.loads(IDEAS_INDEX.read_text()).get("ideas", [])
    except Exception:
        return []


def _update_idea_status(idea_id: str, status: str) -> None:
    if not IDEAS_INDEX.exists():
        return
    try:
        data = json.loads(IDEAS_INDEX.read_text())
        for idea in data.get("ideas", []):
            if idea.get("id") == idea_id:
                idea["status"] = status
                idea["updated_at"] = datetime.now(timezone.utc).isoformat()
        IDEAS_INDEX.write_text(json.dumps(data, indent=2, ensure_ascii=False))
    except Exception:
        pass


def _get_idea(idea_id: str | None) -> tuple[str, str, str] | None:
    """Return (id, title, text) for the specified or first captured idea."""
    ideas = _load_ideas()
    if not ideas:
        print("[autoresearch] No ideas in index. Add one first via idea-capture.")
        return None

    if idea_id:
        candidates = [i for i in ideas if i.get("id") == idea_id]
    else:
        candidates = [i for i in ideas if i.get("status") == "captured"]

    if not candidates:
        print(f"[autoresearch] Idea '{idea_id}' not found or no captured ideas.")
        return None

    idea = candidates[0]
    iid = idea.get("id", "")
    title = idea.get("title", "")
    idea_path = WORKSPACE / idea.get("idea_path", "")
    text = ""
    if idea_path.exists():
        text = idea_path.read_text(encoding="utf-8", errors="ignore")[:600]

    return iid, title, text


# ── main runner ────────────────────────────────────────────────────────────────

def run(idea_id: str | None = None, phase_limit: int | None = None) -> dict:
    """Run the full 5-phase autoresearch loop for one idea."""
    ts_start = time.monotonic()

    result = _get_idea(idea_id)
    if result is None:
        return {"status": "no_idea"}
    iid, title, text = result

    print(f"\n[autoresearch] Starting research: '{title}'")
    print(f"  id={iid}")
    print(f"  ollama={'available' if _ollama_available() else 'UNAVAILABLE'}")

    _update_idea_status(iid, "in_progress")

    record: dict = {
        "ts": datetime.now(timezone.utc).isoformat(),
        "idea_id": iid,
        "title": title,
    }

    # Phase 1
    lit = phase1_literature_search(iid, title, text)
    record["phase1"] = {"papers": len(lit["papers"]), "lit_path": lit["lit_path"]}
    if phase_limit == 1:
        _log(record)
        return record

    # Phase 2
    rag = phase2_rag_query(title, text)
    record["phase2"] = {"rag_hits": len(rag["results"])}
    if phase_limit == 2:
        _log(record)
        return record

    # Phase 3
    synth = phase3_synthesize(iid, title, text, lit, rag)
    record["phase3"] = {"prototype": synth["prototype_path"]}
    if phase_limit == 3:
        _log(record)
        return record

    # Phase 4
    sandbox = phase4_sandbox_execute(iid, synth["prototype_path"])
    record["phase4"] = {
        "success": sandbox["success"],
        "attempts": sandbox["total_attempts"],
    }
    if phase_limit == 4:
        _log(record)
        return record

    # Phase 5
    promotion = phase5_promote(iid, title, text, lit, rag, sandbox)
    record["phase5"] = {
        "report": promotion["report_path"],
        "promoted": promotion["promoted_to_decisions"],
    }

    _update_idea_status(iid, "completed" if sandbox["success"] else "needs_review")
    record["elapsed_s"] = round(time.monotonic() - ts_start, 1)
    record["status"] = "completed" if sandbox["success"] else "partial"

    _log(record)
    print(f"\n[autoresearch] Done in {record['elapsed_s']}s — status={record['status']}")
    return record


# ── CLI ────────────────────────────────────────────────────────────────────────

def main() -> None:
    import argparse
    parser = argparse.ArgumentParser(
        description="Karpathy-style autonomous research agent for SuneelWorkSpace"
    )
    parser.add_argument("idea_id", nargs="?", default=None,
                        help="Idea ID from brain/research/ideas/index.json "
                             "(default: first captured idea)")
    parser.add_argument("--list", action="store_true", help="List all ideas")
    parser.add_argument("--phase", type=int, choices=[1, 2, 3, 4, 5], default=None,
                        help="Run only up to this phase number")
    args = parser.parse_args()

    if args.list:
        ideas = _load_ideas()
        if not ideas:
            print("[autoresearch] No ideas in index.")
            return
        for i in ideas:
            print(f"  {i.get('status', '?'):12s}  {i['id']}")
            print(f"               {i.get('title', '')}")
        return

    result = run(idea_id=args.idea_id, phase_limit=args.phase)
    sys.exit(0 if result.get("status") in ("completed", "partial") else 1)


if __name__ == "__main__":
    main()
