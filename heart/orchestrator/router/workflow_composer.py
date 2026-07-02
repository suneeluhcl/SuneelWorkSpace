#!/usr/bin/env python3
"""Workflow Composer: dynamically chains compatible workflows based on intent, avoiding duplicates and reusing outputs."""

import json
import os
import pathlib
import re

ROOT = pathlib.Path(os.environ.get("SUNEEL_WORKSPACE", str(pathlib.Path.home() / "SuneelWorkSpace"))).resolve()
GEN_DIR = ROOT / "brain/workflows/generated"
WORKFLOWS_DIR = ROOT / "brain/workflows"

def load_json(path: pathlib.Path, default: any) -> any:
    if not path.exists():
        return default
    try:
        return json.loads(path.read_text())
    except Exception:
        return default

def compose_workflows(slugs: list[str], output_slug: str = "composed_workflow") -> bool:
    """Merge multiple workflows, deduplicate steps, reuse outputs, and generate a composed note."""
    merged_steps = []
    seen_steps = set() # Store (action, arg) to deduplicate
    
    # Map step IDs from original workflow to composed step IDs
    # e.g., (workflow_slug, original_step_id) -> composed_step_id
    step_id_map = {}
    composed_step_index = 1
    
    for slug in slugs:
        json_path = GEN_DIR / f"{slug}.json"
        if not json_path.exists():
            # Try matching with dashes/underscores
            alt_slug = slug.replace("-", "_")
            json_path = GEN_DIR / f"{alt_slug}.json"
            if not json_path.exists():
                alt_slug = slug.replace("_", "-")
                json_path = GEN_DIR / f"{alt_slug}.json"
                if not json_path.exists():
                    continue
                    
        w_data = load_json(json_path, {})
        commands = w_data.get("commands", [])
        
        # Parse commands to identify actions & args
        for orig_idx, cmd in enumerate(commands, 1):
            cmd_clean = cmd.strip()
            # Match action and args
            match = re.match(r"^(\w+)(?:\s+['\"]?(.*?)['\"]?)?$", cmd_clean)
            if not match:
                # If it's a typical bash command
                if cmd_clean not in seen_steps:
                    seen_steps.add(cmd_clean)
                    merged_steps.append({
                        "type": "cmd",
                        "command": cmd_clean,
                        "orig_slug": slug,
                        "orig_idx": orig_idx
                    })
                continue
                
            action_name = match.group(1)
            arg_val = match.group(2) or ""
            
            # Remove bounding quotes from argument value if any
            if (arg_val.startswith('"') and arg_val.endswith('"')) or (arg_val.startswith("'") and arg_val.endswith("'")):
                arg_val = arg_val[1:-1]
                
            step_key = (action_name, arg_val)
            orig_step_id = f"step_{orig_idx}"
            
            if step_key in seen_steps:
                # Deduplicated! Find the composed step ID of the original step that we are reusing
                reused_composed_idx = None
                for idx, step in enumerate(merged_steps, 1):
                    if step.get("type") == "mcp" and step.get("action") == action_name and step.get("arg") == arg_val:
                        reused_composed_idx = idx
                        break
                if reused_composed_idx:
                    step_id_map[(slug, orig_step_id)] = f"step_{reused_composed_idx}"
                continue
                
            # Add new step
            seen_steps.add(step_key)
            composed_step_id = f"step_{composed_step_index}"
            step_id_map[(slug, orig_step_id)] = composed_step_id
            
            merged_steps.append({
                "type": "mcp",
                "action": action_name,
                "arg": arg_val,
                "orig_slug": slug,
                "orig_step_id": orig_step_id,
                "composed_step_id": composed_step_id
            })
            composed_step_index += 1
            
    # Now, reconstruct the commands list, replacing placeholders using step_id_map
    composed_commands = []
    
    for idx, step in enumerate(merged_steps, 1):
        if step["type"] == "cmd":
            cmd_str = step["command"]
            placeholders = re.findall(r"\{\{([^}]+)\}\}", cmd_str)
            for ph in placeholders:
                ref = ph.strip()
                ref_base = ref.split(".")[0]
                mapped_id = step_id_map.get((step["orig_slug"], ref_base))
                if mapped_id:
                    cmd_str = cmd_str.replace(f"{{{{{ph}}}}}", f"{{{{{mapped_id}}}}}")
            composed_commands.append(cmd_str)
            
        elif step["type"] == "mcp":
            arg_str = step["arg"]
            placeholders = re.findall(r"\{\{([^}]+)\}\}", arg_str)
            for ph in placeholders:
                ref = ph.strip()
                ref_base = ref.split(".")[0]
                mapped_id = step_id_map.get((step["orig_slug"], ref_base))
                if mapped_id:
                    arg_str = arg_str.replace(f"{{{{{ph}}}}}", f"{{{{{mapped_id}}}}}")
            
            if arg_str:
                composed_commands.append(f"{step['action']} \"{arg_str}\"")
            else:
                composed_commands.append(step["action"])
                
    if not composed_commands:
        return False
        
    out_file = WORKFLOWS_DIR / f"{output_slug}.md"
    out_content = [
        f"# Workflow: Composed Workflow",
        f"",
        f"This workflow was dynamically composed from: {', '.join(slugs)}",
        f"",
        f"## Structure & Steps"
    ]
    for i, cmd in enumerate(composed_commands, 1):
        out_content.append(f"{i}. {cmd}")
        
    out_file.write_text("\n".join(out_content) + "\n")
    print(f"✓ Composed workflow written to {out_file.name}")
    
    # Run knowledge bridge to compile it to bin/workflow-composed-workflow
    try:
        import sys
        sys.path.append(str(ROOT / "hands" / "scripts"))
        import knowledge_bridge
        knowledge_bridge.scan_and_generate_workflows()
    except Exception as e:
        print(f"Failed to compile composed workflow: {e}")
        
    return True

def check_and_compose_for_intent(intent: str) -> str | None:
    """Check if the intent has a compatible workflow chain and compose it. Returns command name if composed."""
    mapping = {
        "improve repo": ["code_improvement_workflow", "system_improvement_workflow", "eval_and_reliability_map"],
        "improve_repo": ["code_improvement_workflow", "system_improvement_workflow", "eval_and_reliability_map"],
        "maintenance": ["obsidian_maintenance", "system_improvement_workflow"],
        "testing": ["eval_and_reliability_map", "rollback-and-recovery"]
    }
    
    intent_clean = intent.lower().strip()
    slugs = mapping.get(intent_clean)
    if not slugs:
        return None
        
    success = compose_workflows(slugs, "composed_workflow")
    if success:
        return "workflow-composed-workflow"
    return None

if __name__ == "__main__":
    import sys
    if len(sys.argv) > 1:
        # e.g., python3 workflow_composer.py code_improvement_workflow system_improvement_workflow
        compose_workflows(sys.argv[1:])
    else:
        # Default test
        compose_workflows(["code_improvement_workflow", "system_improvement_workflow", "eval_and_reliability_map"])
