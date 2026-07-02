#!/usr/bin/env python3
"""Bounded adaptive identity learning loop."""

from __future__ import annotations

import argparse
import difflib
import json
import os
import uuid
from collections import Counter
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


ROOT = Path(os.environ.get("SUNEEL_WORKSPACE", Path.home() / "SuneelWorkSpace")).resolve()
ADAPTIVE = ROOT / "dna/identity/adaptive"
FEEDBACK = ADAPTIVE / "feedback_log.json"
SIGNALS = ADAPTIVE / "signal_memory.json"
UPDATES = ADAPTIVE / "pattern_updates.json"
GUARDRAILS = ADAPTIVE / "drift_guardrails.json"
STATE = ADAPTIVE / "adaptation_state.json"
REPORT = ADAPTIVE / "reports/adaptation_report.md"
WEIGHTS = ADAPTIVE / "signal_weights.json"
IDENTITY_PROMPT = ROOT / "dna/identity/prompts/identity_prompt.md"
CLAUDE_IDENTITY = ROOT / "dna/identity/integration/claude_identity.md"


def now() -> str:
    return datetime.now(timezone.utc).astimezone().isoformat()


def read_json(path: Path, default: Any) -> Any:
    try:
        return json.loads(path.read_text())
    except Exception:
        return default


def write_json(path: Path, data: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(data, indent=2, sort_keys=True) + "\n")


def ensure() -> None:
    ADAPTIVE.mkdir(parents=True, exist_ok=True)
    (ADAPTIVE / "reports").mkdir(parents=True, exist_ok=True)
    if not FEEDBACK.exists():
        write_json(FEEDBACK, {"version": "1.0", "events": []})
    if not SIGNALS.exists():
        write_json(SIGNALS, {"version": "1.0", "last_extracted_at": None, "signals": []})
    if not UPDATES.exists():
        write_json(
            UPDATES,
            {
                "version": "1.0",
                "last_updated_at": None,
                "proposed_adjustments": [],
                "active_adjustments": [],
            },
        )
    if not GUARDRAILS.exists():
        write_json(
            GUARDRAILS,
            {
                "version": "1.0",
                "minimum_signals_before_behavior_update": 3,
                "cap_change_magnitude": 0.15,
                "drift_status": "stable",
                "rules": [
                    "Identity must stay aligned with dna/identity/profile/identity_profile.md.",
                    "No sudden large tone changes.",
                    "Require multiple signals before updating behavior.",
                    "Apply only small iterative shifts.",
                    "Never override explicit user-defined identity rules.",
                ],
                "never_override": [
                    "short_direct_casual_conversational",
                    "softened_not_harsh",
                    "never_condescending",
                    "analysis_first_intuition_second",
                    "autopilot_inside_safe_boundaries",
                    "never_wipe_system",
                    "never_delete_important_files_automatically",
                ],
            },
        )
    if not STATE.exists():
        write_json(
            STATE,
            {
                "version": "1.0",
                "enabled": True,
                "loop_status": "ready",
                "stability_status": "stable",
                "last_feedback_at": None,
                "last_learning_run_at": None,
            },
        )
    if not WEIGHTS.exists():
        write_json(
            WEIGHTS,
            {
                "accepted": 0.2,
                "light_edit": 0.4,
                "heavy_edit": 0.8,
                "rejected": 1.0,
                "manual_adjust": 1.2,
                "repeat_preference": 1.0,
                "goal_outcome_success": 0.7,
                "goal_outcome_failure": 1.1,
            },
        )


def estimate_edit_distance(original: str | None, revised: str | None) -> float | None:
    if not original or not revised:
        return None
    ratio = difflib.SequenceMatcher(None, original, revised).ratio()
    return round(1.0 - ratio, 3)


def record_event(
    output_id: str | None,
    context: str,
    agent: str,
    gstack_mode: str | None,
    user_action: str,
    notes: str = "",
    original: str | None = None,
    revised: str | None = None,
) -> str:
    ensure()
    if user_action not in {"accepted", "edited", "rejected", "adjusted"}:
        raise SystemExit("user_action must be accepted, edited, rejected, or adjusted")
    output_id = output_id or f"out-{uuid.uuid4().hex[:10]}"
    data = read_json(FEEDBACK, {"version": "1.0", "events": []})
    event = {
        "output_id": output_id,
        "context": context,
        "agent_used": agent,
        "gstack_mode": gstack_mode,
        "user_action": user_action,
        "edit_distance_estimate": estimate_edit_distance(original, revised),
        "signal_weight": event_weight(user_action, context, estimate_edit_distance(original, revised)),
        "notes": notes,
        "timestamp": now(),
    }
    data.setdefault("events", []).append(event)
    write_json(FEEDBACK, data)
    state = read_json(STATE, {})
    state["last_feedback_at"] = event["timestamp"]
    state["loop_status"] = "feedback_recorded"
    write_json(STATE, state)
    learn()
    return output_id


