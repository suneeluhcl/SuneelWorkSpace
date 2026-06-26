# Adaptive Identity Loop

This layer lets Suneel's identity evolve from real interaction feedback without drifting away from the explicit identity profile.

## What It Learns From

- Accepted outputs.
- Edited outputs.
- Rejected outputs.
- Rephrasing instructions.
- Changed decisions.

## Safety Model

- Base identity files remain the source of truth.
- Adaptation is small and incremental.
- Multiple signals are required before behavior changes.
- Explicit identity rules are protected.
- Drift is reported, not silently applied.

## Main Files

- `feedback_log.json`: raw feedback events.
- `signal_weights.json`: quality weights for accepted, edited, rejected, adjusted, and goal outcome signals.
- `signal_memory.json`: extracted behavior signals.
- `pattern_updates.json`: proposed and active small adjustments.
- `drift_guardrails.json`: limits and protected rules.
- `adaptation_state.json`: loop status.
- `reports/adaptation_report.md`: human-readable status.

## Commands

- `identity-accept <id>` records an accepted output.
- `identity-reject <id> [reason]` records a rejected output.
- `identity-adjust "instruction"` records a user correction or preference.

## Weighted Learning

Patterns are based on weighted evidence, not raw counts.

Default weights:

- accepted: 0.2
- light_edit: 0.4
- heavy_edit: 0.8
- rejected: 1.0
- manual_adjust: 1.2
- repeat_preference: 1.0
- goal_outcome_success: 0.7
- goal_outcome_failure: 1.1
