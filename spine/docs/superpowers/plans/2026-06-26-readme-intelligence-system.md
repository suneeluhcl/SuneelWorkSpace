# README Intelligence + Enforcement System — Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Build a complete, self-updating README intelligence system that analyzes every workspace folder, generates living documentation, enforces freshness before git push, and propagates changes through the nervous system.

**Architecture:** A Python engine traverses the 12-organ workspace, analyzes each folder's contents and code structure, generates Claude-formatted READMEs via Claude CLI, tracks dependencies in a JSON graph, watches for file changes in real time, and blocks unsafe pushes via a git pre-push hook. All updates emit nervous system events.

**Tech Stack:** Python 3.x (stdlib: ast, json, subprocess, os, pathlib, hashlib, re, argparse), watchdog (install into `.venv`), bash, launchd plists, git hooks.

## Global Constraints

- All Python runs under `/Users/MAC/SuneelWorkSpace/.venv/bin/python3`
- Workspace root: `/Users/MAC/SuneelWorkSpace` (auto-detected via `git rev-parse`)
- Ignored paths: `.git`, `node_modules`, `.venv`, `__pycache__`, `logs`, `*.log`, `.DS_Store`
- 12 organs: brain, heart, eyes, ears, nervous, skeleton, blood, hands, mouth, dna, lab, spine
- Nervous system CLI: `python3 nervous/nerve_propagator.py notify <organ> "readme_updated"`
- NEVER overwrite `<!-- MANUAL SECTION START -->…<!-- MANUAL SECTION END -->` blocks
- All CLI commands symlinked into `hands/bin/` (never copied)
- Log file: `blood/logs/readme_intelligence.log`
- Dependency map: `spine/readme_dependency_map.json`

---

## File Structure

| File | Responsibility |
|------|---------------|
| `hands/automation/readme/__init__.py` | Package marker |
| `hands/automation/readme/intelligence_engine.py` | Traverse workspace → per-folder JSON analysis |
| `hands/automation/readme/readme_generator.py` | JSON → README markdown (Claude CLI + rule-based fallback) |
| `hands/automation/readme/root_synthesizer.py` | Aggregate all READMEs → root README.md |
| `hands/automation/readme/consistency_engine.py` | Diff README vs folder state; auto-fix |
| `hands/automation/readme/validator.py` | Pre-push validation; exits 1 on failure |
| `hands/automation/readme/watcher.py` | Watchdog-based real-time file watcher |
| `hands/automation/readme/run_nightly.sh` | Nightly full-refresh shell script |
| `hands/automation/git/pre_push_guard.sh` | Git pre-push hook (blocks push on failure) |
| `hands/automation/launchd/com.suneelworkspace.readme.plist` | macOS LaunchAgent for nightly run |
| `spine/readme_dependency_map.json` | folder → deps + reverse deps graph |
| `hands/bin/readme-update-all` | CLI: update all READMEs |
| `hands/bin/readme-update` | CLI: update single folder README |
| `hands/bin/readme-root-build` | CLI: rebuild root README |
| `hands/bin/readme-validate` | CLI: run validator |
| `hands/bin/readme-watch-start` | CLI: start real-time watcher |
| `hands/bin/git-safe-push` | CLI: validate + push |

---

### Task 1: Scaffold + Dependencies

**Files:**
- Create: `hands/automation/readme/__init__.py`
- Create: `hands/automation/readme/requirements.txt`
- Create: `hands/automation/git/` (dir)

- [ ] **Step 1: Install watchdog into workspace venv**

```bash
/Users/MAC/SuneelWorkSpace/.venv/bin/pip install watchdog
```

Expected: `Successfully installed watchdog-X.Y.Z`

- [ ] **Step 2: Create package scaffold**

```bash
mkdir -p /Users/MAC/SuneelWorkSpace/hands/automation/readme
mkdir -p /Users/MAC/SuneelWorkSpace/hands/automation/git
touch /Users/MAC/SuneelWorkSpace/hands/automation/readme/__init__.py
echo "watchdog" > /Users/MAC/SuneelWorkSpace/hands/automation/readme/requirements.txt
```

- [ ] **Step 3: Verify**

```bash
/Users/MAC/SuneelWorkSpace/.venv/bin/python3 -c "import watchdog; print('ok')"
```

Expected: `ok`

- [ ] **Step 4: Commit**

```bash
git add hands/automation/readme/ hands/automation/git/
git commit -m "feat(readme): scaffold readme intelligence system"
```

---

### Task 2: Intelligence Engine — Folder Analyzer

**Files:**
- Create: `hands/automation/readme/intelligence_engine.py`

**Produces:**
- `analyze_folder(folder_path: str) -> dict` — returns structured JSON for one folder
- `analyze_workspace(workspace_root: str) -> list[dict]` — returns list of folder analyses
- `build_dependency_map(analyses: list[dict]) -> dict` — returns `{folder: {deps: [...], rdeps: [...]}}`

- [ ] **Step 1: Write intelligence_engine.py**

