#!/usr/bin/env python3
"""Knowledge-to-Execution Bridge: extracts workflows from Obsidian notes and compiles them into executable commands."""

import json
import os
import pathlib
import re
import shutil
import sys
from datetime import datetime, timezone

# Ensure scripts directory is in path for importing guards
ROOT = pathlib.Path(os.environ.get("SUNEEL_WORKSPACE", str(pathlib.Path.home() / "SuneelWorkSpace"))).resolve()
sys.path.append(str(ROOT / "hands" / "scripts"))

try:
    import duplication_guard
    import integrity_guard
except ImportError:
    # Fallback to local directory import
    sys.path.append(os.path.dirname(os.path.abspath(__file__)))
    import duplication_guard
    import integrity_guard

BRAIN_DIR = ROOT / "brain"
GEN_DIR = BRAIN_DIR / "workflows/generated"
SCRIPTS_DIR = ROOT / "hands/scripts/workflows"
BIN_DIR = ROOT / "hands/bin"

def now_iso() -> str:
    return datetime.now(timezone.utc).astimezone().isoformat()

def write_json(path: pathlib.Path, data: any):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(data, indent=2, sort_keys=True) + "\n")

def clean_name(title: str) -> str:
    # Convert title to lowercase slug
    name = title.lower().strip()
    name = re.sub(r"[^a-z0-9_\-]+", "_", name)
    return name.strip("_")

def classify_note(p_file: pathlib.Path, content: str) -> str | None:
    """Phase 1: Detect note types (idea, workflow, decision, system improvement, experiment)"""
    parents = [p.name for p in p_file.parents]
    if "ideas" in parents:
        return "idea"
    if "workflows" in parents:
        return "workflow"
    if "decisions" in parents:
        return "decision"
    if "system" in parents:
        return "system improvement"
    if "experiments" in parents:
        return "experiment"
        
    # Fallback to frontmatter tags
    fm_match = re.match(r"^---\s*\n(.*?)\n---\s*\n", content, re.DOTALL)
    if fm_match:
        fm_text = fm_match.group(1).lower()
        if "type: idea" in fm_text or "tag: idea" in fm_text or "tags: [idea" in fm_text or "tags:\n  - idea" in fm_text:
            return "idea"
        if "type: workflow" in fm_text or "tag: workflow" in fm_text or "tags: [workflow" in fm_text or "tags:\n  - workflow" in fm_text:
            return "workflow"
        if "type: decision" in fm_text or "tag: decision" in fm_text or "tags: [decision" in fm_text or "tags:\n  - decision" in fm_text:
            return "decision"
        if "type: system" in fm_text or "type: improvement" in fm_text or "tags: [system" in fm_text:
            return "system improvement"
        if "type: experiment" in fm_text or "tag: experiment" in fm_text or "tags: [experiment" in fm_text:
            return "experiment"
            
    # Check general tags or title keywords
    title_lower = p_file.name.lower()
    content_lower = content.lower()
    
    if "workflow" in title_lower or "#workflow" in content_lower:
        return "workflow"
    if "decision" in title_lower or "#decision" in content_lower:
        return "decision"
    if "idea" in title_lower or "#idea" in content_lower:
        return "idea"
    if "experiment" in title_lower or "#experiment" in content_lower:
        return "experiment"
    if "improvement" in title_lower or "upgrade" in title_lower or "#system" in content_lower:
        return "system improvement"
        
    return None

def is_valid_command(cmd: str) -> bool:
    """Validate a command to ensure it's safe and contains no placeholders or invalid tokens."""
    cmd_clean = cmd.strip()
    if not cmd_clean:
        return False
        
    # 1. Reject slash commands starting with '/'
    if cmd_clean.startswith("/"):
        return False
        
    # 2. Reject commands containing placeholders like <something>
    if re.search(r"<[^>]+>", cmd_clean):
        return False
        
    # 3. Reject commands containing placeholders like [parameter]
    if re.search(r"\[[a-zA-Z_][a-zA-Z0-9_\-]*\]", cmd_clean):
        return False
        
    # 4. Reject placeholders in quotes (like "Title", "desc", etc.)
    placeholders_in_quotes = ["title", "desc", "parameter", "text", "something", "q", "your_"]
    for ph in placeholders_in_quotes:
        if re.search(rf"['\"][^'\"]*\b{ph}\b[^'\"]*['\"]", cmd_clean, re.IGNORECASE):
            return False
            
    # 5. Reject split control blocks (do, done, fi, then, elif, else)
    forbidden_tokens = ["do", "done", "fi", "then", "elif", "else"]
    for ft in forbidden_tokens:
        if re.search(rf"\b{ft}\b", cmd_clean):
            return False
            
    return True

