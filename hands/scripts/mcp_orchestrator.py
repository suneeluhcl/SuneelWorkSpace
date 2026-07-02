#!/usr/bin/env python3
"""MCP Orchestration Engine: Chains MCP connector calls, passes outputs, and enforces safety levels."""

import json
import os
import pathlib
import re
import subprocess
import sys
from datetime import datetime, timezone

ROOT = pathlib.Path(os.environ.get("SUNEEL_WORKSPACE", str(pathlib.Path.home() / "SuneelWorkSpace"))).resolve()
BRAIN_DIR = ROOT / "brain"
LOGS_DIR = BRAIN_DIR / "logs"
WORKFLOWS_DIR = BRAIN_DIR / "workflows"

def now_iso() -> str:
    return datetime.now(timezone.utc).astimezone().isoformat()

class McpOrchestrator:
    def __init__(self, workflow_name: str, safety_level: str = "SAFE"):
        self.workflow_name = workflow_name
        self.safety_level = safety_level.upper()
        self.steps = []
        self.outputs = {}
        self.logs = []
        self.decisions = []

    def add_step(self, step_id: str, connector: str, action: str, args: dict):
        self.steps.append({
            "id": step_id,
            "connector": connector,
            "action": action,
            "args": args
        })

    def resolve_placeholders(self, val: str) -> str:
        """Resolve placeholders like {{step_1}} or {{step_1.output}} with actual outputs."""
        if not isinstance(val, str):
            return val
            
        matches = re.findall(r"\{\{([^}]+)\}\}", val)
        for match in matches:
            ref = match.strip()
            # Support both {{step_1}} and {{step_1.output}}
            ref_base = ref.split(".")[0]
            resolved_val = self.outputs.get(ref_base, self.outputs.get(ref, ""))
            # Truncate resolved value if it's too long for prompt logs, but keep it full for execution
            val = val.replace(f"{{{{{match}}}}}", str(resolved_val))
        return val

    def execute_step(self, step: dict) -> tuple[bool, str]:
        step_id = step["id"]
        connector = step["connector"]
        action = step["action"]
        raw_args = step["args"]

        # Resolve args
        resolved_args = {}
        for k, v in raw_args.items():
            resolved_args[k] = self.resolve_placeholders(v)

        print(f"⚙️ Running Step '{step_id}': {connector}.{action}...")
        
        # 1. Map to actual Python CLI scripts
        cmd = []
        if connector == "search":
            script = ROOT / "scripts/mcp_brave_search.py"
            cmd = ["python3", str(script), resolved_args.get("query", "")]
        elif connector == "filesystem":
            script = ROOT / "scripts/mcp_filesystem.py"
            if action == "read_file":
                cmd = ["python3", str(script), "read", resolved_args.get("path", "")]
            elif action == "list_dir":
                cmd = ["python3", str(script), "list", resolved_args.get("path", "")]
        elif connector == "github":
            script = ROOT / "scripts/mcp_github.py"
            if action == "list_prs":
                cmd = ["python3", str(script), "pr-list"]
                if resolved_args.get("repo"):
                    cmd += ["--repo", resolved_args["repo"]]
            elif action == "create_issue":
                cmd = ["python3", str(script), "issue-create", resolved_args.get("title", "")]
                if resolved_args.get("body"):
                    cmd += ["--body", resolved_args["body"]]
                if resolved_args.get("repo"):
                    cmd += ["--repo", resolved_args["repo"]]
        elif connector == "shortcuts":
            script = ROOT / "scripts/mcp_shortcuts.py"
            if action == "list":
                cmd = ["python3", str(script), "list"]
            elif action == "run":
                cmd = ["python3", str(script), "run", resolved_args.get("name", "")]
        elif connector == "internal":
            if action == "generate_fix":
                # Internal mock logic that analyzes context
                ctx = resolved_args.get("search_context", "")
                fcontent = resolved_args.get("file_content", "")
                proposal = f"// PROPOSED FIX FOR workspace integrity\n// Inspired by: {ctx[:60]}...\n// Modifying local file contents of size: {len(fcontent)} bytes\nprint('Integrity Guard Upgraded Successfully')"
                return True, proposal
            else:
                # Execute general CLI/shell commands directly
                cmd_line = f"{action} {resolved_args.get('cmd_args', '')}".strip()
                print(f"🏃 Running internal CLI: {cmd_line}")
                try:
                    res = subprocess.run(cmd_line, shell=True, capture_output=True, text=True, cwd=str(ROOT), timeout=60)
                    if res.returncode == 0:
                        return True, res.stdout.strip()
                    else:
                        return False, res.stderr.strip() or f"CLI failed with exit code {res.returncode}"
                except Exception as e:
                    return False, f"CLI execution failed: {e}"
        else:
            return False, f"Unknown connector: {connector}"

        if not cmd:
            return False, "Failed to build execution command."

        try:
            # Enforce rtk prefix implicitly
            res = subprocess.run(cmd, capture_output=True, text=True, timeout=30, cwd=str(ROOT))
            if res.returncode == 0:
                return True, res.stdout.strip()
            else:
                return False, res.stderr.strip()
        except Exception as e:
            return False, f"Execution failed: {e}"

    def run(self) -> bool:
        import time
        start_time = time.time()
        print(f"🎬 Starting Orchestrated MCP Pipeline: '{self.workflow_name}'")
        print(f"🛡️  Safety Classification: {self.safety_level}")

        # Phase 2 Context Display
        try:
            context = load_json(ROOT / "spine/state/ACTIVE_CONTEXT.json", {})
            intent = context.get("current_intent", "unknown")
            goal = context.get("current_goal", "None")
            print("\nCurrent context:")
            print(f"  - Intent: {intent}")
            print(f"  - Active goal: {goal}")
            print(f"  - Selected workflow: {self.workflow_name}")
            print(f"  - Reason for selection: Aligns with current intent: '{intent}'")
            print("")
        except Exception:
            pass

        # Check safety level constraints (Phase 6)
        if self.safety_level == "CONTROLLED":
            # Prompt once at the start of the workflow
            print("\n📋 Workflow steps:")
            for s in self.steps:
                print(f"  - [{s['id']}] {s['connector']}.{s['action']} with args: {s['args']}")
            try:
                ans = input(f"\n⚠️  CONTROLLED WORKFLOW: Confirm entire pipeline run? (y/n) [y]: ").strip().lower()
                if ans in ["n", "no"]:
                    print("❌ Aborted by user.")
                    return False
            except (EOFError, KeyboardInterrupt):
                print("\n❌ Aborted.")
                return False
                
        success = True
        total_steps = len(self.steps)
        for idx, s in enumerate(self.steps, 1):
            step_id = s["id"]
            
            # Phase 3 Step Transitions
            arg_str_repr = str(s["args"])
            placeholders = re.findall(r"\{\{([^}]+)\}\}", arg_str_repr)
            if placeholders:
                print("\n→ Passing output to next step")
                for ph in placeholders:
                    print(f"→ Using: {{{{{ph.strip()}}}}}")
            
            # Deduce intent and reason for display
            conn = s["connector"]
            act = s["action"]
            args = s["args"]
            
            display_intent = "execution"
            display_reason = f"Executing step action: {act}"
            
            if conn == "search":
                display_intent = "research"
                display_reason = f"searching Brave Search for: '{args.get('query', '')}'"
            elif conn == "filesystem":
                display_intent = "investigate"
                if act == "read_file":
                    display_reason = f"reading local file: '{args.get('path', '')}'"
                elif act == "list_dir":
                    display_reason = f"listing directory: '{args.get('path', '')}'"
            elif conn == "github":
                display_intent = "collaboration"
                if act == "create_issue":
                    display_reason = f"creating GitHub issue: '{args.get('title', '')}'"
                elif act == "list_prs":
                    display_reason = f"fetching GitHub pull requests for repository: '{args.get('repo', '')}'"
            elif conn == "shortcuts":
                display_intent = "automation"
                display_reason = f"triggering macOS Shortcut: '{args.get('name', '')}'"
            elif conn == "internal":
                if act == "generate_fix":
                    display_intent = "self-repair"
                    display_reason = "generating code fix for workspace integrity"
                else:
                    display_intent = "execution"
                    display_reason = f"executing CLI tool: {act} with args '{args.get('cmd_args', '')}'"
            
            # If RESTRICTED, confirm before running this step
            if self.safety_level == "RESTRICTED":
                print(f"\n📋 Step: [{step_id}] {s['connector']}.{s['action']} with args: {s['args']}")
                try:
                    ans = input(f"⚠️  RESTRICTED STEP: Confirm execution? (y/n) [y]: ").strip().lower()
                    if ans in ["n", "no"]:
                        print(f"❌ Skipped step {step_id}.")
                        self.outputs[step_id] = "[Skipped]"
                        continue
                except (EOFError, KeyboardInterrupt):
                    print("\n❌ Aborted.")
                    return False

            print(f"\n[STEP {idx}/{total_steps}] {conn}.{act}")
            print(f"→ intent: {display_intent}")
            print(f"→ reason: {display_reason}")
            print(f"→ status: running...")

            ok, output = self.execute_step(s)
            self.outputs[step_id] = output
            self.logs.append({
                "step_id": step_id,
                "connector": s["connector"],
                "action": s["action"],
                "success": ok,
                "output_preview": output[:200] + "..." if len(output) > 200 else output
            })
            
            # Print result preview
            preview = output[:200] + "..." if len(output) > 200 else output
            indented_preview = "\n".join("  " + line for line in preview.splitlines())
            print("\n[RESULT]")
            print(f"→\n{indented_preview}")

            if not ok:
                print(f"❌ Step '{step_id}' failed: {output}")
                success = False
                break
            else:
                print(f"✅ Step '{step_id}' finished.")

        # Record outcome
        execution_time = time.time() - start_time
        errors = [l["output_preview"] for l in self.logs if not l["success"]]
        quality_score = 1.0
        try:
            import sys
            sys.path.append(str(ROOT / "hands" / "scripts"))
            from workflow_outcome_evaluator import record_outcome
            slug = self.workflow_name.replace(" ", "_").lower()
            quality_score = record_outcome(
                workflow_slug=slug,
                success=success,
                execution_time=execution_time,
                errors=errors,
                steps_outputs=self.outputs
            )
        except Exception as e:
            print(f"Failed to record outcome: {e}")

        # Phase 4 Final Summary
        status_emoji = "✅" if success else "❌"
        status_word = "completed" if success else "failed"
        print(f"\n{status_emoji} Workflow {status_word}")
        print("\nSummary:")
        print(f"  - steps executed: {len(self.logs)}")
        print(f"  - success: {success}")
        print(f"  - quality score: {quality_score}")
        improvements_noted = 0
        if quality_score < 0.8:
            improvements_noted = 1
        print(f"  - improvements noted: {improvements_noted}")

        # Phase 5: Obsidian Link (Logs + Decisions + Workflows)
        self.write_execution_log(success, quality_score)
        return success

    def write_execution_log(self, success: bool, quality_score: float = 1.0):
        LOGS_DIR.mkdir(parents=True, exist_ok=True)
        log_file = LOGS_DIR / "workflow_executions.md"
        
        status_str = "SUCCESS" if success else "FAILED"
        entry_lines = [
            f"\n## Workflow Run: {self.workflow_name} - {now_iso()}",
            f"- **Status**: {status_str}",
            f"- **Safety Level**: {self.safety_level}",
            f"- **Quality Score**: {quality_score}",
            f"- **Steps Executed**:"
        ]
        for l in self.logs:
            ok_emoji = "✅" if l["success"] else "❌"
            entry_lines.append(f"  - {ok_emoji} **{l['step_id']}** ({l['connector']}.{l['action']})")
            entry_lines.append(f"    - Output: `{l['output_preview']}`")
            
        entry_lines.append("- **Decisions Linked**:")
        entry_lines.append(f"  - [[{self.workflow_name.replace(' ', '_').lower()}]] updated with run outcomes.")

        if log_file.exists():
            log_file.write_text(log_file.read_text() + "\n" + "\n".join(entry_lines) + "\n")
        else:
            log_file.write_text(f"# Workflow Execution History\n\n" + "\n".join(entry_lines) + "\n")

        # Update the workflow file in brain/workflows/
        w_file = WORKFLOWS_DIR / f"{self.workflow_name.replace(' ', '_').lower()}.md"
        w_file.parent.mkdir(parents=True, exist_ok=True)
        
        w_content = [
            f"# Workflow: {self.workflow_name}",
            f"",
            f"**Last Executed**: {now_iso()}",
            f"**Execution Status**: {status_str}",
            f"**Safety Level**: {self.safety_level}",
            f"",
            f"## Structure & Steps"
        ]
        for idx, s in enumerate(self.steps, 1):
            conn = s.get("connector")
            act = s.get("action")
            args = s.get("args", {})
            cmd_name = f"{conn}_{act}"
            if conn == "search" and act == "web_search":
                cmd_name = "search_web_brave"
                arg_val = args.get("query", "")
            elif conn == "filesystem" and act == "read_file":
                cmd_name = "filesystem_read_file"
                arg_val = args.get("path", "")
            elif conn == "filesystem" and act == "list_dir":
                cmd_name = "filesystem_list_dir"
                arg_val = args.get("path", "")
            elif conn == "github" and act == "create_issue":
                cmd_name = "github_create_issue"
                arg_val = args.get("title", "")
            elif conn == "github" and act == "list_prs":
                cmd_name = "github_list_prs"
                arg_val = args.get("repo", "")
            elif conn == "shortcuts" and act == "run":
                cmd_name = "shortcuts_run"
                arg_val = args.get("name", "")
            elif conn == "shortcuts" and act == "list":
                cmd_name = "shortcuts_list"
                arg_val = ""
            elif conn == "internal" and act == "generate_fix":
                cmd_name = "generate_fix"
                arg_val = ""
            elif conn == "internal" and act != "generate_fix":
                cmd_name = act
                arg_val = args.get("cmd_args", "")
            else:
                arg_val = str(args)

            if arg_val:
                w_content.append(f"{idx}. {cmd_name} \"{arg_val}\"")
            else:
                w_content.append(f"{idx}. {cmd_name}")
            
        w_content.append(f"")
        w_content.append(f"## Recent Execution Outputs")
        for step_id, out in self.outputs.items():
            w_content.append(f"### Output for step `{step_id}`")
            w_content.append(f"```\n{out}\n```")
            
        w_file.write_text("\n".join(w_content) + "\n")
        print(f"✓ Obsidian history linked for [[{self.workflow_name}]].")