```python
#!/usr/bin/env python3
"""
README Intelligence Engine — analyzes every workspace folder and produces
structured JSON describing purpose, contents, dependencies, and gaps.
"""
import ast
import json
import os
import re
import subprocess
from pathlib import Path
from typing import Optional

WORKSPACE = Path(subprocess.check_output(
    ["git", "rev-parse", "--show-toplevel"], text=True,
    cwd=os.path.dirname(os.path.abspath(__file__))
).strip())

IGNORED_DIRS = {".git", "node_modules", ".venv", "__pycache__", "logs", ".DS_Store"}
IGNORED_EXTS = {".log", ".pyc", ".pyo", ".DS_Store"}

ORGANS = {
    "brain", "heart", "eyes", "ears", "nervous", "skeleton",
    "blood", "hands", "mouth", "dna", "lab", "spine"
}


def _classify_organ(folder_path: Path) -> Optional[str]:
    rel = folder_path.relative_to(WORKSPACE)
    parts = rel.parts
    if parts and parts[0] in ORGANS:
        return parts[0]
    return None


def _scan_python_imports(py_file: Path) -> list[str]:
    try:
        tree = ast.parse(py_file.read_text(errors="ignore"))
        imports = []
        for node in ast.walk(tree):
            if isinstance(node, ast.Import):
                imports.extend(n.name for n in node.names)
            elif isinstance(node, ast.ImportFrom) and node.module:
                imports.append(node.module)
        return imports
    except Exception:
        return []


def _scan_json_keys(json_file: Path) -> list[str]:
    try:
        data = json.loads(json_file.read_text(errors="ignore"))
        if isinstance(data, dict):
            return list(data.keys())[:20]
    except Exception:
        pass
    return []


def _infer_purpose(folder_path: Path, files: list[str], imports: list[str]) -> str:
    name = folder_path.name.lower()
    purpose_hints = {
        "brain": "vector memory, context search, anticipation",
        "heart": "goal scheduling, task queues, model routing",
        "eyes": "web dashboard, visual monitoring",
        "ears": "external monitors, RSS, briefings",
        "nervous": "event propagation, MCP connectors",
        "skeleton": "shared rules, safety gates, agent instructions",
        "blood": "telemetry, logs, SQLite databases",
        "hands": "scripts, automation, CI, launchd",
        "mouth": "communication dispatch, Mail, iMessage",
        "dna": "identity prompts, adapt loop, scorers",
        "lab": "autolab experiments, self-evolution",
        "spine": "health state, workspace index, registers",
    }
    for organ, hint in purpose_hints.items():
        if name == organ or str(folder_path).endswith(f"/{organ}"):
            return hint

    # heuristic inference
    if any("test" in f for f in files):
        return "test suite"
    if any("server" in f or "api" in f for f in files):
        return "API/server component"
    if any("router" in f or "dispatch" in f for f in files):
        return "routing/dispatch layer"
    if any(f.endswith(".sh") for f in files):
        return "automation scripts"
    if any("config" in f or "settings" in f for f in files):
        return "configuration"
    return "workspace component"


def analyze_folder(folder_path: str) -> dict:
    path = Path(folder_path)
    if not path.is_dir():
        return {}

    files = []
    subdirs = []
    all_imports = []
    json_structures = []
    script_names = []
    config_files = []

    for item in sorted(path.iterdir()):
        if item.name in IGNORED_DIRS or item.suffix in IGNORED_EXTS:
            continue
        if item.is_dir():
            subdirs.append(item.name)
        else:
            files.append(item.name)
            if item.suffix == ".py":
                imports = _scan_python_imports(item)
                all_imports.extend(imports)
                if "__main__" in item.read_text(errors="ignore"):
                    script_names.append(item.name)
            elif item.suffix == ".json":
                json_structures.append({item.name: _scan_json_keys(item)})
                config_files.append(item.name)
            elif item.suffix in (".yaml", ".yml", ".toml", ".sh", ".plist"):
                config_files.append(item.name)

    # detect organ-level workspace references in imports
    workspace_refs = sorted({
        imp.split(".")[0] for imp in all_imports
        if imp.split(".")[0] in ORGANS or
        any(organ in imp for organ in ORGANS)
    })

    organ = _classify_organ(path)
    purpose = _infer_purpose(path, files + subdirs, all_imports)
    rel_path = str(path.relative_to(WORKSPACE))

    existing_readme = None
    readme_path = path / "README.md"
    if readme_path.exists():
        content = readme_path.read_text(errors="ignore")
        existing_readme = {
            "exists": True,
            "lines": len(content.splitlines()),
            "has_manual_sections": "<!-- MANUAL SECTION START -->" in content,
        }
    else:
        existing_readme = {"exists": False}

    return {
        "path": rel_path,
        "name": path.name,
        "organ": organ,
        "purpose": purpose,
        "files": files,
        "subdirectories": subdirs,
        "python_imports": sorted(set(all_imports))[:30],
        "workspace_references": workspace_refs,
        "config_files": config_files,
        "json_structures": json_structures[:5],
        "script_names": script_names,
        "file_count": len(files),
        "subdir_count": len(subdirs),
        "existing_readme": existing_readme,
        "gaps": _detect_gaps(files, subdirs),
        "capabilities": _detect_capabilities(files, subdirs, all_imports),
    }


def _detect_gaps(files: list[str], subdirs: list[str]) -> list[str]:
    gaps = []
    all_names = [f.lower() for f in files + subdirs]
    if not any("test" in n for n in all_names):
        gaps.append("No test coverage detected")
    if not any("readme" in n for n in all_names):
        gaps.append("Missing README.md")
    if not any(n.endswith(".py") for n in files) and not any(n.endswith(".sh") for n in files):
        gaps.append("No executable code found")
    return gaps


def _detect_capabilities(files: list[str], subdirs: list[str], imports: list[str]) -> list[str]:
    caps = []
    all_names = [f.lower() for f in files + subdirs]
    if any("api" in n or "server" in n for n in all_names):
        caps.append("HTTP API")
    if any("db" in n or "sqlite" in n or "chroma" in n for n in all_names + imports):
        caps.append("Database storage")
    if any("schedule" in n or "cron" in n or "plist" in n for n in all_names):
        caps.append("Scheduled automation")
    if any("claude" in i or "anthropic" in i for i in imports):
        caps.append("Claude AI integration")
    if any("webhook" in n or "dispatch" in n for n in all_names):
        caps.append("Event dispatch")
    return caps


def analyze_workspace(workspace_root: Optional[str] = None) -> list[dict]:
    root = Path(workspace_root) if workspace_root else WORKSPACE
    analyses = []

    for dirpath, dirnames, _ in os.walk(root):
        # prune ignored
        dirnames[:] = [d for d in dirnames if d not in IGNORED_DIRS]
        path = Path(dirpath)
        rel = path.relative_to(root)
        # skip root itself and deeply nested paths (>3 levels)
        if rel == Path(".") or len(rel.parts) > 3:
            continue
        result = analyze_folder(str(path))
        if result:
            analyses.append(result)

    return sorted(analyses, key=lambda x: x["path"])


def build_dependency_map(analyses: list[dict]) -> dict:
    dep_map = {}
    path_set = {a["path"] for a in analyses}

    for analysis in analyses:
        path = analysis["path"]
        deps = []
        # cross-reference workspace_references to known organ paths
        for ref in analysis.get("workspace_references", []):
            if ref in ORGANS and ref != path.split("/")[0]:
                deps.append(ref)
        dep_map[path] = {"dependencies": sorted(set(deps)), "reverse_dependencies": []}

    # build reverse deps
    for path, data in dep_map.items():
        for dep in data["dependencies"]:
            # find entries whose path starts with dep
            for other_path in dep_map:
                if other_path.startswith(dep + "/") or other_path == dep:
                    if path not in dep_map[other_path]["reverse_dependencies"]:
                        dep_map[other_path]["reverse_dependencies"].append(path)

    return dep_map


if __name__ == "__main__":
    import argparse
    parser = argparse.ArgumentParser(description="Analyze workspace folders")
    parser.add_argument("folder", nargs="?", help="Single folder to analyze (default: all)")
    parser.add_argument("--json", action="store_true", help="Output raw JSON")
    args = parser.parse_args()

    if args.folder:
        result = analyze_folder(args.folder)
        print(json.dumps(result, indent=2))
    else:
        results = analyze_workspace()
        if args.json:
            print(json.dumps(results, indent=2))
        else:
            print(f"Analyzed {len(results)} folders")
            for r in results:
                print(f"  {r['path']} ({r['file_count']} files, organ={r['organ']})")
```

- [ ] **Step 2: Quick smoke test**

```bash
cd /Users/MAC/SuneelWorkSpace && .venv/bin/python3 hands/automation/readme/intelligence_engine.py brain
```

Expected: JSON output with `path`, `name`, `organ`, `purpose`, `files` etc.

- [ ] **Step 3: Commit**

```bash
git add hands/automation/readme/intelligence_engine.py
git commit -m "feat(readme): add workspace intelligence engine"
```

---

### Task 3: Dependency Map Builder

**Files:**
- Modify: `spine/readme_dependency_map.json` (create/update)

**Consumes:** `analyze_workspace()`, `build_dependency_map()` from Task 2

- [ ] **Step 1: Generate initial dependency map**

```bash
cd /Users/MAC/SuneelWorkSpace && .venv/bin/python3 -c "
from hands.automation.readme.intelligence_engine import analyze_workspace, build_dependency_map
import json, sys
sys.path.insert(0, '.')
analyses = analyze_workspace()
dep_map = build_dependency_map(analyses)
out = {'generated': __import__('datetime').datetime.now().isoformat(), 'folders': dep_map}
open('spine/readme_dependency_map.json', 'w').write(json.dumps(out, indent=2))
print(f'Wrote map for {len(dep_map)} folders')
"
```

- [ ] **Step 2: Verify file exists**

