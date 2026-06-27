# Workspace Autoresearch Program

## Purpose

This system exists to improve `~/SuneelWorkSpace` itself. It should make the shared Claude/Codex workspace more reliable, clear, self-repairing, observable, and easy for Suneel to use.

## Research Organization

Autolab has three layers:

- Human strategy layer: `program.md`, `mutation_policy.md`, `safeguards.md`, and `evaluator.md`.
- Agent execution layer: Claude or Codex may run bounded experiments using Autolab scripts.
- Infrastructure layer: canonical paths, backups, safety gates, state, logs, and rollback are guarded.

## Improvement Rules

- Prefer small changes over sweeping rewrites.
- Every experiment must be bounded, measurable, and revertible.
- Only keep a change when it improves the workspace score and preserves safety gates.
- When uncertain, choose safety and transparency.
- Do not chase novelty for its own sake.
- Preserve beginner-friendliness.
- Keep state file-based and inspectable.
- Do not perform money-related actions.
- Do not touch unrelated personal documents.

## Improvement Themes

- Better startup clarity.
- Better automatic closeout.
- Better handoff quality.
- Less instruction drift.
- Better docs.
- More reliable wrappers.
- Stronger repair routines.
- Better state indexing.
- Simpler operator experience.
- Cleaner experiment history.
- Better reports about what improved recently.

## Experiment Shape

Each experiment should include:

- Target area.
- Hypothesis.
- Files that may change.
- Evaluation before and after.
- Keep/revert decision.
- Notes for the next agent.

## Meta-Improvement

Autolab may improve its own program, evaluator, templates, and selected scripts. Changes to scoring logic or safety policy require a higher bar: safety gates must pass, the score must not drop, and the reason must be documented.

## Autolab v2 Learning Loop

Autolab must learn from experiment history:

- Analyze `results.tsv` after experiments.
- Track successful mutation types in `lab/autolab/meta/patterns.json`.
- Track repeated failure types in `lab/autolab/meta/failure_patterns.json`.
- Record human-readable lessons in `lab/autolab/meta/insights.md`.
- Prefer future experiments that match successful patterns.
- Avoid repeating known failure patterns.
- Occasionally explore under-tested low-risk areas.
- Share durable lessons through workspace memory and handoff files when they matter to both Claude and Codex.

## Strategy Evolution

Autolab may evolve this `program.md` only when the change improves clarity, consistency, success rate, or failure avoidance.

Before changing this file, snapshot the current version into `lab/autolab/meta/strategy_versions/`.

Never remove safety constraints, rollback requirements, mutation limits, or the rule that changes must be measurable and reversible.

Strategy changes require a higher confidence threshold than report or template changes. If uncertain, do not change the strategy.

## Learned Strategy Note

- Added 2026-06-24T15:41:08-0500 after analysis. Prefer experiments tied to observed score gaps; avoid repeating failure classes listed in `meta/failure_patterns.json`.
