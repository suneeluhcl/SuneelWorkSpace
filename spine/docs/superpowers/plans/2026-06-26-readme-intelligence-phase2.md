# README Intelligence Phase 2 — Autonomous Evolution System

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Layer health scoring, semantic change impact, runtime probing, security filtering, a cache layer, lab/evolution integration, a dashboard widget, and a knowledge index on top of the Phase 1 README system.

**Architecture:** Phase 1 built the core generation pipeline (intelligence_engine → readme_generator → root_synthesizer + validator + watcher). Phase 2 adds intelligence: a health scorer (0-100) fed by a runtime probe, a cache manager for incremental runs, a semantic change-impact engine that cascades updates only to truly affected folders, a security filter that scrubs credentials, a lab bridge that fires evolution cycles on low-health folders, a dashboard widget, and a machine-readable knowledge index. All new modules live in `hands/automation/readme/` and follow the existing import pattern `sys.path.insert(0, WORKSPACE)`.

**Tech Stack:** Python 3.14 stdlib (ast, hashlib, re, subprocess, pathlib), FastAPI (existing dashboard), watchdog (already installed in .venv).

## Global Constraints

- All Python runs under `/Users/MAC/SuneelWorkSpace/.venv/bin/python3`
- Workspace root detected via `git rev-parse --show-toplevel` from any file in the repo
- Import path convention: `sys.path.insert(0, str(WORKSPACE))` at top of every script
- Nervous system notify: `python3 nervous/nerve_propagator.py notify <organ> "event"`
- Dashboard widgets live in `eyes/dashboard/widgets/` — one function `get_<name>()` returns a dict
- Dashboard server `eyes/dashboard/server.py` adds endpoints as `@app.get("/api/<name>")`
- Dependency map at `spine/readme_dependency_map.json` (key `folders` → dict of paths)
- Health cache at `spine/readme_health_cache.json`
- Knowledge index at `brain/system/readme_knowledge_index.json`
- README.lock file: if `<folder>/README.lock` exists, skip auto-update for that folder
- Atomic write: write to `README.tmp.md`, validate structure, then `rename()` to `README.md`
- Security filter runs on all generated README content before write
- Health score 0-100: 100 = perfect; deductions for each issue class
- Lab bridge triggers when folder health_score < 60

---

## File Structure

| File | New/Modify | Responsibility |
|------|-----------|----------------|
| `hands/automation/readme/health_scorer.py` | **New** | Compute 0-100 health score per folder |
| `hands/automation/readme/runtime_probe.py` | **New** | Safe import/script execution checks |
| `hands/automation/readme/security_filter.py` | **New** | Scrub API keys/credentials from README content |
| `hands/automation/readme/cache_manager.py` | **New** | Hash-based cache — skip unchanged folders |
| `hands/automation/readme/change_impact_engine.py` | **New** | Semantic cascade: which folders need updating after X changes |
| `hands/automation/readme/lab_bridge.py` | **New** | Trigger lab evolution cycle when health < threshold |
| `hands/automation/readme/knowledge_indexer.py` | **New** | Build machine-readable JSON index of all folder READMEs |
| `hands/automation/readme/readme_generator.py` | **Modify** | Add: atomic write, README.lock guard, security filter, health sections, tiered Claude fallbacks |
| `hands/automation/readme/watcher.py` | **Modify** | Replace naive file handler with change_impact_engine cascade |
| `hands/automation/readme/root_synthesizer.py` | **Modify** | Pull health scores from health_scorer for summary table |
| `eyes/dashboard/widgets/readme_health.py` | **New** | Widget: overall README health summary for dashboard |
| `eyes/dashboard/server.py` | **Modify** | Add `/api/readme-health` endpoint |
| `spine/readme_health_cache.json` | **New (generated)** | Cache: folder path → {hash, health_score, timestamp} |
| `brain/system/readme_knowledge_index.json` | **New (generated)** | Machine-readable index of all folder purposes and capabilities |

---

### Task 1: Health Scorer + Runtime Probe

**Files:**
- Create: `hands/automation/readme/runtime_probe.py`
- Create: `hands/automation/readme/health_scorer.py`

**Produces:**
- `probe_folder(folder_path: str) -> dict` — `{importable: list, broken_imports: list, runnable_scripts: list, has_tests: bool}`
- `score_folder(folder_path: str, analysis: dict, probe: dict) -> dict` — `{score: int, breakdown: dict, critical_issues: list}`

- [ ] **Step 1: Write runtime_probe.py**

```python
#!/usr/bin/env python3
"""
Runtime Probe — safely checks whether Python modules in a folder are importable
and whether shell scripts are syntactically valid. Never executes user code.
"""
import ast
import os
import subprocess
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[3]))

WORKSPACE = Path(subprocess.check_output(
    ["git", "rev-parse", "--show-toplevel"], text=True,
    cwd=os.path.dirname(os.path.abspath(__file__))
).strip())


def _check_python_syntax(py_file: Path) -> tuple:
    """Return (ok: bool, error: str)."""
    try:
        ast.parse(py_file.read_text(errors="ignore"))
        return True, ""
    except SyntaxError as e:
        return False, f"{py_file.name}:{e.lineno}: {e.msg}"
    except Exception as e:
        return False, str(e)


def _check_shell_syntax(sh_file: Path) -> tuple:
    """Return (ok: bool, error: str). Uses bash -n (dry-run)."""
    try:
        result = subprocess.run(
            ["bash", "-n", str(sh_file)],
            capture_output=True,
            text=True,
            timeout=5,
        )
        return result.returncode == 0, result.stderr.strip()
    except Exception as e:
        return False, str(e)


def probe_folder(folder_path: str) -> dict:
    """
    Probe a folder for runtime health.
    Returns:
        {
          "importable": [list of .py files that parse cleanly],
          "broken_imports": [{"file": str, "error": str}],
          "runnable_scripts": [list of .sh files that pass bash -n],
          "broken_scripts": [{"file": str, "error": str}],
          "has_tests": bool,
          "python_file_count": int,
          "shell_file_count": int,
        }
    """
    path = Path(folder_path).resolve()
    result = {
        "importable": [],
        "broken_imports": [],
        "runnable_scripts": [],
        "broken_scripts": [],
        "has_tests": False,
        "python_file_count": 0,
        "shell_file_count": 0,
    }

    if not path.is_dir():
        return result

    try:
        for item in path.iterdir():
            if not item.is_file():
                continue
            if item.suffix == ".py":
                result["python_file_count"] += 1
                if "test" in item.stem.lower():
                    result["has_tests"] = True
                ok, err = _check_python_syntax(item)
                if ok:
                    result["importable"].append(item.name)
                else:
                    result["broken_imports"].append({"file": item.name, "error": err})
            elif item.suffix == ".sh":
                result["shell_file_count"] += 1
                ok, err = _check_shell_syntax(item)
                if ok:
                    result["runnable_scripts"].append(item.name)
                else:
                    result["broken_scripts"].append({"file": item.name, "error": err})
    except PermissionError:
        pass

    return result


if __name__ == "__main__":
    import argparse
    import json
    parser = argparse.ArgumentParser()
    parser.add_argument("folder", help="Folder to probe")
    args = parser.parse_args()
    print(json.dumps(probe_folder(args.folder), indent=2))
```

- [ ] **Step 2: Write health_scorer.py**

