"""
Phase 13 path updater — rewrites old organ paths to new locations in all files.
Safe: skips binary files, git dir, venvs, vault, backups.
"""
import os

PATH_MAPPINGS = [
    ("from brain.memory",       "from brain.memory"),
    ("from blood.telemetry",    "from blood.telemetry"),
    ("from heart.model_router", "from heart.model_router"),
    ("from dna.feedback",     "from dna.feedback"),
    ("from dna.identity.",                 "from dna.identity."),
    ("from heart.orchestrator.",             "from heart.orchestrator."),
    ("from lab.autolab.",                  "from lab.autolab."),
    ("from lab.evolution.",                "from lab.evolution."),
    ("from eyes.dashboard.",                "from eyes.dashboard."),
    ("from eyes.visual.",                   "from eyes.visual."),
    ("from ears.monitor.",                  "from ears.monitor."),
    ("from mouth.dispatcher.",               "from mouth.dispatcher."),
    ("from mouth.comms.",                    "from mouth.comms."),
    ("from nervous.mcp.",                      "from nervous.mcp."),
    ("from nervous.gateway.",                  "from nervous.gateway."),
    ("brain/memory/",           "brain/memory/"),
    ("blood/telemetry/",        "blood/telemetry/"),
    ("blood/logs/",             "blood/logs/"),
    ("spine/state/",            "spine/state/"),
    ("heart/tasks/",            "heart/tasks/"),
    ("skeleton/rules/",           "skeleton/rules/"),
    ("dna/feedback/",         "dna/feedback/"),
    ("heart/model_router/",     "heart/model_router/"),
    ("heart/model_router/",     "heart/model_router/"),
    ("dna/dna/dna/identity/profile/",              "dna/dna/dna/dna/identity/profile/"),
    ("dna/dna/dna/identity/prompts/",              "dna/dna/dna/dna/identity/prompts/"),
    ("dna/dna/dna/identity/adaptive/",             "dna/dna/dna/dna/identity/adaptive/"),
    ("heart/heart/heart/orchestrator/mesh/",             "heart/heart/heart/heart/orchestrator/mesh/"),
    ("heart/heart/heart/orchestrator/router/",           "heart/heart/heart/heart/orchestrator/router/"),
    ("hands/automation/dag/",              "hands/automation/dag/"),
    ("heart/goals/",                   "heart/goals/"),
    ("lab/lab/autolab/",                       "lab/lab/lab/autolab/"),
    ("lab/lab/evolution/",                     "lab/lab/lab/evolution/"),
    ("eyes/eyes/dashboard/",                     "eyes/eyes/eyes/dashboard/"),
    ("eyes/eyes/visual/",                        "eyes/eyes/eyes/visual/"),
    ("ears/ears/monitor/",                       "ears/ears/ears/monitor/"),
    ("mouth/mouth/dispatcher/",                    "mouth/mouth/mouth/dispatcher/"),
    ("mouth/mouth/comms/",                         "mouth/mouth/mouth/comms/"),
    ("nervous/nervous/mcp/",                           "nervous/nervous/nervous/mcp/"),
    ("nervous/nervous/gateway/",                       "nervous/nervous/nervous/gateway/"),
    ("spine/spine/audit/",                         "spine/spine/spine/audit/"),
    ("spine/spine/docs/",                          "spine/spine/spine/docs/"),
    ("spine/spine/snapshots/",                     "spine/spine/spine/snapshots/"),
    ("brain/vault/",                "brain/vault/"),
    ("brain/research/",               "brain/research/"),
    ("brain/brain/anticipation/",                  "brain/brain/brain/anticipation/"),
]

SKIP_DIRS = {
    ".git", "__pycache__", ".venv", "venv", "env", "node_modules",
    "spine/backups", "brain/vault", ".agent-backups", ".playwright-mcp",
    ".pytest_cache", ".rtk",
}
PROCESS_EXTS = {".py", ".md", ".json", ".yaml", ".yml", ".sh", ".txt"}


def should_skip(path):
    return any(s in path.replace("\\", "/") for s in SKIP_DIRS)


def update_file(filepath):
    if should_skip(filepath):
        return 0
    if os.path.splitext(filepath)[1] not in PROCESS_EXTS:
        return 0
    try:
        content = open(filepath, encoding="utf-8", errors="ignore").read()
        original = content
        for old, new in PATH_MAPPINGS:
            content = content.replace(old, new)
        if content != original:
            open(filepath, "w", encoding="utf-8").write(content)
            return 1
    except Exception:
        pass
    return 0


if __name__ == "__main__":
    workspace = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    total = 0
    for root, dirs, files in os.walk(workspace):
        rel = os.path.relpath(root, workspace)
        if should_skip(rel):
            dirs.clear()
            continue
        dirs[:] = [d for d in dirs if not d.startswith(".") and d not in SKIP_DIRS]
        for fname in files:
            fpath = os.path.join(root, fname)
            if update_file(fpath):
                print(f"  ✅ {os.path.relpath(fpath, workspace)}")
                total += 1
    print(f"\nTotal: {total} files updated")
