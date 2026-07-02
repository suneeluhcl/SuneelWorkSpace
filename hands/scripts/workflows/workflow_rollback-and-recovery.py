#!/usr/bin/env python3
"""Auto-generated workflow execution wrapper for: Rollback-And-Recovery"""

import sys
import os
import pathlib
import subprocess
from datetime import datetime, timezone

ROOT = pathlib.Path("/Users/MAC/SuneelWorkSpace")
COMMANDS = ["git log --oneline adwi/adwi_cli.py", "python3 -m py_compile adwi/adwi_cli.py && echo \"syntax OK\"", "python3 -m py_compile adwi/nightly.py && echo \"syntax OK\"", "launchctl unload ~/Library/LaunchAgents/com.suneel.obsidian-bridge.plist", "launchctl load   ~/Library/LaunchAgents/com.suneel.obsidian-bridge.plist", "nohup python3 ~/SuneelWorkSpace/adwi/overnight_learn.py > /tmp/overnight-learn.log 2>&1 &", "adwi", "cd ~/SuneelWorkSpace/local-ai-stack", "docker compose down", "docker compose up -d", "docker ps", "brew services restart ollama", "curl http://localhost:11434/api/tags", "launchctl unload \"$plist\" 2>/dev/null", "launchctl load \"$plist\"", "echo \"loaded: $plist\"", "cd ~/SuneelWorkSpace", "git status", "git diff", "git checkout -- .", "python3 -m py_compile adwi/adwi_cli.py", "python3 -m py_compile adwi/nightly.py", "python3 -m py_compile adwi/overnight_learn.py", "echo \"All clear\"", "python3 -m py_compile adwi/adwi_cli.py && echo \"cli OK\"", "python3 -m py_compile adwi/nightly.py   && echo \"nightly OK\"", "python3 -m py_compile adwi/overnight_learn.py && echo \"overnight OK\"", "python3 -m py_compile mcp-servers/obsidian-bridge/server.py && echo \"bridge OK\"", "curl -s http://localhost:11434/api/tags | python3 -c \"import sys,json; print('Ollama OK:', len(json.load(sys.stdin)['models']), 'models')\"", "curl -s http://localhost:3000/api/version", "curl -s http://localhost:8888/search?q=test&format=json | python3 -c \"import sys,json; d=json.load(sys.stdin); print('SearXNG OK:', len(d.get('results',[])),'results')\"", "curl -s http://localhost:5056/ | python3 -c \"import sys,json; d=json.load(sys.stdin); print('Obsidian bridge OK:', d['status'])\"", "echo \"/memory-stats\\n/exit\" | python3 adwi/adwi_cli.py 2>/dev/null | grep -E \"Total|Memory|Error\""]
WORKFLOW_NAME = "Rollback-And-Recovery"
SOURCE_NOTE = "/Users/MAC/SuneelWorkSpace/brain/knowledge/rollback-and-recovery.md"

def run_command(cmd: str) -> tuple[bool, str, str]:
    print(f"\n🏃 Running: rtk {cmd}")
    
    # Safety Check: Outbound/Controlled confirmation
    is_controlled = any(x in cmd for x in ["git commit", "git push", "run", "improve"])
    if is_controlled:
        try:
            ans = input(f"⚠️  Controlled command: '{cmd}'. Confirm run? (y/n) [y]: ").strip().lower()
            if ans in ["n", "no"]:
                print("❌ Skipped by user.")
                return False, "", "Skipped by user"
        except (EOFError, KeyboardInterrupt):
            print("\n❌ Cancelled.")
            return False, "", "Cancelled by user"
            
    try:
        res = subprocess.run(cmd, shell=True, cwd=str(ROOT), capture_output=True, text=True)
        if res.stdout:
            print(res.stdout, end="")
        if res.stderr:
            print(res.stderr, file=sys.stderr, end="")
        return res.returncode == 0, res.stdout, res.stderr
    except Exception as e:
        print(f"Error running command: {e}")
        return False, "", str(e)

def main():
    import time
    start_time = time.time()
    print(f"🎬 Initiating Workflow: {WORKFLOW_NAME}")
    print(f"Source: {SOURCE_NOTE}\n")
    
    # Phase 2 Context Display
    try:
        import json
        context_path = ROOT / "spine/state/ACTIVE_CONTEXT.json"
        if context_path.exists():
            context = json.loads(context_path.read_text())
            intent = context.get("current_intent", "unknown")
            goal = context.get("current_goal", "None")
            print("Current context:")
            print(f"  - Intent: {intent}")
            print(f"  - Active goal: {goal}")
            print(f"  - Selected workflow: {WORKFLOW_NAME}")
            print(f"  - Reason for selection: Aligns with current intent: '{intent}'")
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
        display_reason = f"Executing shell command: {cmd}"
        if "git" in cmd:
            display_intent = "collaboration"
            display_reason = f"running git command: {cmd}"
        elif "python3" in cmd:
            display_intent = "execution"
            display_reason = f"running python script: {cmd}"

        print(f"[STEP {idx}/{total_steps}] {cmd}")
        print(f"→ intent: {display_intent}")
        print(f"→ reason: {display_reason}")
        print(f"→ status: running...")

        ok, stdout, stderr = run_command(cmd)
        steps_outputs.append(stdout)
        
        print("\n[RESULT]")
        preview = stdout[:200] + "..." if len(stdout) > 200 else stdout
        indented_preview = "\n".join("  " + line for line in preview.splitlines())
        print(f"→\n{indented_preview}\n")

        if not ok:
            print(f"\n❌ Workflow interrupted at command: '{cmd}'")
            errors.append(stderr or f"Command '{cmd}' failed")
            success = False
            break
            
    execution_time = time.time() - start_time
    
    # Record outcome
    quality_score = 1.0
    try:
        sys.path.append(str(ROOT / "hands" / "scripts"))
        from workflow_outcome_evaluator import record_outcome
        quality_score = record_outcome(
            workflow_slug="rollback-and-recovery",
            success=success,
            execution_time=execution_time,
            errors=errors,
            steps_outputs=steps_outputs
        )
    except Exception as e:
        print(f"Failed to record outcome: {e}")

    # Phase 4 Final Summary
    status_emoji = "✅" if success else "❌"
    status_word = "completed" if success else "failed"
    print(f"\n{status_emoji} Workflow {status_word}")
    print("\nSummary:")
    print(f"  - steps executed: {len(steps_outputs)}")
    print(f"  - success: {success}")
    print(f"  - quality score: {quality_score}")
    improvements_noted = 0
    if quality_score < 0.8:
        improvements_noted = 1
    print(f"  - improvements noted: {improvements_noted}")

    if success:
        sys.exit(0)
    else:
        sys.exit(1)

if __name__ == "__main__":
    main()
