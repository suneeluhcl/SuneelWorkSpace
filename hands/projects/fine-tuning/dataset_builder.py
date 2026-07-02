#!/usr/bin/env python3
"""Fine-Tuning Dataset Builder.
Converts feedback_log.json into instruction-tuning format for model training.
"""
import json
import os
import sys
from pathlib import Path
from datetime import datetime

WORKSPACE = Path(os.environ.get('WORKSPACE', Path.home() / 'SuneelWorkSpace'))
FEEDBACK_FILE = WORKSPACE / 'dna/identity/adaptive/feedback_log.json'
OUTPUT_DIR = WORKSPACE / 'projects/fine-tuning/datasets'


def load_feedback():
    if not FEEDBACK_FILE.exists():
        return []
    with open(FEEDBACK_FILE) as f:
        data = json.load(f)
    # Handle both list and dict formats
    if isinstance(data, list):
        return data
    return data.get('entries', data.get('feedback', []))


def classify_entry(entry: dict) -> str:
    """Determine if entry is accepted, rejected, or ambiguous."""
    signal = entry.get('signal', entry.get('feedback', entry.get('label', '')))
    if isinstance(signal, str):
        signal = signal.lower()
        if any(k in signal for k in ['accept', 'good', 'correct', 'yes', 'approve']):
            return 'accepted'
        if any(k in signal for k in ['reject', 'bad', 'wrong', 'no', 'decline']):
            return 'rejected'
    if isinstance(signal, bool):
        return 'accepted' if signal else 'rejected'
    if isinstance(signal, (int, float)):
        return 'accepted' if signal > 0.5 else 'rejected'
    return 'ambiguous'


def to_training_pair(entry: dict, label: str) -> dict:
    return {
        "instruction": entry.get('instruction', entry.get('prompt', entry.get('input', ''))),
        "input": entry.get('context', entry.get('input', '')),
        "output": entry.get('response', entry.get('output', entry.get('completion', ''))),
        "label": label,
        "source": "feedback_log",
        "date": entry.get('timestamp', entry.get('date', datetime.now().isoformat()))
    }


def main():
    print(f"Loading feedback from: {FEEDBACK_FILE}")

    if not FEEDBACK_FILE.exists():
        print(f"No feedback log found at {FEEDBACK_FILE}")
        print("The system will build training data once feedback is collected.")
        # Create empty dataset as placeholder
        OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
        placeholder = OUTPUT_DIR / 'README.md'
        if not placeholder.exists():
            placeholder.write_text(
                "# Fine-Tuning Datasets\n\nDatasets built from dna/identity/adaptive/feedback_log.json.\n"
                "Run `build-training-data` after collecting feedback.\n"
            )
        return

    feedback = load_feedback()
    print(f"  Entries found: {len(feedback)}")

    accepted = []
    rejected = []
    ambiguous = []

    for entry in feedback:
        label = classify_entry(entry)
        pair = to_training_pair(entry, label)

        # Filter: only include entries with actual content
        if not pair['instruction'] and not pair['output']:
            ambiguous.append(pair)
            continue

        if label == 'accepted':
            accepted.append(pair)
        elif label == 'rejected':
            rejected.append(pair)
        else:
            ambiguous.append(pair)

    all_pairs = accepted + rejected
    print(f"  Accepted pairs:  {len(accepted)}")
    print(f"  Rejected pairs:  {len(rejected)}")
    print(f"  Ambiguous (skipped): {len(ambiguous)}")

    if not all_pairs:
        print("\nNo clean pairs found. Collect more feedback first.")
        return

    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    output_file = OUTPUT_DIR / f"preference_data_{timestamp}.jsonl"

    with open(output_file, 'w') as f:
        for pair in all_pairs:
            f.write(json.dumps(pair) + '\n')

    accept_ratio = len(accepted) / len(all_pairs) if all_pairs else 0
    reject_ratio = len(rejected) / len(all_pairs) if all_pairs else 0

    print(f"\n✅ Dataset built: {output_file.name}")
    print(f"   Total pairs:    {len(all_pairs)}")
    print(f"   Accept ratio:   {accept_ratio:.1%}")
    print(f"   Reject ratio:   {reject_ratio:.1%}")
    print(f"   Output:         {output_file}")


if __name__ == '__main__':
    main()
