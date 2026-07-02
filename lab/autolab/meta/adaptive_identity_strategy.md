# Adaptive Identity Strategy

Autolab may analyze identity effectiveness, but it must not override identity automatically.

## Inputs

- `dna/identity/adaptive/feedback_log.json`
- `dna/identity/adaptive/signal_weights.json`
- `dna/identity/adaptive/signal_memory.json`
- `dna/identity/adaptive/pattern_updates.json`
- `dna/identity/adaptive/drift_guardrails.json`
- `dna/identity/adaptive/reports/adaptation_report.md`

## What Autolab Can Do

- Detect repeated rejection/edit patterns.
- Recommend small identity tweaks.
- Report degraded output trends.
- Compare active adjustments against drift guardrails.
- Check whether weighted signals indicate improving or degrading identity quality.

## What Autolab Must Not Do

- Override `dna/identity/profile/identity_profile.md`.
- Remove explicit user preferences.
- Change safety boundaries.
- Make large tone shifts automatically.
- Send messages, install tools, or modify external services.
