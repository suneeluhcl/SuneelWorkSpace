# Workspace Cleanup Plan

This plan classifies workspace files, archives logs, and cleans up empty directories and temporary files safely without breaking system integrity.

## Classification Matrix

### Core System (KEEP)
- `brain/memory/` — Shared memory, tasks, and state.
- `brain/anticipation/` — Prediction and execution engine.
- `lab/autolab/` — Workspace self-improvement system.
- `automation/` — Maintenance, plist and background execution rules.
- `bin/` — Primary CLI entrypoints.
- `mouth/comms/` — Messaging and email subsystems.
- `heart/goals/` — Planning and execution graph system.
- `dna/identity/` — User profile, tone, and decision identity maps.
- `nervous/mcp/` — Model Context Protocol servers and logic.
- `brain/vault/` — Knowledge base and canvas files.
- `heart/orchestrator/` — Task routing and model allocation logic.
- `projects/` — User development projects folder.
- `brain/research/` — Codebase research and decision capturing engine.
- `scripts/` — Auxiliary system intelligence tools.
- `spine/system-context/` — Workspace profile and metadata details.
- `spine/tools/` — Code inventory and recommendation details.

### Configurations (PROTECT)
- `opencode.json` (Root) — Used by `swopencode`.
- `GEMINI.md` (Root) — Used by `swgemini`.
- `AGENTS.md` (Root) — Primary agents config.
- `CLAUDE.md` (Root) — Primary Claude config.
- `.agents/AGENTS.md` — Customizations entrypoint.
- `mouth/mouth/comms/config/*.json` — Communications permissions and settings.
- `nervous/nervous/mcp/server/config/*.json` — MCP resource mappings and tool policies.
- `heart/heart/orchestrator/router/*.json` — Routing policy configuration.
- `dna/dna/identity/adaptive/*.json` — Identity learning guards.

### Logs (ARCHIVE)
- `mouth/comms/mail/logs/*.log` -> Move to `blood/logs/archive/mail/` (compressed).
- `mouth/comms/imessage/logs/*.log` -> Move to `blood/logs/archive/imessage/` (compressed).
- `nervous/nervous/mcp/server/logs/*.log` -> Move to `blood/logs/archive/nervous/mcp/` (compressed).
- `automation/reports/*.log` -> Move to `blood/logs/archive/automation/` (compressed).
- `lab/autolab/reports/*.log` -> Move to `blood/logs/archive/lab/autolab/` (compressed).

### Temp Files & Backups (CLEANUP)
- Empty directories (remove):
  - `brain/vault/mcp-config`
  - `brain/vault/inbox`
  - `mouth/comms/imessage/state/drafts`
  - `nervous/nervous/mcp/server/cache`
  - `nervous/nervous/mcp/server/storage/cache`
  - `automation/doctor`
  - `automation/repair`
  - `lab/autolab/sandboxes`
- Real-time generated log leftovers.

### Duplicates & Unclear Files (PRESERVE/FLAG)
- Autolab snapshots: Preserved as they store historic frontiers and rollback points.
- Binaries/Scripts outside `bin/`: Placed in subsystem-specific script folders (e.g. `mouth/comms/mail/scripts/`, `nervous/nervous/mcp/server/scripts/`, etc.). Keep intact as they are called by internal APIs.

---

## Action Plan

### Step 1: Create Log Archive Structure
Create directory: `blood/logs/archive/`.

### Step 2: Safe Log Compression & Archiving
Compress `.log` files to `.tar.gz` or `.gz` and store in `blood/logs/archive/`. Then clear or truncate the active log files.

### Step 3: Remove Empty Directories
Remove the 8 empty directories identified during the scan to clean up directory trees.

### Step 4: Normalize Naming
Ensure system files are consistent. No action needed as files are already structured properly.