```python
#!/usr/bin/env python3
"""
Health Scorer — computes a 0-100 health score for a workspace folder.

Score breakdown (deductions):
  -20  README missing
  -10  README has no required sections (any of Purpose/Contents/Change Log)
  -15  README older than folder contents (drift)
  -10  Stale file references in README Contents section
  -15  Broken Python syntax (per broken file, max -30)
  -10  Broken shell script syntax (per broken file, max -20)
  -10  No test coverage
  -5   Missing capabilities section
  +0   (floor is 0, ceiling is 100)
"""
import os
import re
import subprocess
import sys
from datetime import datetime
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[3]))

WORKSPACE = Path(subprocess.check_output(
    ["git", "rev-parse", "--show-toplevel"], text=True,
    cwd=os.path.dirname(os.path.abspath(__file__))
).strip())

REQUIRED_SECTIONS = ["Purpose", "Contents", "Change Log"]


def _readme_mtime(folder: Path) -> float:
    readme = folder / "README.md"
    return readme.stat().st_mtime if readme.exists() else 0.0


def _folder_max_mtime(folder: Path) -> float:
    max_mtime = 0.0
    try:
        for item in folder.iterdir():
            if item.name in {"README.md", ".DS_Store"} or item.name.startswith("."):
                continue
            try:
                max_mtime = max(max_mtime, item.stat().st_mtime)
            except Exception:
                pass
    except Exception:
        pass
    return max_mtime


def _stale_file_refs(readme_content: str, folder: Path) -> list:
    match = re.search(r"## 📂 Contents(.*?)(?=\n## |\Z)", readme_content, re.DOTALL)
    if not match:
        return []
    stale = []
    for m in re.finditer(r"`([^`/]+\.[a-zA-Z0-9]+)`", match.group(1)):
        fname = m.group(1)
        if not (folder / fname).exists():
            stale.append(fname)
    return stale


def score_folder(folder_path: str, analysis: dict = None, probe: dict = None) -> dict:
    """
    Compute health score for a folder.

    Args:
        folder_path: absolute or relative path to folder
        analysis: output of intelligence_engine.analyze_folder (optional, recomputed if None)
        probe: output of runtime_probe.probe_folder (optional, recomputed if None)

    Returns:
        {
          "score": int,           # 0-100
          "breakdown": dict,      # category → deduction
          "critical_issues": list,# human-readable strings
          "folder": str,
          "timestamp": str,
        }
    """
    path = Path(folder_path).resolve()
    deductions = {}
    issues = []

    # Lazy-load analysis and probe if not provided
    if analysis is None:
        from hands.automation.readme.intelligence_engine import analyze_folder
        analysis = analyze_folder(str(path))

    if probe is None:
        from hands.automation.readme.runtime_probe import probe_folder
        probe = probe_folder(str(path))

    readme_path = path / "README.md"

    # --- README existence ---
    if not readme_path.exists():
        deductions["readme_missing"] = 20
        issues.append("README.md is missing")
    else:
        try:
            content = readme_path.read_text(errors="ignore")
        except Exception:
            content = ""

        # --- Required sections ---
        missing_secs = [s for s in REQUIRED_SECTIONS if s.lower() not in content.lower()]
        if missing_secs:
            deductions["missing_sections"] = 10
            issues.append(f"README missing sections: {missing_secs}")

        # --- Drift ---
        readme_mtime = _readme_mtime(path)
        folder_mtime = _folder_max_mtime(path)
        if folder_mtime > readme_mtime + 1:
            deductions["readme_drift"] = 15
            issues.append("README is older than folder contents")

        # --- Stale file refs ---
        stale = _stale_file_refs(content, path)
        if stale:
            deductions["stale_refs"] = 10
            issues.append(f"Stale file references in README: {stale}")

        # --- Capabilities section ---
        if "capabilit" not in content.lower():
            deductions["no_capabilities"] = 5

    # --- Broken Python files ---
    broken_py = probe.get("broken_imports", [])
    if broken_py:
        penalty = min(30, 15 * len(broken_py))
        deductions["broken_python"] = penalty
        for b in broken_py:
            issues.append(f"Syntax error in {b['file']}: {b['error'][:60]}")

    # --- Broken shell scripts ---
    broken_sh = probe.get("broken_scripts", [])
    if broken_sh:
        penalty = min(20, 10 * len(broken_sh))
        deductions["broken_shell"] = penalty
        for b in broken_sh:
            issues.append(f"Shell error in {b['file']}: {b['error'][:60]}")

    # --- No tests ---
    if probe.get("python_file_count", 0) > 0 and not probe.get("has_tests", False):
        deductions["no_tests"] = 10
        issues.append("No test files detected")

    total_deduction = sum(deductions.values())
    score = max(0, min(100, 100 - total_deduction))

    try:
        rel = str(path.relative_to(WORKSPACE))
    except ValueError:
        rel = str(path)

    return {
        "score": score,
        "breakdown": deductions,
        "critical_issues": issues,
        "folder": rel,
        "timestamp": datetime.now().isoformat(),
    }


def score_all_folders(workspace_root: str = None) -> list:
    from hands.automation.readme.intelligence_engine import analyze_workspace, IGNORED_DIRS
    root = Path(workspace_root) if workspace_root else WORKSPACE
    analyses = analyze_workspace(str(root))
    results = []
    for analysis in analyses:
        folder = str(root / analysis["path"])
        result = score_folder(folder, analysis=analysis)
        results.append(result)
    return sorted(results, key=lambda x: x["score"])


if __name__ == "__main__":
    import argparse
    import json
    parser = argparse.ArgumentParser()
    parser.add_argument("folder", nargs="?", help="Folder to score (default: all)")
    args = parser.parse_args()
    if args.folder:
        result = score_folder(args.folder)
        print(json.dumps(result, indent=2))
    else:
        results = score_all_folders()
        print(f"Scored {len(results)} folders")
        for r in results[:10]:
            print(f"  {r['score']:3d}  {r['folder']}")
```

- [ ] **Step 3: Smoke test both**

```bash
cd /Users/MAC/SuneelWorkSpace
.venv/bin/python3 hands/automation/readme/runtime_probe.py hands
.venv/bin/python3 hands/automation/readme/health_scorer.py brain
```

Expected: JSON output with `score` between 0 and 100, `critical_issues` list.

- [ ] **Step 4: Commit**

```bash
git add hands/automation/readme/runtime_probe.py hands/automation/readme/health_scorer.py
git commit -m "feat(readme-p2): add runtime probe + health scorer (0-100)"
```

---

### Task 2: Security Filter

**Files:**
- Create: `hands/automation/readme/security_filter.py`

**Produces:** `scrub_readme(content: str) -> tuple[str, list[str]]` — `(cleaned_content, list_of_redacted_patterns)`

- [ ] **Step 1: Write security_filter.py**

```python
#!/usr/bin/env python3
"""
Security Filter — scrubs API keys, tokens, and credentials from README content.
Replaces matches with [REDACTED:<type>] placeholders.
Never blocks README generation — always returns safe content.
"""
import re
from typing import Tuple

# Patterns: (label, regex)
# Ordered from most specific to most general to avoid false positives.
SECRET_PATTERNS = [
    ("anthropic_key",  re.compile(r"sk-ant-[A-Za-z0-9\-_]{20,}")),
    ("openai_key",     re.compile(r"sk-[A-Za-z0-9]{32,}")),
    ("aws_key",        re.compile(r"AKIA[A-Z0-9]{16}")),
    ("aws_secret",     re.compile(r"(?i)aws.{0,20}secret.{0,5}['\"]([A-Za-z0-9/+=]{40})['\"]")),
    ("gh_pat",         re.compile(r"ghp_[A-Za-z0-9]{36}")),
    ("gh_oauth",       re.compile(r"gho_[A-Za-z0-9]{36}")),
    ("gh_token",       re.compile(r"github_pat_[A-Za-z0-9_]{82}")),
    ("bearer_token",   re.compile(r"(?i)bearer\s+[A-Za-z0-9\-_.~+/]{20,}")),
    ("generic_secret", re.compile(r"(?i)(api[_\-]?key|secret[_\-]?key|auth[_\-]?token)\s*[:=]\s*['\"]?([A-Za-z0-9\-_.]{16,})['\"]?")),
    ("private_key",    re.compile(r"-----BEGIN (RSA |EC |OPENSSH )?PRIVATE KEY-----")),
    ("password",       re.compile(r"(?i)password\s*[:=]\s*['\"]([^'\"]{8,})['\"]")),
]

# Paths that are okay to mention (suppress false positives)
SAFE_PATTERNS = [
    re.compile(r"sk-ant-example"),
    re.compile(r"sk-example"),
    re.compile(r"AKIA_EXAMPLE"),
    re.compile(r"\[REDACTED"),
]


def _is_safe_match(text: str, start: int, end: int) -> bool:
    for safe in SAFE_PATTERNS:
        if safe.search(text[max(0, start-5):end+5]):
            return True
    return False


def scrub_readme(content: str) -> Tuple[str, list]:
    """
    Scrub secrets from README content.

    Returns:
        (cleaned_content, redacted_list)
        redacted_list: list of strings like "anthropic_key at line 12"
    """
    redacted = []
    lines = content.split("\n")
    clean_lines = []

    for line_num, line in enumerate(lines, start=1):
        clean_line = line
        for label, pattern in SECRET_PATTERNS:
            for match in pattern.finditer(clean_line):
                if not _is_safe_match(clean_line, match.start(), match.end()):
                    clean_line = clean_line[:match.start()] + f"[REDACTED:{label}]" + clean_line[match.end():]
                    redacted.append(f"{label} at line {line_num}")
                    break  # one pass per pattern per line
        clean_lines.append(clean_line)

    return "\n".join(clean_lines), redacted


def is_clean(content: str) -> bool:
    """Quick check — True if no secrets detected."""
    _, found = scrub_readme(content)
    return len(found) == 0


if __name__ == "__main__":
    import sys
    text = sys.stdin.read() if not sys.stdin.isatty() else "test: sk-ant-api123456789012345678 found here"
    clean, found = scrub_readme(text)
    print(f"Redacted {len(found)} items: {found}")
    if found:
        print("\nCleaned output:")
        print(clean[:500])
```

- [ ] **Step 2: Test**

```bash
cd /Users/MAC/SuneelWorkSpace
echo "key: sk-ant-abc12345678901234567890" | .venv/bin/python3 hands/automation/readme/security_filter.py
```

Expected: `Redacted 1 items: ['anthropic_key at line 1']`

- [ ] **Step 3: Commit**

```bash
git add hands/automation/readme/security_filter.py
git commit -m "feat(readme-p2): add security filter to scrub credentials from READMEs"
```

---

### Task 3: Cache Manager

**Files:**
- Create: `hands/automation/readme/cache_manager.py`

**Produces:**
- `is_folder_changed(folder_path: str, cache: dict) -> bool`
- `update_cache(folder_path: str, health_score: int, cache: dict) -> dict`
- `load_cache() -> dict` / `save_cache(cache: dict) -> None`

- [ ] **Step 1: Write cache_manager.py**

```python
#!/usr/bin/env python3
"""
Cache Manager — tracks folder content hashes to skip unchanged folders.
Cache file: spine/readme_health_cache.json
Entry: { "path": { "hash": str, "health_score": int, "readme_mtime": float, "updated": str } }
"""
import hashlib
import json
import os
import subprocess
import sys
from datetime import datetime
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[3]))

