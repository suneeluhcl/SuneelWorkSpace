# Autolab Safeguards

## Purpose

Safeguards keep self-improvement bounded, reversible, and understandable.

## Hard Boundaries

- No money-related actions.
- No destructive changes without backup.
- No hidden databases or external services.
- No mutation of unrelated personal files.
- No blind merge of `~/suneelworkspace` and `~/SuneelWorkSpace`.
- No weakening of safety gates to make a bad experiment look good.

## Rollback Rules

- Every mutating experiment creates a snapshot first.
- Failed or non-improving experiments restore the snapshot.
- The failed attempt is logged in `results.tsv`.
- Failed artifacts may be moved to `lab/autolab/quarantine/` for inspection.

## Meta-Improvement Rules

Autolab may improve its own program, templates, reports, and scripts.

Changing evaluator/scoring logic requires stronger evidence:

- Safety gates must pass.
- Score must not drop.
- The reason must be logged.
- The previous evaluator must remain available in a snapshot.

Changing `lab/autolab/safeguards.md` or `skeleton/rules/SAFETY_BOUNDARIES.md` requires explicit human approval.

## Strategy Evolution Safeguards

Autolab may update `lab/autolab/program.md` only when:

- The previous program is copied to `lab/autolab/meta/strategy_versions/`.
- Safety constraints remain present.
- Mutation boundaries remain present.
- The workspace score does not drop.
- The result is logged in `results.tsv` and `meta/learning_log.md`.

Autolab must reject or revert any program change that allows mutation outside authorized areas or weakens safety language.

## Failure Intelligence

Failures must be classified and used for future avoidance.

Common failure classes:

- `no_score_improvement`
- `safety_gate_failed`
- `json_invalid`
- `script_not_executable`
- `link_drift`
- `overbroad_change`
- `unknown`

## Beginner-Friendly Rule

If a change makes the system harder for Suneel to understand, it should be rejected unless it fixes a clear safety or reliability issue.