```bash
python3 -c "import json; d=json.load(open('spine/readme_dependency_map.json')); print(f'{len(d[\"folders\"])} entries')"
```

- [ ] **Step 3: Commit**

```bash
git add spine/readme_dependency_map.json
git commit -m "feat(readme): add initial dependency map"
```

---

### Task 4: README Generator

**Files:**
- Create: `hands/automation/readme/readme_generator.py`

**Consumes:** folder analysis dict from Task 2  
**Produces:** `generate_readme(analysis: dict, existing_content: str = "") -> str` — markdown string

- [ ] **Step 1: Write readme_generator.py**

```python
#!/usr/bin/env python3
"""
README Generator — takes folder analysis JSON and produces a structured README.md.
Tries Claude CLI first; falls back to rule-based generation if unavailable.
Preserves <!-- MANUAL SECTION START/END --> blocks.
"""
import json
import os
import re
import subprocess
import shutil
from datetime import datetime
from pathlib import Path

MANUAL_BLOCK_RE = re.compile(
    r"(<!-- MANUAL SECTION START -->.*?<!-- MANUAL SECTION END -->)",
    re.DOTALL
)

README_TEMPLATE = """\
# 📁 {name}

## 🧠 Purpose
{purpose}

## ⚙️ Responsibilities
{responsibilities}

## 🔗 System Role
{system_role}

## 📂 Contents
{contents}

## 🔄 Dependencies
{dependencies}

## 🧩 Interactions
{interactions}

## 📈 Current Capabilities
{capabilities}

## ⚠️ Gaps & Weaknesses
{gaps}

## 🚀 Suggested Enhancements
{enhancements}

## 🔗 Connected Modules
{connected_modules}

## 📝 Change Log (Auto)
- {date}: README auto-generated by README Intelligence System
"""


def _extract_manual_blocks(content: str) -> list[str]:
    return MANUAL_BLOCK_RE.findall(content)


def _restore_manual_blocks(new_content: str, manual_blocks: list[str]) -> str:
    for block in manual_blocks:
        if block not in new_content:
            new_content += f"\n\n{block}\n"
    return new_content


def _build_contents_section(analysis: dict) -> str:
    lines = []
    for f in analysis.get("files", []):
        lines.append(f"- `{f}`")
    for d in analysis.get("subdirectories", []):
        lines.append(f"- `{d}/` *(directory)*")
    return "\n".join(lines) if lines else "*(empty)*"


def _build_dependencies_section(analysis: dict) -> str:
    deps = analysis.get("workspace_references", [])
    if not deps:
        return "None detected"
    return "\n".join(f"- `{d}/`" for d in deps)


def _build_connected_modules(analysis: dict) -> str:
    refs = analysis.get("workspace_references", [])
    if not refs:
        return "*(no cross-organ references detected)*"
    lines = []
    for ref in refs:
        lines.append(f"- [`../{ref}/README.md`](../{ref}/README.md)")
    return "\n".join(lines)


def _build_capabilities_section(analysis: dict) -> str:
    caps = analysis.get("capabilities", [])
    if not caps:
        return "- Basic workspace component"
    return "\n".join(f"- {c}" for c in caps)


def _build_gaps_section(analysis: dict) -> str:
    gaps = analysis.get("gaps", [])
    if not gaps:
        return "None identified"
    return "\n".join(f"- {g}" for g in gaps)


def _build_responsibilities(analysis: dict) -> str:
    lines = []
    organ = analysis.get("organ")
    organ_resp = {
        "brain": ["Vector memory search", "Context anticipation", "Research aggregation"],
        "heart": ["Goal scheduling", "Task queue management", "Model fallback routing"],
        "eyes": ["Web dashboard serving", "Visual monitoring", "Screenshot healing"],
        "ears": ["External RSS monitoring", "GitHub event watching", "Morning briefing build"],
        "nervous": ["Event propagation", "MCP server connections", "Nerve routing"],
        "skeleton": ["Agent rules enforcement", "Safety gate checks", "Shared instructions"],
        "blood": ["Telemetry logging", "SQLite database management", "Anomaly detection"],
        "hands": ["Script execution", "LaunchD automation", "CI runner"],
        "mouth": ["Communication dispatch", "Mail/iMessage delivery"],
        "dna": ["Identity prompt management", "Adapt loop scoring"],
        "lab": ["Experiment execution", "Self-evolution cycles"],
        "spine": ["Health state tracking", "Workspace index"],
    }
    if organ and organ in organ_resp:
        lines = organ_resp[organ]
    else:
        files = analysis.get("files", [])
        if any(f.endswith(".py") for f in files):
            lines.append("Python module execution")
        if any(f.endswith(".sh") for f in files):
            lines.append("Shell script automation")
        if any(f.endswith(".json") for f in files):
            lines.append("Configuration management")
    return "\n".join(f"- {r}" for r in lines) if lines else "- General workspace operations"


def _rule_based_readme(analysis: dict, existing_content: str = "") -> str:
    manual_blocks = _extract_manual_blocks(existing_content)
    organ = analysis.get("organ", "")
    system_role = (
        f"Part of the **{organ}** organ in the 12-organ SuneelWorkSpace architecture."
        if organ else "Supporting component within SuneelWorkSpace."
    )

    readme = README_TEMPLATE.format(
        name=analysis.get("name", "Unknown"),
        purpose=analysis.get("purpose", "Workspace component"),
        responsibilities=_build_responsibilities(analysis),
        system_role=system_role,
        contents=_build_contents_section(analysis),
        dependencies=_build_dependencies_section(analysis),
        interactions=f"Emits `readme_updated` events to nervous system on change.",
        capabilities=_build_capabilities_section(analysis),
        gaps=_build_gaps_section(analysis),
        enhancements="- Add integration tests\n- Add metrics collection",
        connected_modules=_build_connected_modules(analysis),
        date=datetime.now().strftime("%Y-%m-%d"),
    )

    return _restore_manual_blocks(readme, manual_blocks)


def _claude_readme(analysis: dict, existing_content: str = "") -> str:
    if not shutil.which("claude"):
        return None

    manual_blocks = _extract_manual_blocks(existing_content)
    prompt = f"""You are a technical documentation writer for a 12-organ AI workspace called SuneelWorkSpace.

Generate a README.md for this folder based on the analysis below.

ANALYSIS JSON:
{json.dumps(analysis, indent=2)}

OUTPUT FORMAT (use exactly these sections with emoji headers):
# 📁 <Folder Name>
## 🧠 Purpose
## ⚙️ Responsibilities
## 🔗 System Role
## 📂 Contents
## 🔄 Dependencies
## 🧩 Interactions
## 📈 Current Capabilities
## ⚠️ Gaps & Weaknesses
## 🚀 Suggested Enhancements
## 🔗 Connected Modules
## 📝 Change Log (Auto)

Rules:
- Be concise and technical
- Reference the 12-organ architecture where relevant
- List actual file names in Contents
- Do not invent capabilities not evident in the analysis
- Add: `- {datetime.now().strftime('%Y-%m-%d')}: README auto-generated` to Change Log

Output ONLY the markdown. No preamble or explanation."""

    try:
        result = subprocess.run(
            ["claude", "--print", prompt],
            capture_output=True, text=True, timeout=60
        )
        if result.returncode == 0 and result.stdout.strip():
            content = result.stdout.strip()
            return _restore_manual_blocks(content, manual_blocks)
    except Exception:
        pass
    return None


def generate_readme(analysis: dict, existing_content: str = "", use_claude: bool = True) -> str:
    if use_claude:
        result = _claude_readme(analysis, existing_content)
        if result:
            return result
    return _rule_based_readme(analysis, existing_content)


def update_readme_for_folder(folder_path: str, use_claude: bool = True) -> bool:
    path = Path(folder_path)
    if not path.is_dir():
        return False

    from hands.automation.readme.intelligence_engine import analyze_folder
    analysis = analyze_folder(folder_path)
    if not analysis:
        return False

    readme_path = path / "README.md"
    existing = readme_path.read_text(errors="ignore") if readme_path.exists() else ""

    new_content = generate_readme(analysis, existing, use_claude=use_claude)
    readme_path.write_text(new_content, encoding="utf-8")
    return True


if __name__ == "__main__":
    import argparse
    import sys
    sys.path.insert(0, str(Path(__file__).parent.parent.parent.parent))
    parser = argparse.ArgumentParser()
    parser.add_argument("folder", help="Folder to generate README for")
    parser.add_argument("--no-claude", action="store_true")
    args = parser.parse_args()
    ok = update_readme_for_folder(args.folder, use_claude=not args.no_claude)
    print("✅ README updated" if ok else "❌ Failed")
    sys.exit(0 if ok else 1)
```