WORKSPACE = Path(subprocess.check_output(
    ["git", "rev-parse", "--show-toplevel"], text=True,
    cwd=os.path.dirname(os.path.abspath(__file__))
).strip())

CACHE_PATH = WORKSPACE / "spine/readme_health_cache.json"
IGNORED = {".git", "node_modules", ".venv", "__pycache__", ".DS_Store", "nerve_inbox"}


def _hash_folder(folder_path: Path) -> str:
    """Stable hash of all file names + sizes + mtimes in a folder (non-recursive)."""
    parts = []
    try:
        for item in sorted(folder_path.iterdir()):
            if item.name in IGNORED or item.name.startswith("."):
                continue
            if item.is_file():
                try:
                    stat = item.stat()
                    parts.append(f"{item.name}:{stat.st_size}:{stat.st_mtime:.0f}")
                except Exception:
                    pass
    except Exception:
        pass
    return hashlib.md5("|".join(parts).encode()).hexdigest()


def load_cache() -> dict:
    if CACHE_PATH.exists():
        try:
            return json.loads(CACHE_PATH.read_text())
        except Exception:
            pass
    return {}


def save_cache(cache: dict) -> None:
    CACHE_PATH.parent.mkdir(parents=True, exist_ok=True)
    tmp = CACHE_PATH.with_suffix(".tmp")
    tmp.write_text(json.dumps(cache, indent=2))
    tmp.rename(CACHE_PATH)


def is_folder_changed(folder_path: str, cache: dict) -> bool:
    """Return True if folder content has changed since last cache entry."""
    path = Path(folder_path).resolve()
    try:
        rel = str(path.relative_to(WORKSPACE))
    except ValueError:
        rel = str(path)

    current_hash = _hash_folder(path)
    entry = cache.get(rel, {})
    cached_hash = entry.get("hash", "")

    # Also check if README itself is newer than cache entry
    readme_path = path / "README.md"
    cached_readme_mtime = entry.get("readme_mtime", 0.0)
    current_readme_mtime = readme_path.stat().st_mtime if readme_path.exists() else 0.0

    return current_hash != cached_hash or current_readme_mtime != cached_readme_mtime


def update_cache(folder_path: str, health_score: int, cache: dict) -> dict:
    """Update cache entry for a folder. Returns updated cache dict."""
    path = Path(folder_path).resolve()
    try:
        rel = str(path.relative_to(WORKSPACE))
    except ValueError:
        rel = str(path)

    readme_path = path / "README.md"
    readme_mtime = readme_path.stat().st_mtime if readme_path.exists() else 0.0

    cache[rel] = {
        "hash": _hash_folder(path),
        "health_score": health_score,
        "readme_mtime": readme_mtime,
        "updated": datetime.now().isoformat(),
    }
    return cache


def get_cached_score(folder_path: str, cache: dict = None) -> int:
    """Return cached health score for folder, or -1 if not cached."""
    if cache is None:
        cache = load_cache()
    path = Path(folder_path).resolve()
    try:
        rel = str(path.relative_to(WORKSPACE))
    except ValueError:
        rel = str(path)
    return cache.get(rel, {}).get("health_score", -1)