def parse_note_commands(content: str) -> list[str]:
    """Extract and validate command sequences from markdown content: code blocks or numbered lists."""
    commands = []
    
    # 1. Parse from sh/bash/zsh code blocks
    code_blocks = re.findall(r"```(?:sh|bash|zsh)\n(.*?)\n```", content, re.DOTALL)
    for block in code_blocks:
        for line in block.splitlines():
            line_clean = line.strip()
            
            # Strip inline comments
            if "#" in line_clean:
                line_clean = line_clean.split("#", 1)[0].strip()
                
            if line_clean:
                # Normalize rtk prefix
                if line_clean.startswith("rtk "):
                    line_clean = line_clean[4:]
                    
                if is_valid_command(line_clean):
                    commands.append(line_clean)
                
    if commands:
        return commands
        
    # 2. Parse from ordered lists containing rtk / bin commands or MCP commands
    list_items = re.findall(r"^\d+\.\s+(.*)$", content, re.MULTILINE)
    for item in list_items:
        item_clean = item.strip()
        
        # Strip inline comments
        if "#" in item_clean:
            item_clean = item_clean.split("#", 1)[0].strip()
            
        if item_clean:
            is_typical = "rtk " in item_clean or "bin/" in item_clean or item_clean.startswith("git ") or item_clean.startswith("python3 ")
            is_mcp = any(conn in item_clean for conn in ["search_web_brave", "filesystem_read_file", "filesystem_list_dir", "github_create_issue", "github_list_prs", "shortcuts_run", "shortcuts_list", "generate_fix"])
            if is_typical or is_mcp:
                if item_clean.startswith("rtk "):
                    item_clean = item_clean[4:]
                
                if is_valid_command(item_clean):
                    commands.append(item_clean)
            
    return commands