- [ ] **Step 2: Test rule-based generation (no Claude needed)**

```bash
cd /Users/MAC/SuneelWorkSpace && .venv/bin/python3 -c "
import sys; sys.path.insert(0,'.')
from hands.automation.readme.intelligence_engine import analyze_folder
from hands.automation.readme.readme_generator import generate_readme
a = analyze_folder('brain')
print(generate_readme(a, use_claude=False)[:500])
"
```

Expected: Markdown starting with `# 📁 brain`

- [ ] **Step 3: Commit**

```bash
git add hands/automation/readme/readme_generator.py
git commit -m "feat(readme): add README generator with Claude CLI + rule-based fallback"
```

---

### Task 5: Root Synthesizer

**Files:**
- Create: `hands/automation/readme/root_synthesizer.py`

**Consumes:** all organ README files  
**Produces:** `synthesize_root() -> None` — writes to `README.md`

- [ ] **Step 1: Write root_synthesizer.py**

```python
#!/usr/bin/env python3
"""
Root README Synthesizer — reads all organ READMEs and rebuilds the workspace root README.md.
Preserves MANUAL SECTION blocks. Appends architecture table and capability summary.
"""
import json
import os
import re
import subprocess
import sys
from datetime import datetime
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent.parent.parent))

WORKSPACE = Path(subprocess.check_output(
    ["git", "rev-parse", "--show-toplevel"], text=True
).strip())

ORGANS = ["brain", "heart", "eyes", "ears", "nervous", "skeleton",
          "blood", "hands", "mouth", "dna", "lab", "spine"]

MANUAL_BLOCK_RE = re.compile(
    r"(<!-- MANUAL SECTION START -->.*?<!-- MANUAL SECTION END -->)",
    re.DOTALL
)

ORGAN_EMOJI = {
    "brain": "🧠", "heart": "❤️", "eyes": "👁️", "ears": "👂",
    "nervous": "⚡", "skeleton": "🦴", "blood": "🩸", "hands": "🤲",
    "mouth": "🗣️", "dna": "🧬", "lab": "🧪", "spine": "🫀",
}

def _extract_section(readme_content: str, section: str) -> str:
    pattern = rf"## [^\n]*{re.escape(section)}[^\n]*\n(.*?)(?=\n## |\Z)"
    match = re.search(pattern, readme_content, re.DOTALL)
    if match:
        return match.group(1).strip()[:300]
    return ""


def _get_organ_summary(organ: str) -> dict:
    readme_path = WORKSPACE / organ / "README.md"
    if not readme_path.exists():
        return {"purpose": "Not yet documented", "capabilities": "Unknown"}

    content = readme_path.read_text(errors="ignore")
    purpose = _extract_section(content, "Purpose") or _extract_section(content, "purpose")
    caps = _extract_section(content, "Capabilities") or _extract_section(content, "Capabilit")
    return {"purpose": purpose[:200], "capabilities": caps[:200]}


def synthesize_root() -> None:
    existing = (WORKSPACE / "README.md").read_text(errors="ignore") \
        if (WORKSPACE / "README.md").exists() else ""
    manual_blocks = MANUAL_BLOCK_RE.findall(existing)

    # Load dep map for stats
    dep_map_path = WORKSPACE / "spine/readme_dependency_map.json"
    dep_stats = {}
    if dep_map_path.exists():
        try:
            dep_stats = json.loads(dep_map_path.read_text())
        except Exception:
            pass

    summaries = {organ: _get_organ_summary(organ) for organ in ORGANS}

    arch_table = "| Organ | Role | Purpose |\n|-------|------|---------|"
    for organ in ORGANS:
        emoji = ORGAN_EMOJI.get(organ, "📁")
        purpose = summaries[organ]["purpose"].split("\n")[0][:80].replace("|", "\\|")
        arch_table += f"\n| {emoji} **{organ}** | `{organ}/` | {purpose} |"

    cap_lines = []
    for organ in ORGANS:
        caps = summaries[organ]["capabilities"]
        if caps:
            cap_lines.append(f"- **{organ}**: {caps.split(chr(10))[0][:100]}")

    total_folders = len(dep_stats.get("folders", {}))

    root_readme = f"""# 🧠 SuneelWorkSpace

> **Autonomous AI Engineering Workspace** — a living 12-organ system that thinks, learns, and self-heals.

## 🏗️ Architecture

{arch_table}

## 📈 System Capabilities

{"chr(10)".join(cap_lines) if cap_lines else "Run `readme-update-all` to populate."}

## 🔧 Quick Commands

```bash
readme-update-all          # Regenerate all READMEs
readme-update <folder>     # Update single folder
readme-root-build          # Rebuild this file
readme-watch-start         # Start real-time watcher
readme-validate            # Validate before push
git-safe-push              # Validate + push
```

## 📊 System Stats

- **Organs**: {len(ORGANS)} active
- **Documented folders**: {total_folders}
- **Last root rebuild**: {datetime.now().strftime("%Y-%m-%d %H:%M")}

## 🔗 Key Entrypoints

- [`skeleton/rules/AGENT_SYSTEM.md`](skeleton/rules/AGENT_SYSTEM.md) — agent operating rules
- [`spine/state/CURRENT_STATE.json`](spine/state/CURRENT_STATE.json) — live workspace state
- [`spine/readme_dependency_map.json`](spine/readme_dependency_map.json) — folder dependency graph
- [`blood/logs/readme_intelligence.log`](blood/logs/readme_intelligence.log) — README update log

## 📝 Change Log (Auto)

- {datetime.now().strftime("%Y-%m-%d")}: Root README rebuilt by README Intelligence System
"""

    # restore manual blocks
    for block in manual_blocks:
        if block not in root_readme:
            root_readme += f"\n\n{block}\n"

    (WORKSPACE / "README.md").write_text(root_readme, encoding="utf-8")
    print(f"✅ Root README rebuilt ({len(root_readme)} chars)")


if __name__ == "__main__":
    synthesize_root()
```

- [ ] **Step 2: Test**

```bash
cd /Users/MAC/SuneelWorkSpace && .venv/bin/python3 hands/automation/readme/root_synthesizer.py
head -30 README.md
```

Expected: Root README with architecture table.

- [ ] **Step 3: Commit**