def event_weight(action: str, context: str = "", edit_distance: float | None = None) -> float:
    weights = read_json(WEIGHTS, {})
    if action == "edited":
        key = "heavy_edit" if edit_distance is not None and edit_distance >= 0.35 else "light_edit"
    elif action == "adjusted":
        key = "manual_adjust"
    elif action == "accepted" and "goal_failure" in context:
        key = "goal_outcome_failure"
    elif action == "accepted" and "goal_success" in context:
        key = "goal_outcome_success"
    else:
        key = action
    return float(weights.get(key, 1.0))


def keyword_signals(events: list[dict[str, Any]]) -> dict[str, dict[str, float]]:
    signals: dict[str, dict[str, float]] = {}

    def add(name: str, weight: float) -> None:
        entry = signals.setdefault(name, {"count": 0.0, "weighted_score": 0.0})
        entry["count"] += 1
        entry["weighted_score"] += weight

    for event in events:
        text = f"{event.get('context','')} {event.get('notes','')}".lower()
        action = event.get("user_action")
        weight = float(event.get("signal_weight") or event_weight(action, event.get("context", ""), event.get("edit_distance_estimate")))
        if "short" in text or "concise" in text or "too long" in text or "verbose" in text:
            add("prefer_shorter_outputs", weight)
        if "direct" in text or "straight" in text:
            add("increase_directness", weight)
        if "soft" in text or "harsh" in text:
            add("preserve_softened_tone", weight)
        if "structure" in text or "structured" in text or "clear" in text:
            add("increase_clear_structure", weight)
        if "tool" in text or "simple" in text or "cost" in text:
            add("preserve_tool_priority_order", weight)
        if action == "rejected":
            add("review_rejected_outputs", weight)
        if action == "edited":
            add("learn_from_user_edits", weight)
        if action == "accepted":
            add("reinforce_current_identity", weight)
        if action == "adjusted":
            add("manual_identity_adjustment", weight)
    return signals


def learn() -> None:
    ensure()
    feedback = read_json(FEEDBACK, {"events": []})
    events = feedback.get("events", [])
    guardrails = read_json(GUARDRAILS, {})
    min_signals = int(guardrails.get("minimum_signals_before_behavior_update", 3))
    cap = float(guardrails.get("cap_change_magnitude", 0.15))
    weighted_signals = keyword_signals(events)
    signal_entries = []
    proposed = []
    active = []
    for name, stats in sorted(weighted_signals.items()):
        count = int(stats["count"])
        weighted_score = round(stats["weighted_score"], 3)
        confidence = round(min(0.95, weighted_score / max(min_signals, 1)), 2)
        signal_entries.append(
            {
                "signal": name,
                "count": count,
                "weighted_score": weighted_score,
                "confidence": confidence,
            }
        )
        adjustment = adjustment_for_signal(name)
        if adjustment:
            item = {
                "signal": name,
                "adjustment": adjustment,
                "support_count": count,
                "weighted_score": weighted_score,
                "confidence": confidence,
                "change_magnitude": cap,
            }
            if weighted_score >= min_signals and safe_adjustment(name):
                active.append(item)
            else:
                proposed.append(item)
    write_json(
        SIGNALS,
        {"version": "1.0", "last_extracted_at": now(), "signals": signal_entries},
    )
    write_json(
        UPDATES,
        {
            "version": "1.0",
            "last_updated_at": now(),
            "proposed_adjustments": proposed,
            "active_adjustments": active,
        },
    )
    state = read_json(STATE, {})
    state["last_learning_run_at"] = now()
    state["loop_status"] = "learning_updated"
    state["stability_status"] = "stable"
    write_json(STATE, state)
    apply_adaptations()
    write_report()


def adjustment_for_signal(name: str) -> str | None:
    return {
        "prefer_shorter_outputs": "Slightly reduce response length while preserving clarity.",
        "increase_directness": "Slightly increase directness without becoming blunt.",
        "preserve_softened_tone": "Keep softened phrasing active when giving direct feedback.",
        "increase_clear_structure": "Use clearer lightweight structure for complex tasks.",
        "preserve_tool_priority_order": "Keep tool choices aligned to simplicity, cost, power, speed, reliability.",
        "review_rejected_outputs": "Inspect rejected outputs for tone, length, and decision mismatch.",
        "learn_from_user_edits": "Treat repeated edits as stronger voice examples.",
        "reinforce_current_identity": "Keep the current base identity stable.",
        "manual_identity_adjustment": "Respect repeated manual identity instructions as high-quality signals.",
    }.get(name)


def safe_adjustment(name: str) -> bool:
    blocked = {"review_rejected_outputs", "learn_from_user_edits"}
    return name not in blocked


def adaptive_block() -> str:
    updates = read_json(UPDATES, {})
    active = updates.get("active_adjustments", [])
    if not active:
        lines = [
            "<!-- adaptive-identity:start -->",
            "## Adaptive Identity Loop",
            "",
            "Base identity is active. No adaptive behavior shifts have enough repeated evidence yet.",
            "",
            "Adaptive learning is bounded by `dna/identity/adaptive/drift_guardrails.json`.",
            "<!-- adaptive-identity:end -->",
        ]
    else:
        lines = [
            "<!-- adaptive-identity:start -->",
            "## Adaptive Identity Loop",
            "",
            "Apply these small, bounded adjustments without overriding the base identity:",
            "",
        ]
        lines.extend(f"- {item['adjustment']}" for item in active)
        lines.extend(
            [
                "",
                "Guardrail: keep Suneel's original identity recognizable and never override explicit profile rules.",
                "<!-- adaptive-identity:end -->",
            ]
        )
    return "\n".join(lines) + "\n"