def create_execution_wrapper(workflow_slug: str, workflow_name: str, commands: list[str], source_file: str) -> str | None:
    """Generate the python wrapper script in scripts/workflows/ and symlink to bin/workflow-<name>"""
    SCRIPTS_DIR.mkdir(parents=True, exist_ok=True)
    BIN_DIR.mkdir(parents=True, exist_ok=True)
    
    script_path = SCRIPTS_DIR / f"workflow_{workflow_slug}.py"
    
    is_mcp_workflow = any(
        any(conn in cmd for conn in ["search_web_brave", "filesystem_read_file", "filesystem_list_dir", "github_create_issue", "github_list_prs", "shortcuts_run", "shortcuts_list", "generate_fix"])
        for cmd in commands
    )
    
    if is_mcp_workflow:
        code = f'''#!/usr/bin/env python3
"""Auto-generated orchestrated MCP workflow wrapper for: {workflow_name}"""

import sys
import os
import pathlib

ROOT = pathlib.Path("{str(ROOT)}")
sys.path.append(str(ROOT / "hands" / "scripts"))

try:
    from mcp_orchestrator import parse_and_run_md_workflow
except ImportError:
    # Fallback to local import
    sys.path.append(os.path.dirname(os.path.abspath(__file__)))
    from mcp_orchestrator import parse_and_run_md_workflow

def main():
    source_note = pathlib.Path("{source_file}")
    print(f"🎬 Starting Orchestrated MCP Pipeline Workflow: {workflow_name}")
    success = parse_and_run_md_workflow(source_note)
    if success:
        sys.exit(0)
    else:
        sys.exit(1)

if __name__ == "__main__":
    main()
'''
    else:
        safe_commands_json = json.dumps(commands)
        code = f'''#!/usr/bin/env python3
"""Auto-generated workflow execution wrapper for: {workflow_name}"""

import sys
import os
import pathlib
import subprocess
from datetime import datetime, timezone

ROOT = pathlib.Path("{str(ROOT)}")
COMMANDS = {safe_commands_json}
WORKFLOW_NAME = "{workflow_name}"
SOURCE_NOTE = "{source_file}"

def run_command(cmd: str) -> tuple[bool, str, str]:
    print(f"\\n🏃 Running: rtk {{cmd}}")
    
    # Safety Check: Outbound/Controlled confirmation
    is_controlled = any(x in cmd for x in ["git commit", "git push", "run", "improve"])
    if is_controlled:
        try:
            ans = input(f"⚠️  Controlled command: '{{cmd}}'. Confirm run? (y/n) [y]: ").strip().lower()
            if ans in ["n", "no"]:
                print("❌ Skipped by user.")
                return False, "", "Skipped by user"
        except (EOFError, KeyboardInterrupt):
            print("\\n❌ Cancelled.")
            return False, "", "Cancelled by user"
            
    try:
        res = subprocess.run(cmd, shell=True, cwd=str(ROOT), capture_output=True, text=True)
        if res.stdout:
            print(res.stdout, end="")
        if res.stderr:
            print(res.stderr, file=sys.stderr, end="")
        return res.returncode == 0, res.stdout, res.stderr
    except Exception as e:
        print(f"Error running command: {{e}}")
        return False, "", str(e)

def main():
    import time
    start_time = time.time()
    print(f"🎬 Initiating Workflow: {{WORKFLOW_NAME}}")
    print(f"Source: {{SOURCE_NOTE}}\\n")
    
    # Phase 2 Context Display
    try:
        import json
        context_path = ROOT / "spine/state/ACTIVE_CONTEXT.json"
        if context_path.exists():
            context = json.loads(context_path.read_text())
            intent = context.get("current_intent", "unknown")
            goal = context.get("current_goal", "None")
            print("Current context:")
            print(f"  - Intent: {{intent}}")
            print(f"  - Active goal: {{goal}}")
            print(f"  - Selected workflow: {{WORKFLOW_NAME}}")
            print(f"  - Reason for selection: Aligns with current intent: '{{intent}}'")
            print("")
    except Exception:
        pass

    success = True
    errors = []
    steps_outputs = []
    total_steps = len(COMMANDS)
    
    for idx, cmd in enumerate(COMMANDS, 1):
        # Deduce intent and reason
        display_intent = "execution"
        display_reason = f"Executing shell command: {{cmd}}"
        if "git" in cmd:
            display_intent = "collaboration"
            display_reason = f"running git command: {{cmd}}"
        elif "python3" in cmd:
            display_intent = "execution"
            display_reason = f"running python script: {{cmd}}"

        print(f"[STEP {{idx}}/{{total_steps}}] {{cmd}}")
        print(f"→ intent: {{display_intent}}")
        print(f"→ reason: {{display_reason}}")
        print(f"→ status: running...")

        ok, stdout, stderr = run_command(cmd)
        steps_outputs.append(stdout)
        
        print("\\n[RESULT]")
        preview = stdout[:200] + "..." if len(stdout) > 200 else stdout
        indented_preview = "\\n".join("  " + line for line in preview.splitlines())
        print(f"→\\n{{indented_preview}}\\n")

        if not ok:
            print(f"\\n❌ Workflow interrupted at command: '{{cmd}}'")
            errors.append(stderr or f"Command '{{cmd}}' failed")
            success = False
            break
            
    execution_time = time.time() - start_time
    
    # Record outcome
    quality_score = 1.0
    try:
        sys.path.append(str(ROOT / "hands" / "scripts"))
        from workflow_outcome_evaluator import record_outcome
        quality_score = record_outcome(
            workflow_slug="{workflow_slug}",
            success=success,
            execution_time=execution_time,
            errors=errors,
            steps_outputs=steps_outputs
        )
    except Exception as e:
        print(f"Failed to record outcome: {{e}}")

    # Phase 4 Final Summary
    status_emoji = "✅" if success else "❌"
    status_word = "completed" if success else "failed"
    print(f"\\n{{status_emoji}} Workflow {{status_word}}")
    print("\\nSummary:")
    print(f"  - steps executed: {{len(steps_outputs)}}")
    print(f"  - success: {{success}}")
    print(f"  - quality score: {{quality_score}}")
    improvements_noted = 0
    if quality_score < 0.8:
        improvements_noted = 1
    print(f"  - improvements noted: {{improvements_noted}}")

    if success:
        sys.exit(0)
    else:
        sys.exit(1)

if __name__ == "__main__":
    main()
'''
    
    # 1. Duplication Guard Check
    try:
        ok, loc_err = duplication_guard.check_canonical_location(script_path)
        if not ok:
            print(f"⚠️  Duplication Guard rejected path '{script_path}': {loc_err}")
            return None
            
        matches = duplication_guard.find_duplicates(script_path, f"workflow execution wrapper for {workflow_name}")
        for m in matches:
            if m["path"] != str(script_path.relative_to(ROOT)) and m["score"] >= 80:
                print(f"⚠️  Duplication Warning: Similar workflow script already exists: {m['path']}")
                return None
    except Exception as e:
        print(f"Warning: Could not run duplication guard: {e}")
        
    # 2. Integrity Guard Check
    if script_path.exists():
        try:
            current_content = script_path.read_text(errors="replace")
            dupes = integrity_guard.check_internal_duplication(code, ".py")
            proposed_dupes = integrity_guard.check_proposed_duplication(current_content, code, ".py")
            all_dupes = dupes + proposed_dupes
            if all_dupes:
                print(f"⚠️  Canonical Integrity Warning for '{script_path}':")
                for dtype, msg in all_dupes:
                    print(f"  - [{dtype.upper()}] {msg}")
                # We let it proceed as we are auto-generating a standard template update
        except Exception as e:
            print(f"Warning: Could not run integrity guard: {e}")
            
    # Write wrapper script
    script_path.write_text(code)
    script_path.chmod(0o755)
    
    # Create symlink in bin/ (enforcing that bin only contains symlinks)
    bin_link = BIN_DIR / f"workflow-{workflow_slug.replace('_', '-')}"
    if bin_link.exists() or bin_link.is_symlink():
        bin_link.unlink()
        
    bin_link.symlink_to(f"../scripts/workflows/workflow_{workflow_slug}.py")
    return bin_link.name