```bash
git add hands/automation/readme/root_synthesizer.py README.md
git commit -m "feat(readme): add root synthesizer + rebuild root README"
```

---

### Task 6: Consistency Engine

**Files:**
- Create: `hands/automation/readme/consistency_engine.py`

**Produces:** `check_consistency(folder_path: str) -> dict` returning `{ok: bool, issues: list, fixed: bool}`

- [ ] **Step 1: Write consistency_engine.py**

```python
#!/usr/bin/env python3
"""
Consistency Engine — compares README content against actual folder state.
Detects drift and auto-fixes by triggering readme_generator.
"""
import os
import re
import sys
from datetime import datetime
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent.parent.parent))

REQUIRED_SECTIONS = [
    "Purpose", "Responsibilities", "System Role", "Contents",
    "Dependencies", "Capabilities", "Gaps", "Change Log"
]


def _missing_sections(readme_content: str) -> list[str]:
    missing = []
    for section in REQUIRED_SECTIONS:
        if f"## " not in readme_content or section.lower() not in readme_content.lower():
            missing.append(section)
    return missing


def _readme_lists_nonexistent_files(readme_content: str, folder_path: Path) -> list[str]:
    stale = []
    # find backtick-wrapped filenames in Contents section
    contents_match = re.search(r"## 📂 Contents(.*?)(?=\n## |\Z)", readme_content, re.DOTALL)
    if not contents_match:
        return []
    section = contents_match.group(1)
    for m in re.finditer(r"`([^`/]+\.[a-z]+)`", section):
        fname = m.group(1)
        if not (folder_path / fname).exists():
            stale.append(fname)
    return stale


def _readme_is_stale(readme_path: Path, folder_path: Path) -> bool:
    if not readme_path.exists():
        return True
    readme_mtime = readme_path.stat().st_mtime
    for item in folder_path.iterdir():
        if item.name == "README.md":
            continue
        if item.stat().st_mtime > readme_mtime:
            return True
    return False


def check_consistency(folder_path: str) -> dict:
    path = Path(folder_path)
    readme_path = path / "README.md"
    issues = []

    if not readme_path.exists():
        issues.append("README.md missing")
        return {"ok": False, "issues": issues, "fixed": False, "path": folder_path}

    content = readme_path.read_text(errors="ignore")

    missing = _missing_sections(content)
    if missing:
        issues.append(f"Missing sections: {missing}")

    stale_refs = _readme_lists_nonexistent_files(content, path)
    if stale_refs:
        issues.append(f"Stale file references: {stale_refs}")

    if _readme_is_stale(readme_path, path):
        issues.append("README older than folder contents")

    return {"ok": len(issues) == 0, "issues": issues, "fixed": False, "path": folder_path}


def fix_consistency(folder_path: str, use_claude: bool = False) -> dict:
    result = check_consistency(folder_path)
    if result["ok"]:
        return result

    from hands.automation.readme.readme_generator import update_readme_for_folder
    try:
        update_readme_for_folder(folder_path, use_claude=use_claude)
        result["fixed"] = True
        result["ok"] = True
    except Exception as e:
        result["fix_error"] = str(e)

    return result


def check_all_consistency(workspace_root: str = None) -> list[dict]:
    import subprocess
    if not workspace_root:
        workspace_root = subprocess.check_output(
            ["git", "rev-parse", "--show-toplevel"], text=True
        ).strip()

    root = Path(workspace_root)
    results = []
    ignored = {".git", "node_modules", ".venv", "__pycache__"}

    for dirpath, dirnames, _ in os.walk(root):
        dirnames[:] = [d for d in dirnames if d not in ignored]
        path = Path(dirpath)
        rel = path.relative_to(root)
        if rel == Path(".") or len(rel.parts) > 3:
            continue
        results.append(check_consistency(str(path)))

    return results


if __name__ == "__main__":
    import argparse
    import json
    parser = argparse.ArgumentParser()
    parser.add_argument("folder", nargs="?", help="Folder to check (default: all)")
    parser.add_argument("--fix", action="store_true")
    args = parser.parse_args()

    if args.folder:
        fn = fix_consistency if args.fix else check_consistency
        result = fn(args.folder)
        print(json.dumps(result, indent=2))
        sys.exit(0 if result["ok"] else 1)
    else:
        results = check_all_consistency()
        ok = sum(1 for r in results if r["ok"])
        bad = [r for r in results if not r["ok"]]
        print(f"✅ {ok} OK  ❌ {len(bad)} need attention")
        for r in bad:
            print(f"  {r['path']}: {r['issues']}")
        sys.exit(0 if not bad else 1)
```

- [ ] **Step 2: Test**

```bash
cd /Users/MAC/SuneelWorkSpace && .venv/bin/python3 hands/automation/readme/consistency_engine.py brain
```

Expected: JSON with `ok`, `issues` fields.

- [ ] **Step 3: Commit**

```bash
git add hands/automation/readme/consistency_engine.py
git commit -m "feat(readme): add consistency engine with drift detection"
```

---

### Task 7: Validator

**Files:**
- Create: `hands/automation/readme/validator.py`

**Produces:** `validate_pre_push(changed_files: list[str]) -> bool` — returns True if valid, exits 1 if not

- [ ] **Step 1: Write validator.py**

```python
#!/usr/bin/env python3
"""
Pre-push README Validator — checks that all changed folders have updated READMEs.
Exits 1 (blocks push) if any condition fails.
"""
import os
import subprocess
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent.parent.parent))

WORKSPACE = Path(subprocess.check_output(
    ["git", "rev-parse", "--show-toplevel"], text=True
).strip())

IGNORED = {".git", "node_modules", ".venv", "__pycache__"}


def _get_changed_files(base_ref: str = "origin/main") -> list[str]:
    try:
        result = subprocess.run(
            ["git", "diff", "--name-only", f"HEAD...{base_ref}"],
            capture_output=True, text=True, cwd=WORKSPACE
        )
        if result.returncode == 0:
            return [f.strip() for f in result.stdout.splitlines() if f.strip()]
    except Exception:
        pass
    # fallback: staged changes
    try:
        result = subprocess.run(
            ["git", "diff", "--name-only", "--cached"],
            capture_output=True, text=True, cwd=WORKSPACE
        )
        return [f.strip() for f in result.stdout.splitlines() if f.strip()]
    except Exception:
        return []


def _files_to_folders(changed_files: list[str]) -> set[Path]:
    folders = set()
    for f in changed_files:
        path = WORKSPACE / f
        folder = path.parent if path.suffix else path
        if folder.is_dir() and not any(p in IGNORED for p in folder.parts):
            folders.add(folder)
    return folders


def _readme_up_to_date(folder: Path) -> bool:
    readme = folder / "README.md"
    if not readme.exists():
        return False
    readme_mtime = readme.stat().st_mtime
    for item in folder.iterdir():
        if item.name == "README.md" or item.name.startswith("."):
            continue
        if item.is_file() and item.stat().st_mtime > readme_mtime:
            return False
    return True


def _root_readme_newer_than_children() -> bool:
    root_readme = WORKSPACE / "README.md"
    if not root_readme.exists():
        return False
    root_mtime = root_readme.stat().st_mtime
    for organ in ["brain", "heart", "eyes", "ears", "nervous", "skeleton",
                  "blood", "hands", "mouth", "dna", "lab", "spine"]:
        organ_readme = WORKSPACE / organ / "README.md"
        if organ_readme.exists():
            if organ_readme.stat().st_mtime > root_mtime:
                return False
    return True