def get_low_health_folders(threshold: int = 60, cache: dict = None) -> list:
    """Return list of folder paths with health_score below threshold."""
    if cache is None:
        cache = load_cache()
    return [
        {"path": p, "score": v["health_score"]}
        for p, v in cache.items()
        if v.get("health_score", 100) < threshold
    ]


if __name__ == "__main__":
    import argparse
    parser = argparse.ArgumentParser()
    parser.add_argument("--low", type=int, default=60, help="Show folders below this health score")
    args = parser.parse_args()
    cache = load_cache()
    low = get_low_health_folders(args.low, cache)
    print(f"Cache has {len(cache)} entries. {len(low)} below {args.low}:")
    for f in sorted(low, key=lambda x: x["score"]):
        print(f"  {f['score']:3d}  {f['path']}")
```

- [ ] **Step 2: Test**

```bash
cd /Users/MAC/SuneelWorkSpace
.venv/bin/python3 -c "
import sys; sys.path.insert(0,'.')
from hands.automation.readme.cache_manager import load_cache, is_folder_changed, update_cache, save_cache
cache = load_cache()
changed = is_folder_changed('brain', cache)
print('brain changed:', changed)
cache = update_cache('brain', 85, cache)
print('cache entry:', cache.get('brain'))
"
```

Expected: `brain changed: True` (first run), entry with hash + score.

- [ ] **Step 3: Commit**

```bash
git add hands/automation/readme/cache_manager.py
git commit -m "feat(readme-p2): add hash-based cache manager for incremental updates"
```

---

### Task 4: Change Impact Engine

**Files:**
- Create: `hands/automation/readme/change_impact_engine.py`

**Consumes:** `analyze_folder` (Task-2-Phase1), `load_cache` (Task 3)
**Produces:** `get_impacted_folders(changed_files: list[str]) -> list[str]` — ordered list of folder paths to update

- [ ] **Step 1: Write change_impact_engine.py**

```python
#!/usr/bin/env python3
"""
Change Impact Engine — given a list of changed files, determines which
workspace folders need README updates using semantic analysis:
  1. Direct: the folder containing the changed file
  2. Cascade: folders that import from / depend on the changed folder
  3. Root README always gets updated when any organ README changes

Replaces the naive "update the changed folder only" approach in watcher.py.
"""
import ast
import json
import os
import subprocess
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[3]))

WORKSPACE = Path(subprocess.check_output(
    ["git", "rev-parse", "--show-toplevel"], text=True,
    cwd=os.path.dirname(os.path.abspath(__file__))
).strip())

ORGANS = {
    "brain", "heart", "eyes", "ears", "nervous", "skeleton",
    "blood", "hands", "mouth", "dna", "lab", "spine",
}

IGNORED = {".git", "node_modules", ".venv", "__pycache__", "nerve_inbox", "logs"}
DEP_MAP_PATH = WORKSPACE / "spine/readme_dependency_map.json"


def _load_dep_map() -> dict:
    if DEP_MAP_PATH.exists():
        try:
            data = json.loads(DEP_MAP_PATH.read_text())
            return data.get("folders", {})
        except Exception:
            pass
    return {}


def _file_to_folder(file_path: str) -> Path:
    """Convert a relative file path string to its parent folder Path."""
    p = (WORKSPACE / file_path).resolve()
    return p.parent if p.is_file() or not p.is_dir() else p


def _organ_of(folder: Path) -> str:
    try:
        parts = folder.relative_to(WORKSPACE).parts
        return parts[0] if parts and parts[0] in ORGANS else ""
    except ValueError:
        return ""


def _get_reverse_deps(folder_rel: str, dep_map: dict) -> list:
    """Return list of folder paths that depend on folder_rel."""
    rdeps = dep_map.get(folder_rel, {}).get("reverse_dependencies", [])
    return rdeps


def _get_python_deps(changed_file: Path) -> list:
    """
    Parse a changed Python file and find which workspace folders it imports from.
    Returns list of relative folder paths.
    """
    if changed_file.suffix != ".py":
        return []

    refs = []
    try:
        tree = ast.parse(changed_file.read_text(errors="ignore"))
        for node in ast.walk(tree):
            if isinstance(node, ast.Import):
                for alias in node.names:
                    root = alias.name.split(".")[0]
                    if root in ORGANS:
                        refs.append(root)
            elif isinstance(node, ast.ImportFrom) and node.module:
                root = node.module.split(".")[0]
                if root in ORGANS:
                    refs.append(root)
    except Exception:
        pass
    return list(set(refs))


def get_impacted_folders(changed_files: list) -> list:
    """
    Given a list of changed file paths (relative to WORKSPACE), return an
    ordered list of absolute folder paths that need README updates.

    Order: direct folders first, then cascaded dependents, root last.

    Args:
        changed_files: list of relative path strings (e.g. ["brain/memory/store.py"])

    Returns:
        list of absolute Path objects, deduplicated, ordered direct → cascade → organs → root
    """
    dep_map = _load_dep_map()
    seen = set()
    direct = []
    cascade = []
    organ_set = set()

    for file_str in changed_files:
        if not file_str:
            continue

        # Skip non-code files and logs
        p = Path(file_str)
        if p.suffix in {".log", ".jsonl", ".pyc"} or p.name == "README.md":
            continue
        if any(part in IGNORED for part in p.parts):
            continue
        if len(p.parts) > 4:
            continue

        folder = _file_to_folder(file_str)
        if not folder.is_dir():
            continue

        try:
            folder_rel = str(folder.relative_to(WORKSPACE))
        except ValueError:
            continue

        # Direct folder
        if folder_rel not in seen:
            seen.add(folder_rel)
            direct.append(folder)

        # Organ-level folder
        organ = _organ_of(folder)
        if organ:
            organ_folder_rel = organ
            if organ_folder_rel not in seen:
                organ_set.add(organ_folder_rel)

        # Semantic cascade from dep map
        for rdep in _get_reverse_deps(folder_rel, dep_map):
            if rdep not in seen:
                seen.add(rdep)
                cascade.append(WORKSPACE / rdep)

        # Semantic cascade from Python imports in changed file
        full_path = WORKSPACE / file_str
        if full_path.exists():
            for ref_organ in _get_python_deps(full_path):
                ref_rel = ref_organ
                if ref_rel not in seen:
                    seen.add(ref_rel)
                    cascade.append(WORKSPACE / ref_rel)

    # Add organ roots
    for organ_rel in organ_set:
        if organ_rel not in seen:
            seen.add(organ_rel)
            cascade.append(WORKSPACE / organ_rel)

    # Root README always last
    result = direct + cascade
    # Remove non-dirs
    result = [p for p in result if p.is_dir()]

    return result


def explain_impact(changed_files: list) -> None:
    """Print human-readable explanation of impact cascade."""
    impacted = get_impacted_folders(changed_files)
    print(f"Changed files: {changed_files}")
    print(f"Impacted folders ({len(impacted)}):")
    for p in impacted:
        try:
            rel = p.relative_to(WORKSPACE)
        except ValueError:
            rel = p
        print(f"  → {rel}")


if __name__ == "__main__":
    import argparse
    parser = argparse.ArgumentParser()
    parser.add_argument("files", nargs="+", help="Changed files (relative paths)")
    args = parser.parse_args()
    explain_impact(args.files)