def replace_block(text: str, block: str) -> str:
    start = "<!-- adaptive-identity:start -->"
    end = "<!-- adaptive-identity:end -->"
    if start in text and end in text:
        before = text.split(start)[0].rstrip()
        after = text.split(end, 1)[1].lstrip()
        return before + "\n\n" + block + ("\n" + after if after else "")
    return text.rstrip() + "\n\n" + block


def apply_adaptations() -> None:
    ensure()
    block = adaptive_block()
    for path in [IDENTITY_PROMPT, CLAUDE_IDENTITY]:
        if path.exists():
            path.write_text(replace_block(path.read_text(), block))


def write_report() -> None:
    ensure()
    feedback = read_json(FEEDBACK, {"events": []})
    signals = read_json(SIGNALS, {"signals": []})
    updates = read_json(UPDATES, {})
    guardrails = read_json(GUARDRAILS, {})
    events = feedback.get("events", [])
    lines = [
        "# Adaptive Identity Report",
        "",
        f"Generated: {now()}",
        "",
        "## Stability",
        "",
        f"- Status: {guardrails.get('drift_status', 'stable')}",
        f"- Feedback events: {len(events)}",
        f"- Active adjustments: {len(updates.get('active_adjustments', []))}",
        f"- Proposed adjustments: {len(updates.get('proposed_adjustments', []))}",
        "",
        "## Key Patterns Learned",
        "",
    ]
    if signals.get("signals"):
        for item in signals["signals"]:
            lines.append(
                f"- {item['signal']}: count {item['count']}, confidence {item['confidence']}"
            )
    else:
        lines.append("- No repeated patterns learned yet.")
    lines.extend(["", "## Behavior Shifts", ""])
    if updates.get("active_adjustments"):
        for item in updates["active_adjustments"]:
            lines.append(f"- {item['adjustment']}")
    else:
        lines.append("- No active shifts yet. Base identity remains unchanged.")
    lines.extend(
        [
            "",
            "## Guardrails",
            "",
            "- Identity evolves slowly.",
            "- Original identity rules stay protected.",
            "- Multiple signals are required before behavior changes.",
            "- Large tone or safety changes require review.",
        ]
    )
    REPORT.write_text("\n".join(lines) + "\n")


def main() -> int:
    parser = argparse.ArgumentParser(description="Adaptive identity loop")
    sub = parser.add_subparsers(dest="command", required=True)

    rec = sub.add_parser("record")
    rec.add_argument("--output-id")
    rec.add_argument("--context", default="general")
    rec.add_argument("--agent", default="Codex")
    rec.add_argument("--gstack-mode")
    rec.add_argument("--user-action", choices=["accepted", "edited", "rejected", "adjusted"], required=True)
    rec.add_argument("--notes", default="")
    rec.add_argument("--original")
    rec.add_argument("--revised")

    hook = sub.add_parser("hook")
    hook.add_argument("--output-id")
    hook.add_argument("--context", default="execution_cycle")
    hook.add_argument("--agent", default="Codex")
    hook.add_argument("--gstack-mode")
    hook.add_argument("--notes", default="cycle_completed")

    accept = sub.add_parser("accept")
    accept.add_argument("output_id")
    accept.add_argument("notes", nargs="*", default=[])

    reject = sub.add_parser("reject")
    reject.add_argument("output_id")
    reject.add_argument("notes", nargs="*", default=[])

    adjust = sub.add_parser("adjust")
    adjust.add_argument("instruction", nargs="+")

    sub.add_parser("learn")
    sub.add_parser("report")
    sub.add_parser("apply")

    args = parser.parse_args()
    ensure()
    if args.command == "record":
        output_id = record_event(
            args.output_id,
            args.context,
            args.agent,
            args.gstack_mode,
            args.user_action,
            args.notes,
            args.original,
            args.revised,
        )
        print(output_id)
    elif args.command == "hook":
        output_id = record_event(
            args.output_id,
            args.context,
            args.agent,
            args.gstack_mode,
            "accepted",
            args.notes,
        )
        print(output_id)
    elif args.command == "accept":
        print(record_event(args.output_id, "manual_feedback", "user", None, "accepted", " ".join(args.notes)))
    elif args.command == "reject":
        print(record_event(args.output_id, "manual_feedback", "user", None, "rejected", " ".join(args.notes)))
    elif args.command == "adjust":
        print(record_event(None, "manual_adjustment", "user", None, "adjusted", " ".join(args.instruction)))
    elif args.command == "learn":
        learn()
        print(SIGNALS)
    elif args.command == "report":
        write_report()
        print(REPORT)
    elif args.command == "apply":
        apply_adaptations()
        print("adaptive identity applied")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