def _has_required_sections(folder: Path) -> bool:
    readme = folder / "README.md"
    if not readme.exists():
        return False
    content = readme.read_text(errors="ignore")
    required = ["Purpose", "Contents", "Change Log"]
    return all(s in content for s in required)


def validate_pre_push(changed_files: list[str] = None) -> bool:
    if changed_files is None:
        changed_files = _get_changed_files()

    if not changed_files:
        print("✅ No changed files detected — validation skipped.")
        return True

    failures = []
    changed_folders = _files_to_folders(changed_files)

    for folder in sorted(changed_folders):
        rel = folder.relative_to(WORKSPACE)

        if not (folder / "README.md").exists():
            failures.append(f"❌ {rel}: Missing README.md")
            continue

        if not _readme_up_to_date(folder):
            failures.append(f"❌ {rel}: README.md older than folder contents")

        if not _has_required_sections(folder):
            failures.append(f"❌ {rel}: README.md missing required sections")

    if not _root_readme_newer_than_children():
        failures.append("❌ Root README.md is stale (older than an organ README)")

    if failures:
        print("\n📛 README VALIDATION FAILED\n")
        for f in failures:
            print(f"  {f}")
        print("\nRun `readme-update-all && readme-root-build` to fix.\n")
        return False

    print(f"✅ README validation passed ({len(changed_folders)} folders checked)")
    return True


if __name__ == "__main__":
    import argparse
    parser = argparse.ArgumentParser(description="Validate READMEs before push")
    parser.add_argument("--files", nargs="*", help="Specific files to validate against")
    args = parser.parse_args()

    ok = validate_pre_push(args.files)
    sys.exit(0 if ok else 1)
```

- [ ] **Step 2: Test**

```bash
cd /Users/MAC/SuneelWorkSpace && .venv/bin/python3 hands/automation/readme/validator.py
```

Expected: Validation pass or list of failures (no crash).

- [ ] **Step 3: Commit**

```bash
git add hands/automation/readme/validator.py
git commit -m "feat(readme): add pre-push validator"
```

---

### Task 8: Real-Time Watcher

**Files:**
- Create: `hands/automation/readme/watcher.py`

**Produces:** Long-running process that reacts to file changes

- [ ] **Step 1: Write watcher.py**

```python
#!/usr/bin/env python3
"""
Real-time README watcher — uses watchdog to detect file changes and trigger README updates.
Falls back to polling if watchdog unavailable.
"""
import os
import subprocess
import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent.parent.parent))

WORKSPACE = Path(subprocess.check_output(
    ["git", "rev-parse", "--show-toplevel"], text=True
).strip())

IGNORED_DIRS = {".git", "node_modules", ".venv", "__pycache__", "logs"}
IGNORED_NAMES = {"README.md", ".DS_Store"}


def _get_organ(path: Path) -> str:
    try:
        rel = path.relative_to(WORKSPACE)
        return rel.parts[0] if rel.parts else "unknown"
    except Exception:
        return "unknown"


def _handle_change(changed_path: Path):
    if changed_path.name in IGNORED_NAMES:
        return
    folder = changed_path.parent if changed_path.is_file() else changed_path
    organ = _get_organ(folder)

    print(f"[{time.strftime('%H:%M:%S')}] Change detected: {changed_path.relative_to(WORKSPACE)}")

    # Update this folder's README
    try:
        from hands.automation.readme.readme_generator import update_readme_for_folder
        update_readme_for_folder(str(folder), use_claude=False)
        print(f"  ✅ Updated {folder.relative_to(WORKSPACE)}/README.md")
    except Exception as e:
        print(f"  ❌ README update failed: {e}")
        return

    # Rebuild root README
    try:
        from hands.automation.readme.root_synthesizer import synthesize_root
        synthesize_root()
        print(f"  ✅ Root README rebuilt")
    except Exception as e:
        print(f"  ⚠️ Root rebuild failed: {e}")

    # Notify nervous system
    try:
        subprocess.run(
            [sys.executable, str(WORKSPACE / "nervous/nerve_propagator.py"),
             "notify", organ, "readme_updated"],
            cwd=WORKSPACE, capture_output=True, timeout=5
        )
    except Exception:
        pass


def _watchdog_watch():
    from watchdog.observers import Observer
    from watchdog.events import FileSystemEventHandler

    class ReadmeHandler(FileSystemEventHandler):
        def __init__(self):
            self._debounce: dict[str, float] = {}

        def _debounced(self, path: str) -> bool:
            now = time.time()
            last = self._debounce.get(path, 0)
            if now - last < 2.0:
                return True
            self._debounce[path] = now
            return False

        def on_modified(self, event):
            if not event.is_directory:
                p = Path(event.src_path)
                if any(part in IGNORED_DIRS for part in p.parts):
                    return
                if not self._debounced(event.src_path):
                    _handle_change(p)

        def on_created(self, event):
            self.on_modified(event)

    observer = Observer()
    handler = ReadmeHandler()
    observer.schedule(handler, str(WORKSPACE), recursive=True)
    observer.start()
    print(f"👁️  Watching {WORKSPACE} for changes (watchdog mode)...")
    try:
        while True:
            time.sleep(1)
    except KeyboardInterrupt:
        observer.stop()
    observer.join()


def _poll_watch(interval: int = 5):
    print(f"👁️  Polling {WORKSPACE} every {interval}s (fallback mode)...")
    state: dict[str, float] = {}

    def snapshot():
        s = {}
        for dirpath, dirnames, filenames in os.walk(WORKSPACE):
            dirnames[:] = [d for d in dirnames if d not in IGNORED_DIRS]
            for fname in filenames:
                if fname in IGNORED_NAMES:
                    continue
                fp = Path(dirpath) / fname
                try:
                    s[str(fp)] = fp.stat().st_mtime
                except Exception:
                    pass
        return s

    state = snapshot()
    while True:
        time.sleep(interval)
        new_state = snapshot()
        for path, mtime in new_state.items():
            if state.get(path, 0) != mtime:
                _handle_change(Path(path))
                break  # handle one at a time to avoid cascade
        state = new_state


if __name__ == "__main__":
    try:
        import watchdog
        _watchdog_watch()
    except ImportError:
        print("⚠️  watchdog not installed — using polling fallback")
        _poll_watch()
```

- [ ] **Step 2: Test (quick, then Ctrl-C)**

```bash
cd /Users/MAC/SuneelWorkSpace && timeout 5 .venv/bin/python3 hands/automation/readme/watcher.py || true
```

Expected: Print "Watching..." then exit cleanly.

- [ ] **Step 3: Commit**

```bash
git add hands/automation/readme/watcher.py
git commit -m "feat(readme): add real-time file watcher with watchdog + polling fallback"
```

---

### Task 9: Nightly Shell Script + LaunchAgent

**Files:**
- Create: `hands/automation/readme/run_nightly.sh`
- Create: `hands/automation/launchd/com.suneelworkspace.readme.plist`

- [ ] **Step 1: Write run_nightly.sh**

```bash
#!/usr/bin/env bash
# Nightly README refresh — updates all READMEs, rebuilds root, validates.
set -euo pipefail

WORKSPACE="$(cd "$(dirname "$0")/../../.." && pwd)"
VENV_PY="$WORKSPACE/.venv/bin/python3"
LOG="$WORKSPACE/blood/logs/readme_intelligence.log"
TIMESTAMP="$(date '+%Y-%m-%d %H:%M:%S')"

