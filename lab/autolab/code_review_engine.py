"""
code_review_engine.py
Uses local Ollama (codellama) to review every Python file in the workspace.
Finds bugs, anti-patterns, missing error handling, and improvements.
Applies SAFE fixes (adding try/except, fixing typos) automatically.
Queues CONTROLLED fixes (refactoring, logic changes) for Claude.
"""

import glob
import json
import os
import re
import urllib.request
from datetime import datetime, timezone

OLLAMA_BASE = "http://localhost:11434"
REVIEW_LOG = "blood/logs/code_reviews.jsonl"
REVIEW_REPORT = "blood/logs/code_review_report.md"
SAFE_FIX_LOG = "blood/logs/code_review_safe_fixes.jsonl"
CONTROLLED_QUEUE = "blood/logs/code_review_controlled_queue.json"

SKIP_DIRS = {
    ".git", "__pycache__", ".venv", "venv", "env",
    "node_modules", "chroma_store", "spine/backups",
    "brain/vault", ".agent-backups", "nerve_inbox"
}

REVIEW_PROMPT = """You are a senior Python code reviewer analyzing a file from SuneelWorkSpace.

File: {filepath}
```python
{content}
```

Review this code and find:
1. BUGS: actual errors that would cause failures
2. MISSING_ERROR_HANDLING: places where exceptions should be caught
3. ANTI_PATTERNS: bad practices (bare except, mutable defaults, etc.)
4. IMPROVEMENTS: specific code quality improvements
5. SAFE_FIXES: small fixes you can apply directly (add try/except, fix variable names)

Respond in JSON only:
{{
  "bugs": [
    {{"line": 42, "description": "...", "fix": "exact replacement code"}}
  ],
  "missing_error_handling": [
    {{"line": 15, "description": "...", "fix": "wrap in try/except"}}
  ],
  "anti_patterns": [
    {{"line": 8, "description": "...", "fix": "..."}}
  ],
  "improvements": [
    {{"description": "...", "effort": "small|medium|large", "impact": "high|medium|low"}}
  ],
  "safe_fixes": [
    {{"find": "exact text to find", "replace": "exact replacement", "description": "what this fixes"}}
  ],
  "overall_quality": "good|fair|poor",
  "summary": "one sentence"
}}"""