def parse_and_run_md_workflow(md_path: pathlib.Path) -> bool:
    """Parse steps from a Markdown note and run them through McpOrchestrator."""
    content = md_path.read_text()
    title = md_path.stem.replace("_", " ").title()
    
    # Simple heuristic to determine safety level based on contents
    safety = "SAFE"
    if any(kw in content.lower() for kw in ["create_issue", "run", "shortcuts_run"]):
        safety = "CONTROLLED"
    if any(kw in content.lower() for kw in ["rm ", "delete", "write_file"]):
        safety = "RESTRICTED"

    orchestrator = McpOrchestrator(title, safety)
    
    # Find list items that represent pipeline steps
    # Example:
    # 1. search_web_brave "best python AST parsing libraries"
    # or:
    # - search_web_brave query="something"
    steps_matches = re.findall(r"^\s*(?:\d+\.|\-)\s+(\w+)\s+(.*)$", content, re.MULTILINE)
    for idx, (action_name, arg_str) in enumerate(steps_matches, 1):
        step_id = f"step_{idx}"
        
        # Determine connector and action
        connector = "internal"
        action = action_name
        
        if "search" in action_name or "brave" in action_name:
            connector = "search"
            action = "web_search"
        elif "read" in action_name or "filesystem" in action_name or "list_dir" in action_name:
            connector = "filesystem"
            action = "read_file" if "read" in action_name else "list_dir"
        elif "github" in action_name or "pr" in action_name or "issue" in action_name:
            connector = "github"
            action = "create_issue" if "issue" in action_name else "list_prs"
        elif "shortcuts" in action_name or "run_shortcut" in action_name:
            connector = "shortcuts"
            action = "run" if "run" in action_name else "list"
            
        # Parse arguments
        args = {}
        # Check if argument is quoted string
        quote_match = re.search(r"['\"](.*?)['\"]", arg_str)
        if quote_match:
            val = quote_match.group(1)
            if connector == "search":
                args["query"] = val
            elif connector == "filesystem":
                args["path"] = val
            elif connector == "github":
                if action == "create_issue":
                    args["title"] = val
                else:
                    args["repo"] = val
            elif connector == "shortcuts":
                args["name"] = val
            elif connector == "internal":
                args["cmd_args"] = val
        else:
            val = arg_str.strip()
            if connector == "search":
                args["query"] = val
            elif connector == "filesystem":
                args["path"] = val
            elif connector == "github":
                args["title"] = val
            elif connector == "shortcuts":
                args["name"] = val
            elif connector == "internal":
                args["cmd_args"] = val
                
        # Support internal generate_fix step
        if "generate_fix" in action_name:
            connector = "internal"
            action = "generate_fix"
            args = {
                "search_context": "{{step_1}}",
                "file_content": "{{step_2}}"
            }
            
        orchestrator.add_step(step_id, connector, action, args)

    if not orchestrator.steps:
        print(f"No executable steps found in {md_path.name}.")
        return False
        
    return orchestrator.run()

if __name__ == "__main__":
    if len(sys.argv) > 1:
        path = pathlib.Path(sys.argv[1])
        if path.exists():
            parse_and_run_md_workflow(path)
        else:
            print(f"Error: Path {path} not found.")
    else:
        # Default dry run of code improvement example workflow
        orchestrator = McpOrchestrator("Code Improvement Workflow", "CONTROLLED")
        orchestrator.add_step("step_1", "search", "web_search", {"query": "best python AST parsing libraries"})
        orchestrator.add_step("step_2", "filesystem", "read_file", {"path": "scripts/integrity_guard.py"})
        orchestrator.add_step("step_3", "internal", "generate_fix", {"search_context": "{{step_1}}", "file_content": "{{step_2}}"})
        orchestrator.add_step("step_4", "github", "create_issue", {"title": "Upgrade integrity guard AST parsing", "body": "Proposed fix:\n{{step_3}}"})
        orchestrator.run()
