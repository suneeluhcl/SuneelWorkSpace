---
name: nlu-fix
description: Guided NLU repair workflow for Adwi. Reads NLU_REPAIR_BACKLOG.md for the next open item, shows failure context, then guides through the fix → verify → mark-applied cycle. Use when starting an NLU improvement session.
---

You are guiding an NLU fix session for the Adwi local AI OS. Follow this exact workflow:

## Step 1 — Read the current backlog

Read `adwi/adwi/spine/docs/NLU_REPAIR_BACKLOG.md` and identify all items with status `🔴 Open` or `🟡 In progress`.

If there are no open items, report: "No open NHR items in backlog. Run /eval-summary to check current failure clusters and identify new targets."

## Step 2 — Select the highest-priority open item

Present the top open item with:
- NHR ID and title
- Category (regex ordering / regex pattern / INTENT_SYSTEM / etc.)
- The specific failure examples from the backlog
- The proposed fix if one is documented

Ask the user: "Work on this item, or pick a different one?"

## Step 3 — Locate the fix sites

For **regex fixes**:
- Read `adwi/adwi_cli.py` around `_REGEX_INTENTS` (lines ~503–660)
- Identify exactly where the new pattern must be inserted (ordering is load-bearing — first match wins)
- Show the surrounding context so the user can verify placement

For **`_INTENT_SYSTEM` fixes**:
- Read `adwi/adwi_cli.py` around lines 865–1020
- Find the relevant intent description

For **eval file fixes**:
- Check if the fix needs to be mirrored to `adwi/logs/simeval/run_large_eval.py` and `adwi/logs/simeval/run_large_eval_p2.py`

## Step 4 — Apply the fix

Apply the minimal change. After editing:
1. Run `python3 -m py_compile adwi/adwi_cli.py && echo "syntax OK"` immediately
2. If the fix touches all 3 files, run `/adwi-sync-check` to confirm sync
3. Run `/adwi-check` for the fast regression suite

## Step 5 — Verify improvement

After passing adwi-check, run a targeted mini-eval if the fix affected a specific intent family:
```bash
python3 adwi/logs/simeval/run_large_eval_p2.py --workers 5
```
(P2 is faster — use it first; only run full P1 for broad changes)

## Step 6 — Mark as applied

Update `adwi/adwi/spine/docs/NLU_REPAIR_BACKLOG.md`:
- Change `🔴 Open` → `✅ Applied <date>`
- Add the measured pass rate improvement

Update `CLAUDE.md` eval table if the pass rate changed materially (>0.3pp).

Update `notes/adwi-mistakes-and-fixes.md` with a one-line entry if a bug pattern was fixed.

## Key invariants (never violate)

- `_REGEX_INTENTS` ordering is load-bearing — new patterns go BEFORE any intent they must beat
- All fixes must be synced across all 3 files (adwi_cli.py, run_large_eval.py, run_large_eval_p2.py)
- Never run P1 and P2 evals in parallel — sequential only
- Current baseline: P1=96.7%, P2=98.2%, Combined=~97.0%