def ask_ollama(prompt: str, model: str = "codellama", timeout: int = 120) -> str:
    payload = json.dumps({
        "model": model,
        "prompt": prompt,
        "stream": False,
        "options": {"temperature": 0.1, "num_ctx": 4096}
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


def get_python_files(organs: list = None) -> list:
    """Get all Python files to review."""
    if organs is None:
        organs = ["brain", "heart", "eyes", "ears", "nervous", "skeleton",
                  "blood", "hands", "mouth", "dna", "lab", "spine"]

    files = []
    for organ in organs:
        if not os.path.exists(organ):
            continue
        for root, dirs, filenames in os.walk(organ):
            dirs[:] = [d for d in dirs if d not in SKIP_DIRS and not d.startswith(".")]
            rel_root = os.path.relpath(root)
            if any(skip in rel_root for skip in SKIP_DIRS):
                continue
            for f in filenames:
                if f.endswith(".py") and not f.endswith(".pyc"):
                    files.append(os.path.join(root, f))
    return sorted(files)


def apply_safe_fix(filepath: str, find_text: str, replace_text: str) -> bool:
    """Apply a safe fix to a file."""
    try:
        content = open(filepath, encoding="utf-8", errors="ignore").read()
        if find_text not in content:
            return False
        new_content = content.replace(find_text, replace_text, 1)
        if new_content == content:
            return False
        open(filepath, "w", encoding="utf-8").write(new_content)
        return True
    except Exception:
        return False


def review_file(filepath: str) -> dict:
    """Review a single Python file."""
    try:
        content = open(filepath, encoding="utf-8", errors="ignore").read()
    except Exception:
        return {}

    if len(content) < 50:
        return {}

    if len(content) > 4000:
        content = content[:4000] + "\n# ... [truncated for review]"

    prompt = REVIEW_PROMPT.format(filepath=filepath, content=content)
    response = ask_ollama(prompt, model="codellama")

    if not response:
        return {}

    try:
        match = re.search(r'\{.*\}', response, re.DOTALL)
        if match:
            result = json.loads(match.group())
            result["filepath"] = filepath
            result["reviewed_at"] = datetime.now(timezone.utc).isoformat()
            return result
    except Exception:
        pass
    return {}


def run_code_review(organs: list = None, max_files: int = 50) -> dict:
    """Run code review across all Python files."""
    print("Code Review Engine starting...")
    files = get_python_files(organs)
    print(f"  Found {len(files)} Python files")

    if len(files) > max_files:
        print(f"  Limiting to {max_files} files (most recently modified)")
        files = sorted(files, key=os.path.getmtime, reverse=True)[:max_files]

    all_reviews = []
    safe_fixes_applied = 0
    controlled_queue = []
    bugs_found = 0

    for i, filepath in enumerate(files):
        print(f"  [{i+1}/{len(files)}] Reviewing {filepath}...")
        review = review_file(filepath)

        if not review:
            continue

        all_reviews.append(review)
        quality = review.get("overall_quality", "?")
        bugs = len(review.get("bugs", []))
        bugs_found += bugs

        if bugs > 0 or quality == "poor":
            print(f"    Quality: {quality} | Bugs: {bugs} | {review.get('summary', '')}")

        # Apply safe fixes automatically
        for fix in review.get("safe_fixes", []):
            find_text = fix.get("find", "")
            replace_text = fix.get("replace", "")
            if find_text and replace_text and find_text != replace_text:
                if apply_safe_fix(filepath, find_text, replace_text):
                    safe_fixes_applied += 1
                    print(f"    Applied safe fix: {fix.get('description', '')}")
                    with open(SAFE_FIX_LOG, "a") as f:
                        f.write(json.dumps({
                            "timestamp": datetime.now(timezone.utc).isoformat(),
                            "file": filepath,
                            "fix": fix.get("description", ""),
                            "find": find_text[:100],
                            "replace": replace_text[:100],
                        }) + "\n")

        # Queue controlled fixes
        if bugs > 0 or review.get("anti_patterns") or review.get("missing_error_handling"):
            controlled_queue.append({
                "filepath": filepath,
                "bugs": review.get("bugs", []),
                "anti_patterns": review.get("anti_patterns", []),
                "missing_error_handling": review.get("missing_error_handling", []),
                "summary": review.get("summary", ""),
                "quality": quality,
            })

        with open(REVIEW_LOG, "a") as f:
            f.write(json.dumps(review) + "\n")

    os.makedirs(os.path.dirname(CONTROLLED_QUEUE), exist_ok=True)
    with open(CONTROLLED_QUEUE, "w") as f:
        json.dump(controlled_queue, f, indent=2)

    _generate_report(all_reviews, safe_fixes_applied, bugs_found)

    print(f"\nCode review complete:")
    print(f"   Files reviewed: {len(all_reviews)}")
    print(f"   Bugs found: {bugs_found}")
    print(f"   Safe fixes applied: {safe_fixes_applied}")
    print(f"   Controlled fixes queued: {len(controlled_queue)}")
    print(f"   Report: {REVIEW_REPORT}")

    return {
        "files_reviewed": len(all_reviews),
        "bugs_found": bugs_found,
        "safe_fixes_applied": safe_fixes_applied,
        "controlled_fixes_queued": len(controlled_queue),
    }


def _generate_report(reviews: list, safe_fixes: int, bugs: int):
    lines = [
        f"# Code Review Report — {datetime.now().strftime('%Y-%m-%d %H:%M')}",
        f"",
        f"**Files reviewed:** {len(reviews)} | **Bugs:** {bugs} | **Safe fixes applied:** {safe_fixes}",
        f"",
        f"## Files Needing Attention",
        f"",
    ]
    poor_files = [r for r in reviews if r.get("overall_quality") in ("poor", "fair") or r.get("bugs")]
    for r in sorted(poor_files, key=lambda x: len(x.get("bugs", [])), reverse=True)[:20]:
        lines.append(f"### `{r.get('filepath', '?')}`")
        lines.append(f"Quality: **{r.get('overall_quality', '?')}** | {r.get('summary', '')}")
        for bug in r.get("bugs", [])[:3]:
            lines.append(f"- Bug line {bug.get('line', '?')}: {bug.get('description', '')}")
        lines.append("")

    os.makedirs(os.path.dirname(REVIEW_REPORT), exist_ok=True)
    with open(REVIEW_REPORT, "w") as f:
        f.write("\n".join(lines))


if __name__ == "__main__":
    run_code_review()