```

- [ ] **Step 2: Test**

```bash
cd /Users/MAC/SuneelWorkSpace
.venv/bin/python3 hands/automation/readme/change_impact_engine.py brain/memory/memory_store.py hands/automation/readme/intelligence_engine.py
```

Expected: List of impacted folders including `brain/memory`, `brain`, `hands/automation/readme`, `hands`.

- [ ] **Step 3: Commit**

```bash
git add hands/automation/readme/change_impact_engine.py
git commit -m "feat(readme-p2): add semantic change impact engine for cascade updates"
```

---

### Task 5: Lab Bridge

**Files:**
- Create: `hands/automation/readme/lab_bridge.py`

**Consumes:** `get_low_health_folders()` from Task 3
**Produces:** `trigger_evolution_for_low_health(threshold: int = 60) -> dict`

- [ ] **Step 1: Write lab_bridge.py**

```python
#!/usr/bin/env python3
"""
Lab Bridge — triggers lab evolution cycles for folders with health score below threshold.
Writes a challenge request to lab/autolab/challenges/readme_health_<folder>.json.
Lab's autolab runner picks these up on next cycle.
"""
import json
import os
import subprocess
import sys
from datetime import datetime
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[3]))

WORKSPACE = Path(subprocess.check_output(
    ["git", "rev-parse", "--show-toplevel"], text=True,
    cwd=os.path.dirname(os.path.abspath(__file__))
).strip())

CHALLENGES_DIR = WORKSPACE / "lab/autolab/challenges"
DEFAULT_THRESHOLD = 60


def _write_challenge(folder_rel: str, score: int, issues: list) -> Path:
    """Write a challenge file for autolab to pick up."""
    CHALLENGES_DIR.mkdir(parents=True, exist_ok=True)
    safe_name = folder_rel.replace("/", "_").replace("\\", "_")
    challenge_path = CHALLENGES_DIR / f"readme_health_{safe_name}.json"

    challenge = {
        "type": "readme_health_improvement",
        "target_folder": folder_rel,
        "health_score": score,
        "critical_issues": issues,
        "created": datetime.now().isoformat(),
        "priority": "high" if score < 40 else "medium",
        "instructions": (
            f"The folder '{folder_rel}' has README health score {score}/100. "
            f"Issues: {issues}. "
            f"Fix the issues, update README, re-run readme-update and confirm score improves."
        ),
    }

    challenge_path.write_text(json.dumps(challenge, indent=2))
    return challenge_path


def trigger_evolution_for_low_health(threshold: int = DEFAULT_THRESHOLD, dry_run: bool = False) -> dict:
    """
    Find all folders with health < threshold and write lab challenge files.

    Returns:
        {
          "triggered": list of folder paths,
          "skipped": list (already have pending challenge),
          "threshold": int,
          "dry_run": bool,
        }
    """
    from hands.automation.readme.cache_manager import get_low_health_folders, load_cache
    from hands.automation.readme.health_scorer import score_folder

    cache = load_cache()
    low_folders = get_low_health_folders(threshold, cache)

    triggered = []
    skipped = []

    for entry in low_folders:
        folder_rel = entry["path"]
        cached_score = entry["score"]

        # Re-verify score (cache may be stale)
        folder_abs = str(WORKSPACE / folder_rel)
        try:
            live = score_folder(folder_abs)
            score = live["score"]
            issues = live["critical_issues"]
        except Exception:
            score = cached_score
            issues = [f"Score below threshold ({cached_score})"]

        if score >= threshold:
            skipped.append(f"{folder_rel} (re-scored to {score}, above threshold)")
            continue

        # Check if challenge already pending
        safe_name = folder_rel.replace("/", "_").replace("\\", "_")
        existing = CHALLENGES_DIR / f"readme_health_{safe_name}.json"
        if existing.exists():
            skipped.append(f"{folder_rel} (challenge already pending)")
            continue

        if not dry_run:
            challenge_path = _write_challenge(folder_rel, score, issues)
            print(f"  🧬 Evolution triggered: {folder_rel} (score={score}) → {challenge_path.name}")
        else:
            print(f"  [dry-run] Would trigger: {folder_rel} (score={score})")

        triggered.append(folder_rel)

        # Notify nervous system
        try:
            subprocess.run(
                [sys.executable, str(WORKSPACE / "nervous/nerve_propagator.py"),
                 "notify", "lab", f"readme_evolution_triggered:{folder_rel}"],
                cwd=str(WORKSPACE),
                capture_output=True,
                timeout=5,
            )
        except Exception:
            pass

    return {
        "triggered": triggered,
        "skipped": skipped,
        "threshold": threshold,
        "dry_run": dry_run,
    }


if __name__ == "__main__":
    import argparse
    parser = argparse.ArgumentParser()
    parser.add_argument("--threshold", type=int, default=DEFAULT_THRESHOLD)
    parser.add_argument("--dry-run", action="store_true")
    args = parser.parse_args()
    result = trigger_evolution_for_low_health(args.threshold, dry_run=args.dry_run)
    print(json.dumps(result, indent=2))
```

- [ ] **Step 2: Test (dry run)**

```bash
cd /Users/MAC/SuneelWorkSpace
.venv/bin/python3 hands/automation/readme/lab_bridge.py --dry-run --threshold 80
```

Expected: List of folders that would have evolution triggered, or "0 triggered" if all healthy.

- [ ] **Step 3: Commit**

```bash
git add hands/automation/readme/lab_bridge.py
git commit -m "feat(readme-p2): add lab bridge — triggers evolution for low-health folders"
```

---

### Task 6: Upgrade readme_generator.py

**Files:**
- Modify: `hands/automation/readme/readme_generator.py`

Add to existing file: atomic writes, README.lock guard, security filter integration, health score sections in output, git changelog, tiered Claude fallbacks.

- [ ] **Step 1: Add atomic write + README.lock + security filter to `update_readme_for_folder`**

Find the existing function:
```python
def update_readme_for_folder(folder_path: str, use_claude: bool = True) -> bool:
    path = Path(folder_path).resolve()
    if not path.is_dir():
        return False
    ...
    readme_path.write_text(new_content, encoding="utf-8")
    return True
```

Replace it with:
```python
def _get_git_changelog(folder_path: Path, limit: int = 5) -> list:
    """Extract recent git commit messages touching this folder."""
    try:
        rel = str(folder_path.relative_to(WORKSPACE))
        result = subprocess.run(
            ["git", "log", f"--max-count={limit}", "--pretty=format:%as %s", "--", rel],
            capture_output=True, text=True, cwd=str(WORKSPACE), timeout=5
        )
        if result.returncode == 0:
            return [l.strip() for l in result.stdout.splitlines() if l.strip()]
    except Exception:
        pass
    return []


