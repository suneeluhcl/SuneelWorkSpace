# Mutation Policy

## Purpose

This policy defines what Autolab may change automatically.

## Allowed Mutable Surface

Autolab may change:

- `lab/autolab/program.md`
- `lab/autolab/evaluator.md`
- `lab/autolab/current_frontier.md`
- `lab/autolab/experiment_queue.md`
- `lab/autolab/reports/`
- `lab/autolab/state/`
- `lab/autolab/templates/`
- `lab/autolab/scripts/`
- Selected workspace scripts in `bin/` when explicitly queued or agent-approved.
- Selected docs in `brain/memory/spine/docs/`.
- Selected shared prompt/rule files in `skeleton/rules/`, except safety-critical boundaries.
- Selected maintenance logic in `automation/maintenance/` and `automation/hooks/` when explicitly queued or agent-approved.

## Denylist

Autolab must not autonomously mutate:

- `.agent-backups/`
- `.git/`
- `.env`, secrets, credentials, keys, tokens, or private config.
- `secrets/`
- Financial, billing, account, or purchase-related files.
- Unrelated personal documents.
- `skeleton/rules/SAFETY_BOUNDARIES.md` without explicit human approval.
- `lab/autolab/safeguards.md` without explicit human approval.
- Canonical path declarations that point away from `~/SuneelWorkSpace`.
- Global shell configuration rewrites outside the existing small marked helper block.
- Anything outside `~/SuneelWorkSpace` except launchd symlinks/plists that point back into the workspace.

## Snapshot Rule

Before a mutating experiment, Autolab must snapshot the allowed mutable surface into `lab/autolab/spine/snapshots/`.

## Revert Rule

If an experiment fails safety gates or does not improve score, Autolab must restore the snapshot and write a rollback note.