log() { echo "[$TIMESTAMP] $*" | tee -a "$LOG"; }

log "=== Nightly README refresh started ==="

# Step 1: Update all READMEs
log "Step 1/4: Updating all folder READMEs..."
"$VENV_PY" "$WORKSPACE/hands/automation/readme/run_update_all.py" --no-claude \
  2>>"$LOG" && log "  ✅ All READMEs updated" || log "  ⚠️ Some READMEs failed (non-fatal)"

# Step 2: Rebuild root README
log "Step 2/4: Rebuilding root README..."
"$VENV_PY" "$WORKSPACE/hands/automation/readme/root_synthesizer.py" \
  2>>"$LOG" && log "  ✅ Root README rebuilt" || log "  ❌ Root rebuild failed"

# Step 3: Rebuild dependency map
log "Step 3/4: Rebuilding dependency map..."
"$VENV_PY" -c "
import sys; sys.path.insert(0,'$WORKSPACE')
from hands.automation.readme.intelligence_engine import analyze_workspace, build_dependency_map
import json, datetime
analyses = analyze_workspace()
dep_map = build_dependency_map(analyses)
out = {'generated': datetime.datetime.now().isoformat(), 'folders': dep_map}
open('$WORKSPACE/spine/readme_dependency_map.json','w').write(json.dumps(out,indent=2))
print(f'Wrote {len(dep_map)} entries')
" 2>>"$LOG" && log "  ✅ Dependency map rebuilt" || log "  ⚠️ Dep map failed"

# Step 4: Validate
log "Step 4/4: Running validation..."
"$VENV_PY" "$WORKSPACE/hands/automation/readme/validator.py" \
  2>>"$LOG" && log "  ✅ Validation passed" || log "  ❌ Validation failed (see log)"

# Notify nervous system
"$VENV_PY" "$WORKSPACE/nervous/nerve_propagator.py" notify spine "nightly_readme_refresh" \
  2>>/dev/null || true

log "=== Nightly README refresh complete ==="
```

- [ ] **Step 2: Write the helper run_update_all.py**

```python
#!/usr/bin/env python3
"""Bulk README updater — runs generate for every non-trivial folder."""
import argparse
import os
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent.parent.parent))

from hands.automation.readme.intelligence_engine import analyze_workspace, WORKSPACE, IGNORED_DIRS
from hands.automation.readme.readme_generator import update_readme_for_folder

def run_all(use_claude: bool = True):
    analyses = analyze_workspace()
    ok = 0
    fail = 0
    for analysis in analyses:
        folder = str(WORKSPACE / analysis["path"])
        try:
            update_readme_for_folder(folder, use_claude=use_claude)
            ok += 1
            print(f"  ✅ {analysis['path']}")
        except Exception as e:
            fail += 1
            print(f"  ❌ {analysis['path']}: {e}")
    print(f"\n{ok} updated, {fail} failed")
    return fail == 0

if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--no-claude", action="store_true")
    args = parser.parse_args()
    ok = run_all(use_claude=not args.no_claude)
    sys.exit(0 if ok else 1)
```

- [ ] **Step 3: Write LaunchAgent plist**

```xml
<?xml version="1.0" encoding="UTF-8"?>
<!DOCTYPE plist PUBLIC "-//Apple//DTD PLIST 1.0//EN" "http://www.apple.com/DTDs/PropertyList-1.0.dtd">
<plist version="1.0">
<dict>
  <key>Label</key>
  <string>com.suneelworkspace.readme</string>
  <key>ProgramArguments</key>
  <array>
    <string>/bin/bash</string>
    <string>/Users/MAC/SuneelWorkSpace/hands/automation/readme/run_nightly.sh</string>
  </array>
  <key>StartCalendarInterval</key>
  <dict>
    <key>Hour</key>
    <integer>0</integer>
    <key>Minute</key>
    <integer>0</integer>
  </dict>
  <key>StandardOutPath</key>
  <string>/Users/MAC/SuneelWorkSpace/blood/logs/readme-nightly.out.log</string>
  <key>StandardErrorPath</key>
  <string>/Users/MAC/SuneelWorkSpace/blood/logs/readme-nightly.err.log</string>
  <key>WorkingDirectory</key>
  <string>/Users/MAC/SuneelWorkSpace</string>
  <key>RunAtLoad</key>
  <false/>
</dict>
</plist>
```

- [ ] **Step 4: Make script executable and test**

```bash
chmod +x /Users/MAC/SuneelWorkSpace/hands/automation/readme/run_nightly.sh
bash /Users/MAC/SuneelWorkSpace/hands/automation/readme/run_nightly.sh 2>&1 | head -20
```

- [ ] **Step 5: Commit**

```bash
git add hands/automation/readme/run_nightly.sh hands/automation/readme/run_update_all.py hands/automation/launchd/com.suneelworkspace.readme.plist
git commit -m "feat(readme): add nightly script and LaunchAgent plist"
```

---

### Task 10: Git Pre-Push Guard

**Files:**
- Create: `hands/automation/git/pre_push_guard.sh`

- [ ] **Step 1: Write pre_push_guard.sh**

```bash
#!/usr/bin/env bash
# Git pre-push hook — blocks push if README validation fails.
# Install: ln -sf ~/SuneelWorkSpace/hands/automation/git/pre_push_guard.sh .git/hooks/pre-push
set -uo pipefail

WORKSPACE="$(git rev-parse --show-toplevel)"
VENV_PY="$WORKSPACE/.venv/bin/python3"
LOG="$WORKSPACE/blood/logs/readme_intelligence.log"

echo "🔍 README pre-push validation..."

# Read push target from stdin (git provides it)
while read local_ref local_sha remote_ref remote_sha; do
  # get changed files vs remote
  CHANGED=$(git diff --name-only "$remote_sha".."$local_sha" 2>/dev/null || \
            git diff --name-only HEAD~1 2>/dev/null || echo "")

  if [ -z "$CHANGED" ]; then
    echo "✅ No file changes detected — skipping README check."
    exit 0
  fi

  # Step 1: Update READMEs for changed folders
  echo "  Step 1/4: Updating READMEs for changed folders..."
  echo "$CHANGED" | while read f; do
    folder="$(dirname "$WORKSPACE/$f")"
    if [ -d "$folder" ]; then
      "$VENV_PY" "$WORKSPACE/hands/automation/readme/readme_generator.py" \
        "$folder" --no-claude 2>>"$LOG" || true
    fi
  done

  # Step 2: Rebuild root README
  echo "  Step 2/4: Rebuilding root README..."
  "$VENV_PY" "$WORKSPACE/hands/automation/readme/root_synthesizer.py" \
    2>>"$LOG" || echo "  ⚠️ Root rebuild failed (non-fatal)"

  # Step 3: Stage updated READMEs
  echo "  Step 3/4: Staging README updates..."
  git add "**README.md" 2>/dev/null || git add -u 2>/dev/null || true

  # Step 4: Validate
  echo "  Step 4/4: Running validation..."
  if ! "$VENV_PY" "$WORKSPACE/hands/automation/readme/validator.py" 2>>"$LOG"; then
    echo ""
    echo "❌ README validation FAILED. Push blocked."
    echo "   Fix: run 'readme-update-all && readme-root-build' then push again."
    echo ""
    exit 1
  fi
done