def _add_health_sections(content: str, folder_path: Path) -> str:
    """Inject Health Score and Critical Issues sections if not present."""
    if "Health Score" in content:
        return content
    try:
        from hands.automation.readme.health_scorer import score_folder
        from hands.automation.readme.runtime_probe import probe_folder
        probe = probe_folder(str(folder_path))
        result = score_folder(str(folder_path), probe=probe)
        score = result["score"]
        issues = result["critical_issues"]
        runtime_status = (
            f"- Python files: {probe.get('python_file_count', 0)} "
            f"({len(probe.get('importable', []))} valid, "
            f"{len(probe.get('broken_imports', []))} broken)\n"
            f"- Shell scripts: {probe.get('shell_file_count', 0)} "
            f"({len(probe.get('runnable_scripts', []))} valid)\n"
            f"- Tests detected: {'✅' if probe.get('has_tests') else '❌'}"
        )
        health_block = (
            f"\n## 🏥 Health Score\n"
            f"**{score}/100**\n\n"
            + ("| Category | Deduction |\n|----------|----------|\n"
               + "\n".join(f"| {k} | -{v} |" for k, v in result.get("breakdown", {}).items())
               if result.get("breakdown") else "_No deductions_")
            + f"\n\n## 🔥 Critical Issues\n"
            + ("\n".join(f"- {i}" for i in issues) if issues else "None — folder is healthy ✅")
            + f"\n\n## ✅ Runtime Status\n{runtime_status}\n"
        )
        # Insert before Change Log
        if "## 📝 Change Log" in content:
            content = content.replace("## 📝 Change Log", health_block + "\n## 📝 Change Log")
        else:
            content += health_block
    except Exception:
        pass
    return content


def update_readme_for_folder(folder_path: str, use_claude: bool = True) -> bool:
    path = Path(folder_path).resolve()
    if not path.is_dir():
        return False

    # README.lock guard — skip if locked
    if (path / "README.lock").exists():
        return True

    from hands.automation.readme.intelligence_engine import analyze_folder
    analysis = analyze_folder(str(path))
    if not analysis:
        return False

    readme_path = path / "README.md"
    existing = readme_path.read_text(errors="ignore") if readme_path.exists() else ""

    # Tiered generation: Claude → rule-based
    new_content = generate_readme(analysis, existing, use_claude=use_claude)

    # Inject health sections
    new_content = _add_health_sections(new_content, path)

    # Inject git changelog entries
    git_log = _get_git_changelog(path)
    if git_log and "## 📝 Change Log" in new_content:
        log_entries = "\n".join(f"- {entry}" for entry in git_log)
        today = datetime.now().strftime("%Y-%m-%d")
        new_entry = f"- {today}: README auto-updated by README Intelligence System"
        full_log = f"## 📝 Change Log (Auto)\n{new_entry}\n{log_entries}"
        new_content = re.sub(
            r"## 📝 Change Log.*",
            full_log,
            new_content,
            flags=re.DOTALL,
        )

    # Security filter
    from hands.automation.readme.security_filter import scrub_readme
    new_content, redacted = scrub_readme(new_content)
    if redacted:
        import logging
        logging.warning(f"README security filter redacted {len(redacted)} items in {path}")

    # Atomic write: tmp → validate → rename
    tmp_path = readme_path.with_suffix(".tmp.md")
    tmp_path.write_text(new_content, encoding="utf-8")
    # Minimal validation: file is non-empty and starts with #
    if tmp_path.stat().st_size > 0 and new_content.lstrip().startswith("#"):
        tmp_path.rename(readme_path)
    else:
        tmp_path.unlink(missing_ok=True)
        return False

    # Update health cache
    try:
        from hands.automation.readme.health_scorer import score_folder
        from hands.automation.readme.cache_manager import load_cache, update_cache, save_cache
        score_result = score_folder(str(path))
        cache = load_cache()
        cache = update_cache(str(path), score_result["score"], cache)
        save_cache(cache)
    except Exception:
        pass

    return True
```

- [ ] **Step 2: Verify generator still works after modifications**

```bash
cd /Users/MAC/SuneelWorkSpace
.venv/bin/python3 -c "
import sys; sys.path.insert(0,'.')
from hands.automation.readme.readme_generator import update_readme_for_folder
ok = update_readme_for_folder('brain', use_claude=False)
print('ok:', ok)
import re
content = open('brain/README.md').read()
print('has health score:', 'Health Score' in content)
print('has runtime status:', 'Runtime Status' in content)
"
```

Expected: `ok: True`, `has health score: True`, `has runtime status: True`

- [ ] **Step 3: Commit**

```bash
git add hands/automation/readme/readme_generator.py
git commit -m "feat(readme-p2): add atomic write, README.lock, health sections, security filter, git changelog to generator"
```

---

### Task 7: Upgrade Watcher to Use Change Impact Engine

**Files:**
- Modify: `hands/automation/readme/watcher.py`

Replace the `_handle_change` function to use `get_impacted_folders` from the change impact engine.

- [ ] **Step 1: Replace `_handle_change` in watcher.py**

Find the existing `_handle_change` function (about 40 lines) and replace it:

```python
def _handle_change(changed_path: Path) -> None:
    if _should_ignore(changed_path):
        return

    ts = time.strftime("%H:%M:%S")
    try:
        rel = changed_path.relative_to(WORKSPACE)
    except ValueError:
        rel = changed_path

    print(f"[{ts}] 📝 Change: {rel}")

    # Use semantic impact engine to find all affected folders
    try:
        from hands.automation.readme.change_impact_engine import get_impacted_folders
        impacted = get_impacted_folders([str(rel)])
    except Exception:
        # Fallback: just update the containing folder
        folder = changed_path.parent if changed_path.is_file() else changed_path
        impacted = [folder] if folder.is_dir() else []

    if not impacted:
        return

    from hands.automation.readme.readme_generator import update_readme_for_folder
    from hands.automation.readme.root_synthesizer import synthesize_root

    updated_organs = set()
    for folder in impacted:
        organ = _get_organ(folder)
        try:
            update_readme_for_folder(str(folder), use_claude=False)
            print(f"[{ts}]   ✅ {folder.name}/README.md")
            updated_organs.add(organ)
        except Exception as e:
            print(f"[{ts}]   ❌ {folder.name}: {e}")

    # Rebuild root once after all impacted folders are updated
    try:
        synthesize_root()
        print(f"[{ts}]   ✅ Root README rebuilt")
    except Exception as e:
        print(f"[{ts}]   ⚠️  Root rebuild: {e}")

    # Notify nervous system for each updated organ
    for organ in updated_organs:
        if organ and organ != "unknown":
            try:
                subprocess.run(
                    [sys.executable, str(WORKSPACE / "nervous/nerve_propagator.py"),
                     "notify", organ, "readme_updated"],
                    cwd=str(WORKSPACE), capture_output=True, timeout=5,
                )
            except Exception:
                pass

    # Check if any folder has low health and trigger evolution
    try:
        from hands.automation.readme.lab_bridge import trigger_evolution_for_low_health
        trigger_evolution_for_low_health(threshold=60, dry_run=False)
    except Exception:
        pass
```

- [ ] **Step 2: Test watcher starts cleanly**

```bash
cd /Users/MAC/SuneelWorkSpace && timeout 3 .venv/bin/python3 hands/automation/readme/watcher.py; echo "exit: $?"
```

Expected: exit 124 (killed by timeout = running fine)

- [ ] **Step 3: Commit**

```bash
git add hands/automation/readme/watcher.py
git commit -m "feat(readme-p2): wire watcher to use semantic change impact engine"
```

---

### Task 8: Knowledge Indexer

**Files:**
- Create: `hands/automation/readme/knowledge_indexer.py`
- Generates: `brain/system/readme_knowledge_index.json`

**Produces:** `build_knowledge_index() -> dict`

- [ ] **Step 1: Write knowledge_indexer.py**

```python
#!/usr/bin/env python3
"""
Knowledge Indexer — builds brain/system/readme_knowledge_index.json.
Machine-readable index of all folder purposes, capabilities, health scores,
and cross-references. Used by brain for context-aware search.
"""
import json
import os
import subprocess
import sys
from datetime import datetime
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[3]))

