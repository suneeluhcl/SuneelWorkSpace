# Workspace Autolab

## Purpose

Autolab is a safe, file-based self-improvement loop for `~/SuneelWorkSpace`.

It does not train model weights. It improves the workspace itself: prompts, rules, helper scripts, validation, reports, repair logic, and operating docs.

## How It Works

1. Read `lab/autolab/program.md`.
2. Pick one small bounded improvement.
3. Snapshot the allowed mutable surface.
4. Apply the change only inside allowed paths.
5. Run `autolab-eval`.
6. Keep the change only if the score improves and safety gates pass.
7. Otherwise restore from the snapshot and log the revert.

## Main Commands

```sh
~/SuneelWorkSpace/lab/autolab/scripts/autolab-eval
~/SuneelWorkSpace/lab/autolab/scripts/autolab-once
~/SuneelWorkSpace/lab/autolab/scripts/autolab-report
~/SuneelWorkSpace/lab/autolab/scripts/autolab-frontier
~/SuneelWorkSpace/lab/autolab/scripts/autolab-enqueue "docs" "Improve operator guide clarity"
```

Periodic background automation runs light evaluation. Mutating experiments are bounded and conservative.

## Autolab v2 Learning

Autolab v2 learns from its own experiment history.

It tracks:

- Which mutation types succeed.
- Which failure types repeat.
- Which target areas are under-explored.
- Whether Claude, Codex, or an unknown agent is associated with outcomes when detectable.
- A simple confidence score based on experiment history.

Learning files live in:

`~/SuneelWorkSpace/lab/autolab/meta/`

Run:

```sh
~/SuneelWorkSpace/lab/autolab/scripts/autolab-analyze
```

## What To Remember

You usually do not need to run Autolab manually. It is integrated with maintenance. Use `autolab-report` when you want to see what changed or what could improve next.
