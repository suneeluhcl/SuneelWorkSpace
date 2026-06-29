#!/usr/bin/env python3
"""
Root README Synthesizer — reads all organ READMEs and rebuilds the workspace root README.md.
Preserves MANUAL SECTION blocks. Builds architecture table and capability summary.
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
    ["git", "rev-parse", "--show-toplevel"], text=True,
    cwd=os.path.dirname(os.path.abspath(__file__))
).strip())

ORGANS = [
    "brain", "heart", "eyes", "ears", "nervous", "skeleton",
    "blood", "hands", "mouth", "dna", "lab", "spine",
]

ORGAN_EMOJI = {
    "brain": "🧠", "heart": "❤️", "eyes": "👁️", "ears": "👂",
    "nervous": "⚡", "skeleton": "🦴", "blood": "🩸", "hands": "🤲",
    "mouth": "🗣️", "dna": "🧬", "lab": "🧪", "spine": "🫀",
}

MANUAL_BLOCK_RE = re.compile(
    r"(<!-- MANUAL SECTION START -->.*?<!-- MANUAL SECTION END -->)",
    re.DOTALL,
)


def _extract_section(readme_content: str, section_keyword: str) -> str:
    pattern = rf"## [^\n]*{re.escape(section_keyword)}[^\n]*\n(.*?)(?=\n## |\Z)"
    match = re.search(pattern, readme_content, re.DOTALL | re.IGNORECASE)
    if match:
        return match.group(1).strip()[:300]
    return ""


def _get_organ_summary(organ: str) -> dict:
    readme_path = WORKSPACE / organ / "README.md"
    if not readme_path.exists():
        return {"purpose": "Not yet documented", "capabilities": ""}

    try:
        content = readme_path.read_text(errors="ignore")
    except Exception:
        return {"purpose": "Could not read", "capabilities": ""}

    purpose = _extract_section(content, "Purpose")
    caps = _extract_section(content, "Capabilit")
    return {
        "purpose": purpose.split("\n")[0][:120] if purpose else "Not yet documented",
        "capabilities": caps[:120] if caps else "",
    }


def _load_dep_stats() -> dict:
    dep_map_path = WORKSPACE / "spine/readme_dependency_map.json"
    if dep_map_path.exists():
        try:
            return json.loads(dep_map_path.read_text())
        except Exception:
            pass
    return {}


PROTECTED_MARKER = "<!-- README_PROTECTED: manual -->"


def synthesize_root() -> None:
    existing_path = WORKSPACE / "README.md"
    existing = existing_path.read_text(errors="ignore") if existing_path.exists() else ""

    # If the README is marked as manually maintained, skip regeneration entirely.
    if PROTECTED_MARKER in existing:
        print("✅ Root README is manually maintained (protected marker found) — skipping regeneration.")
        return

    manual_blocks = MANUAL_BLOCK_RE.findall(existing)

    dep_stats = _load_dep_stats()
    total_folders = len(dep_stats.get("folders", {}))

    summaries = {organ: _get_organ_summary(organ) for organ in ORGANS}

    # Architecture table
    arch_rows = []
    for organ in ORGANS:
        emoji = ORGAN_EMOJI.get(organ, "📁")
        purpose = summaries[organ]["purpose"].replace("|", "\\|")
        arch_rows.append(f"| {emoji} **{organ}** | `{organ}/` | {purpose} |")

    arch_table = (
        "| Organ | Path | Purpose |\n"
        "|-------|------|---------|"
    )
    arch_table += "\n" + "\n".join(arch_rows)

    # Capability summary
    cap_lines = []
    for organ in ORGANS:
        caps = summaries[organ]["capabilities"]
        if caps:
            first_cap = caps.split("\n")[0].lstrip("- ").strip()
            if first_cap:
                cap_lines.append(f"- **{organ}**: {first_cap[:80]}")

    today = datetime.now().strftime("%Y-%m-%d %H:%M")

    root_readme = f"""# 🧠 SuneelWorkSpace

> **Autonomous AI Engineering Workspace** — a living 12-organ system that thinks, learns, and self-heals.

## 🏗️ Architecture

{arch_table}

## 📈 System Capabilities

{chr(10).join(cap_lines) if cap_lines else "Run `readme-update-all` to populate organ READMEs."}

## 🔧 Quick Commands

```bash
readme-update-all          # Regenerate all READMEs (rule-based, fast)
readme-update <folder>     # Update a single folder's README
readme-root-build          # Rebuild this root README
readme-watch-start         # Start real-time file watcher
readme-validate            # Validate README freshness before push
git-safe-push              # Validate + push (blocks on stale docs)
```

## 📊 System Stats

| Metric | Value |
|--------|-------|
| Active organs | {len(ORGANS)} |
| Documented folders | {total_folders} |
| Last root rebuild | {today} |

## 🔗 Key Entrypoints

- [`skeleton/rules/AGENT_SYSTEM.md`](skeleton/rules/AGENT_SYSTEM.md) — canonical agent operating rules
- [`spine/state/CURRENT_STATE.json`](spine/state/CURRENT_STATE.json) — live workspace state
- [`spine/readme_dependency_map.json`](spine/readme_dependency_map.json) — folder dependency graph
- [`spine/docs/PROMPTS_INDEX.md`](spine/docs/PROMPTS_INDEX.md) — all reusable agent prompts
- [`blood/logs/readme_intelligence.log`](blood/logs/readme_intelligence.log) — README update log

## 🧬 Nervous System

Changes propagate via `nervous/nerve_propagator.py`. After any update:
```bash
python3 nervous/nerve_propagator.py notify <organ> "readme_updated"
```

## 📝 Change Log (Auto)

- {datetime.now().strftime("%Y-%m-%d")}: Root README rebuilt by README Intelligence System
"""

    # Restore manual blocks
    for block in manual_blocks:
        if block not in root_readme:
            root_readme += f"\n\n{block}\n"

    existing_path.write_text(root_readme, encoding="utf-8")
    print(f"✅ Root README rebuilt ({len(root_readme)} chars, {len(ORGANS)} organs, {total_folders} folders)")


if __name__ == "__main__":
    synthesize_root()