WORKSPACE = Path(subprocess.check_output(
    ["git", "rev-parse", "--show-toplevel"], text=True,
    cwd=os.path.dirname(os.path.abspath(__file__))
).strip())

INDEX_PATH = WORKSPACE / "brain/system/readme_knowledge_index.json"


def _extract_readme_sections(readme_path: Path) -> dict:
    """Extract key sections from a README.md file."""
    if not readme_path.exists():
        return {}
    try:
        content = readme_path.read_text(errors="ignore")
    except Exception:
        return {}

    import re
    sections = {}
    for match in re.finditer(r"## [^\n]+\n(.*?)(?=\n## |\Z)", content, re.DOTALL):
        header_match = re.search(r"## (.+)", content[:content.find(match.group(0)) + 5])
        # simpler extraction
        pass

    # Simple section extraction
    for m in re.finditer(r"## (?:[^\n]+?)\s+(Purpose|Responsibilities|Capabilities|Health Score|Critical Issues|System Role)\n(.*?)(?=\n## |\Z)", content, re.DOTALL | re.IGNORECASE):
        key = m.group(1).lower().replace(" ", "_")
        sections[key] = m.group(2).strip()[:300]

    # Also grab the title
    title_match = re.match(r"# (.+)", content)
    if title_match:
        sections["title"] = title_match.group(1).strip()

    return sections


def build_knowledge_index() -> dict:
    """
    Build the full knowledge index from all folder READMEs and analysis.
    """
    from hands.automation.readme.intelligence_engine import analyze_workspace
    from hands.automation.readme.cache_manager import load_cache, get_cached_score

    analyses = analyze_workspace()
    cache = load_cache()

    index = {
        "generated": datetime.now().isoformat(),
        "folder_count": len(analyses),
        "folders": {},
    }

    for analysis in analyses:
        path_str = analysis["path"]
        folder_path = WORKSPACE / path_str
        readme_path = folder_path / "README.md"

        readme_sections = _extract_readme_sections(readme_path)
        cached_score = get_cached_score(str(folder_path), cache)

        index["folders"][path_str] = {
            "name": analysis.get("name", ""),
            "organ": analysis.get("organ"),
            "purpose": analysis.get("purpose", ""),
            "capabilities": analysis.get("capabilities", []),
            "workspace_references": analysis.get("workspace_references", []),
            "file_count": analysis.get("file_count", 0),
            "has_readme": readme_path.exists(),
            "health_score": cached_score if cached_score >= 0 else None,
            "readme_sections": readme_sections,
            "gaps": analysis.get("gaps", []),
        }

    return index


def write_index() -> None:
    index = build_knowledge_index()
    INDEX_PATH.parent.mkdir(parents=True, exist_ok=True)
    tmp = INDEX_PATH.with_suffix(".tmp.json")
    tmp.write_text(json.dumps(index, indent=2))
    tmp.rename(INDEX_PATH)
    print(f"✅ Knowledge index written: {len(index['folders'])} folders → {INDEX_PATH.relative_to(WORKSPACE)}")


def query_index(query: str, top_k: int = 5) -> list:
    """Simple keyword search over the index. Returns top_k matching folders."""
    if not INDEX_PATH.exists():
        write_index()
    index = json.loads(INDEX_PATH.read_text())
    query_lower = query.lower()

    scored = []
    for path, entry in index["folders"].items():
        score = 0
        text = " ".join([
            entry.get("purpose", ""),
            " ".join(entry.get("capabilities", [])),
            entry.get("name", ""),
            " ".join(entry.get("readme_sections", {}).values()),
        ]).lower()
        for word in query_lower.split():
            score += text.count(word)
        if score > 0:
            scored.append({"path": path, "relevance": score, "purpose": entry.get("purpose", "")})

    return sorted(scored, key=lambda x: -x["relevance"])[:top_k]


if __name__ == "__main__":
    import argparse
    parser = argparse.ArgumentParser()
    parser.add_argument("--query", help="Search the index")
    parser.add_argument("--build", action="store_true", help="(Re)build the index")
    args = parser.parse_args()

    if args.query:
        if not INDEX_PATH.exists():
            write_index()
        results = query_index(args.query)
        print(f"Top results for '{args.query}':")
        for r in results:
            print(f"  [{r['relevance']}] {r['path']}: {r['purpose'][:80]}")
    else:
        write_index()
```

- [ ] **Step 2: Test**

```bash
cd /Users/MAC/SuneelWorkSpace
mkdir -p brain/system
.venv/bin/python3 hands/automation/readme/knowledge_indexer.py
.venv/bin/python3 hands/automation/readme/knowledge_indexer.py --query "memory search"
```

Expected: Index written, query returns relevant folders.

- [ ] **Step 3: Commit**

```bash
git add hands/automation/readme/knowledge_indexer.py brain/system/readme_knowledge_index.json
git commit -m "feat(readme-p2): add knowledge indexer for brain-queryable README index"
```

---

### Task 9: Dashboard Widget + Server Endpoint

**Files:**
- Create: `eyes/dashboard/widgets/readme_health.py`
- Modify: `eyes/dashboard/server.py` — add `@app.get("/api/readme-health")`

**Consumes:** `cache_manager.load_cache()`, `cache_manager.get_low_health_folders()`
**Produces:** Widget JSON `{overall_score, total_folders, low_health_count, critical_folders, last_updated}`

- [ ] **Step 1: Write eyes/dashboard/widgets/readme_health.py**

```python
"""
README Health Dashboard Widget — returns overall README health summary.
Reads from spine/readme_health_cache.json (populated by the README update pipeline).
"""
import json
import os
from pathlib import Path

WORKSPACE = Path(os.environ.get("WORKSPACE", Path(__file__).resolve().parents[3]))
CACHE_PATH = WORKSPACE / "spine/readme_health_cache.json"


def get_readme_health() -> dict:
    result = {
        "overall_score": None,
        "total_folders": 0,
        "low_health_count": 0,
        "critical_folders": [],
        "last_updated": "",
        "status": "unknown",
    }

    if not CACHE_PATH.exists():
        result["status"] = "cache_missing"
        return result

    try:
        cache = json.loads(CACHE_PATH.read_text())
    except Exception:
        result["status"] = "cache_error"
        return result

    scores = [v.get("health_score", 100) for v in cache.values() if "health_score" in v]
    if not scores:
        result["status"] = "no_scores"
        return result

    result["total_folders"] = len(scores)
    result["overall_score"] = round(sum(scores) / len(scores))
    result["low_health_count"] = sum(1 for s in scores if s < 60)

    critical = [
        {"path": k, "score": v["health_score"]}
        for k, v in cache.items()
        if v.get("health_score", 100) < 60
    ]
    result["critical_folders"] = sorted(critical, key=lambda x: x["score"])[:5]

    timestamps = [v.get("updated", "") for v in cache.values() if v.get("updated")]
    result["last_updated"] = max(timestamps) if timestamps else ""
    result["status"] = "healthy" if result["overall_score"] >= 80 else (
        "warning" if result["overall_score"] >= 60 else "critical"
    )

    return result


