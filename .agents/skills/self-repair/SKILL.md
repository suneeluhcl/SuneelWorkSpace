---
name: self-repair
description: >
  Systematic self-repair skill to diagnose failures, check workspace health, repair syntax/test errors, and manage safe rollbacks.
---

# Self Repair

## Purpose
Use this skill when you encounter task failures, command crashes, lint/compilation errors, or test failures, to systematically diagnose and resolve the issue.

## Step-by-Step Instructions

### Phase 1: Locate and Diagnose
1. **Identify the Failure**: Inspect recent terminal error outputs, stderr logs, or test reports. If the failure happened in a previous session, read [SESSION_LOG.md](file:///Users/MAC/SuneelWorkSpace/agent-system/logs/SESSION_LOG.md) and the latest exit code in [SESSION_HANDOFF.md](file:///Users/MAC/SuneelWorkSpace/agent-system/memory/SESSION_HANDOFF.md).
2. **Check Workspace Health**: Run `./bin/agent-doctor` to see if there is any script permission drift, broken symlinks, duplicate files, or JSON corruption.
3. **Isolate the Cause**: Determine if the error is due to:
   - Workspace drift (missing directory, permissions).
   - Code syntax/logic errors.
   - Missing environment variables or configuration.

### Phase 2: Core Workspace Repairs
1. **Fix Environment/Drift**: If `agent-doctor` reported issues, run `./bin/agent-repair` first to restore baseline folders, symlinks, and scripts.
2. **Verify Headroom**: Check if the Headroom proxy is active on port `8787` (`nc -z 127.0.0.1 8787`). If it is down, warn the operator to start it.

### Phase 3: Code and Syntax Correction
1. **Isolate Code Files**: Find the files containing syntax or logic errors using `rtk grep` or compiler output messages.
2. **Review Lint / Compiler Logs**: Run the compiler or linter (e.g. `rtk cargo check`, `rtk tsc`, `rtk lint`) to pin down precise line numbers.
3. **Make Targeted Replacements**: Use code editing tools to make minimal, focused changes to the problematic files. Never rewrite files from scratch when a targeted replacement works.

### Phase 4: Test & Verify
1. **Execute Tests**: Run the specific test command (prefixed with `rtk`) or run the global E2E loop [agent-test-loop](file:///Users/MAC/SuneelWorkSpace/bin/agent-test-loop).
2. **Verify Improvement**: Confirm that the health issues or compilation errors are resolved, and the test pass rate has increased.

### Phase 5: Safe Rollback
1. **Detect Regression**: If your edits broke other tests or reduced the pass rate, DO NOT commit.
2. **Revert Changes**: Revert to the last known good git commit:
   ```bash
   rtk git reset --hard HEAD
   ```
   Or restore the snapshot if using Autolab:
   ```bash
   python3 autolab/scripts/autolab-core revert
   ```
3. **Iterate**: Adjust your hypothesis and try a different, safer fix.

## Execution Rules
- Always use `rtk` command wrappers.
- Keep session handoffs up to date in [agent-system/memory/SESSION_HANDOFF.md](file:///Users/MAC/SuneelWorkSpace/agent-system/memory/SESSION_HANDOFF.md).
- Run `./bin/agent-doctor` after executing code edits.

