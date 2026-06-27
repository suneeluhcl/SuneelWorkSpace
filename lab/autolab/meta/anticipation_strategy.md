# Anticipation Strategy

Autolab may inspect anticipation quality and recommend improvements, but it must not auto-execute suggested actions.

## Inputs

- `brain/anticipation/prediction_memory.json`
- `brain/anticipation/behavior_patterns.json`
- `brain/anticipation/action_suggestions.md`
- `brain/anticipation/reports/anticipation_report.md`

## What Autolab Can Do

- Identify repeated workflow sequences.
- Recommend better suggestions.
- Detect low-value or noisy suggestions.
- Report whether suggestions remain safe and bounded.

## Limits

- Suggestions are not commands.
- Do not auto-send messages.
- Do not run destructive actions.
- Do not install tools or change accounts.