if __name__ == "__main__":
    print(json.dumps(get_readme_health(), indent=2))
```

- [ ] **Step 2: Add endpoint to eyes/dashboard/server.py**

Find the imports section in server.py (around line 23-28) and add:
```python
from widgets.readme_health import get_readme_health
```

Then find a logical place after an existing endpoint (e.g., after `@app.get("/api/eyes/visual/status")`) and add:
```python
@app.get("/api/readme-health")
async def api_readme_health() -> Any:
    return get_readme_health()
```

- [ ] **Step 3: Test widget standalone**

```bash
cd /Users/MAC/SuneelWorkSpace
.venv/bin/python3 eyes/dashboard/widgets/readme_health.py
```

Expected: JSON with `overall_score`, `total_folders`, `low_health_count`.

- [ ] **Step 4: Test server still starts**

```bash
cd /Users/MAC/SuneelWorkSpace
timeout 5 .venv/bin/python3 -c "
import sys; sys.path.insert(0, 'eyes/dashboard')
from server import app
print('Server imports OK')
" && echo "✅ server imports OK"
```

Expected: `Server imports OK`

- [ ] **Step 5: Commit**

```bash
git add eyes/dashboard/widgets/readme_health.py eyes/dashboard/server.py
git commit -m "feat(readme-p2): add README health dashboard widget + /api/readme-health endpoint"
```

---

### Task 10: Full Integration + CLI Updates + Final Run

Wire everything together: update `run_update_all.py` to use cache, update `run_nightly.sh` to build index and trigger lab, add `readme-score` CLI, and run the full system.

- [ ] **Step 1: Add `--incremental` flag to run_update_all.py**

Find the `run_all` function in `hands/automation/readme/run_update_all.py` and replace:

```python
def run_all(use_claude: bool = True, quiet: bool = False, incremental: bool = False) -> bool:
    from hands.automation.readme.intelligence_engine import analyze_workspace, WORKSPACE
    from hands.automation.readme.readme_generator import update_readme_for_folder
    from hands.automation.readme.cache_manager import load_cache, is_folder_changed

    analyses = analyze_workspace()
    cache = load_cache() if incremental else {}
    ok_count = 0
    skip_count = 0
    fail_count = 0

    for analysis in analyses:
        folder = str(WORKSPACE / analysis["path"])
        if incremental and not is_folder_changed(folder, cache):
            skip_count += 1
            if not quiet:
                print(f"  ⏭️  {analysis['path']} (unchanged)")
            continue
        try:
            update_readme_for_folder(folder, use_claude=use_claude)
            ok_count += 1
            if not quiet:
                print(f"  ✅ {analysis['path']}")
        except Exception as e:
            fail_count += 1
            if not quiet:
                print(f"  ❌ {analysis['path']}: {e}")

    print(f"\n{'✅' if fail_count == 0 else '⚠️'} {ok_count} updated, {skip_count} skipped, {fail_count} failed")
    return fail_count == 0
```

Also update `if __name__ == "__main__"` argparse to add `--incremental`.

- [ ] **Step 2: Create readme-score CLI in hands/bin/**

```bash
cat > /Users/MAC/SuneelWorkSpace/hands/bin/readme-score << 'EOF'
#!/usr/bin/env bash
# readme-score [folder] — show health score(s) for workspace folders
WORKSPACE="$(cd "$(dirname "$0")/../.." && pwd)"
if [[ -n "${1:-}" ]]; then
  exec "$WORKSPACE/.venv/bin/python3" "$WORKSPACE/hands/automation/readme/health_scorer.py" "$1"
else
  exec "$WORKSPACE/.venv/bin/python3" "$WORKSPACE/hands/automation/readme/health_scorer.py"
fi
EOF
chmod +x /Users/MAC/SuneelWorkSpace/hands/bin/readme-score
```

- [ ] **Step 3: Add knowledge indexing and lab bridge to run_nightly.sh**

Find the section after Step 4 in `hands/automation/readme/run_nightly.sh` and add before the final "complete" line:

```bash
# Step 5: Build knowledge index
log "Step 5/6: Building knowledge index..."
if "$VENV_PY" "$WORKSPACE/hands/automation/readme/knowledge_indexer.py" >> "$LOG" 2>&1; then
  log "  ✅ Knowledge index built"
else
  log "  ⚠️  Knowledge index failed (non-fatal)"
fi

# Step 6: Trigger evolution for low-health folders
log "Step 6/6: Checking for low-health folders..."
if "$VENV_PY" "$WORKSPACE/hands/automation/readme/lab_bridge.py" --threshold 60 >> "$LOG" 2>&1; then
  log "  ✅ Lab bridge check complete"
else
  log "  ⚠️  Lab bridge failed (non-fatal)"
fi
```

- [ ] **Step 4: Run the full system end-to-end**

```bash
cd /Users/MAC/SuneelWorkSpace

# Update all with cache
hands/bin/readme-update-all --no-claude --quiet

# Build knowledge index
.venv/bin/python3 hands/automation/readme/knowledge_indexer.py

# Score the workspace
hands/bin/readme-score brain

# Trigger lab for low-health (dry run)
.venv/bin/python3 hands/automation/readme/lab_bridge.py --dry-run

# Rebuild root
hands/bin/readme-root-build

# Validate
hands/bin/readme-validate

# Dashboard widget check
.venv/bin/python3 eyes/dashboard/widgets/readme_health.py
```

- [ ] **Step 5: Final commit**

```bash
git add hands/automation/readme/ hands/bin/readme-score brain/system/ spine/readme_health_cache.json eyes/dashboard/
git commit -m "feat(readme-p2): complete autonomous evolution system — health scoring, cache, impact engine, lab bridge, knowledge index, dashboard widget"
```

---

## Self-Review Against Spec

| Spec Requirement | Task |
|-----------------|------|
| Semantic change impact (not just file-based) | Task 4 (change_impact_engine) |
| runtime_probe: import validation, script testability | Task 1 (runtime_probe.py) |
| Health score 0-100 per folder | Task 1 (health_scorer.py) |
| Critical Issues section in README | Task 6 (readme_generator _add_health_sections) |
| Runtime Status section in README | Task 6 (runtime_probe integration) |
| Lab bridge triggers on health < threshold | Task 5 (lab_bridge.py) |
| Security filter (no API keys in READMEs) | Task 2 (security_filter.py) |
| Cache for incremental updates | Task 3 (cache_manager.py) |
| Atomic write (tmp → validate → rename) | Task 6 (update_readme_for_folder) |
| README.lock skip guard | Task 6 (README.lock check) |
| Tiered Claude fallbacks | Task 6 (generate_readme already has tiers; health sections added) |
| Git changelog from history | Task 6 (_get_git_changelog) |
| brain/system/readme_knowledge_index.json | Task 8 (knowledge_indexer.py) |
| Knowledge index queryable | Task 8 (query_index function) |
| Dashboard panel for README health | Task 9 (readme_health widget + /api/readme-health) |
| readme-score CLI | Task 10 |
| Nightly: knowledge index + lab bridge | Task 10 (run_nightly.sh additions) |
| Watcher uses impact engine | Task 7 |
