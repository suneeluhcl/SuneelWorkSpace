# gstack Integration

gstack is a collection of specialist reasoning modes (skills) for Claude Code. Each skill activates a domain-expert persona with a structured methodology.

Installed at: `~/.claude/skills/gstack/`  
Policy file: `heart/orchestrator/router/gstack_policy.json`  
Task types enhanced: `heart/orchestrator/router/task_types.json`

## What gstack adds

Your workspace handles routing, memory, goals, and orchestration.  
gstack adds **how Claude thinks** for each task type — structured expert methodologies instead of generic responses.

```
You describe a task
      ↓
Orchestrator: WHO handles it (Claude or Codex)
      ↓
gstack: HOW Claude thinks about it (/investigate, /cso, /review, etc.)
```

## Skills and when they trigger

| Skill | Task types | What it does |
|---|---|---|
| `/investigate` | debugging, workspace_repair | 5-phase root-cause: Observe → Hypothesize → Test → Fix → Verify |
| `/cso` | security | OWASP Top 10 + STRIDE threat model; trust boundary analysis |
| `/review` | analysis, code_edit | Auto-fix obvious bugs; flag production risks; check error paths |
| `/office-hours` | planning, orchestration | 10-star product challenge; tighten scope before building |
| `/plan-eng-review` | system_design | Lock interfaces, scope, dependencies, risks before coding |
| `/ship` | (manual) | Tests → diff review → version bump → CHANGELOG → commit → PR |
| `/careful` | scripting, file_manipulation | Preview destructive commands before executing |
| `/qa` | (manual) | Browser-based flow testing with automatic bug reports |
| `/autoplan` | (manual) | Runs CEO + design + eng review sequentially |

## How routing surfaces skills

`route-task "your task"` now includes a `gstack_skill` field:

```
ROUTING DECISION
  Agent:        CLAUDE
  Task type:    debugging (Debugging / Error Analysis)
  Confidence:   78% [medium]
  gstack skill: /investigate  ← 5-phase systematic root-cause analysis
  Reasoning:    matched keywords: error, bug
```

JSON output also includes `gstack_skill` and `gstack_hint` fields.

## How goal-execute surfaces skills

When a goal task has a matching skill, goal-execute shows it in the task card:

```
Task: T002_01
  Description : Diagnose root cause of the NLU routing failure
  Task type   : debugging
  Agent       : claude (orchestrator rec: claude, conf: 78%)
  gstack mode : /investigate  ← 5-phase systematic root-cause analysis
  ============================================================
  TASK FOR CLAUDE: Diagnose root cause of the NLU routing failure
  Cognitive mode: invoke /investigate at session start
  Why: 5-phase systematic root-cause analysis before attempting a fix
```

## How to use it

**Option A — Direct slash command:**
```sh
# In Claude Code, type at start of session:
/investigate
# Then describe what you're debugging
```

**Option B — Let the orchestrator guide you:**
```sh
route-task "fix the NLU intent routing mismatch"
# → shows: gstack skill: /investigate
# → open Claude Code, type /investigate
```

**Option C — MCP tools from inside Claude/Codex:**
```
get_gstack_recommendation("fix the NLU intent routing mismatch")
suggest_cognitive_mode("review the security of the API auth layer")
list_available_gstack_skills()
```

**Option D — Goal engine tasks:**
```sh
goal-create "Debug NLU routing failures" --complexity medium
goal-plan G001
goal-execute G001 --dry-run
# → task cards show /investigate hint automatically
```

## Autolab tracking

`lab/autolab/meta/patterns.json` now has a `cognitive_modes` section that tracks skill usage per experiment. As you use skills and log outcomes, route-learn will update observed success rates per skill.

## Updating gstack

```sh
cd ~/.claude/skills/gstack && git pull
# Then re-run symlinks:
for skill in cso investigate review office-hours ship plan-eng-review qa careful autoplan; do
  ln -sf ~/.claude/skills/gstack/$skill ~/.claude/skills/$skill
done
```

## Safety

- Skills are advisory — they are never auto-invoked
- `/careful` and `/ship` are the only skills with side effects (file writes, git commands)
- All existing safety boundaries remain in force
- Removing `~/.claude/skills/gstack/` and reverting `task_types.json` fully restores the prior state

---

## Supply Chain Protection

gstack is an external dependency installed from `garrytan/gstack`. To prevent silent
updates from changing skill behaviour, the workspace enforces version pinning and
integrity checking at multiple layers.

### How It Works

| Layer | File | What it does |
|-------|------|-------------|
| Version pin | `nervous/mcp/config/gstack_version.json` | Records exact commit hash and version |
| Integrity check | `bin/gstack-verify` | Compares live install to pinned commit; exits non-zero on drift |
| Repair script | `bin/gstack-repair` | Resets to pinned commit or performs a controlled upgrade |
| Snapshot | `spine/snapshots/gstack/` | Local tarball of the pinned install (not committed to git) |
| MCP tools | `verify_gstack_integrity()` | Live integrity check via Claude |
| Autolab gate | `lab/autolab/evaluator.md` | Blocks experiments when drift is detected |
| Maintenance | `bin/agent-maintain` | Runs `gstack-verify` every cycle, logs drift as warning |

### Pinned Version

```
Version: 1.58.4.0
Commit:  9fd03fae9e74f5daa7a138366aca8f86c7367c5c
Config:  nervous/mcp/config/gstack_version.json
```

### Checking Integrity

```bash
# Quick check
~/SuneelWorkSpace/bin/gstack-verify

# JSON output (for scripting)
~/SuneelWorkSpace/bin/gstack-verify --json

# Via MCP (from Claude)
# call: verify_gstack_integrity()
```

Exit 0 = OK. Exit 1 = drift detected. Exit 2 = config error.

### Upgrading gstack Safely

Upgrades require explicit human intent. Never run `git pull` in `~/.claude/skills/gstack` directly.

**Steps:**
1. Review the garrytan/gstack changelog and recent commits
2. Run `bin/gstack-repair --upgrade` — this will:
   - Fetch `origin/main` (read-only, no merge yet)
   - Show old vs new commit and a diff link
   - Ask for typed confirmation (`y`)
   - Snapshot the current install before merging
   - Merge via `--ff-only` (no history rewriting)
   - Update `nervous/mcp/config/gstack_version.json` with the new pin
3. Run `bin/gstack-verify` to confirm the new state is clean
4. Run `git add nervous/mcp/config/gstack_version.json && git commit` to record the new pin

### Restoring from Snapshot

If the install is corrupted beyond git repair:

```bash
# List available snapshots
ls ~/SuneelWorkSpace/spine/snapshots/gstack/

# Restore manually
rm -rf ~/.claude/skills/gstack
tar -xzf ~/SuneelWorkSpace/spine/snapshots/gstack/<snapshot>.tar.gz -C ~/.claude/skills/

# Confirm integrity
~/SuneelWorkSpace/bin/gstack-verify
```

### Drift Response Policy

| Detected by | Action |
|-------------|--------|
| `bin/gstack-verify` (manual) | Review, then run `bin/gstack-repair` if unexpected |
| `bin/agent-maintain` (scheduled) | Logs warning to `MAINTENANCE_LOG.md` — does NOT auto-repair |
| `autolab evaluate` | Blocks experiment — set `AUTOLAB_SKIP_GSTACK_CHECK=1` only if intentional |
| MCP `verify_gstack_integrity()` | Reports status — repair requires human-initiated terminal command |