echo "✅ README validation passed. Proceeding with push."
exit 0
```

- [ ] **Step 2: Install hook**

```bash
chmod +x /Users/MAC/SuneelWorkSpace/hands/automation/git/pre_push_guard.sh
ln -sf /Users/MAC/SuneelWorkSpace/hands/automation/git/pre_push_guard.sh \
  /Users/MAC/SuneelWorkSpace/.git/hooks/pre-push
chmod +x /Users/MAC/SuneelWorkSpace/.git/hooks/pre-push
```

- [ ] **Step 3: Verify hook installed**

```bash
ls -la /Users/MAC/SuneelWorkSpace/.git/hooks/pre-push
```

Expected: symlink to `hands/automation/git/pre_push_guard.sh`

- [ ] **Step 4: Commit**

```bash
git add hands/automation/git/pre_push_guard.sh
git commit -m "feat(readme): add git pre-push guard"
```

---

### Task 11: CLI Commands + Symlinks

**Files:**
- Create: `hands/bin/readme-update-all`
- Create: `hands/bin/readme-update`
- Create: `hands/bin/readme-root-build`
- Create: `hands/bin/readme-validate`
- Create: `hands/bin/readme-watch-start`
- Create: `hands/bin/git-safe-push`

- [ ] **Step 1: Write all CLI wrapper scripts**

`hands/bin/readme-update-all`:
```bash
#!/usr/bin/env bash
WORKSPACE="$(cd "$(dirname "$0")/../.." && pwd)"
exec "$WORKSPACE/.venv/bin/python3" "$WORKSPACE/hands/automation/readme/run_update_all.py" "$@"
```

`hands/bin/readme-update`:
```bash
#!/usr/bin/env bash
WORKSPACE="$(cd "$(dirname "$0")/../.." && pwd)"
if [ -z "${1:-}" ]; then echo "Usage: readme-update <folder>"; exit 1; fi
exec "$WORKSPACE/.venv/bin/python3" "$WORKSPACE/hands/automation/readme/readme_generator.py" "$1" "${@:2}"
```

`hands/bin/readme-root-build`:
```bash
#!/usr/bin/env bash
WORKSPACE="$(cd "$(dirname "$0")/../.." && pwd)"
exec "$WORKSPACE/.venv/bin/python3" "$WORKSPACE/hands/automation/readme/root_synthesizer.py" "$@"
```

`hands/bin/readme-validate`:
```bash
#!/usr/bin/env bash
WORKSPACE="$(cd "$(dirname "$0")/../.." && pwd)"
exec "$WORKSPACE/.venv/bin/python3" "$WORKSPACE/hands/automation/readme/validator.py" "$@"
```

`hands/bin/readme-watch-start`:
```bash
#!/usr/bin/env bash
WORKSPACE="$(cd "$(dirname "$0")/../.." && pwd)"
exec "$WORKSPACE/.venv/bin/python3" "$WORKSPACE/hands/automation/readme/watcher.py" "$@"
```

`hands/bin/git-safe-push`:
```bash
#!/usr/bin/env bash
set -euo pipefail
WORKSPACE="$(cd "$(dirname "$0")/../.." && pwd)"
VENV_PY="$WORKSPACE/.venv/bin/python3"

echo "🚀 git-safe-push starting..."

echo "  Step 1/4: Updating all READMEs..."
"$VENV_PY" "$WORKSPACE/hands/automation/readme/run_update_all.py" --no-claude

echo "  Step 2/4: Rebuilding root README..."
"$VENV_PY" "$WORKSPACE/hands/automation/readme/root_synthesizer.py"

echo "  Step 3/4: Validating..."
"$VENV_PY" "$WORKSPACE/hands/automation/readme/validator.py" || {
  echo "❌ Validation failed. Push aborted."
  exit 1
}

echo "  Step 4/4: Pushing..."
git push "$@"
echo "✅ Push complete."
```

- [ ] **Step 2: Make all executable**

```bash
chmod +x /Users/MAC/SuneelWorkSpace/hands/bin/readme-update-all \
         /Users/MAC/SuneelWorkSpace/hands/bin/readme-update \
         /Users/MAC/SuneelWorkSpace/hands/bin/readme-root-build \
         /Users/MAC/SuneelWorkSpace/hands/bin/readme-validate \
         /Users/MAC/SuneelWorkSpace/hands/bin/readme-watch-start \
         /Users/MAC/SuneelWorkSpace/hands/bin/git-safe-push
```

- [ ] **Step 3: Smoke test each command**

```bash
cd /Users/MAC/SuneelWorkSpace && \
  hands/bin/readme-validate && \
  hands/bin/readme-root-build && \
  hands/bin/readme-update brain --no-claude && \
  echo "✅ All CLIs working"
```

- [ ] **Step 4: Commit**

```bash
git add hands/bin/readme-update-all hands/bin/readme-update hands/bin/readme-root-build \
        hands/bin/readme-validate hands/bin/readme-watch-start hands/bin/git-safe-push
git commit -m "feat(readme): add all CLI commands"
```

---

### Task 12: Final Integration — Wiring + Smoke Test

- [ ] **Step 1: Run full update-all**

```bash
cd /Users/MAC/SuneelWorkSpace && hands/bin/readme-update-all --no-claude
```

- [ ] **Step 2: Run root build**

```bash
hands/bin/readme-root-build
```

- [ ] **Step 3: Run validate**

```bash
hands/bin/readme-validate
```

- [ ] **Step 4: Verify nervous system integration works**

```bash
cd /Users/MAC/SuneelWorkSpace && .venv/bin/python3 nervous/nerve_propagator.py notify spine "readme_updated"
cat blood/logs/nerve_events.jsonl | tail -1
```

Expected: JSON line with `source_organ: spine, event_type: readme_updated`

- [ ] **Step 5: Load LaunchAgent (optional — requires user approval)**

```bash
cp hands/automation/launchd/com.suneelworkspace.readme.plist ~/Library/LaunchAgents/
launchctl load ~/Library/LaunchAgents/com.suneelworkspace.readme.plist
launchctl list | grep readme
```

- [ ] **Step 6: Final commit**

```bash
git add -u
git commit -m "feat(readme): complete README intelligence + enforcement system"
```

---

## Self-Review Against Spec

| Spec Requirement | Covered By |
|-----------------|-----------|
| Every folder has self-updating README | Task 4 (readme_generator) + Task 9 (nightly) |
| READMEs interconnected/context-aware | Task 4 (Connected Modules section) + Task 3 (dep map) |
| Root README always current | Task 5 (root_synthesizer) |
| File change → README update | Task 8 (watcher) |
| No push unless READMEs updated | Task 7 (validator) + Task 10 (pre_push_guard) |
| intelligence_engine.py | Task 2 |
| Claude README generation format | Task 4 |
| README interlinking | Task 3 + Task 4 (Connected Modules section) |
| spine/readme_dependency_map.json | Task 3 |
| watcher.py with watchdog | Task 8 |
| run_nightly.sh at midnight | Task 9 |
| root_synthesizer.py | Task 5 |
| consistency_engine.py | Task 6 |
| validator.py exits 1 on fail | Task 7 |
| pre_push_guard.sh git hook | Task 10 |
| Hook installation | Task 10 Step 2 |
| git-safe-push CLI | Task 11 |
| Nervous system integration | Task 8 + Task 9 + hands/bin/git-safe-push |
| Change log in each README | Task 4 (Change Log section in template) |
| MANUAL SECTION preservation | Task 4 + Task 5 (MANUAL_BLOCK_RE) |
| All 6 CLI commands + symlinks | Task 11 |
| LaunchAgent plist | Task 9 |
