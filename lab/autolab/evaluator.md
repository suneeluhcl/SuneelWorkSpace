# Autolab Evaluator

## Purpose

The evaluator turns workspace health into a measurable score. Experiments are kept only when they improve the score and pass critical safety gates.

## Critical Safety Gates

An experiment is rejected if any of these fail:

- Canonical instruction file exists.
- Workspace and global Claude/Codex entrypoints resolve to the canonical instruction file.
- Required state JSON files are valid.
- `agent-doctor` reports no errors.
- Safety files exist.
- Autolab safeguards and mutation policy exist.
- **gstack integrity**: `bin/gstack-verify` must exit 0 (pinned commit matches). Drift blocks experiments — a tampered skill installation cannot be trusted to guide the evaluation. Skip this gate only if `AUTOLAB_SKIP_GSTACK_CHECK=1` is set explicitly.

## Score Categories

Total score: 100 points.

- Canonical links: 12
- Required files and directories: 12
- JSON validity: 12
- Script executability: 10
- Doctor health: 12
- Automatic startup/closeout readiness: 10
- Launchd maintenance status: 8
- Duplicate instruction drift absent: 8
- Documentation coverage: 8
- Rollback/snapshot readiness: 5
- Git awareness and dirty-worktree safety: 3

## Acceptance Rule

Keep an experiment only when:

- Safety gates pass.
- Score after is greater than score before.
- The change stays within the allowed mutable surface.
- The experiment log explains what changed.

If the score is equal or lower, revert.

## Stronger Bar For Evaluator Changes

Changes to `lab/autolab/evaluator.md`, `lab/autolab/scripts/autolab-core`, or safety gate logic require:

- No safety gate failures.
- No score drop.
- A written reason in `results.tsv`.
- A snapshot before and after the change.

## Autolab v2 Learning Signals

The evaluator and results history track:

- Mutation type.
- Target area.
- Risk level.
- Score delta.
- Failure reason.
- Pattern tag.
- Agent type when detectable.

These fields help Autolab choose future experiments. They do not override safety gates.

## Autolab v2 Reports

Pattern analysis writes:

- `lab/autolab/meta/insights.md`
- `lab/autolab/meta/patterns.json`
- `lab/autolab/meta/failure_patterns.json`
- `lab/autolab/meta/experiment_embeddings.json`
- `lab/autolab/reports/top_improvements.md`
- `lab/autolab/reports/risky_changes.md`
- `lab/autolab/reports/experiment_categories.md`

The confidence score is a simple local heuristic, not a machine learning model.

## Confidence Signal

Autolab computes a simple confidence score from experiment history:

- Higher confidence when repeated low-risk experiments succeed.
- Lower confidence when experiments revert repeatedly.
- No automatic high-risk mutation should be selected from confidence alone.