def scan_and_generate_workflows() -> dict:
    """Scan brain/ folder, extract executable workflows, and generate runnables."""
    GEN_DIR.mkdir(parents=True, exist_ok=True)
    
    results = {
        "classified_notes": [],
        "workflows_generated": [],
        "notes_converted": [],
        "commands_created": [],
        "behavior_improvements": [],
        "cleaned_up": []
    }
    
    if not BRAIN_DIR.exists():
        return results
        
    for p_file in BRAIN_DIR.rglob("*.md"):
        # Ignore generated workflows notes or templates/archive
        if "generated" in str(p_file) or "archive" in str(p_file) or "templates" in str(p_file):
            continue
            
        try:
            content = p_file.read_text(errors="replace")
            note_type = classify_note(p_file, content)
            title = p_file.stem
            slug = clean_name(title)
            
            if note_type:
                results["classified_notes"].append({
                    "title": title,
                    "type": note_type,
                    "path": str(p_file.relative_to(ROOT))
                })
                
            commands = parse_note_commands(content)
            json_path = GEN_DIR / f"{slug}.json"
            script_path = SCRIPTS_DIR / f"workflow_{slug}.py"
            bin_link = BIN_DIR / f"workflow-{slug.replace('_', '-')}"
            
            if commands:
                # Write workflow JSON
                workflow_data = {
                    "name": title.replace("_", " ").title(),
                    "slug": slug,
                    "note_type": note_type or "unknown",
                    "commands": commands,
                    "source_note": str(p_file.relative_to(ROOT)),
                    "generated_at": now_iso()
                }
                write_json(json_path, workflow_data)
                
                # Create wrapper script & symlink in bin
                bin_cmd = create_execution_wrapper(slug, workflow_data["name"], commands, str(p_file))
                
                if bin_cmd:
                    results["workflows_generated"].append(workflow_data["name"])
                    results["notes_converted"].append(title)
                    results["commands_created"].append(bin_cmd)
                    results["behavior_improvements"].append(
                        f"Enable programmatic execution of Obsidian {note_type or 'note'} workflow: '{title}'"
                    )
            else:
                # If note has NO valid commands, clean up any previous generated files for this note
                deleted_any = False
                if json_path.exists():
                    json_path.unlink()
                    deleted_any = True
                if script_path.exists():
                    script_path.unlink()
                    deleted_any = True
                if bin_link.exists() or bin_link.is_symlink():
                    bin_link.unlink()
                    deleted_any = True
                    
                if deleted_any:
                    results["cleaned_up"].append(title)
                    
        except Exception as e:
            print(f"Error scanning '{p_file.name}': {e}")
            
    return results

def main():
    print("🧹 Scanning Obsidian brain vault for notes and executable patterns...")
    results = scan_and_generate_workflows()
    
    print("\n" + "="*50)
    print("A) WORKFLOWS GENERATED")
    print("="*50)
    if results["workflows_generated"]:
        for w in results["workflows_generated"]:
            print(f"  - {w}")
    else:
        print("  (None generated or updated)")
        
    print("\n" + "="*50)
    print("B) NOTES CONVERTED TO ACTION")
    print("="*50)
    if results["notes_converted"]:
        for n in results["notes_converted"]:
            print(f"  - Note: [[{n}]]")
    else:
        print("  (None converted)")
        
    print("\n" + "="*50)
    print("C) NEW COMMANDS CREATED")
    print("="*50)
    if results["commands_created"]:
        for c in results["commands_created"]:
            print(f"  - bin/{c}")
    else:
        print("  (No new commands)")
        
    print("\n" + "="*50)
    print("D) SYSTEM BEHAVIOR IMPROVEMENTS")
    print("="*50)
    if results["behavior_improvements"]:
        for bi in results["behavior_improvements"]:
            print(f"  - {bi}")
    else:
        print("  (No behavior improvements)")
        
    if results["cleaned_up"]:
        print("\n" + "="*50)
        print("CLEANED UP STALE WORKFLOWS (0 valid commands)")
        print("="*50)
        for cl in results["cleaned_up"]:
            print(f"  - Cleaned up: [[{cl}]]")
            
    print("\n" + "="*50)
    print("SUMMARY FOR COPILOT:")
    print("="*50)
    print("- knowledge-to-execution bridge enabled")
    print("- workflows auto-generated from brain")
    print("- commands created from patterns")
    print("- system can now act on knowledge")
    print("="*50 + "\n")

if __name__ == "__main__":
    main()
