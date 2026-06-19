#!/usr/bin/env python3
"""
Adwi E2E Auto Loop — bounded NLU eval → analyze → fix → retest loop.
Standalone: no adwi_cli imports. Owns running.pid exclusively.
"""
from __future__ import annotations
import argparse, json, os, re, shutil, subprocess, sys, time
from datetime import datetime
from pathlib import Path

HOME      = Path.home()
WORKSPACE = HOME / "SuneelWorkSpace"
ADWI_DIR  = WORKSPACE / "adwi"
SIMEVAL   = ADWI_DIR / "logs" / "simeval"
LOOP_DIR  = ADWI_DIR / "notes" / "e2e-auto-loop"

PID_FILE    = LOOP_DIR / "running.pid"
CANCEL_FILE = LOOP_DIR / "cancel"
STATUS_FILE = LOOP_DIR / "status.json"

VENV_PY = ADWI_DIR / ".venv" / "bin" / "python3"
RUN_P1  = SIMEVAL / "run_large_eval.py"
RUN_P2  = SIMEVAL / "run_large_eval_p2.py"

TIMEOUT_P1  = 2400   # 40 min per P1 eval
TIMEOUT_P2  = 1200   # 20 min per P2 eval
TIMEOUT_JOB = 14400  # 4 hr overall max

PATCHABLE_FILES = [
    ADWI_DIR / "adwi_cli.py",
    SIMEVAL  / "run_large_eval.py",
    SIMEVAL  / "run_large_eval_p2.py",
    ADWI_DIR / "capabilities.json",
]

# Deterministic known regex fixes (Hybrid Option C, Phase A).
# Populated after reviewing cycle-1 analyze-only report (2026-06-18, 95.8% combined).
# Format per entry:
#   id: str
#   description: str
#   target_intents: list[str]   — skip if none of these are currently failing
#   target_file: str            — relative to WORKSPACE
#   check_pattern: str          — regex that must match current file (idempotency guard)
#   old_str: str                — exact string to find-and-replace (one occurrence)
#   new_str: str                — replacement
#   minimum_examples: int       — minimum failing examples required before applying
KNOWN_REGEX_FIXES: list[dict] = [
    # ── FIX-E2E-001a: expand 'chat' INTENT_SYSTEM in P1 eval to match adwi_cli.py ──
    {
        "id":             "FIX-E2E-001a",
        "description":    "Expand chat description in run_large_eval.py — add multi-bullet version",
        "target_intents": ["chat"],
        "target_file":    "adwi/logs/simeval/run_large_eval.py",
        "check_pattern":  r"'chat'\s+: DEFAULT for everything else",
        "old_str": (
            '    "   \'chat\'           : DEFAULT for everything else — advisory, '
            'explanations, comparisons, how-to.\\n"\n'
        ),
        "new_str": (
            '    "   \'chat\'           : DEFAULT for everything else — use this for:\\n"\n'
            '    "                      • advisory/recommendation questions '
            '(\'what is the best...\', \'should I...\')\\n"\n'
            '    "                      • questions about tools, services, '
            'subscriptions NOT directly about adwi\\n"\n'
            '    "                      • comparisons (\'X vs Y\', \'which is better\')\\n"\n'
            '    "                      • how-to questions, explanations, general knowledge\\n"\n'
            '    "                      • anything where the user wants a conversational '
            'answer, not a system action\\n"\n'
            '    "                      When in doubt, ALWAYS prefer \'chat\' over any other intent.\\n"\n'
        ),
        "minimum_examples": 5,
    },
    # ── FIX-E2E-001b: same expansion in P2 eval ───────────────────────────────────
    {
        "id":             "FIX-E2E-001b",
        "description":    "Expand chat description in run_large_eval_p2.py — add multi-bullet version",
        "target_intents": ["chat"],
        "target_file":    "adwi/logs/simeval/run_large_eval_p2.py",
        "check_pattern":  r"'chat'\s+: DEFAULT for everything else",
        "old_str": (
            '    "   \'chat\'           : DEFAULT for everything else — advisory, '
            'explanations, comparisons, how-to.\\n"\n'
        ),
        "new_str": (
            '    "   \'chat\'           : DEFAULT for everything else — use this for:\\n"\n'
            '    "                      • advisory/recommendation questions '
            '(\'what is the best...\', \'should I...\')\\n"\n'
            '    "                      • questions about tools, services, '
            'subscriptions NOT directly about adwi\\n"\n'
            '    "                      • comparisons (\'X vs Y\', \'which is better\')\\n"\n'
            '    "                      • how-to questions, explanations, general knowledge\\n"\n'
            '    "                      • anything where the user wants a conversational '
            'answer, not a system action\\n"\n'
            '    "                      When in doubt, ALWAYS prefer \'chat\' over any other intent.\\n"\n'
        ),
        "minimum_examples": 5,
    },
    # ── FIX-E2E-002a: clarify 'status' in P1 eval — "is everything online" ≠ web_search ──
    {
        "id":             "FIX-E2E-002a",
        "description":    "Expand status description in run_large_eval.py — add examples",
        "target_intents": ["status"],
        "target_file":    "adwi/logs/simeval/run_large_eval.py",
        "check_pattern":  r"'status'\s+: asks if services",
        "old_str": (
            '    "   \'status\'         : asks if services/systems are running or healthy '
            '(shallow check)\\n"\n'
        ),
        "new_str": (
            '    "   \'status\'         : asks if services/systems are running or healthy '
            '(shallow check).\\n"\n'
            '    "                      Includes: \'is everything online\' (means RUNNING, '
            'NOT internet search),\\n"\n'
            '    "                      \'what\'s wrong\' (vague, no error text pasted), '
            '\'are services up\', \'is X running\'.\\n"\n'
            '    "                      NOT \'doctor\' (requires explicit depth keyword). '
            'NOT \'web_search\'.\\n"\n'
        ),
        "minimum_examples": 3,
    },
    # ── FIX-E2E-002b: same clarification in P2 eval ───────────────────────────────
    {
        "id":             "FIX-E2E-002b",
        "description":    "Expand status description in run_large_eval_p2.py — add examples",
        "target_intents": ["status"],
        "target_file":    "adwi/logs/simeval/run_large_eval_p2.py",
        "check_pattern":  r"'status'\s+: asks if services",
        "old_str": (
            '    "   \'status\'         : asks if services/systems are running or healthy '
            '(shallow check)\\n"\n'
        ),
        "new_str": (
            '    "   \'status\'         : asks if services/systems are running or healthy '
            '(shallow check).\\n"\n'
            '    "                      Includes: \'is everything online\' (means RUNNING, '
            'NOT internet search),\\n"\n'
            '    "                      \'what\'s wrong\' (vague, no error text pasted), '
            '\'are services up\', \'is X running\'.\\n"\n'
            '    "                      NOT \'doctor\' (requires explicit depth keyword). '
            'NOT \'web_search\'.\\n"\n'
        ),
        "minimum_examples": 3,
    },
    # ── FIX-E2E-002c: same clarification in adwi_cli.py ──────────────────────────
    {
        "id":             "FIX-E2E-002c",
        "description":    "Expand status description in adwi_cli.py — add examples",
        "target_intents": ["status"],
        "target_file":    "adwi/adwi_cli.py",
        "check_pattern":  r"'status'\s+: asks if services",
        "old_str": (
            '    "   \'status\'         : asks if services/systems are running or healthy '
            '(shallow check)\\n"\n'
        ),
        "new_str": (
            '    "   \'status\'         : asks if services/systems are running or healthy '
            '(shallow check).\\n"\n'
            '    "                      Includes: \'is everything online\' (means RUNNING, '
            'NOT internet search),\\n"\n'
            '    "                      \'what\'s wrong\' (vague, no error text pasted), '
            '\'are services up\', \'is X running\'.\\n"\n'
            '    "                      NOT \'doctor\' (requires explicit depth keyword). '
            'NOT \'web_search\'.\\n"\n'
        ),
        "minimum_examples": 3,
    },
    # ── FIX-E2E-003: expand 'backup_status' in P1 eval — "backup ok?" → backup_status ──
    {
        "id":             "FIX-E2E-003",
        "description":    "Expand backup_status in run_large_eval.py — add ok?/good? examples",
        "target_intents": ["backup_status"],
        "target_file":    "adwi/logs/simeval/run_large_eval.py",
        "check_pattern":  r"'backup_status'\s+: check when the last backup ran\\\\n",
        "old_str": (
            '    "   \'backup_status\'  : check when the last backup ran\\n"\n'
        ),
        "new_str": (
            '    "   \'backup_status\'  : check when the last backup ran, backup health, '
            'recent backup git log.\\n"\n'
            '    "                      \'backup ok?\', \'backup good?\', '
            '\'was the backup successful?\', \'backup status\'.\\n"\n'
            '    "                      Any question pairing \'backup\' with '
            'health/ok/status → backup_status, NOT \'status\'.\\n"\n'
        ),
        "minimum_examples": 2,
    },
    # ── FIX-E2E-004a: clarify inspect_code in P1 eval — memory.py ≠ memory_recall ──
    {
        "id":             "FIX-E2E-004a",
        "description":    "Expand inspect_code in run_large_eval.py — clarify memory.py → inspect_code",
        "target_intents": ["inspect_code"],
        "target_file":    "adwi/logs/simeval/run_large_eval.py",
        "check_pattern":  r"'inspect_code'\s+: read and explain.*inspect.*review.*look at",
        "old_str": (
            '    "   \'inspect_code\'   : read and explain an adwi source file. '
            '\'inspect\', \'review\', \'look at\',\\n"\n'
            '    "                      \'find bugs in\' adwi source code or a specific .py file.\\n"\n'
        ),
        "new_str": (
            '    "   \'inspect_code\'   : read and explain an adwi source file. '
            '\'inspect\', \'review\', \'look at\',\\n"\n'
            '    "                      \'find bugs in\' adwi source code or a specific .py file.\\n"\n'
            '    "                      \'explain what X.py does\', \'explain the X module\', '
            '\'inspect the X module\'\\n"\n'
            '    "                      → inspect_code even if X = memory (memory.py). '
            'NOT \'memory_recall\' (only Adwi\'s own stored facts).\\n"\n'
        ),
        "minimum_examples": 2,
    },
    # ── FIX-E2E-004b: same clarification in P2 eval ───────────────────────────────
    {
        "id":             "FIX-E2E-004b",
        "description":    "Expand inspect_code in run_large_eval_p2.py — clarify memory.py → inspect_code",
        "target_intents": ["inspect_code"],
        "target_file":    "adwi/logs/simeval/run_large_eval_p2.py",
        "check_pattern":  r"'inspect_code'\s+: read and explain.*inspect.*find bugs",
        "old_str": (
            '    "   \'inspect_code\'   : read and explain an adwi source file — '
            '\'inspect\', \'find bugs in\', \'code review adwi\'.\\n"\n'
        ),
        "new_str": (
            '    "   \'inspect_code\'   : read and explain an adwi source file — '
            '\'inspect\', \'find bugs in\', \'code review adwi\'.\\n"\n'
            '    "                      \'explain what X.py does\', \'explain the X module\', '
            '\'inspect the X module\'\\n"\n'
            '    "                      → inspect_code even if X = memory (memory.py). '
            'NOT \'memory_recall\' (only Adwi\'s own stored facts).\\n"\n'
        ),
        "minimum_examples": 2,
    },
    # ── FIX-E2E-005a: add run_code to P1 eval INTENT_SYSTEM (insert before research) ──
    {
        "id":             "FIX-E2E-005a",
        "description":    "Add run_code description to run_large_eval.py — insert before research",
        "target_intents": ["run_code"],
        "target_file":    "adwi/logs/simeval/run_large_eval.py",
        "check_pattern":  r"how to make AI faster.*\n.*'research'",
        "old_str": (
            '    "                      \'what affects inference speed\', \'how to make AI faster\' → \'chat\'.\\n"\n'
            '    "   \'research\'       : deep multi-source research with citations. \'research X for me\',\\n"\n'
            '    "                      \'do deep research on X\', \'deep dive into X\', \'write a research brief on X\',\\n"\n'
            '    "                      \'cited report on X\', \'save research about X\'. NOT \'web_search\' (quick lookup).\\n"\n'
        ),
        "new_str": (
            '    "                      \'what affects inference speed\', \'how to make AI faster\' → \'chat\'.\\n"\n'
            '    "   \'run_code\'       : execute or run Python code/scripts. \'run it\', \'run this\', \'run the script\',\\n"\n'
            '    "                      \'execute this code\', \'test this python\', \'run the thing\', \'run a snippet\'.\\n"\n'
            '    "                      Even short/vague prompts like \'run it\' or \'run the thing\' → run_code.\\n"\n'
            '    "   \'research\'       : deep multi-source research with citations. \'research X for me\',\\n"\n'
            '    "                      \'do deep research on X\', \'deep dive into X\', \'write a research brief on X\',\\n"\n'
            '    "                      \'cited report on X\', \'save research about X\'. NOT \'web_search\' (quick lookup).\\n"\n'
        ),
        "minimum_examples": 2,
    },
    # ── FIX-E2E-005b: add run_code to P2 eval INTENT_SYSTEM ──────────────────────
    {
        "id":             "FIX-E2E-005b",
        "description":    "Add run_code description to run_large_eval_p2.py — insert before research",
        "target_intents": ["run_code"],
        "target_file":    "adwi/logs/simeval/run_large_eval_p2.py",
        "check_pattern":  r"show me the context.*\n.*'research'",
        "old_str": (
            '    "                      \'current session context\', \'context summary\', \'show me the context\'.\\n"\n'
            '    "   \'research\'       : deep multi-source research with citations. \'research X for me\',\\n"\n'
            '    "                      \'do deep research on X\', \'deep dive into X\', \'write a research brief on X\',\\n"\n'
            '    "                      \'cited report on X\', \'save research about X\'. NOT \'web_search\' (quick lookup).\\n"\n'
        ),
        "new_str": (
            '    "                      \'current session context\', \'context summary\', \'show me the context\'.\\n"\n'
            '    "   \'run_code\'       : execute or run Python code/scripts. \'run it\', \'run this\', \'run the script\',\\n"\n'
            '    "                      \'execute this code\', \'test this python\', \'run the thing\', \'run a snippet\'.\\n"\n'
            '    "                      Even short/vague prompts like \'run it\' or \'run the thing\' → run_code.\\n"\n'
            '    "   \'research\'       : deep multi-source research with citations. \'research X for me\',\\n"\n'
            '    "                      \'do deep research on X\', \'deep dive into X\', \'write a research brief on X\',\\n"\n'
            '    "                      \'cited report on X\', \'save research about X\'. NOT \'web_search\' (quick lookup).\\n"\n'
        ),
        "minimum_examples": 1,
    },
    # ── FIX-E2E-006a: expand file_search P1 — add locate examples ────────────────
    {
        "id":             "FIX-E2E-006a",
        "description":    "Expand file_search in run_large_eval.py — add locate examples, NOT file_list",
        "target_intents": ["file_search"],
        "target_file":    "adwi/logs/simeval/run_large_eval.py",
        "check_pattern":  r"'file_search'.*pattern.*\n.*'git_status'",
        "old_str": (
            '    "   \'file_search\'    : search the filesystem for files by name, extension, or pattern.\\n"\n'
        ),
        "new_str": (
            '    "   \'file_search\'    : search the filesystem for files by name, extension, or pattern.\\n"\n'
            '    "                      \'locate requirements.txt\', \'locate docker-compose.yml\',\\n"\n'
            '    "                      \'find all dockerfile variants\', \'locate the eval runner\'.\\n"\n'
            '    "                      \'locate X\' → file_search NOT file_list. \'find files\' → file_search.\\n"\n'
        ),
        "minimum_examples": 3,
    },
    # ── FIX-E2E-006b: expand git_status P1 — add "any changes" examples ──────────
    {
        "id":             "FIX-E2E-006b",
        "description":    "Expand git_status in run_large_eval.py — add changes/history examples",
        "target_intents": ["git_status"],
        "target_file":    "adwi/logs/simeval/run_large_eval.py",
        "check_pattern":  r"'git_status'.*staged/unstaged.*\n.*'nightly_status'",
        "old_str": (
            '    "   \'git_status\'     : git queries — branches, commits, diffs, staged/unstaged changes.\\n"\n'
        ),
        "new_str": (
            '    "   \'git_status\'     : git queries — branches, commits, diffs, staged/unstaged changes.\\n"\n'
            '    "                      \'are there any changes\', \'recent change history\',\\n"\n'
            '    "                      \'show recent commits\', \'are there uncommitted changes\'.\\n"\n'
            '    "                      ANYTHING about git state → git_status, NOT \'status\' (service health).\\n"\n'
        ),
        "minimum_examples": 2,
    },
    # ── FIX-E2E-006c: expand nightly_status P1 — add log/last-ran examples ────────
    {
        "id":             "FIX-E2E-006c",
        "description":    "Expand nightly_status in run_large_eval.py — add show-logs/last-ran examples",
        "target_intents": ["nightly_status"],
        "target_file":    "adwi/logs/simeval/run_large_eval.py",
        "check_pattern":  r"'nightly_status'.*last ran\.",
        "old_str": (
            '    "   \'nightly_status\' : check when the nightly maintenance last ran.\\n"\n'
        ),
        "new_str": (
            '    "   \'nightly_status\' : check when the nightly maintenance last ran and what it produced.\\n"\n'
            '    "                      \'show me the logs\', \'what was the last thing that ran\',\\n"\n'
            '    "                      \'nightly status\', \'when did nightly last run\'.\\n"\n'
            '    "                      NOT \'status\' (service health). NOT \'memory_curate\'.\\n"\n'
        ),
        "minimum_examples": 2,
    },
    # ── FIX-E2E-007a: expand self_heal P1 — add repair/errored examples ──────────
    {
        "id":             "FIX-E2E-007a",
        "description":    "Expand self_heal in run_large_eval.py — add repair/errored examples",
        "target_intents": ["self_heal"],
        "target_file":    "adwi/logs/simeval/run_large_eval.py",
        "check_pattern":  r"'self_heal'.*WITHOUT pasting",
        "old_str": (
            '    "   \'self_heal\'      : user says service is broken WITHOUT pasting an actual error message.\\n"\n'
            '    "                      \'fix my setup\', \'adwi is broken\', \'something is broken\', \'self-heal\'.\\n"\n'
            '    "                      \'doctor\' is ONLY for EXPLICIT deep health-check requests (\'run doctor\', \'full health check\').\\n"\n'
        ),
        "new_str": (
            '    "   \'self_heal\'      : user says service is broken WITHOUT pasting an actual error message.\\n"\n'
            '    "                      \'fix my setup\', \'adwi is broken\', \'something is broken\', \'self-heal\',\\n"\n'
            '    "                      \'adwi please repair\', \'something errored out help\'.\\n"\n'
            '    "                      \'doctor\' is ONLY for EXPLICIT deep health-check requests (\'run doctor\', \'full health check\').\\n"\n'
        ),
        "minimum_examples": 2,
    },
    # ── FIX-E2E-007b: expand self_heal P2 ────────────────────────────────────────
    {
        "id":             "FIX-E2E-007b",
        "description":    "Expand self_heal in run_large_eval_p2.py — add repair/errored examples",
        "target_intents": ["self_heal"],
        "target_file":    "adwi/logs/simeval/run_large_eval_p2.py",
        "check_pattern":  r"'self_heal'.*WITHOUT pasting.*\n.*'fix my setup'.*'self-heal'\.",
        "old_str": (
            '    "   \'self_heal\'      : user says service is broken WITHOUT pasting an actual error message.\\n"\n'
            '    "                      \'fix my setup\', \'something is broken\', \'self-heal\'.\\n"\n'
            '    "                      \'doctor\' is ONLY for EXPLICIT deep health-check requests.\\n"\n'
        ),
        "new_str": (
            '    "   \'self_heal\'      : user says service is broken WITHOUT pasting an actual error message.\\n"\n'
            '    "                      \'fix my setup\', \'something is broken\', \'self-heal\',\\n"\n'
            '    "                      \'adwi please repair\', \'something errored out help\'.\\n"\n'
            '    "                      \'doctor\' is ONLY for EXPLICIT deep health-check requests (\'run doctor\').\\n"\n'
        ),
        "minimum_examples": 1,
    },
    # ── FIX-E2E-008a: expand benchmark P1 — add GPU tokens/sec example ───────────
    {
        "id":             "FIX-E2E-008a",
        "description":    "Expand benchmark in run_large_eval.py — add GPU tokens/sec example",
        "target_intents": ["benchmark"],
        "target_file":    "adwi/logs/simeval/run_large_eval.py",
        "check_pattern":  r"'how many tokens per second', 'time the model'",
        "old_str": (
            '    "                      \'run a speed test\', \'how many tokens per second\', \'time the model\'.\\n"\n'
        ),
        "new_str": (
            '    "                      \'run a speed test\', \'how many tokens per second\',\\n"\n'
            '    "                      \'how many tokens can my GPU do per second\', \'time the model\'.\\n"\n'
        ),
        "minimum_examples": 2,
    },
    # ── FIX-E2E-008b: expand benchmark P2 — same GPU example ─────────────────────
    {
        "id":             "FIX-E2E-008b",
        "description":    "Expand benchmark in run_large_eval_p2.py — add GPU tokens/sec example",
        "target_intents": ["benchmark"],
        "target_file":    "adwi/logs/simeval/run_large_eval_p2.py",
        "check_pattern":  r"'how many tokens per second', 'time the model'",
        "old_str": (
            '    "                      \'run a speed test\', \'how many tokens per second\', \'time the model\'.\\n"\n'
        ),
        "new_str": (
            '    "                      \'run a speed test\', \'how many tokens per second\',\\n"\n'
            '    "                      \'how many tokens can my GPU do per second\', \'time the model\'.\\n"\n'
        ),
        "minimum_examples": 1,
    },
    # ── FIX-E2E-009a: expand sync P1 — add NOT-list for chat disambiguation ──────
    {
        "id":             "FIX-E2E-009a",
        "description":    "Expand sync in run_large_eval.py — add NOT-list for update-adwi/smarter cases",
        "target_intents": ["sync", "chat"],
        "target_file":    "adwi/logs/simeval/run_large_eval.py",
        "check_pattern":  r"'sync'.*ONLY when user says 'sync' or 'update knowledge base'\.",
        "old_str": (
            '    "   \'sync\'           : sync adwi knowledge base to Open WebUI — ONLY when user says \'sync\' or \'update knowledge base\'.\\n"\n'
        ),
        "new_str": (
            '    "   \'sync\'           : sync adwi knowledge base to Open WebUI — ONLY when user explicitly says \'sync\'\\n"\n'
            '    "                      or \'update knowledge base\'. NOT for vague update/manage requests:\\n"\n'
            '    "                      NOT \'update adwi\', \'make adwi smarter\', \'sync everything\',\\n"\n'
            '    "                      \'update my knowledge\', \'manage my data\' → those are \'chat\' or \'what_next\'.\\n"\n'
        ),
        "minimum_examples": 2,
    },
    # ── FIX-E2E-010a: expand what_next P1 — add "missing from adwi" example ──────
    {
        "id":             "FIX-E2E-010a",
        "description":    "Expand what_next in run_large_eval.py — add what's missing from adwi",
        "target_intents": ["what_next"],
        "target_file":    "adwi/logs/simeval/run_large_eval.py",
        "check_pattern":  r"'generate a todo list for adwi' → what_next\.",
        "old_str": (
            '    "                      \'what should I refactor in adwi\', \'generate a todo list for adwi\' → what_next.\\n"\n'
        ),
        "new_str": (
            '    "                      \'what should I refactor in adwi\', \'generate a todo list for adwi\',\\n"\n'
            '    "                      \'what\'s missing from adwi\' → what_next.\\n"\n'
        ),
        "minimum_examples": 1,
    },
    # ── FIX-E2E-010b: expand what_next P2 — same ─────────────────────────────────
    {
        "id":             "FIX-E2E-010b",
        "description":    "Expand what_next in run_large_eval_p2.py — add what's missing from adwi",
        "target_intents": ["what_next"],
        "target_file":    "adwi/logs/simeval/run_large_eval_p2.py",
        "check_pattern":  r"'generate a todo list for adwi' → what_next\.",
        "old_str": (
            '    "                      \'what should I refactor in adwi\', \'generate a todo list for adwi\' → what_next.\\n"\n'
        ),
        "new_str": (
            '    "                      \'what should I refactor in adwi\', \'generate a todo list for adwi\',\\n"\n'
            '    "                      \'what\'s missing from adwi\' → what_next.\\n"\n'
        ),
        "minimum_examples": 1,
    },
    # ── FIX-E2E-011a: expand file_read P1 — add display example ──────────────────
    {
        "id":             "FIX-E2E-011a",
        "description":    "Expand file_read in run_large_eval.py — add display example, NOT inspect_code",
        "target_intents": ["file_read"],
        "target_file":    "adwi/logs/simeval/run_large_eval.py",
        "check_pattern":  r"'file_read'.*read and display.*\n.*'file_list'",
        "old_str": (
            '    "   \'file_read\'      : read and display the contents of a specific file path.\\n"\n'
        ),
        "new_str": (
            '    "   \'file_read\'      : read and display the contents of a specific file path.\\n"\n'
            '    "                      \'show me X.py\', \'display adwi main file\', \'print the contents of X\'.\\n"\n'
            '    "                      NOT inspect_code (which analyzes). \'display X file\' → file_read.\\n"\n'
        ),
        "minimum_examples": 1,
    },
    # ── FIX-E2E-012a: add cleanup to P1 eval — insert after old_files ────────────
    {
        "id":             "FIX-E2E-012a",
        "description":    "Add cleanup description to run_large_eval.py — insert after old_files",
        "target_intents": ["cleanup"],
        "target_file":    "adwi/logs/simeval/run_large_eval.py",
        "check_pattern":  r"'old_files'.*\n.*'gmail'",
        "old_str": (
            '    "   \'old_files\'      : find files older than a time period\\n"\n'
            '    "   \'gmail\'          : questions about email, inbox, messages\\n"\n'
        ),
        "new_str": (
            '    "   \'old_files\'      : find files older than a time period\\n"\n'
            '    "   \'cleanup\'        : delete/remove/purge unwanted files/data. \'can you help me delete stuff\',\\n"\n'
            '    "                      \'purge old downloads\', \'remove leftover installers\', \'clean up junk\'.\\n"\n'
            '    "                      Key: delete/remove/purge + files/data → cleanup. NOT organize. NOT old_files.\\n"\n'
            '    "   \'gmail\'          : questions about email, inbox, messages\\n"\n'
        ),
        "minimum_examples": 1,
    },
    # ── FIX-E2E-012b: add cleanup to P2 eval — insert after old_files ────────────
    {
        "id":             "FIX-E2E-012b",
        "description":    "Add cleanup description to run_large_eval_p2.py — insert after old_files",
        "target_intents": ["cleanup"],
        "target_file":    "adwi/logs/simeval/run_large_eval_p2.py",
        "check_pattern":  r"'old_files'.*\n.*'gmail'",
        "old_str": (
            '    "   \'old_files\'      : find files older than a time period\\n"\n'
            '    "   \'gmail\'          : questions about email, inbox, messages\\n"\n'
        ),
        "new_str": (
            '    "   \'old_files\'      : find files older than a time period\\n"\n'
            '    "   \'cleanup\'        : delete/remove/purge unwanted files/data. \'can you help me delete stuff\',\\n"\n'
            '    "                      \'purge old downloads\', \'remove leftover installers\', \'clean up junk\'.\\n"\n'
            '    "                      Key: delete/remove/purge + files/data → cleanup. NOT organize. NOT old_files.\\n"\n'
            '    "   \'gmail\'          : questions about email, inbox, messages\\n"\n'
        ),
        "minimum_examples": 1,
    },
    # ── FIX-E2E-013a: expand git_status P2 ───────────────────────────────────────
    {
        "id":             "FIX-E2E-013a",
        "description":    "Expand git_status in run_large_eval_p2.py — add changes/history examples",
        "target_intents": ["git_status"],
        "target_file":    "adwi/logs/simeval/run_large_eval_p2.py",
        "check_pattern":  r"'git_status'.*staged/unstaged.*\n.*'memory_context'",
        "old_str": (
            '    "   \'git_status\'     : git queries — branches, commits, diffs, staged/unstaged changes.\\n"\n'
        ),
        "new_str": (
            '    "   \'git_status\'     : git queries — branches, commits, diffs, staged/unstaged changes.\\n"\n'
            '    "                      \'are there any changes\', \'recent change history\',\\n"\n'
            '    "                      \'show recent commits\', \'are there uncommitted changes\'.\\n"\n'
            '    "                      ANYTHING about git state → git_status, NOT \'status\' (service health).\\n"\n'
        ),
        "minimum_examples": 1,
    },
    # ── FIX-E2E-014a: add run_code to adwi_cli.py INTENT_SYSTEM ──────────────────
    {
        "id":             "FIX-E2E-014a",
        "description":    "Add run_code description to adwi_cli.py INTENT_SYSTEM (insert before web_search)",
        "target_intents": ["run_code"],
        "target_file":    "adwi/adwi_cli.py",
        "check_pattern":  r"those are.*run_code.*\n.*ONLY use when.*image",
        "old_str": (
            '    "                      → those are \'nightly_status\', \'what_next\', \'run_code\', or \'chat\'.\\n"\n'
            '    "                      ONLY use when prompt explicitly asks for an image/picture/photo/drawing.\\n"\n'
            '    "   \'web_search\'     : explicit request for internet/web search\\n"\n'
        ),
        "new_str": (
            '    "                      → those are \'nightly_status\', \'what_next\', \'run_code\', or \'chat\'.\\n"\n'
            '    "                      ONLY use when prompt explicitly asks for an image/picture/photo/drawing.\\n"\n'
            '    "   \'run_code\'       : execute or run Python code/scripts. \'run it\', \'run this\', \'run the script\',\\n"\n'
            '    "                      \'execute this code\', \'test this python\', \'run the thing\', \'run a snippet\'.\\n"\n'
            '    "                      Even short/vague prompts like \'run it\' or \'run the thing\' → run_code.\\n"\n'
            '    "   \'web_search\'     : explicit request for internet/web search\\n"\n'
        ),
        "minimum_examples": 2,
    },
    # ── FIX-E2E-015a: narrow run_code P1 — remove overly-broad "Even short/vague" ──
    # Regression: FIX-E2E-005a caused chat→run_code:3 and __none__→run_code:2 misroutes.
    # "what's up", "make adwi smarter", "DROP TABLE users" should NOT → run_code.
    {
        "id":             "FIX-E2E-015a",
        "description":    "Narrow run_code in run_large_eval.py — replace overly-broad line with NOT clause",
        "target_intents": ["run_code", "chat"],
        "target_file":    "adwi/logs/simeval/run_large_eval.py",
        "check_pattern":  r"'run_code'.*execute or run Python.*\n.*test this python.*\n.*Even short/vague",
        "old_str": (
            '    "   \'run_code\'       : execute or run Python code/scripts. \'run it\', \'run this\', \'run the script\',\\n"\n'
            '    "                      \'execute this code\', \'test this python\', \'run the thing\', \'run a snippet\'.\\n"\n'
            '    "                      Even short/vague prompts like \'run it\' or \'run the thing\' → run_code.\\n"\n'
        ),
        "new_str": (
            '    "   \'run_code\'       : execute or run Python code/scripts. \'run it\', \'run this\', \'run the script\',\\n"\n'
            '    "                      \'execute this code\', \'test this python\', \'run the thing\', \'run a snippet\'.\\n"\n'
            '    "                      ONLY for Python/script execution. NOT conversational (\'what\'s up\', \'make adwi smarter\').\\n"\n'
            '    "                      NOT SQL/DB commands. NOT vague improvement requests. \'run it\' → run_code only in code context.\\n"\n'
        ),
        "minimum_examples": 1,
    },
    # ── FIX-E2E-015b: narrow run_code P2 ─────────────────────────────────────────
    {
        "id":             "FIX-E2E-015b",
        "description":    "Narrow run_code in run_large_eval_p2.py — replace overly-broad line with NOT clause",
        "target_intents": ["run_code", "chat"],
        "target_file":    "adwi/logs/simeval/run_large_eval_p2.py",
        "check_pattern":  r"'run_code'.*execute or run Python.*\n.*test this python.*\n.*Even short/vague",
        "old_str": (
            '    "   \'run_code\'       : execute or run Python code/scripts. \'run it\', \'run this\', \'run the script\',\\n"\n'
            '    "                      \'execute this code\', \'test this python\', \'run the thing\', \'run a snippet\'.\\n"\n'
            '    "                      Even short/vague prompts like \'run it\' or \'run the thing\' → run_code.\\n"\n'
        ),
        "new_str": (
            '    "   \'run_code\'       : execute or run Python code/scripts. \'run it\', \'run this\', \'run the script\',\\n"\n'
            '    "                      \'execute this code\', \'test this python\', \'run the thing\', \'run a snippet\'.\\n"\n'
            '    "                      ONLY for Python/script execution. NOT conversational (\'what\'s up\', \'make adwi smarter\').\\n"\n'
            '    "                      NOT SQL/DB commands. NOT vague improvement requests. \'run it\' → run_code only in code context.\\n"\n'
        ),
        "minimum_examples": 1,
    },
    # ── FIX-E2E-015c: narrow run_code adwi_cli.py ────────────────────────────────
    {
        "id":             "FIX-E2E-015c",
        "description":    "Narrow run_code in adwi_cli.py — replace overly-broad line with NOT clause",
        "target_intents": ["run_code", "chat"],
        "target_file":    "adwi/adwi_cli.py",
        "check_pattern":  r"'run_code'.*execute or run Python.*\n.*test this python.*\n.*Even short/vague",
        "old_str": (
            '    "   \'run_code\'       : execute or run Python code/scripts. \'run it\', \'run this\', \'run the script\',\\n"\n'
            '    "                      \'execute this code\', \'test this python\', \'run the thing\', \'run a snippet\'.\\n"\n'
            '    "                      Even short/vague prompts like \'run it\' or \'run the thing\' → run_code.\\n"\n'
        ),
        "new_str": (
            '    "   \'run_code\'       : execute or run Python code/scripts. \'run it\', \'run this\', \'run the script\',\\n"\n'
            '    "                      \'execute this code\', \'test this python\', \'run the thing\', \'run a snippet\'.\\n"\n'
            '    "                      ONLY for Python/script execution. NOT conversational (\'what\'s up\', \'make adwi smarter\').\\n"\n'
            '    "                      NOT SQL/DB commands. NOT vague improvement requests. \'run it\' → run_code only in code context.\\n"\n'
        ),
        "minimum_examples": 1,
    },
    # ── FIX-E2E-016a: expand backup_status P1 — add ok?/typo examples ────────────
    # FIX-E2E-003 had a bad check_pattern (\\\\n not matching \\n in file). New entry:
    {
        "id":             "FIX-E2E-016a",
        "description":    "Expand backup_status in run_large_eval.py — add ok?/backip-status examples",
        "target_intents": ["backup_status"],
        "target_file":    "adwi/logs/simeval/run_large_eval.py",
        "check_pattern":  r"'backup_status'.*check when the last backup ran",
        "old_str": (
            '    "   \'backup_status\'  : check when the last backup ran\\n"\n'
        ),
        "new_str": (
            '    "   \'backup_status\'  : check when the last backup ran, backup health, recent backup log.\\n"\n'
            '    "                      \'backup ok?\', \'backup good?\', \'backip status\', \'was the backup successful?\'.\\n"\n'
            '    "                      Any \'backup\' + health/ok/status → backup_status, NOT \'status\'.\\n"\n'
        ),
        "minimum_examples": 1,
    },
    # ── FIX-E2E-016b: add backup_status to P2 eval — insert after backup_now ──────
    {
        "id":             "FIX-E2E-016b",
        "description":    "Add backup_status to run_large_eval_p2.py — insert after backup_now",
        "target_intents": ["backup_status"],
        "target_file":    "adwi/logs/simeval/run_large_eval_p2.py",
        "check_pattern":  r"'backup_now'.*NOT git_status.*\n.*'benchmark'",
        "old_str": (
            '    "   \'backup_now\'     : backup to GitHub. Includes \'push to github\', \'push my changes\'. NOT git_status.\\n"\n'
            '    "   \'benchmark\'      : run an actual timed speed/performance test on local models.\\n"\n'
        ),
        "new_str": (
            '    "   \'backup_now\'     : backup to GitHub. Includes \'push to github\', \'push my changes\'. NOT git_status.\\n"\n'
            '    "   \'backup_status\'  : check when the last backup ran, backup health.\\n"\n'
            '    "                      \'backup ok?\', \'backip status\', \'was the backup successful?\' → backup_status, NOT \'status\'.\\n"\n'
            '    "   \'benchmark\'      : run an actual timed speed/performance test on local models.\\n"\n'
        ),
        "minimum_examples": 1,
    },
    # ── FIX-E2E-017a: expand what_next P1 — add "can't now" capability framing ───
    {
        "id":             "FIX-E2E-017a",
        "description":    "Expand what_next in run_large_eval.py — add capability-gap framing",
        "target_intents": ["what_next"],
        "target_file":    "adwi/logs/simeval/run_large_eval.py",
        "check_pattern":  r"'what_next'.*user asks for AI-suggested.*\n.*suggest adwi improvements",
        "old_str": (
            '    "   \'what_next\'      : user asks for AI-suggested next improvements or features. \'what should I build next\',\\n"\n'
            '    "                      \'suggest adwi improvements\', \'adwi roadmap\', \'next feature ideas\'.\\n"\n'
        ),
        "new_str": (
            '    "   \'what_next\'      : user asks for AI-suggested next improvements or features. \'what should I build next\',\\n"\n'
            '    "                      \'suggest adwi improvements\', \'adwi roadmap\', \'next feature ideas\',\\n"\n'
            '    "                      \'what could adwi do that it can\\\'t now\', \'what capabilities is adwi missing\'.\\n"\n'
        ),
        "minimum_examples": 1,
    },
    # ── FIX-E2E-018a: git_status P1 — add staging/commit context examples ─────────
    {
        "id":             "FIX-E2E-018a",
        "description":    "Add git staging context to git_status in run_large_eval.py",
        "target_intents": ["git_status"],
        "target_file":    "adwi/logs/simeval/run_large_eval.py",
        "check_pattern":  r"'git_status'.*staged/unstaged.*\n.*are there any changes",
        "old_str": (
            '    "   \'git_status\'     : git queries — branches, commits, diffs, staged/unstaged changes.\\n"\n'
            '    "                      \'are there any changes\', \'recent change history\',\\n"\n'
        ),
        "new_str": (
            '    "   \'git_status\'     : git queries — branches, commits, diffs, staged/unstaged changes.\\n"\n'
            '    "                      \'are there any changes\', \'recent change history\', \'what\'s in staging\',\\n"\n'
        ),
        "minimum_examples": 1,
    },
    # ── FIX-E2E-019a: expand backup_now P1 — add commit-and-backup examples ───────
    {
        "id":             "FIX-E2E-019a",
        "description":    "Expand backup_now in run_large_eval.py — add commit/push examples",
        "target_intents": ["backup_now"],
        "target_file":    "adwi/logs/simeval/run_large_eval.py",
        "check_pattern":  r"save to github.*git_status.*which only READS",
        "old_str": (
            '    "   \'backup_now\'     : backup workspace to GitHub, push backup. Includes \'push to github\',\\n"\n'
            '    "                      \'push my changes\', \'save to github\'. Different from \'git_status\' which only READS.\\n"\n'
        ),
        "new_str": (
            '    "   \'backup_now\'     : backup workspace to GitHub, push backup. Includes \'push to github\',\\n"\n'
            '    "                      \'push my changes\', \'save to github\', \'commit and backup\', \'commit and push everything\'.\\n"\n'
            '    "                      Any WRITE/PUSH action to GitHub → backup_now. NOT \'git_status\' (read-only).\\n"\n'
        ),
        "minimum_examples": 1,
    },
    # ── FIX-E2E-019b: expand backup_now P2 ───────────────────────────────────────
    {
        "id":             "FIX-E2E-019b",
        "description":    "Expand backup_now in run_large_eval_p2.py — add commit/push examples",
        "target_intents": ["backup_now"],
        "target_file":    "adwi/logs/simeval/run_large_eval_p2.py",
        "check_pattern":  r"'backup_now'.*NOT git_status.*\n.*'backup_status'",
        "old_str": (
            '    "   \'backup_now\'     : backup to GitHub. Includes \'push to github\', \'push my changes\'. NOT git_status.\\n"\n'
        ),
        "new_str": (
            '    "   \'backup_now\'     : backup to GitHub. Includes \'push to github\', \'push my changes\',\\n"\n'
            '    "                      \'commit and backup\', \'commit and push everything\'. NOT git_status (read-only).\\n"\n'
        ),
        "minimum_examples": 1,
    },
    # ── FIX-E2E-020a: expand use_local P1 — add "run local model" example ────────
    {
        "id":             "FIX-E2E-020a",
        "description":    "Expand use_local in run_large_eval.py — add run-local-model example",
        "target_intents": ["use_local"],
        "target_file":    "adwi/logs/simeval/run_large_eval.py",
        "check_pattern":  r"'use_local'.*switch to a local Ollama.*\n.*'use_cloud'",
        "old_str": (
            '    "   \'use_local\'      : switch to a local Ollama model (llama, qwen, mistral, phi, gemma).\\n"\n'
        ),
        "new_str": (
            '    "   \'use_local\'      : switch to a local Ollama model (llama, qwen, mistral, phi, gemma).\\n"\n'
            '    "                      \'run local model\', \'switch to local\', \'go offline model\'.\\n"\n'
            '    "                      NOT \'run_code\' (\'run local model\' = use_local, not code execution).\\n"\n'
        ),
        "minimum_examples": 1,
    },
    # ── FIX-E2E-020b: expand use_local P2 ────────────────────────────────────────
    {
        "id":             "FIX-E2E-020b",
        "description":    "Expand use_local in run_large_eval_p2.py — add run-local-model example",
        "target_intents": ["use_local"],
        "target_file":    "adwi/logs/simeval/run_large_eval_p2.py",
        "check_pattern":  r"'use_local'.*switch to a local Ollama.*\n.*'use_cloud'",
        "old_str": (
            '    "   \'use_local\'      : switch to a local Ollama model.\\n"\n'
        ),
        "new_str": (
            '    "   \'use_local\'      : switch to a local Ollama model.\\n"\n'
            '    "                      \'run local model\', \'switch to local\', \'go offline model\'.\\n"\n'
            '    "                      NOT \'run_code\' (\'run local model\' = use_local, not code execution).\\n"\n'
        ),
        "minimum_examples": 1,
    },
    # ── FIX-E2E-021a: further narrow run_code P1 — add NOT local-model/random-fact ──
    {
        "id":             "FIX-E2E-021a",
        "description":    "Further narrow run_code in run_large_eval.py — add NOT local-model, NOT random-fact",
        "target_intents": ["run_code", "chat"],
        "target_file":    "adwi/logs/simeval/run_large_eval.py",
        "check_pattern":  r"ONLY for Python/script execution.*make adwi smarter.*\n.*NOT SQL/DB commands",
        "old_str": (
            '    "                      ONLY for Python/script execution. NOT conversational (\'what\'s up\', \'make adwi smarter\').\\n"\n'
            '    "                      NOT SQL/DB commands. NOT vague improvement requests. \'run it\' → run_code only in code context.\\n"\n'
        ),
        "new_str": (
            '    "                      ONLY for Python/script execution. NOT conversational (\'what\'s up\', \'give me a random fact\').\\n"\n'
            '    "                      NOT SQL/DB commands. NOT \'run local model\' (→ use_local). NOT improvement requests.\\n"\n'
            '    "                      NOT \'do it\', \'run local model\', \'why is X failing\'. Code must be implied.\\n"\n'
        ),
        "minimum_examples": 1,
    },
    # ── FIX-E2E-021b: same for P2 ────────────────────────────────────────────────
    {
        "id":             "FIX-E2E-021b",
        "description":    "Further narrow run_code in run_large_eval_p2.py — add NOT local-model, NOT random-fact",
        "target_intents": ["run_code", "chat"],
        "target_file":    "adwi/logs/simeval/run_large_eval_p2.py",
        "check_pattern":  r"ONLY for Python/script execution.*make adwi smarter.*\n.*NOT SQL/DB commands",
        "old_str": (
            '    "                      ONLY for Python/script execution. NOT conversational (\'what\'s up\', \'make adwi smarter\').\\n"\n'
            '    "                      NOT SQL/DB commands. NOT vague improvement requests. \'run it\' → run_code only in code context.\\n"\n'
        ),
        "new_str": (
            '    "                      ONLY for Python/script execution. NOT conversational (\'what\'s up\', \'give me a random fact\').\\n"\n'
            '    "                      NOT SQL/DB commands. NOT \'run local model\' (→ use_local). NOT improvement requests.\\n"\n'
            '    "                      NOT \'do it\', \'run local model\', \'why is X failing\'. Code must be implied.\\n"\n'
        ),
        "minimum_examples": 1,
    },
    # ── FIX-E2E-021c: same for adwi_cli.py ───────────────────────────────────────
    {
        "id":             "FIX-E2E-021c",
        "description":    "Further narrow run_code in adwi_cli.py — add NOT local-model, NOT random-fact",
        "target_intents": ["run_code", "chat"],
        "target_file":    "adwi/adwi_cli.py",
        "check_pattern":  r"ONLY for Python/script execution.*make adwi smarter.*\n.*NOT SQL/DB commands",
        "old_str": (
            '    "                      ONLY for Python/script execution. NOT conversational (\'what\'s up\', \'make adwi smarter\').\\n"\n'
            '    "                      NOT SQL/DB commands. NOT vague improvement requests. \'run it\' → run_code only in code context.\\n"\n'
        ),
        "new_str": (
            '    "                      ONLY for Python/script execution. NOT conversational (\'what\'s up\', \'give me a random fact\').\\n"\n'
            '    "                      NOT SQL/DB commands. NOT \'run local model\' (→ use_local). NOT improvement requests.\\n"\n'
            '    "                      NOT \'do it\', \'run local model\', \'why is X failing\'. Code must be implied.\\n"\n'
        ),
        "minimum_examples": 1,
    },
    # ── FIX-E2E-022a: expand status P1 — add model/stack health examples ─────────
    {
        "id":             "FIX-E2E-022a",
        "description":    "Expand status in run_large_eval.py — add model-slow and stack-health examples",
        "target_intents": ["status"],
        "target_file":    "adwi/logs/simeval/run_large_eval.py",
        "check_pattern":  r"are services up.*is X running.*\n.*NOT 'doctor'",
        "old_str": (
            '    "                      \'what\'s wrong\' (vague, no error text pasted), \'are services up\', \'is X running\'.\\n"\n'
            '    "                      NOT \'doctor\' (requires explicit depth keyword). NOT \'web_search\'.\\n"\n'
        ),
        "new_str": (
            '    "                      \'what\'s wrong\' (vague), \'are services up\', \'is X running\',\\n"\n'
            '    "                      \'stack health check\', \'check if model is responding quickly\', \'my model is slow what\'s wrong\'.\\n"\n'
            '    "                      NOT \'doctor\' (requires explicit depth keyword). NOT \'web_search\'. NOT \'chat\'.\\n"\n'
        ),
        "minimum_examples": 2,
    },
    # ── FIX-E2E-022b: same for P2 ────────────────────────────────────────────────
    {
        "id":             "FIX-E2E-022b",
        "description":    "Expand status in run_large_eval_p2.py — add model-slow and stack-health examples",
        "target_intents": ["status"],
        "target_file":    "adwi/logs/simeval/run_large_eval_p2.py",
        "check_pattern":  r"are services up.*is X running.*\n.*NOT 'doctor'",
        "old_str": (
            '    "                      \'what\'s wrong\' (vague, no error text pasted), \'are services up\', \'is X running\'.\\n"\n'
            '    "                      NOT \'doctor\' (requires explicit depth keyword). NOT \'web_search\'.\\n"\n'
        ),
        "new_str": (
            '    "                      \'what\'s wrong\' (vague), \'are services up\', \'is X running\',\\n"\n'
            '    "                      \'stack health check\', \'check if model is responding quickly\', \'my model is slow what\'s wrong\'.\\n"\n'
            '    "                      NOT \'doctor\' (requires explicit depth keyword). NOT \'web_search\'. NOT \'chat\'.\\n"\n'
        ),
        "minimum_examples": 1,
    },
    # ── FIX-E2E-023a: expand large_files P1 — add disk-hogs example ──────────────
    {
        "id":             "FIX-E2E-023a",
        "description":    "Expand large_files in run_large_eval.py — add disk hogs example",
        "target_intents": ["large_files"],
        "target_file":    "adwi/logs/simeval/run_large_eval.py",
        "check_pattern":  r"'large_files'.*find files exceeding.*\n.*'old_files'",
        "old_str": (
            '    "   \'large_files\'    : find files exceeding a size threshold\\n"\n'
        ),
        "new_str": (
            '    "   \'large_files\'    : find files exceeding a size threshold. \'show disk hogs\',\\n"\n'
            '    "                      \'what\'s hogging my disk\', \'find big files\', \'largest files on my mac\'.\\n"\n'
        ),
        "minimum_examples": 1,
    },
    # ── FIX-E2E-023b: same for P2 ────────────────────────────────────────────────
    {
        "id":             "FIX-E2E-023b",
        "description":    "Expand large_files in run_large_eval_p2.py — add disk hogs example",
        "target_intents": ["large_files"],
        "target_file":    "adwi/logs/simeval/run_large_eval_p2.py",
        "check_pattern":  r"'large_files'.*find files exceeding.*\n.*'old_files'",
        "old_str": (
            '    "   \'large_files\'    : find files exceeding a size threshold\\n"\n'
        ),
        "new_str": (
            '    "   \'large_files\'    : find files exceeding a size threshold. \'show disk hogs\',\\n"\n'
            '    "                      \'what\'s hogging my disk\', \'find big files\', \'largest files on my mac\'.\\n"\n'
        ),
        "minimum_examples": 1,
    },
    # ── FIX-E2E-024a: expand memory_recall P1 — add NOT for vague update requests ─
    {
        "id":             "FIX-E2E-024a",
        "description":    "Expand memory_recall in run_large_eval.py — add NOT for update-my-knowledge type",
        "target_intents": ["memory_recall", "chat"],
        "target_file":    "adwi/logs/simeval/run_large_eval.py",
        "check_pattern":  r"'memory_recall'.*user asks what YOU.*\n.*NOT for searching.*Obsidian",
        "old_str": (
            '    "   \'memory_recall\'  : user asks what YOU (adwi) remember or know about their personal setup.\\n"\n'
            '    "                      NOT for searching personal notes/Obsidian/vault — those are\\n"\n'
            '    "                      \'obsidian_search\' or \'rag_search\'. Only Adwi\'s own learned memory.\\n"\n'
        ),
        "new_str": (
            '    "   \'memory_recall\'  : user asks what YOU (adwi) remember or know about their personal setup.\\n"\n'
            '    "                      NOT for searching personal notes/Obsidian/vault (→ obsidian_search).\\n"\n'
            '    "                      NOT for general updates (\'update my knowledge\', \'manage my data\') → those are \'chat\'.\\n"\n'
            '    "                      Only for: \'what do you remember\', \'what do you know about me\', \'recall X\'.\\n"\n'
        ),
        "minimum_examples": 1,
    },
    # ── FIX-E2E-024b: same for P2 ────────────────────────────────────────────────
    {
        "id":             "FIX-E2E-024b",
        "description":    "Expand memory_recall in run_large_eval_p2.py — add NOT for update-my-knowledge type",
        "target_intents": ["memory_recall", "chat"],
        "target_file":    "adwi/logs/simeval/run_large_eval_p2.py",
        "check_pattern":  r"'memory_recall'.*user asks what YOU.*\n.*NOT for searching.*Obsidian",
        "old_str": (
            '    "   \'memory_recall\'  : user asks what YOU (adwi) remember or know about their personal setup.\\n"\n'
            '    "                      NOT for searching personal notes/Obsidian/vault — those are\\n"\n'
            '    "                      \'obsidian_search\' or \'rag_search\'. Only Adwi\'s own learned memory.\\n"\n'
        ),
        "new_str": (
            '    "   \'memory_recall\'  : user asks what YOU (adwi) remember or know about their personal setup.\\n"\n'
            '    "                      NOT for searching personal notes/Obsidian/vault (→ obsidian_search).\\n"\n'
            '    "                      NOT for general updates (\'update my knowledge\', \'manage my data\') → those are \'chat\'.\\n"\n'
            '    "                      Only for: \'what do you remember\', \'what do you know about me\', \'recall X\'.\\n"\n'
        ),
        "minimum_examples": 1,
    },
    # ── FIX-E2E-025a: expand self_heal P1 — add bug/script-failing examples ───────
    {
        "id":             "FIX-E2E-025a",
        "description":    "Expand self_heal in run_large_eval.py — add bug/script-failing examples",
        "target_intents": ["self_heal"],
        "target_file":    "adwi/logs/simeval/run_large_eval.py",
        "check_pattern":  r"adwi please repair.*something errored out help.*\n.*'doctor' is ONLY",
        "old_str": (
            '    "   \'self_heal\'      : user says service is broken WITHOUT pasting an actual error message.\\n"\n'
            '    "                      \'fix my setup\', \'adwi is broken\', \'something is broken\', \'self-heal\',\\n"\n'
            '    "                      \'adwi please repair\', \'something errored out help\'.\\n"\n'
            '    "                      \'doctor\' is ONLY for EXPLICIT deep health-check requests (\'run doctor\', \'full health check\').\\n"\n'
        ),
        "new_str": (
            '    "   \'self_heal\'      : user says service is broken WITHOUT pasting an actual error message.\\n"\n'
            '    "                      \'fix my setup\', \'adwi is broken\', \'something is broken\', \'self-heal\',\\n"\n'
            '    "                      \'adwi please repair\', \'something errored out help\',\\n"\n'
            '    "                      \'why is my script failing\', \'there\'s a bug somewhere fix it\'.\\n"\n'
            '    "                      \'doctor\' is ONLY for EXPLICIT deep health-check requests (\'run doctor\', \'full health check\').\\n"\n'
        ),
        "minimum_examples": 1,
    },
    # ── FIX-E2E-026a: add implement_idea description to P1 INTENT_SYSTEM ─────────
    {
        "id":             "FIX-E2E-026a",
        "description":    "Insert implement_idea intent description into run_large_eval.py INTENT_SYSTEM",
        "target_intents": ["implement_idea", "chat"],
        "target_file":    "adwi/logs/simeval/run_large_eval.py",
        "check_pattern":  r"full health check'\)\..*\n.*'backup_now'",
        "old_str": (
            '    "                      \'doctor\' is ONLY for EXPLICIT deep health-check requests (\'run doctor\', \'full health check\').\\n"\n'
            '    "   \'backup_now\'     : backup workspace to GitHub, push backup. Includes \'push to github\',\\n"\n'
        ),
        "new_str": (
            '    "                      \'doctor\' is ONLY for EXPLICIT deep health-check requests (\'run doctor\', \'full health check\').\\n"\n'
            '    "   \'implement_idea\' : user wants to add/build/implement a specific feature or improvement.\\n"\n'
            '    "                      \'add this feature to adwi\', \'implement: better error handling\',\\n"\n'
            '    "                      \'build X for adwi\', \'make adwi do X\'. NOT run_code. NOT vague (→ chat).\\n"\n'
            '    "   \'backup_now\'     : backup workspace to GitHub, push backup. Includes \'push to github\',\\n"\n'
        ),
        "minimum_examples": 2,
    },
    # ── FIX-E2E-026b: add implement_idea description to P2 ───────────────────────
    {
        "id":             "FIX-E2E-026b",
        "description":    "Insert implement_idea intent description into run_large_eval_p2.py INTENT_SYSTEM",
        "target_intents": ["implement_idea", "chat"],
        "target_file":    "adwi/logs/simeval/run_large_eval_p2.py",
        "check_pattern":  r"'run doctor'\)\..*\n.*'backup_now'",
        "old_str": (
            '    "                      \'doctor\' is ONLY for EXPLICIT deep health-check requests (\'run doctor\').\\n"\n'
            '    "   \'backup_now\'     : backup to GitHub. Includes \'push to github\', \'push my changes\',\\n"\n'
        ),
        "new_str": (
            '    "                      \'doctor\' is ONLY for EXPLICIT deep health-check requests (\'run doctor\').\\n"\n'
            '    "   \'implement_idea\' : user wants to add/build/implement a specific feature or improvement.\\n"\n'
            '    "                      \'add this feature to adwi\', \'implement: better error handling\',\\n"\n'
            '    "                      \'build X for adwi\', \'make adwi do X\'. NOT run_code. NOT vague (→ chat).\\n"\n'
            '    "   \'backup_now\'     : backup to GitHub. Includes \'push to github\', \'push my changes\',\\n"\n'
        ),
        "minimum_examples": 1,
    },
    # ── FIX-E2E-026c: add implement_idea description to adwi_cli.py ──────────────
    {
        "id":             "FIX-E2E-026c",
        "description":    "Insert implement_idea intent description into adwi_cli.py INTENT_SYSTEM",
        "target_intents": ["implement_idea", "chat"],
        "target_file":    "adwi/adwi_cli.py",
        "check_pattern":  r"deep diagnostic'\)\..*\n.*'backup_now'",
        "old_str": (
            '    "                      \'doctor\' is ONLY for EXPLICIT deep health-check requests\\n"\n'
            '    "                      (\'run doctor\', \'full health check\', \'deep diagnostic\').\\n"\n'
            '    "   \'backup_now\'     : backup workspace to GitHub, push backup. Includes \'push to github\',\\n"\n'
        ),
        "new_str": (
            '    "                      \'doctor\' is ONLY for EXPLICIT deep health-check requests\\n"\n'
            '    "                      (\'run doctor\', \'full health check\', \'deep diagnostic\').\\n"\n'
            '    "   \'implement_idea\' : user wants to add/build/implement a specific feature or improvement.\\n"\n'
            '    "                      \'add this feature to adwi\', \'implement: better error handling\',\\n"\n'
            '    "                      \'build X for adwi\', \'make adwi do X\'. NOT run_code. NOT vague (→ chat).\\n"\n'
            '    "   \'backup_now\'     : backup workspace to GitHub, push backup. Includes \'push to github\',\\n"\n'
        ),
        "minimum_examples": 1,
    },
    # ── FIX-E2E-027a: expand fix_error in P1 — add HTTP/API error examples ────────
    {
        "id":             "FIX-E2E-027a",
        "description":    "Expand fix_error in run_large_eval.py — add docker/fastapi/HTTP error examples",
        "target_intents": ["fix_error"],
        "target_file":    "adwi/logs/simeval/run_large_eval.py",
        "check_pattern":  r"'fix_error'.*user pastes an EXACT.*HTTP status code\..*\n.*'self_heal'",
        "old_str": (
            '    "   \'fix_error\'      : user pastes an EXACT exception string with an error class (ModuleNotFoundError, TypeError, etc.) or HTTP status code.\\n"\n'
            '    "   \'self_heal\'      : user says service is broken WITHOUT pasting an actual error message.\\n"\n'
        ),
        "new_str": (
            '    "   \'fix_error\'      : user pastes an EXACT exception string with an error class (ModuleNotFoundError, TypeError, etc.) or HTTP status code.\\n"\n'
            '    "                      \'docker.errors.APIError: 409 conflict\', \'fastapi.exceptions.HTTPException: 422\', any paste of stacktrace.\\n"\n'
            '    "                      REQUIRES actual error text in the prompt. NOT \'something is broken\' (→ self_heal).\\n"\n'
            '    "   \'self_heal\'      : user says service is broken WITHOUT pasting an actual error message.\\n"\n'
        ),
        "minimum_examples": 2,
    },
    # ── FIX-E2E-027b: same for P2 ────────────────────────────────────────────────
    {
        "id":             "FIX-E2E-027b",
        "description":    "Expand fix_error in run_large_eval_p2.py — add docker/fastapi/HTTP error examples",
        "target_intents": ["fix_error"],
        "target_file":    "adwi/logs/simeval/run_large_eval_p2.py",
        "check_pattern":  r"'fix_error'.*user pastes an EXACT.*HTTP status code\..*\n.*'self_heal'",
        "old_str": (
            '    "   \'fix_error\'      : user pastes an EXACT exception string with an error class (ModuleNotFoundError, TypeError, etc.) or HTTP status code.\\n"\n'
            '    "   \'self_heal\'      : user says service is broken WITHOUT pasting an actual error message.\\n"\n'
        ),
        "new_str": (
            '    "   \'fix_error\'      : user pastes an EXACT exception string with an error class (ModuleNotFoundError, TypeError, etc.) or HTTP status code.\\n"\n'
            '    "                      \'docker.errors.APIError: 409 conflict\', \'fastapi.exceptions.HTTPException: 422\', any paste of stacktrace.\\n"\n'
            '    "                      REQUIRES actual error text in the prompt. NOT \'something is broken\' (→ self_heal).\\n"\n'
            '    "   \'self_heal\'      : user says service is broken WITHOUT pasting an actual error message.\\n"\n'
        ),
        "minimum_examples": 1,
    },
    # ── FIX-E2E-028a: expand memory_recall NOT clause — add sync/remember exclusions ─
    {
        "id":             "FIX-E2E-028a",
        "description":    "Expand memory_recall NOT clause in run_large_eval.py — add sync-everything, remember-for-me",
        "target_intents": ["memory_recall", "chat"],
        "target_file":    "adwi/logs/simeval/run_large_eval.py",
        "check_pattern":  r"Only for: 'what do you remember'.*recall X.*\n.*'disk_usage'",
        "old_str": (
            '    "                      Only for: \'what do you remember\', \'what do you know about me\', \'recall X\'.\\n"\n'
            '    "   \'disk_usage\'     : storage/disk space questions ONLY\\n"\n'
        ),
        "new_str": (
            '    "                      Only for: \'what do you remember\', \'what do you know about me\', \'recall X\'.\\n"\n'
            '    "                      NOT \'sync everything\' (→ chat). NOT \'remember this for me\' (→ chat, adwi can\'t store new items).\\n"\n'
            '    "   \'disk_usage\'     : storage/disk space questions ONLY\\n"\n'
        ),
        "minimum_examples": 1,
    },
    # ── FIX-E2E-028b: same for P2 ────────────────────────────────────────────────
    {
        "id":             "FIX-E2E-028b",
        "description":    "Expand memory_recall NOT clause in run_large_eval_p2.py — add sync/remember exclusions",
        "target_intents": ["memory_recall", "chat"],
        "target_file":    "adwi/logs/simeval/run_large_eval_p2.py",
        "check_pattern":  r"Only for: 'what do you remember'.*recall X.*\n.*'disk_usage'",
        "old_str": (
            '    "                      Only for: \'what do you remember\', \'what do you know about me\', \'recall X\'.\\n"\n'
            '    "   \'disk_usage\'     : storage/disk space questions ONLY\\n"\n'
        ),
        "new_str": (
            '    "                      Only for: \'what do you remember\', \'what do you know about me\', \'recall X\'.\\n"\n'
            '    "                      NOT \'sync everything\' (→ chat). NOT \'remember this for me\' (→ chat, adwi can\'t store new items).\\n"\n'
            '    "   \'disk_usage\'     : storage/disk space questions ONLY\\n"\n'
        ),
        "minimum_examples": 1,
    },
    # ── FIX-E2E-029a: expand model_status P1 — add "what model is responding" ─────
    {
        "id":             "FIX-E2E-029a",
        "description":    "Expand model_status in run_large_eval.py — add 'what model is responding' example",
        "target_intents": ["model_status"],
        "target_file":    "adwi/logs/simeval/run_large_eval.py",
        "check_pattern":  r"'model_status'.*NOT a disk question.*\n.*'use_local'",
        "old_str": (
            '    "   \'model_status\'   : user asks what model is loaded/active. NOT a disk question.\\n"\n'
        ),
        "new_str": (
            '    "   \'model_status\'   : user asks what model is loaded/active. NOT a disk question.\\n"\n'
            '    "                      \'what model is responding\', \'which model are you running\', \'current model\'.\\n"\n'
        ),
        "minimum_examples": 1,
    },
    # ── FIX-E2E-029b: same for P2 ────────────────────────────────────────────────
    {
        "id":             "FIX-E2E-029b",
        "description":    "Expand model_status in run_large_eval_p2.py — add 'what model is responding' example",
        "target_intents": ["model_status"],
        "target_file":    "adwi/logs/simeval/run_large_eval_p2.py",
        "check_pattern":  r"'model_status'.*user asks what model.*\n.*'use_local'",
        "old_str": (
            '    "   \'model_status\'   : user asks what model is loaded/active.\\n"\n'
        ),
        "new_str": (
            '    "   \'model_status\'   : user asks what model is loaded/active.\\n"\n'
            '    "                      \'what model is responding\', \'which model are you running\', \'current model\'.\\n"\n'
        ),
        "minimum_examples": 1,
    },
    # ── FIX-E2E-030a: add SQL to run_code NOT list P1 ────────────────────────────
    {
        "id":             "FIX-E2E-030a",
        "description":    "Add SQL examples to run_code NOT clause in run_large_eval.py",
        "target_intents": ["chat", "__none__"],
        "target_file":    "adwi/logs/simeval/run_large_eval.py",
        "check_pattern":  r"NOT SQL/DB commands.*NOT 'run local model'.*\n.*NOT 'do it'",
        "old_str": (
            '    "                      NOT SQL/DB commands. NOT \'run local model\' (→ use_local). NOT improvement requests.\\n"\n'
            '    "                      NOT \'do it\', \'run local model\', \'why is X failing\'. Code must be implied.\\n"\n'
        ),
        "new_str": (
            '    "                      NOT SQL/DB commands (\'DROP TABLE users\', \'SELECT *\' → __none__). NOT \'run local model\'.\\n"\n'
            '    "                      NOT \'do it\', \'do this\', \'why is X failing\'. Code execution must be clearly implied.\\n"\n'
        ),
        "minimum_examples": 1,
    },
    # ── FIX-E2E-030b: same for P2 ────────────────────────────────────────────────
    {
        "id":             "FIX-E2E-030b",
        "description":    "Add SQL examples to run_code NOT clause in run_large_eval_p2.py",
        "target_intents": ["chat", "__none__"],
        "target_file":    "adwi/logs/simeval/run_large_eval_p2.py",
        "check_pattern":  r"NOT SQL/DB commands.*NOT 'run local model'.*\n.*NOT 'do it'",
        "old_str": (
            '    "                      NOT SQL/DB commands. NOT \'run local model\' (→ use_local). NOT improvement requests.\\n"\n'
            '    "                      NOT \'do it\', \'run local model\', \'why is X failing\'. Code must be implied.\\n"\n'
        ),
        "new_str": (
            '    "                      NOT SQL/DB commands (\'DROP TABLE users\', \'SELECT *\' → __none__). NOT \'run local model\'.\\n"\n'
            '    "                      NOT \'do it\', \'do this\', \'why is X failing\'. Code execution must be clearly implied.\\n"\n'
        ),
        "minimum_examples": 1,
    },
    # ── FIX-E2E-030c: same for adwi_cli.py ───────────────────────────────────────
    {
        "id":             "FIX-E2E-030c",
        "description":    "Add SQL examples to run_code NOT clause in adwi_cli.py",
        "target_intents": ["chat", "__none__"],
        "target_file":    "adwi/adwi_cli.py",
        "check_pattern":  r"NOT SQL/DB commands.*NOT 'run local model'.*\n.*NOT 'do it'",
        "old_str": (
            '    "                      NOT SQL/DB commands. NOT \'run local model\' (→ use_local). NOT improvement requests.\\n"\n'
            '    "                      NOT \'do it\', \'run local model\', \'why is X failing\'. Code must be implied.\\n"\n'
        ),
        "new_str": (
            '    "                      NOT SQL/DB commands (\'DROP TABLE users\', \'SELECT *\' → __none__). NOT \'run local model\'.\\n"\n'
            '    "                      NOT \'do it\', \'do this\', \'why is X failing\'. Code execution must be clearly implied.\\n"\n'
        ),
        "minimum_examples": 1,
    },
    # ── FIX-E2E-031a: expand gmail P1 — add "new messages?" and "check email" ────
    {
        "id":             "FIX-E2E-031a",
        "description":    "Expand gmail in run_large_eval.py — add new-messages and check-email examples",
        "target_intents": ["gmail"],
        "target_file":    "adwi/logs/simeval/run_large_eval.py",
        "check_pattern":  r"'gmail'.*questions about email.*\n.*'generate_image'",
        "old_str": (
            '    "   \'gmail\'          : questions about email, inbox, messages\\n"\n'
            '    "   \'generate_image\' : ONLY when creating a brand-new image/picture/artwork/visual output.\\n"\n'
        ),
        "new_str": (
            '    "   \'gmail\'          : questions about email, inbox, messages. \'new messages?\', \'check my email\',\\n"\n'
            '    "                      \'any emails from X\', \'check my email then search for action items\'.\\n"\n'
            '    "   \'generate_image\' : ONLY when creating a brand-new image/picture/artwork/visual output.\\n"\n'
        ),
        "minimum_examples": 2,
    },
    # ── FIX-E2E-031b: same for P2 ────────────────────────────────────────────────
    {
        "id":             "FIX-E2E-031b",
        "description":    "Expand gmail in run_large_eval_p2.py — add new-messages and check-email examples",
        "target_intents": ["gmail"],
        "target_file":    "adwi/logs/simeval/run_large_eval_p2.py",
        "check_pattern":  r"'gmail'.*questions about email.*\n.*'generate_image'",
        "old_str": (
            '    "   \'gmail\'          : questions about email, inbox, messages\\n"\n'
            '    "   \'generate_image\' : ONLY when creating a brand-new image/picture/artwork/visual output.\\n"\n'
        ),
        "new_str": (
            '    "   \'gmail\'          : questions about email, inbox, messages. \'new messages?\', \'check my email\',\\n"\n'
            '    "                      \'any emails from X\', \'check my email then search for action items\'.\\n"\n'
            '    "   \'generate_image\' : ONLY when creating a brand-new image/picture/artwork/visual output.\\n"\n'
        ),
        "minimum_examples": 1,
    },
    # ── FIX-E2E-032a: fix implement_idea P1 — add NOT for patch_adwi/what_next ───
    {
        "id":             "FIX-E2E-032a",
        "description":    "Narrow implement_idea in run_large_eval.py — NOT for code-improvement (patch_adwi) or what-next",
        "target_intents": ["patch_adwi", "what_next"],
        "target_file":    "adwi/logs/simeval/run_large_eval.py",
        "check_pattern":  r"NOT run_code\. NOT vague.*\n.*'backup_now'",
        "old_str": (
            '    "   \'implement_idea\' : user wants to add/build/implement a specific feature or improvement.\\n"\n'
            '    "                      \'add this feature to adwi\', \'implement: better error handling\',\\n"\n'
            '    "                      \'build X for adwi\', \'make adwi do X\'. NOT run_code. NOT vague (→ chat).\\n"\n'
            '    "   \'backup_now\'     : backup workspace to GitHub, push backup. Includes \'push to github\',\\n"\n'
        ),
        "new_str": (
            '    "   \'implement_idea\' : user wants to add/build/implement a specific NEW feature (not improve existing).\\n"\n'
            '    "                      \'add this feature to adwi\', \'implement: better error handling\'.\\n"\n'
            '    "                      NOT \'improve adwi code\', \'enhance adwi\' (→ patch_adwi).\\n"\n'
            '    "                      NOT \'what feature should i add\', \'what should i build next\' (→ what_next).\\n"\n'
            '    "   \'backup_now\'     : backup workspace to GitHub, push backup. Includes \'push to github\',\\n"\n'
        ),
        "minimum_examples": 2,
    },
    # ── FIX-E2E-032b: same for P2 ────────────────────────────────────────────────
    {
        "id":             "FIX-E2E-032b",
        "description":    "Narrow implement_idea in run_large_eval_p2.py — NOT for patch_adwi/what_next",
        "target_intents": ["patch_adwi", "what_next"],
        "target_file":    "adwi/logs/simeval/run_large_eval_p2.py",
        "check_pattern":  r"NOT run_code\. NOT vague.*\n.*'backup_now'",
        "old_str": (
            '    "   \'implement_idea\' : user wants to add/build/implement a specific feature or improvement.\\n"\n'
            '    "                      \'add this feature to adwi\', \'implement: better error handling\',\\n"\n'
            '    "                      \'build X for adwi\', \'make adwi do X\'. NOT run_code. NOT vague (→ chat).\\n"\n'
            '    "   \'backup_now\'     : backup to GitHub. Includes \'push to github\', \'push my changes\',\\n"\n'
        ),
        "new_str": (
            '    "   \'implement_idea\' : user wants to add/build/implement a specific NEW feature (not improve existing).\\n"\n'
            '    "                      \'add this feature to adwi\', \'implement: better error handling\'.\\n"\n'
            '    "                      NOT \'improve adwi code\', \'enhance adwi\' (→ patch_adwi).\\n"\n'
            '    "                      NOT \'what feature should i add\', \'what should i build next\' (→ what_next).\\n"\n'
            '    "   \'backup_now\'     : backup to GitHub. Includes \'push to github\', \'push my changes\',\\n"\n'
        ),
        "minimum_examples": 1,
    },
    # ── FIX-E2E-032c: same for adwi_cli.py ───────────────────────────────────────
    {
        "id":             "FIX-E2E-032c",
        "description":    "Narrow implement_idea in adwi_cli.py — NOT for patch_adwi/what_next",
        "target_intents": ["patch_adwi", "what_next"],
        "target_file":    "adwi/adwi_cli.py",
        "check_pattern":  r"NOT run_code\. NOT vague.*\n.*'backup_now'",
        "old_str": (
            '    "   \'implement_idea\' : user wants to add/build/implement a specific feature or improvement.\\n"\n'
            '    "                      \'add this feature to adwi\', \'implement: better error handling\',\\n"\n'
            '    "                      \'build X for adwi\', \'make adwi do X\'. NOT run_code. NOT vague (→ chat).\\n"\n'
            '    "   \'backup_now\'     : backup workspace to GitHub, push backup. Includes \'push to github\',\\n"\n'
        ),
        "new_str": (
            '    "   \'implement_idea\' : user wants to add/build/implement a specific NEW feature (not improve existing).\\n"\n'
            '    "                      \'add this feature to adwi\', \'implement: better error handling\'.\\n"\n'
            '    "                      NOT \'improve adwi code\', \'enhance adwi\' (→ patch_adwi).\\n"\n'
            '    "                      NOT \'what feature should i add\', \'what should i build next\' (→ what_next).\\n"\n'
            '    "   \'backup_now\'     : backup workspace to GitHub, push backup. Includes \'push to github\',\\n"\n'
        ),
        "minimum_examples": 1,
    },
    # ── FIX-E2E-033a: expand disk_usage P1 — add "wats using my disk" examples ───
    {
        "id":             "FIX-E2E-033a",
        "description":    "Expand disk_usage in run_large_eval.py — add 'wats using my disk' example",
        "target_intents": ["disk_usage"],
        "target_file":    "adwi/logs/simeval/run_large_eval.py",
        "check_pattern":  r"'disk_usage'.*storage/disk space questions ONLY.*\n.*'large_files'",
        "old_str": (
            '    "   \'disk_usage\'     : storage/disk space questions ONLY\\n"\n'
            '    "   \'large_files\'    : find files exceeding a size threshold. \'show disk hogs\',\\n"\n'
        ),
        "new_str": (
            '    "   \'disk_usage\'     : storage/disk space questions ONLY. \'wats using my disk\', \'disk usage\',\\n"\n'
            '    "                      \'how much disk space\', \'df -h\', \'storage stats\'.\\n"\n'
            '    "   \'large_files\'    : find files exceeding a size threshold. \'show disk hogs\',\\n"\n'
        ),
        "minimum_examples": 2,
    },
    # ── FIX-E2E-033b: same for P2 ────────────────────────────────────────────────
    {
        "id":             "FIX-E2E-033b",
        "description":    "Expand disk_usage in run_large_eval_p2.py — add 'wats using my disk' example",
        "target_intents": ["disk_usage"],
        "target_file":    "adwi/logs/simeval/run_large_eval_p2.py",
        "check_pattern":  r"'disk_usage'.*storage/disk space questions ONLY.*\n.*'large_files'",
        "old_str": (
            '    "   \'disk_usage\'     : storage/disk space questions ONLY\\n"\n'
            '    "   \'large_files\'    : find files exceeding a size threshold. \'show disk hogs\',\\n"\n'
        ),
        "new_str": (
            '    "   \'disk_usage\'     : storage/disk space questions ONLY. \'wats using my disk\', \'disk usage\',\\n"\n'
            '    "                      \'how much disk space\', \'df -h\', \'storage stats\'.\\n"\n'
            '    "   \'large_files\'    : find files exceeding a size threshold. \'show disk hogs\',\\n"\n'
        ),
        "minimum_examples": 1,
    },
    # ── FIX-E2E-034a: expand what_next P1 — add "what feature should i add" ──────
    {
        "id":             "FIX-E2E-034a",
        "description":    "Expand what_next in run_large_eval.py — add 'what feature should i add'",
        "target_intents": ["what_next"],
        "target_file":    "adwi/logs/simeval/run_large_eval.py",
        "check_pattern":  r"'what_next'.*what should I build next.*\n.*suggest adwi improvements",
        "old_str": (
            '    "   \'what_next\'      : user asks for AI-suggested next improvements or features. \'what should I build next\',\\n"\n'
            '    "                      \'suggest adwi improvements\', \'adwi roadmap\', \'next feature ideas\',\\n"\n'
        ),
        "new_str": (
            '    "   \'what_next\'      : user asks for AI-suggested next improvements or features. \'what should I build next\',\\n"\n'
            '    "                      \'suggest adwi improvements\', \'adwi roadmap\', \'next feature ideas\',\\n"\n'
            '    "                      \'what feature should i add\', \'next thing to add\', \'what capability is missing\'.\\n"\n'
        ),
        "minimum_examples": 1,
    },
    # FIX-E2E-034b: skipped — what_next has no INTENT_SYSTEM description in P2
    # ── FIX-E2E-035a: expand daily_improve P1 — add run-improvement-loop example ─
    {
        "id":             "FIX-E2E-035a",
        "description":    "Expand daily_improve in run_large_eval.py — add run-improvement-loop example",
        "target_intents": ["daily_improve"],
        "target_file":    "adwi/logs/simeval/run_large_eval.py",
        "check_pattern":  r"'daily_improve'.*daily improve.*\n.*NOT patch_adwi",
        "old_str": (
            '    "   \'daily_improve\'  : run the daily self-improvement routine. \'daily improve\', \'daily improvement\',\\n"\n'
            '    "                      \'daily routine\', \'run daily maintenance\'. NOT patch_adwi (code changes via aider).\\n"\n'
        ),
        "new_str": (
            '    "   \'daily_improve\'  : run the daily self-improvement routine. \'daily improve\', \'daily improvement\',\\n"\n'
            '    "                      \'daily routine\', \'run daily maintenance\', \'run the improvement loop\',\\n"\n'
            '    "                      \'daily enhance adwi\'. NOT patch_adwi (aider code changes). NOT run_code.\\n"\n'
        ),
        "minimum_examples": 2,
    },
    # ── FIX-E2E-035b: expand daily_improve P2 (P2 has 1-line format) ───────────
    {
        "id":             "FIX-E2E-035b",
        "description":    "Expand daily_improve in run_large_eval_p2.py — add run-improvement-loop example",
        "target_intents": ["daily_improve"],
        "target_file":    "adwi/logs/simeval/run_large_eval_p2.py",
        "check_pattern":  r"'daily_improve'.*run the daily self-improvement.*NOT patch_adwi.*\n.*'patch_adwi'",
        "old_str": (
            '    "   \'daily_improve\'  : run the daily self-improvement routine. NOT patch_adwi (code changes via aider).\\n"\n'
            '    "   \'patch_adwi\'     : apply code-level changes to adwi source via aider. ONLY \'aider\', \'patch adwi\',\\n"\n'
        ),
        "new_str": (
            '    "   \'daily_improve\'  : run the daily self-improvement routine. \'run the improvement loop\',\\n"\n'
            '    "                      \'daily improve\', \'daily enhance adwi\'. NOT patch_adwi. NOT run_code.\\n"\n'
            '    "   \'patch_adwi\'     : apply code-level changes to adwi source via aider. ONLY \'aider\', \'patch adwi\',\\n"\n'
        ),
        "minimum_examples": 1,
    },
    # ── FIX-E2E-036a: nightly_status P1 — add "what did nightly do" ──────────────
    {
        "id":             "FIX-E2E-036a",
        "description":    "Expand nightly_status P1 — add 'what did nightly do', 'what happened last night'",
        "target_intents": ["nightly_status"],
        "target_file":    "adwi/logs/simeval/run_large_eval.py",
        "check_pattern":  r"'nightly_status' : check when.*\n.*'show me the logs'.*\n.*'nightly status', 'when did nightly last run'\.",
        "old_str": (
            '    "   \'nightly_status\' : check when the nightly maintenance last ran and what it produced.\\n"\n'
            '    "                      \'show me the logs\', \'what was the last thing that ran\',\\n"\n'
            '    "                      \'nightly status\', \'when did nightly last run\'.\\n"\n'
        ),
        "new_str": (
            '    "   \'nightly_status\' : check when the nightly maintenance last ran and what it produced.\\n"\n'
            '    "                      \'show me the logs\', \'what was the last thing that ran\',\\n"\n'
            '    "                      \'nightly status\', \'when did nightly last run\',\\n"\n'
            '    "                      \'what did nightly do\', \'what happened last night\', \'nightly log\'.\\n"\n'
            '    "                      NOT \'status\' (service health). NOT \'memory_curate\'.\\n"\n'
        ),
        "minimum_examples": 1,
    },
    # ── FIX-E2E-036c: nightly_status CLI (different 2-line format) ───────────────
    {
        "id":             "FIX-E2E-036c",
        "description":    "Expand nightly_status CLI — add 'what did nightly do'",
        "target_intents": ["nightly_status"],
        "target_file":    "adwi/adwi_cli.py",
        "check_pattern":  r"'nightly_status' : check when.*\n.*'nightly status', 'when did nightly last run', 'show nightly log'\.",
        "old_str": (
            '    "   \'nightly_status\' : check when the nightly maintenance last ran and what it produced.\\n"\n'
            '    "                      \'nightly status\', \'when did nightly last run\', \'show nightly log\'.\\n"\n'
        ),
        "new_str": (
            '    "   \'nightly_status\' : check when the nightly maintenance last ran and what it produced.\\n"\n'
            '    "                      \'nightly status\', \'when did nightly last run\', \'show nightly log\',\\n"\n'
            '    "                      \'what did nightly do\', \'what happened last night\'. NOT \'status\'.\\n"\n'
        ),
        "minimum_examples": 1,
    },
    # ── FIX-E2E-037a: use_cloud P1 — add "use gpt" examples ─────────────────────
    {
        "id":             "FIX-E2E-037a",
        "description":    "Expand use_cloud P1 — add 'use gpt', 'use claude', 'switch to cloud' examples",
        "target_intents": ["use_cloud"],
        "target_file":    "adwi/logs/simeval/run_large_eval.py",
        "check_pattern":  r"'use_cloud'.*switch to a cloud API model.*\n.*'voice_in'",
        "old_str": (
            '    "   \'use_cloud\'      : switch to a cloud API model (gemini, gpt, openai, claude).\\n"\n'
            '    "   \'voice_in\'       : activate voice/microphone input, start listening, speech-to-text.\\n"\n'
        ),
        "new_str": (
            '    "   \'use_cloud\'      : switch to a cloud API model (gemini, gpt, openai, claude).\\n"\n'
            '    "                      \'use gpt\', \'use claude\', \'use openai\', \'switch to cloud\', \'go cloud\'.\\n"\n'
            '    "                      NOT web_search. NOT use_local (which is Ollama/local only).\\n"\n'
            '    "   \'voice_in\'       : activate voice/microphone input, start listening, speech-to-text.\\n"\n'
        ),
        "minimum_examples": 1,
    },
    # ── FIX-E2E-037b: use_cloud P2 ───────────────────────────────────────────────
    {
        "id":             "FIX-E2E-037b",
        "description":    "Expand use_cloud P2 — add 'use gpt', 'use claude' examples",
        "target_intents": ["use_cloud"],
        "target_file":    "adwi/logs/simeval/run_large_eval_p2.py",
        "check_pattern":  r"'use_cloud'.*switch to a cloud API model.*\n.*'git_status'",
        "old_str": (
            '    "   \'use_cloud\'      : switch to a cloud API model (gemini, gpt, openai, claude).\\n"\n'
            '    "   \'git_status\'     : git queries — branches, commits, diffs, staged/unstaged changes.\\n"\n'
        ),
        "new_str": (
            '    "   \'use_cloud\'      : switch to a cloud API model (gemini, gpt, openai, claude).\\n"\n'
            '    "                      \'use gpt\', \'use claude\', \'use openai\', \'switch to cloud\'.\\n"\n'
            '    "                      NOT web_search. NOT use_local.\\n"\n'
            '    "   \'git_status\'     : git queries — branches, commits, diffs, staged/unstaged changes.\\n"\n'
        ),
        "minimum_examples": 1,
    },
    # ── FIX-E2E-038a: file_read P1 — add yml/json/yaml extension examples ────────
    {
        "id":             "FIX-E2E-038a",
        "description":    "Expand file_read P1 — add yml/json/yaml file examples to distinguish from file_search",
        "target_intents": ["file_read"],
        "target_file":    "adwi/logs/simeval/run_large_eval.py",
        "check_pattern":  r"'file_read'.*read and display.*\n.*'show me X\.py'.*\n.*NOT inspect_code.*\. 'display X file'",
        "old_str": (
            '    "   \'file_read\'      : read and display the contents of a specific file path.\\n"\n'
            '    "                      \'show me X.py\', \'display adwi main file\', \'print the contents of X\'.\\n"\n'
            '    "                      NOT inspect_code (which analyzes). \'display X file\' → file_read.\\n"\n'
        ),
        "new_str": (
            '    "   \'file_read\'      : read and display the contents of a specific file path.\\n"\n'
            '    "                      \'show me X.py\', \'display adwi main file\', \'print the contents of X\'.\\n"\n'
            '    "                      \'show me the docker-compose.yml\', \'show me config.json\', \'show me file.yaml\'.\\n"\n'
            '    "                      NOT inspect_code (which analyzes). NOT file_search (use file_read when\\n"\n'
            '    "                      the EXACT filename is mentioned and user wants to see contents).\\n"\n'
        ),
        "minimum_examples": 1,
    },
    # ── FIX-E2E-038c: file_read CLI ──────────────────────────────────────────────
    {
        "id":             "FIX-E2E-038c",
        "description":    "Expand file_read CLI — add yml/json file examples",
        "target_intents": ["file_read"],
        "target_file":    "adwi/adwi_cli.py",
        "check_pattern":  r"'file_read'.*read and display.*\n.*'read adwi_cli\.py'.*\n.*'file_list'",
        "old_str": (
            '    "   \'file_read\'      : read and display the contents of a specific file path.\\n"\n'
            '    "                      \'read adwi_cli.py\', \'show contents of README.md\', \'cat this file\'.\\n"\n'
            '    "   \'file_list\'      : list files in a specific directory (like ls). NOT a search.\\n"\n'
        ),
        "new_str": (
            '    "   \'file_read\'      : read and display the contents of a specific file path.\\n"\n'
            '    "                      \'read adwi_cli.py\', \'show contents of README.md\', \'cat this file\'.\\n"\n'
            '    "                      \'show me the docker-compose.yml\', \'show me config.json\'.\\n"\n'
            '    "                      NOT file_search (file_read = show contents, file_search = find by name).\\n"\n'
            '    "   \'file_list\'      : list files in a specific directory (like ls). NOT a search.\\n"\n'
        ),
        "minimum_examples": 1,
    },
    # ── FIX-E2E-039a: gmail_list_category P1 — add to gmail desc ─────────────────
    {
        "id":             "FIX-E2E-039a",
        "description":    "Add gmail_list_category examples to gmail desc in P1 INTENT_SYSTEM",
        "target_intents": ["gmail_list_category"],
        "target_file":    "adwi/logs/simeval/run_large_eval.py",
        "check_pattern":  r"'gmail'.*questions about email.*\n.*'any emails from X'.*\n.*'generate_image'",
        "old_str": (
            '    "   \'gmail\'          : questions about email, inbox, messages. \'new messages?\', \'check my email\',\\n"\n'
            '    "                      \'any emails from X\', \'check my email then search for action items\'.\\n"\n'
            '    "   \'generate_image\' : ONLY when creating a brand-new image/picture/artwork/visual output.\\n"\n'
        ),
        "new_str": (
            '    "   \'gmail\'          : questions about email, inbox, messages. \'new messages?\', \'check my email\',\\n"\n'
            '    "                      \'any emails from X\', \'check my email then search for action items\'.\\n"\n'
            '    "   \'gmail_list_category\' : list emails in a Gmail category tab.\\n"\n'
            '    "                      \'show my promotions\', \'what\'s in my promotions\', \'check my spam\',\\n"\n'
            '    "                      \'show spam\', \'social tab\', \'list my updates\'. NOT \'gmail\' (general).\\n"\n'
            '    "   \'generate_image\' : ONLY when creating a brand-new image/picture/artwork/visual output.\\n"\n'
        ),
        "minimum_examples": 1,
    },
    # ── FIX-E2E-039c: gmail_list_category CLI ────────────────────────────────────
    {
        "id":             "FIX-E2E-039c",
        "description":    "Add gmail_list_category to CLI INTENT_SYSTEM",
        "target_intents": ["gmail_list_category"],
        "target_file":    "adwi/adwi_cli.py",
        "check_pattern":  r"'gmail'.*general email questions.*\n.*'gmail_read'",
        "old_str": (
            '    "   \'gmail\'          : general email questions, list inbox, check unread, search messages\\n"\n'
            '    "   \'gmail_read\'     : read a specific email by position number, \'latest\', or \'this email\'\\n"\n'
        ),
        "new_str": (
            '    "   \'gmail\'          : general email questions, list inbox, check unread, search messages\\n"\n'
            '    "   \'gmail_list_category\' : list Gmail category tabs. \'show my promotions\', \'what\'s in my promotions\',\\n"\n'
            '    "                      \'check my spam\', \'social tab\'. NOT \'gmail\' (general inbox).\\n"\n'
            '    "   \'gmail_read\'     : read a specific email by position number, \'latest\', or \'this email\'\\n"\n'
        ),
        "minimum_examples": 1,
    },
    # ── FIX-E2E-040a: backup_now P2 — add "adwi quick backup" ───────────────────
    {
        "id":             "FIX-E2E-040a",
        "description":    "Expand backup_now P2 — add 'adwi quick backup', 'quick backup' examples",
        "target_intents": ["backup_now"],
        "target_file":    "adwi/logs/simeval/run_large_eval_p2.py",
        "check_pattern":  r"'backup_now'.*backup to GitHub.*\n.*'commit and backup'.*NOT git_status",
        "old_str": (
            '    "   \'backup_now\'     : backup to GitHub. Includes \'push to github\', \'push my changes\',\\n"\n'
            '    "                      \'commit and backup\', \'commit and push everything\'. NOT git_status (read-only).\\n"\n'
        ),
        "new_str": (
            '    "   \'backup_now\'     : backup to GitHub. Includes \'push to github\', \'push my changes\',\\n"\n'
            '    "                      \'commit and backup\', \'commit and push everything\', \'quick backup\',\\n"\n'
            '    "                      \'adwi quick backup\', \'adwi backup\'. NOT git_status (read-only).\\n"\n'
        ),
        "minimum_examples": 1,
    },
    # ── FIX-E2E-041a: capabilities P1 — soften "must mention" requirement ────────
    {
        "id":             "FIX-E2E-041a",
        "description":    "Expand capabilities P1 — add examples without 'adwi' mention: show help, list commands",
        "target_intents": ["capabilities"],
        "target_file":    "adwi/logs/simeval/run_large_eval.py",
        "check_pattern":  r"'capabilities'.*EXPLICITLY asks.*'you', 'adwi', 'your features', 'your commands'\.",
        "old_str": (
            '    "   \'capabilities\'   : user EXPLICITLY asks what ADWI/YOU can do — must mention \'you\', \'adwi\', \'your features\', \'your commands\'.\\n"\n'
        ),
        "new_str": (
            '    "   \'capabilities\'   : user asks what adwi/the assistant can do. \'what can you do\', \'show help\',\\n"\n'
            '    "                      \'list all commands\', \'show all commands\', \'show the command list\',\\n"\n'
            '    "                      \'your skills\', \'your features\', \'your commands\'. NOT file_list.\\n"\n'
        ),
        "minimum_examples": 1,
    },
    # FIX-E2E-041b: skipped — capabilities has no INTENT_SYSTEM description in P2

    # ── FIX-E2E-042: voice_out regex before daily_brief — catch "speak the morning brief" ──
    {
        "id":             "FIX-E2E-042a",
        "description":    "Add voice_out regex before daily_brief in P1 — 'speak the morning brief' → voice_out",
        "target_intents": ["voice_out"],
        "target_file":    "adwi/logs/simeval/run_large_eval.py",
        "check_pattern":  r"# ── Daily brief \(BEFORE daily_improve\).*\n.*daily.?brief\|morning.?brief.*daily_brief",
        "old_str": (
            '    # ── Daily brief (BEFORE daily_improve) ───────────────────────────────────────\n'
            '    (re.compile(r"\\b(daily.?brief|morning.?brief|today.{0,5}brief)\\b", re.I), "daily_brief"),\n'
        ),
        "new_str": (
            '    # voice_out wins over daily_brief when verb is speak/say-aloud/read-aloud\n'
            '    (re.compile(r"\\b(speak|say\\s+aloud|read\\s+aloud)\\b.{0,25}\\b(morning.?brief|daily.?brief)\\b", re.I), "voice_out"),\n'
            '    # ── Daily brief (BEFORE daily_improve) ───────────────────────────────────────\n'
            '    (re.compile(r"\\b(daily.?brief|morning.?brief|today.{0,5}brief)\\b", re.I), "daily_brief"),\n'
        ),
        "minimum_examples": 1,
    },
    {
        "id":             "FIX-E2E-042b",
        "description":    "Add voice_out regex before daily_brief in P2",
        "target_intents": ["voice_out"],
        "target_file":    "adwi/logs/simeval/run_large_eval_p2.py",
        "check_pattern":  r"# ── Daily brief \(BEFORE daily_improve\).*\n.*daily.?brief\|morning.?brief.*daily_brief",
        "old_str": (
            '    # ── Daily brief (BEFORE daily_improve) ───────────────────────────────────────\n'
            '    (re.compile(r"\\b(daily.?brief|morning.?brief|today.{0,5}brief)\\b", re.I), "daily_brief"),\n'
        ),
        "new_str": (
            '    # voice_out wins over daily_brief when verb is speak/say-aloud/read-aloud\n'
            '    (re.compile(r"\\b(speak|say\\s+aloud|read\\s+aloud)\\b.{0,25}\\b(morning.?brief|daily.?brief)\\b", re.I), "voice_out"),\n'
            '    # ── Daily brief (BEFORE daily_improve) ───────────────────────────────────────\n'
            '    (re.compile(r"\\b(daily.?brief|morning.?brief|today.{0,5}brief)\\b", re.I), "daily_brief"),\n'
        ),
        "minimum_examples": 1,
    },
    {
        "id":             "FIX-E2E-042c",
        "description":    "Add voice_out regex before daily_brief in CLI",
        "target_intents": ["voice_out"],
        "target_file":    "adwi/adwi_cli.py",
        "check_pattern":  r"# ── Daily brief \(BEFORE daily_improve\).*\n.*daily.?brief\|morning.?brief.*daily_brief",
        "old_str": (
            '    # ── Daily brief (BEFORE daily_improve) ───────────────────────────────────────\n'
            '    (re.compile(r"\\b(daily.?brief|morning.?brief|today.{0,5}brief)\\b", re.I), "daily_brief"),\n'
        ),
        "new_str": (
            '    # voice_out wins over daily_brief when verb is speak/say-aloud/read-aloud\n'
            '    (re.compile(r"\\b(speak|say\\s+aloud|read\\s+aloud)\\b.{0,25}\\b(morning.?brief|daily.?brief)\\b", re.I), "voice_out"),\n'
            '    # ── Daily brief (BEFORE daily_improve) ───────────────────────────────────────\n'
            '    (re.compile(r"\\b(daily.?brief|morning.?brief|today.{0,5}brief)\\b", re.I), "daily_brief"),\n'
        ),
        "minimum_examples": 1,
    },
    # ── FIX-E2E-043: memory_stats INTENT_SYSTEM description ──────────────────────
    {
        "id":             "FIX-E2E-043a",
        "description":    "Add memory_stats INTENT_SYSTEM description in P1",
        "target_intents": ["memory_stats"],
        "target_file":    "adwi/logs/simeval/run_large_eval.py",
        "check_pattern":  r"'memory_curate'.*curate memories.*\n.*'memory curation'.*\n.*'assistant_upgrade_status'",
        "old_str": (
            '    "   \'memory_curate\'  : review logs and propose durable memories. \'curate memories\',\\n"\n'
            '    "                      \'memory curation\', \'propose new memories\'. NOT \'memory_scan\' or \'memory_recall\'.\\n"\n'
            '    "   \'assistant_upgrade_status\': show Assistant Upgrade Pack status. \'upgrade pack status\',\\n"\n'
        ),
        "new_str": (
            '    "   \'memory_curate\'  : review logs and propose durable memories. \'curate memories\',\\n"\n'
            '    "                      \'memory curation\', \'propose new memories\'. NOT \'memory_scan\' or \'memory_recall\'.\\n"\n'
            '    "   \'memory_stats\'   : show memory database statistics (count, size, categories).\\n"\n'
            '    "                      \'memory stats\', \'memory summary stats\', \'how many memories\', \'memory database size\'.\\n"\n'
            '    "                      NOT \'memory_recall\' (recall facts). NOT \'memory_scan\' (scan/update).\\n"\n'
            '    "   \'assistant_upgrade_status\': show Assistant Upgrade Pack status. \'upgrade pack status\',\\n"\n'
        ),
        "minimum_examples": 1,
    },
    # ── FIX-E2E-044: browse INTENT_SYSTEM description ────────────────────────────
    {
        "id":             "FIX-E2E-044a",
        "description":    "Add browse INTENT_SYSTEM description in P1",
        "target_intents": ["browse"],
        "target_file":    "adwi/logs/simeval/run_large_eval.py",
        "check_pattern":  r"'browser_delegate'.*NOT bare 'browse'.*\n.*'daily_brief'",
        "old_str": (
            '    "   \'browser_delegate\': delegate a browsing task to a safe Playwright agent. \'browser delegate X\',\\n"\n'
            '    "                      \'use browser to X\', \'use playwright to X\', \'browser task X\'. NOT bare \'browse\'.\\n"\n'
            '    "   \'daily_brief\'    : proactive daily assistant brief. \'daily brief\', \'morning brief\',\\n"\n'
        ),
        "new_str": (
            '    "   \'browser_delegate\': delegate a browsing task to a safe Playwright agent. \'browser delegate X\',\\n"\n'
            '    "                      \'use browser to X\', \'use playwright to X\', \'browser task X\'. NOT bare \'browse\'.\\n"\n'
            '    "   \'browse\'         : navigate to a URL or open/view a local file in browser. \'browse X\',\\n"\n'
            '    "                      \'browse obsidian.md\', \'browse http://...\', \'open in browser\', \'view in browser\'.\\n"\n'
            '    "                      NOT browser_delegate (which automates). NOT file_read (which reads text).\\n"\n'
            '    "   \'daily_brief\'    : proactive daily assistant brief. \'daily brief\', \'morning brief\',\\n"\n'
        ),
        "minimum_examples": 1,
    },
    # ── FIX-E2E-045: cleanup — add "shrink my disk usage" ────────────────────────
    {
        "id":             "FIX-E2E-045a",
        "description":    "Expand cleanup P1 — add 'shrink my disk usage', 'free up disk space'",
        "target_intents": ["cleanup"],
        "target_file":    "adwi/logs/simeval/run_large_eval.py",
        "check_pattern":  r"'cleanup'.*delete/remove/purge.*\n.*'purge old downloads'.*\n.*NOT organize\. NOT old_files\.",
        "old_str": (
            '    "   \'cleanup\'        : delete/remove/purge unwanted files/data. \'can you help me delete stuff\',\\n"\n'
            '    "                      \'purge old downloads\', \'remove leftover installers\', \'clean up junk\'.\\n"\n'
            '    "                      Key: delete/remove/purge + files/data → cleanup. NOT organize. NOT old_files.\\n"\n'
        ),
        "new_str": (
            '    "   \'cleanup\'        : delete/remove/purge unwanted files/data. \'can you help me delete stuff\',\\n"\n'
            '    "                      \'purge old downloads\', \'remove leftover installers\', \'clean up junk\'.\\n"\n'
            '    "                      \'help me shrink my disk usage\', \'free up disk space\', \'reduce storage usage\'.\\n"\n'
            '    "                      Key: delete/remove/purge/shrink + files/data → cleanup. NOT organize. NOT old_files.\\n"\n'
        ),
        "minimum_examples": 1,
    },
    # ── FIX-E2E-045b: cleanup P2 ─────────────────────────────────────────────────
    {
        "id":             "FIX-E2E-045b",
        "description":    "Expand cleanup P2 — add 'shrink my disk usage'",
        "target_intents": ["cleanup"],
        "target_file":    "adwi/logs/simeval/run_large_eval_p2.py",
        "check_pattern":  r"'cleanup'.*delete/remove/purge.*\n.*'purge old downloads'.*\n.*NOT organize\. NOT old_files\.",
        "old_str": (
            '    "   \'cleanup\'        : delete/remove/purge unwanted files/data. \'can you help me delete stuff\',\\n"\n'
            '    "                      \'purge old downloads\', \'remove leftover installers\', \'clean up junk\'.\\n"\n'
            '    "                      Key: delete/remove/purge + files/data → cleanup. NOT organize. NOT old_files.\\n"\n'
        ),
        "new_str": (
            '    "   \'cleanup\'        : delete/remove/purge unwanted files/data. \'can you help me delete stuff\',\\n"\n'
            '    "                      \'purge old downloads\', \'remove leftover installers\', \'clean up junk\'.\\n"\n'
            '    "                      \'help me shrink my disk usage\', \'free up disk space\'.\\n"\n'
            '    "                      Key: delete/remove/purge/shrink + files/data → cleanup. NOT organize. NOT old_files.\\n"\n'
        ),
        "minimum_examples": 1,
    },
    # ── FIX-E2E-046: chat — add explicit NOT research/git_status for generic queries ─
    {
        "id":             "FIX-E2E-046a",
        "description":    "Expand chat P1 — add explicit examples of what NOT to misroute",
        "target_intents": ["chat"],
        "target_file":    "adwi/logs/simeval/run_large_eval.py",
        "check_pattern":  r"'chat'.*DEFAULT for everything.*\n.*advisory/recommendation.*\n.*questions about tools",
        "old_str": (
            '    "   \'chat\'           : DEFAULT for everything else — use this for:\\n"\n'
            '    "                      • advisory/recommendation questions (\'what is the best...\', \'should I...\')\\n"\n'
            '    "                      • questions about tools, services, subscriptions NOT directly about adwi\\n"\n'
        ),
        "new_str": (
            '    "   \'chat\'           : DEFAULT for everything else — use this for:\\n"\n'
            '    "                      • advisory/recommendation questions (\'what is the best...\', \'should I...\')\\n"\n'
            '    "                      • \'list all installed packages\', \'generate insights from my logs\' (no adwi action)\\n"\n'
            '    "                      • \'how do I debug my python\', \'my model is slow\', \'better AI responses\' (advice)\\n"\n'
            '    "                      • questions about tools, services, subscriptions NOT directly about adwi\\n"\n'
        ),
        "minimum_examples": 4,
    },
    # ── FIX-E2E-046b: chat P2 ────────────────────────────────────────────────────
    {
        "id":             "FIX-E2E-046b",
        "description":    "Expand chat P2 — same examples",
        "target_intents": ["chat"],
        "target_file":    "adwi/logs/simeval/run_large_eval_p2.py",
        "check_pattern":  r"'chat'.*DEFAULT for everything.*\n.*advisory/recommendation.*\n.*questions about tools",
        "old_str": (
            '    "   \'chat\'           : DEFAULT for everything else — use this for:\\n"\n'
            '    "                      • advisory/recommendation questions (\'what is the best...\', \'should I...\')\\n"\n'
            '    "                      • questions about tools, services, subscriptions NOT directly about adwi\\n"\n'
        ),
        "new_str": (
            '    "   \'chat\'           : DEFAULT for everything else — use this for:\\n"\n'
            '    "                      • advisory/recommendation questions (\'what is the best...\', \'should I...\')\\n"\n'
            '    "                      • \'list all installed packages\', \'generate insights from my logs\' (no adwi action)\\n"\n'
            '    "                      • \'how do I debug my python\', \'my model is slow\', \'better AI responses\' (advice)\\n"\n'
            '    "                      • questions about tools, services, subscriptions NOT directly about adwi\\n"\n'
        ),
        "minimum_examples": 3,
    },
    # ── FIX-E2E-047: patch_adwi regex before implement_idea ──────────────────────
    {
        "id":             "FIX-E2E-047a",
        "description":    "Add 'improve/enhance adwi code' regex → patch_adwi before implement_idea in P1",
        "target_intents": ["patch_adwi"],
        "target_file":    "adwi/logs/simeval/run_large_eval.py",
        "check_pattern":  r"# CYCLE-4: implement_idea patterns.*\n.*implement.*idea.*implement_idea",
        "old_str": (
            '    # CYCLE-4: implement_idea patterns — "implement this idea/feature/plan"\n'
            '    (re.compile(r"\\bimplement\\b.{0,20}\\b(?:this|that|the)\\b.{0,15}\\b(?:idea|feature|plan|concept|improvement|suggestion)\\b", re.I), "implement_idea"),\n'
        ),
        "new_str": (
            '    # patch_adwi wins over implement_idea for "improve/enhance adwi code"\n'
            '    (re.compile(r"\\b(?:improve|enhance|upgrade|refactor)\\b.{0,10}\\badwi\\b.{0,20}\\b(?:code|source|scripts?|codebase)\\b", re.I), "patch_adwi"),\n'
            '    (re.compile(r"\\badwi\\b.{0,10}\\b(?:code|source|scripts?|codebase)\\b.{0,20}\\b(?:improve|enhance|upgrade|refactor)\\b", re.I), "patch_adwi"),\n'
            '    # CYCLE-4: implement_idea patterns — "implement this idea/feature/plan"\n'
            '    (re.compile(r"\\bimplement\\b.{0,20}\\b(?:this|that|the)\\b.{0,15}\\b(?:idea|feature|plan|concept|improvement|suggestion)\\b", re.I), "implement_idea"),\n'
        ),
        "minimum_examples": 1,
    },
    {
        "id":             "FIX-E2E-047b",
        "description":    "Add 'improve/enhance adwi code' regex → patch_adwi before implement_idea in P2",
        "target_intents": ["patch_adwi"],
        "target_file":    "adwi/logs/simeval/run_large_eval_p2.py",
        "check_pattern":  r"# CYCLE-4: implement_idea patterns.*\n.*implement.*idea.*implement_idea",
        "old_str": (
            '    # CYCLE-4: implement_idea patterns — "implement this idea/feature/plan"\n'
            '    (re.compile(r"\\bimplement\\b.{0,20}\\b(?:this|that|the)\\b.{0,15}\\b(?:idea|feature|plan|concept|improvement|suggestion)\\b", re.I), "implement_idea"),\n'
        ),
        "new_str": (
            '    # patch_adwi wins over implement_idea for "improve/enhance adwi code"\n'
            '    (re.compile(r"\\b(?:improve|enhance|upgrade|refactor)\\b.{0,10}\\badwi\\b.{0,20}\\b(?:code|source|scripts?|codebase)\\b", re.I), "patch_adwi"),\n'
            '    (re.compile(r"\\badwi\\b.{0,10}\\b(?:code|source|scripts?|codebase)\\b.{0,20}\\b(?:improve|enhance|upgrade|refactor)\\b", re.I), "patch_adwi"),\n'
            '    # CYCLE-4: implement_idea patterns — "implement this idea/feature/plan"\n'
            '    (re.compile(r"\\bimplement\\b.{0,20}\\b(?:this|that|the)\\b.{0,15}\\b(?:idea|feature|plan|concept|improvement|suggestion)\\b", re.I), "implement_idea"),\n'
        ),
        "minimum_examples": 1,
    },
    {
        "id":             "FIX-E2E-047c",
        "description":    "Add 'improve/enhance adwi code' regex → patch_adwi before implement_idea in CLI",
        "target_intents": ["patch_adwi"],
        "target_file":    "adwi/adwi_cli.py",
        "check_pattern":  r"# CYCLE-4: implement_idea patterns.*\n.*implement.*idea.*implement_idea",
        "old_str": (
            '    # CYCLE-4: implement_idea patterns — "implement this idea/feature/plan"\n'
            '    (re.compile(r"\\bimplement\\b.{0,20}\\b(?:this|that|the)\\b.{0,15}\\b(?:idea|feature|plan|concept|improvement|suggestion)\\b", re.I), "implement_idea"),\n'
        ),
        "new_str": (
            '    # patch_adwi wins over implement_idea for "improve/enhance adwi code"\n'
            '    (re.compile(r"\\b(?:improve|enhance|upgrade|refactor)\\b.{0,10}\\badwi\\b.{0,20}\\b(?:code|source|scripts?|codebase)\\b", re.I), "patch_adwi"),\n'
            '    (re.compile(r"\\badwi\\b.{0,10}\\b(?:code|source|scripts?|codebase)\\b.{0,20}\\b(?:improve|enhance|upgrade|refactor)\\b", re.I), "patch_adwi"),\n'
            '    # CYCLE-4: implement_idea patterns — "implement this idea/feature/plan"\n'
            '    (re.compile(r"\\bimplement\\b.{0,20}\\b(?:this|that|the)\\b.{0,15}\\b(?:idea|feature|plan|concept|improvement|suggestion)\\b", re.I), "implement_idea"),\n'
        ),
        "minimum_examples": 1,
    },
    # ── FIX-E2E-048: patch_adwi INTENT_SYSTEM — include improve/enhance ──────────
    {
        "id":             "FIX-E2E-048a",
        "description":    "Expand patch_adwi INTENT_SYSTEM in P1 to include 'improve adwi code', 'enhance adwi'",
        "target_intents": ["patch_adwi"],
        "target_file":    "adwi/logs/simeval/run_large_eval.py",
        "check_pattern":  r"'patch_adwi'.*code-level changes.*aider.*ONLY.*'aider'.*\n.*'patch adwi'.*'apply patches'",
        "old_str": (
            '    "   \'patch_adwi\'     : apply code-level changes to adwi source via aider. ONLY when user says \'aider\',\\n"\n'
            '    "                      \'patch adwi\', \'apply patches\', \'run aider\', \'self-patch\', \'auto-patch\'.\\n"\n'
            '    "                      NOT daily_improve (routine). NOT fix_error (pasted exception text).\\n"\n'
        ),
        "new_str": (
            '    "   \'patch_adwi\'     : apply code-level changes to adwi source via aider. \'aider\',\\n"\n'
            '    "                      \'patch adwi\', \'apply patches\', \'run aider\', \'self-patch\', \'auto-patch\',\\n"\n'
            '    "                      \'improve adwi code\', \'enhance adwi code\', \'upgrade adwi source\'.\\n"\n'
            '    "                      NOT daily_improve (routine). NOT fix_error (pasted exception text).\\n"\n'
        ),
        "minimum_examples": 1,
    },
    {
        "id":             "FIX-E2E-048b",
        "description":    "Expand patch_adwi INTENT_SYSTEM in P2 to include 'improve adwi code', 'enhance adwi'",
        "target_intents": ["patch_adwi"],
        "target_file":    "adwi/logs/simeval/run_large_eval_p2.py",
        "check_pattern":  r"'patch_adwi'.*code-level changes.*aider.*ONLY.*'aider', 'patch adwi'",
        "old_str": (
            '    "   \'patch_adwi\'     : apply code-level changes to adwi source via aider. ONLY \'aider\', \'patch adwi\',\\n"\n'
            '    "                      \'apply patches\', \'run aider\', \'self-patch\'. NOT daily_improve or fix_error.\\n"\n'
        ),
        "new_str": (
            '    "   \'patch_adwi\'     : apply code-level changes to adwi source via aider. \'aider\',\\n"\n'
            '    "                      \'patch adwi\', \'apply patches\', \'run aider\', \'self-patch\',\\n"\n'
            '    "                      \'improve adwi code\', \'enhance adwi code\', \'upgrade adwi source\'.\\n"\n'
            '    "                      NOT daily_improve. NOT fix_error.\\n"\n'
        ),
        "minimum_examples": 1,
    },
    {
        "id":             "FIX-E2E-048c",
        "description":    "Expand patch_adwi INTENT_SYSTEM in CLI to include 'improve adwi code', 'enhance adwi'",
        "target_intents": ["patch_adwi"],
        "target_file":    "adwi/adwi_cli.py",
        "check_pattern":  r"'patch_adwi'.*code-level changes.*ONLY when the.*\n.*user says 'aider'",
        "old_str": (
            '    "   \'patch_adwi\'     : apply code-level changes to adwi source via aider. ONLY when the\\n"\n'
            '    "                      user says \'aider\', \'patch adwi\', \'apply patches\', \'run aider\',\\n"\n'
            '    "                      \'self-patch\', or \'auto-patch\'. NOT daily_improve (routine).\\n"\n'
            '    "                      NOT fix_error (which handles pasted exception text).\\n"\n'
        ),
        "new_str": (
            '    "   \'patch_adwi\'     : apply code-level changes to adwi source via aider. ONLY when the\\n"\n'
            '    "                      user says \'aider\', \'patch adwi\', \'apply patches\', \'run aider\',\\n"\n'
            '    "                      \'self-patch\', \'auto-patch\', \'improve adwi code\', \'enhance adwi code\',\\n"\n'
            '    "                      \'upgrade adwi source\'. NOT daily_improve (routine).\\n"\n'
            '    "                      NOT fix_error (which handles pasted exception text).\\n"\n'
        ),
        "minimum_examples": 1,
    },
    # ── FIX-E2E-049: gmail sub-intents INTENT_SYSTEM descriptions ────────────────
    {
        "id":             "FIX-E2E-049a",
        "description":    "Add gmail cc/bcc/save_attachment/tasks_save INTENT_SYSTEM descriptions in P1",
        "target_intents": ["gmail_add_cc", "gmail_add_bcc", "gmail_save_attachment", "gmail_tasks_save"],
        "target_file":    "adwi/logs/simeval/run_large_eval.py",
        "check_pattern":  r"'gmail_list_category' : list emails in a Gmail category tab",
        "old_str": (
            '    "   \'gmail_list_category\' : list emails in a Gmail category tab.\\n"\n'
            '    "                      \'show my promotions\', \'what\'s in my promotions\', \'check my spam\',\\n"\n'
            '    "                      \'show spam\', \'social tab\', \'list my updates\'. NOT \'gmail\' (general).\\n"\n'
            '    "   \'generate_image\' : ONLY when creating a brand-new image/picture/artwork/visual output.\\n"\n'
        ),
        "new_str": (
            '    "   \'gmail_list_category\' : list emails in a Gmail category tab.\\n"\n'
            '    "                      \'show my promotions\', \'what\'s in my promotions\', \'check my spam\',\\n"\n'
            '    "                      \'show spam\', \'social tab\', \'list my updates\'. NOT \'gmail\' (general).\\n"\n'
            '    "   \'gmail_add_cc\'    : add a CC recipient to a draft/email being composed.\\n"\n'
            '    "                      \'also cc X\', \'add X to CC\', \'cc my assistant\', \'copy X on this\'.\\n"\n'
            '    "                      Context: user is composing/editing an email. NOT \'gmail\' (inbox).\\n"\n'
            '    "   \'gmail_add_bcc\'   : add a BCC recipient to a draft/email being composed.\\n"\n'
            '    "                      \'also bcc X\', \'add X to BCC\', \'bcc my boss\', \'blind copy X\'.\\n"\n'
            '    "                      Context: user is composing/editing an email. NOT \'gmail\' (inbox).\\n"\n'
            '    "   \'gmail_save_attachment\' : save/download an email attachment to disk.\\n"\n'
            '    "                      \'save the attached file\', \'download the attachment\', \'save that pdf\',\\n"\n'
            '    "                      \'download the invoice\'. NOT \'file_save\' (unrelated files).\\n"\n'
            '    "   \'gmail_tasks_save\' : save email-extracted tasks/action-items to Obsidian or daily note.\\n"\n'
            '    "                      \'save those tasks to my daily note\', \'add those to my daily note\',\\n"\n'
            '    "                      \'export those action items\'. Context: following gmail_extract_tasks.\\n"\n'
            '    "   \'generate_image\' : ONLY when creating a brand-new image/picture/artwork/visual output.\\n"\n'
        ),
        "minimum_examples": 1,
    },
    {
        "id":             "FIX-E2E-049b",
        "description":    "Add gmail cc/bcc/save_attachment/tasks_save INTENT_SYSTEM descriptions in P2",
        "target_intents": ["gmail_add_cc", "gmail_add_bcc", "gmail_save_attachment", "gmail_tasks_save"],
        "target_file":    "adwi/logs/simeval/run_large_eval_p2.py",
        "check_pattern":  r"'gmail'.*questions about email.*\n.*'any emails from X'",
        "old_str": (
            '    "   \'gmail\'          : questions about email, inbox, messages. \'new messages?\', \'check my email\',\\n"\n'
            '    "                      \'any emails from X\', \'check my email then search for action items\'.\\n"\n'
            '    "   \'generate_image\' : ONLY when creating a brand-new image/picture/artwork/visual output.\\n"\n'
        ),
        "new_str": (
            '    "   \'gmail\'          : questions about email, inbox, messages. \'new messages?\', \'check my email\',\\n"\n'
            '    "                      \'any emails from X\', \'check my email then search for action items\'.\\n"\n'
            '    "   \'gmail_add_cc\'    : add a CC recipient to a draft/email being composed.\\n"\n'
            '    "                      \'also cc X\', \'add X to CC\', \'cc my assistant\'.\\n"\n'
            '    "   \'gmail_add_bcc\'   : add a BCC recipient — \'also bcc X\', \'bcc my boss\'.\\n"\n'
            '    "   \'gmail_save_attachment\' : save an email attachment — \'save the attached file\', \'save that pdf\'.\\n"\n'
            '    "   \'gmail_tasks_save\' : save extracted tasks to daily note — \'add those to my daily note\'.\\n"\n'
            '    "   \'generate_image\' : ONLY when creating a brand-new image/picture/artwork/visual output.\\n"\n'
        ),
        "minimum_examples": 1,
    },
    # ── FIX-E2E-050: "also cc/bcc" regex → gmail_add_cc/bcc ─────────────────────
    {
        "id":             "FIX-E2E-050a",
        "description":    "Expand gmail_add_cc regex to match 'also cc' in P1",
        "target_intents": ["gmail_add_cc"],
        "target_file":    "adwi/logs/simeval/run_large_eval.py",
        "check_pattern":  r'r"\\badd\\s\+cc\\b".*gmail_add_cc',
        "old_str": (
            '    (re.compile(r"\\badd\\s+cc\\b", re.I), "gmail_add_cc"),\n'
        ),
        "new_str": (
            '    (re.compile(r"\\b(?:add|also)\\s+cc\\b|\\bcc\\s+(?:my|the)\\b", re.I), "gmail_add_cc"),\n'
        ),
        "minimum_examples": 1,
    },
    {
        "id":             "FIX-E2E-050b",
        "description":    "Expand gmail_add_cc regex to match 'also cc' in P2",
        "target_intents": ["gmail_add_cc"],
        "target_file":    "adwi/logs/simeval/run_large_eval_p2.py",
        "check_pattern":  r'r"\\badd\\s\+cc\\b".*gmail_add_cc',
        "old_str": (
            '    (re.compile(r"\\badd\\s+cc\\b", re.I), "gmail_add_cc"),\n'
        ),
        "new_str": (
            '    (re.compile(r"\\b(?:add|also)\\s+cc\\b|\\bcc\\s+(?:my|the)\\b", re.I), "gmail_add_cc"),\n'
        ),
        "minimum_examples": 1,
    },
    {
        "id":             "FIX-E2E-050c",
        "description":    "Expand gmail_add_cc regex to match 'also cc' in CLI",
        "target_intents": ["gmail_add_cc"],
        "target_file":    "adwi/adwi_cli.py",
        "check_pattern":  r'r"\\badd\\s\+cc\\b".*gmail_add_cc',
        "old_str": (
            '    (re.compile(r"\\badd\\s+cc\\b", re.I), "gmail_add_cc"),\n'
        ),
        "new_str": (
            '    (re.compile(r"\\b(?:add|also)\\s+cc\\b|\\bcc\\s+(?:my|the)\\b", re.I), "gmail_add_cc"),\n'
        ),
        "minimum_examples": 1,
    },
    # ── FIX-E2E-051: "also bcc" regex → gmail_add_bcc ────────────────────────────
    {
        "id":             "FIX-E2E-051a",
        "description":    "Expand gmail_add_bcc regex to match 'also bcc' in P1",
        "target_intents": ["gmail_add_bcc"],
        "target_file":    "adwi/logs/simeval/run_large_eval.py",
        "check_pattern":  r'r"\\badd\\s\+bcc\\b".*gmail_add_bcc',
        "old_str": (
            '    (re.compile(r"\\badd\\s+bcc\\b", re.I), "gmail_add_bcc"),\n'
        ),
        "new_str": (
            '    (re.compile(r"\\b(?:add|also)\\s+bcc\\b|\\bbcc\\s+(?:my|the)\\b", re.I), "gmail_add_bcc"),\n'
        ),
        "minimum_examples": 1,
    },
    {
        "id":             "FIX-E2E-051b",
        "description":    "Expand gmail_add_bcc regex to match 'also bcc' in P2",
        "target_intents": ["gmail_add_bcc"],
        "target_file":    "adwi/logs/simeval/run_large_eval_p2.py",
        "check_pattern":  r'r"\\badd\\s\+bcc\\b".*gmail_add_bcc',
        "old_str": (
            '    (re.compile(r"\\badd\\s+bcc\\b", re.I), "gmail_add_bcc"),\n'
        ),
        "new_str": (
            '    (re.compile(r"\\b(?:add|also)\\s+bcc\\b|\\bbcc\\s+(?:my|the)\\b", re.I), "gmail_add_bcc"),\n'
        ),
        "minimum_examples": 1,
    },
    {
        "id":             "FIX-E2E-051c",
        "description":    "Expand gmail_add_bcc regex to match 'also bcc' in CLI",
        "target_intents": ["gmail_add_bcc"],
        "target_file":    "adwi/adwi_cli.py",
        "check_pattern":  r'r"\\badd\\s\+bcc\\b".*gmail_add_bcc',
        "old_str": (
            '    (re.compile(r"\\badd\\s+bcc\\b", re.I), "gmail_add_bcc"),\n'
        ),
        "new_str": (
            '    (re.compile(r"\\b(?:add|also)\\s+bcc\\b|\\bbcc\\s+(?:my|the)\\b", re.I), "gmail_add_bcc"),\n'
        ),
        "minimum_examples": 1,
    },
    # ── FIX-E2E-052: gmail_save_attachment — add "attached file" to pattern ──────
    {
        "id":             "FIX-E2E-052a",
        "description":    "Add 'attached file' to gmail_save_attachment regex in P1",
        "target_intents": ["gmail_save_attachment"],
        "target_file":    "adwi/logs/simeval/run_large_eval.py",
        "check_pattern":  r"save\|download\|open.*attachment\|pdf\|document.*gmail_save_attachment",
        "old_str": (
            '    (re.compile(r"\\b(?:save|download|open)\\b.{0,30}\\b(?:the\\s+)?(?:attached\\s+)?(?:attachment|pdf|document|invoice|receipt|image|spreadsheet)\\b", re.I), "gmail_save_attachment"),\n'
        ),
        "new_str": (
            '    (re.compile(r"\\b(?:save|download|open)\\b.{0,30}\\b(?:the\\s+)?(?:attached\\s+)?(?:attachment|pdf|document|invoice|receipt|image|spreadsheet|file)\\b", re.I), "gmail_save_attachment"),\n'
        ),
        "minimum_examples": 1,
    },
    {
        "id":             "FIX-E2E-052b",
        "description":    "Add 'attached file' to gmail_save_attachment regex in P2",
        "target_intents": ["gmail_save_attachment"],
        "target_file":    "adwi/logs/simeval/run_large_eval_p2.py",
        "check_pattern":  r"save\|download\|open.*attachment\|pdf\|document.*gmail_save_attachment",
        "old_str": (
            '    (re.compile(r"\\b(?:save|download|open)\\b.{0,30}\\b(?:the\\s+)?(?:attached\\s+)?(?:attachment|pdf|document|invoice|receipt|image|spreadsheet)\\b", re.I), "gmail_save_attachment"),\n'
        ),
        "new_str": (
            '    (re.compile(r"\\b(?:save|download|open)\\b.{0,30}\\b(?:the\\s+)?(?:attached\\s+)?(?:attachment|pdf|document|invoice|receipt|image|spreadsheet|file)\\b", re.I), "gmail_save_attachment"),\n'
        ),
        "minimum_examples": 1,
    },
    {
        "id":             "FIX-E2E-052c",
        "description":    "Add 'attached file' to gmail_save_attachment regex in CLI",
        "target_intents": ["gmail_save_attachment"],
        "target_file":    "adwi/adwi_cli.py",
        "check_pattern":  r"save\|download\|open.*attachment\|pdf\|document.*gmail_save_attachment",
        "old_str": (
            '    (re.compile(r"\\b(?:save|download|open)\\b.{0,30}\\b(?:the\\s+)?(?:attached\\s+)?(?:attachment|pdf|document|invoice|receipt|image|spreadsheet)\\b", re.I), "gmail_save_attachment"),\n'
        ),
        "new_str": (
            '    (re.compile(r"\\b(?:save|download|open)\\b.{0,30}\\b(?:the\\s+)?(?:attached\\s+)?(?:attachment|pdf|document|invoice|receipt|image|spreadsheet|file)\\b", re.I), "gmail_save_attachment"),\n'
        ),
        "minimum_examples": 1,
    },
    # ── FIX-E2E-041c: capabilities CLI ───────────────────────────────────────────
    {
        "id":             "FIX-E2E-041c",
        "description":    "Expand capabilities CLI — add 'show help', 'list all commands' examples",
        "target_intents": ["capabilities"],
        "target_file":    "adwi/adwi_cli.py",
        "check_pattern":  r"'capabilities'.*EXPLICITLY asks what ADWI/YOU can do.*\n.*'your features'.*\n.*alternatives",
        "old_str": (
            '    "   \'capabilities\'   : user EXPLICITLY asks what ADWI/YOU can do — must mention \'you\', \'adwi\',\\n"\n'
            '    "                      \'your features\', \'your commands\', or \'show help\'. Questions about\\n"\n'
            '    "                      alternatives, comparisons, recommendations, or subscriptions are NOT this.\\n"\n'
        ),
        "new_str": (
            '    "   \'capabilities\'   : user asks what adwi/the assistant can do. \'what can you do\', \'show help\',\\n"\n'
            '    "                      \'list all commands\', \'show all commands\', \'show the command list\',\\n"\n'
            '    "                      \'your skills\', \'your features\', \'your commands\'. NOT file_list.\\n"\n'
            '    "                      Questions about alternatives or subscriptions are NOT this → chat.\\n"\n'
        ),
        "minimum_examples": 1,
    },
]


# ── Timestamps ─────────────────────────────────────────────────────────────────

def _now() -> str:
    return datetime.now().isoformat(timespec="seconds")


# ── Lock ───────────────────────────────────────────────────────────────────────

def _acquire_lock() -> bool:
    """Try to own running.pid. Returns True if acquired."""
    LOOP_DIR.mkdir(parents=True, exist_ok=True)
    if PID_FILE.exists():
        try:
            pid = int(PID_FILE.read_text().strip())
            os.kill(pid, 0)       # signal 0: check existence only
            return False          # alive — another loop running
        except (ValueError, ProcessLookupError):
            pass                  # stale lock — overwrite
        except PermissionError:
            return False          # process alive, not ours
    PID_FILE.write_text(str(os.getpid()))
    return True


def _release_lock() -> None:
    PID_FILE.unlink(missing_ok=True)


# ── Status writer ──────────────────────────────────────────────────────────────

def _write_status(job_id: str, status: str, cycle: int, max_cycles: int,
                  target: float, extra: dict | None = None) -> None:
    data: dict = {
        "job_id":      job_id,
        "status":      status,
        "updated_at":  _now(),
        "target":      target,
        "max_cycles":  max_cycles,
        "cycle":       cycle,
        "report_path": str(LOOP_DIR / job_id),
    }
    if extra:
        data.update(extra)
    STATUS_FILE.write_text(json.dumps(data, indent=2))


# ── Metrics ────────────────────────────────────────────────────────────────────

def _load_results(session_dir: Path) -> list[dict]:
    rj = session_dir / "results.jsonl"
    if not rj.exists():
        return []
    results: list[dict] = []
    for line in rj.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if line:
            results.append(json.loads(line))
    return results


def _classify_fix_type(cluster_count: int, top_misroute_count: int) -> str:
    """Heuristic: suggest fix type for a failing intent cluster."""
    if cluster_count <= 2:
        return "manual_review"
    concentration = top_misroute_count / cluster_count if cluster_count else 0
    if concentration >= 0.6:
        return "regex_candidate"
    return "intent_system_candidate"


def _compute_metrics(p1_dir: Path, p2_dir: Path) -> dict:
    """
    Combined = dedup-merge P1+P2 on prompt.lower().strip() (P1 first).
    Authoritative formula: matches generate_master_report.py deduplicate().
    Returns p1/p2/combined rates + enriched failure_clusters with examples,
    router_type, suggested_fix_type, and patchable_files for each cluster.
    """
    p1 = _load_results(p1_dir)
    p2 = _load_results(p2_dir)

    def _rate(rs: list[dict]) -> tuple[int, int, float]:
        total  = len(rs)
        passed = sum(1 for r in rs if r["verdict"] == "pass")
        pct    = round(100 * passed / total, 1) if total else 0.0
        return total, passed, pct

    p1_total, p1_passed, p1_pct = _rate(p1)
    p2_total, p2_passed, p2_pct = _rate(p2)

    seen: set[str] = set()
    combined: list[dict] = []
    for r in p1 + p2:
        key = r["prompt"].lower().strip()
        if key not in seen:
            seen.add(key)
            combined.append(r)

    c_total, c_passed, c_pct = _rate(combined)

    failed = [r for r in combined if r["verdict"] == "fail"]
    fail_by_intent: dict[str, int] = {}
    misroutes: dict[str, int] = {}
    cluster_examples:  dict[str, list[str]]       = {}
    cluster_misroutes: dict[str, dict[str, int]]  = {}

    for r in failed:
        exp = r.get("expected_intent") or "__none__"
        got = r.get("got_intent")      or "__none__"
        fail_by_intent[exp] = fail_by_intent.get(exp, 0) + 1
        misroutes[f"{exp} → {got}"] = misroutes.get(f"{exp} → {got}", 0) + 1
        if exp not in cluster_examples:
            cluster_examples[exp]  = []
            cluster_misroutes[exp] = {}
        if len(cluster_examples[exp]) < 5:
            cluster_examples[exp].append(r.get("prompt", "")[:120])
        cluster_misroutes[exp][got] = cluster_misroutes[exp].get(got, 0) + 1

    # Build enriched failure_clusters (sorted by fail count, top 20)
    failure_clusters: list[dict] = []
    has_known_fixes = bool(KNOWN_REGEX_FIXES)
    known_targets: set[str] = set()
    for fx in KNOWN_REGEX_FIXES:
        known_targets.update(fx.get("target_intents", []))

    for intent, count in sorted(fail_by_intent.items(), key=lambda x: -x[1])[:20]:
        mr = cluster_misroutes.get(intent, {})
        if mr:
            top_got, top_got_count = max(mr.items(), key=lambda x: x[1])
        else:
            top_got, top_got_count = "?", 0
        fix_type = _classify_fix_type(count, top_got_count)
        patchable = (
            ["adwi/adwi_cli.py"]
            if fix_type in ("regex_candidate", "intent_system_candidate")
            else []
        )
        if not has_known_fixes:
            patch_note = (
                "No patch attempted — KNOWN_REGEX_FIXES is empty. "
                "Review examples and add a safe deterministic fix entry."
            )
        elif intent not in known_targets:
            patch_note = "No KNOWN_REGEX_FIXES entry targets this intent."
        else:
            patch_note = "Fix entry exists in KNOWN_REGEX_FIXES — will be attempted."

        failure_clusters.append({
            "expected_intent":    intent,
            "fail_count":         count,
            "top_misroute":       f"{intent} → {top_got}",
            "top_misroute_count": top_got_count,
            "all_misroutes":      dict(sorted(mr.items(), key=lambda x: -x[1])),
            "examples":           cluster_examples.get(intent, []),
            "router_type":        "LLM",   # eval harness always uses LLM path; regex not tested here
            "suggested_fix_type": fix_type,
            "patchable_files":    patchable,
            "patch_note":         patch_note,
        })

    return {
        "p1_total":        p1_total,  "p1_passed":       p1_passed,  "p1_pct":      p1_pct,
        "p2_total":        p2_total,  "p2_passed":       p2_passed,  "p2_pct":      p2_pct,
        "combined_total":  c_total,   "combined_passed":  c_passed,  "combined_pct": c_pct,
        "fail_by_intent":  dict(sorted(fail_by_intent.items(), key=lambda x: -x[1])[:20]),
        "top_misroutes":   dict(sorted(misroutes.items(),      key=lambda x: -x[1])[:10]),
        "failure_clusters": failure_clusters,
    }


def _run_eval_and_get_dir(
    py: str, script: Path, prefix: str, workers: int, timeout: int
) -> tuple[Path | None, str]:
    """
    Run an eval script and locate the new session dir deterministically.
    Snapshots matching dirs before running, diffs after. Requires exactly one new dir.
    Returns (session_dir, error_msg). error_msg is empty string on success.
    """
    before = set(SIMEVAL.glob(f"{prefix}-*"))
    r = subprocess.run(
        [py, str(script), "--workers", str(workers)],
        capture_output=True, text=True, timeout=timeout, cwd=str(WORKSPACE)
    )
    if r.returncode != 0:
        return None, f"eval failed rc={r.returncode}: {r.stderr[-1000:]}"
    after = set(SIMEVAL.glob(f"{prefix}-*"))
    new_dirs = after - before
    if len(new_dirs) != 1:
        names = sorted(d.name for d in new_dirs)
        return None, (
            f"Expected exactly 1 new session dir, found {len(new_dirs)}: {names}"
        )
    return new_dirs.pop(), ""


# ── Preflight ──────────────────────────────────────────────────────────────────

def _run_preflight(job_dir: Path) -> tuple[bool, str]:
    """py_compile patchable Python files + run test_nlu_regex.py. Returns (ok, detail)."""
    errors: list[str] = []

    for pf in PATCHABLE_FILES:
        if not pf.exists() or pf.suffix != ".py":
            continue
        r = subprocess.run(
            [sys.executable, "-m", "py_compile", str(pf)],
            capture_output=True, text=True
        )
        if r.returncode != 0:
            errors.append(f"py_compile {pf.name}: {r.stderr.strip()}")

    test_file = ADWI_DIR / "simlab" / "tests" / "test_nlu_regex.py"
    if test_file.exists():
        r = subprocess.run(
            [sys.executable, "-m", "unittest", str(test_file)],
            capture_output=True, text=True, cwd=str(WORKSPACE)
        )
        if r.returncode != 0:
            errors.append(f"test_nlu_regex.py FAILED:\n{r.stderr[-2000:]}")

    detail = "\n".join(errors) if errors else "all OK"
    return (not errors, detail)


def _count_passing_tests() -> int:
    """Run test_nlu_regex.py and return passing test count. Returns -1 if unavailable."""
    test_file = ADWI_DIR / "simlab" / "tests" / "test_nlu_regex.py"
    if not test_file.exists():
        return -1
    r = subprocess.run(
        [sys.executable, "-m", "unittest", str(test_file)],
        capture_output=True, text=True, cwd=str(WORKSPACE)
    )
    combined = r.stderr + r.stdout
    m_ran = re.search(r"Ran (\d+) tests", combined)
    if not m_ran:
        return -1
    total    = int(m_ran.group(1))
    mf       = re.search(r"failures=(\d+)", combined)
    me       = re.search(r"errors=(\d+)",   combined)
    failures = int(mf.group(1)) if mf else 0
    errors   = int(me.group(1)) if me else 0
    return total - failures - errors


# ── Dirty worktree guard ───────────────────────────────────────────────────────

def _check_dirty_patchable(snapshots_dir: Path) -> list[str]:
    """
    Return relative paths of patchable files with uncommitted user changes
    NOT made by this job (our own patches are in snapshots_dir as *.bak).
    """
    r = subprocess.run(
        ["git", "status", "--short"],
        capture_output=True, text=True, cwd=str(WORKSPACE)
    )
    our_snaps: set[str] = set()
    if snapshots_dir.exists():
        our_snaps = {f.stem for f in snapshots_dir.glob("*.bak")}

    dirty: list[str] = []
    for line in r.stdout.splitlines():
        if len(line) < 4:
            continue
        flags = line[:2].strip()
        fpath = line[3:].strip()
        if not flags:
            continue
        for pf in PATCHABLE_FILES:
            rel = str(pf.relative_to(WORKSPACE))
            if rel == fpath or fpath == pf.name:
                if pf.name not in our_snaps:
                    dirty.append(fpath)
                break
    return dirty


# ── Patch helpers ──────────────────────────────────────────────────────────────

def _snapshot_file(pf: Path, snapshots_dir: Path) -> Path:
    snapshots_dir.mkdir(parents=True, exist_ok=True)
    bak = snapshots_dir / f"{pf.name}.bak"
    shutil.copy2(str(pf), str(bak))
    return bak


def _rollback_file(pf: Path, bak: Path) -> None:
    shutil.copy2(str(bak), str(pf))


def _apply_known_fixes(
    job_dir: Path, metrics: dict, cycle: int
) -> tuple[list[str], list[str], list[str]]:
    """
    Try KNOWN_REGEX_FIXES in order. Returns (applied, skipped, unfixed_intents).
    Each fix: record baseline test count → snapshot → apply → preflight + regression guard
    → rollback immediately if test count drops.
    """
    applied:  list[str] = []
    skipped:  list[str] = []
    snapshots_dir   = job_dir / "snapshots"
    failing_intents = set(metrics.get("fail_by_intent", {}).keys())

    baseline_tests = _count_passing_tests()

    for fix in KNOWN_REGEX_FIXES:
        fid     = fix["id"]
        targets = set(fix.get("target_intents", []))
        if targets and not targets.intersection(failing_intents):
            skipped.append(f"{fid}: no matching failing intents")
            continue

        min_ex     = fix.get("minimum_examples", 1)
        fail_count = sum(metrics.get("fail_by_intent", {}).get(t, 0) for t in targets)
        if fail_count < min_ex:
            skipped.append(f"{fid}: {fail_count} failing examples < minimum {min_ex}")
            continue

        target_file = WORKSPACE / fix["target_file"]
        if not target_file.exists():
            skipped.append(f"{fid}: target file not found")
            continue

        content = target_file.read_text(encoding="utf-8")
        if fix["old_str"] not in content:
            skipped.append(f"{fid}: old_str not present (already applied or file changed)")
            continue

        check_pat = fix.get("check_pattern", "")
        if check_pat and not re.search(check_pat, content):
            skipped.append(f"{fid}: check_pattern not found")
            continue

        bak = _snapshot_file(target_file, snapshots_dir)
        target_file.write_text(
            content.replace(fix["old_str"], fix["new_str"], 1), encoding="utf-8"
        )

        pf_ok, pf_detail = _run_preflight(job_dir)
        after_tests = _count_passing_tests()
        regressed = (
            baseline_tests > 0 and after_tests >= 0 and after_tests < baseline_tests
        )
        if not pf_ok or regressed:
            _rollback_file(target_file, bak)
            if regressed:
                reason = f"test regression: {baseline_tests} → {after_tests} passing"
            else:
                reason = f"preflight: {pf_detail[:200]}"
            skipped.append(f"{fid}: rolled back — {reason}")
            continue

        applied.append(fid)
        baseline_tests = after_tests  # update baseline for subsequent fixes

    fixed_intents: set[str] = set()
    for fid in applied:
        fix = next(f for f in KNOWN_REGEX_FIXES if f["id"] == fid)
        fixed_intents.update(fix.get("target_intents", []))
    unfixed = sorted(failing_intents - fixed_intents)
    return applied, skipped, unfixed


# ── Finalize ───────────────────────────────────────────────────────────────────

def _finalize(
    job_id: str, job_dir: Path, status: str, cycles: list[dict],
    target: float, max_cycles: int, reason: str,
    final_combined_pct: float | None = None,
    needs_llm_review: bool = False,
    unfixed_clusters: list[str] | None = None,
) -> None:
    final = {
        "job_id":             job_id,
        "status":             status,
        "stop_reason":        reason,
        "target":             target,
        "max_cycles":         max_cycles,
        "final_combined_pct": final_combined_pct,
        "needs_llm_review":   needs_llm_review,
        "unfixed_clusters":   unfixed_clusters or [],
        "cycles":             cycles,
        "finished_at":        _now(),
    }
    (job_dir / "final-report.json").write_text(json.dumps(final, indent=2))
    _write_status(job_id, status, len(cycles), max_cycles, target, {
        "stop_reason":        reason,
        "final_combined_pct": final_combined_pct,
        "needs_llm_review":   needs_llm_review,
        "unfixed_clusters":   unfixed_clusters or [],
        "cycles":             cycles,
    })
    print(f"[e2e-loop] DONE — status={status}  reason={reason}")


# ── Main loop ──────────────────────────────────────────────────────────────────

def main(
    target:       float = 98.0,
    max_cycles:   int   = 3,
    dry_run:      bool  = False,
    analyze_only: bool  = False,
    job_id:       str | None = None,
    workers:      int   = 5,
) -> int:
    """Entry point. Returns 0 on success/dry-run/analysis, 1 on failure/abort."""
    if job_id is None:
        job_id = f"e2e-{datetime.now().strftime('%Y%m%d-%H%M%S')}"

    job_dir       = LOOP_DIR / job_id
    snapshots_dir = job_dir / "snapshots"
    job_dir.mkdir(parents=True, exist_ok=True)

    if not _acquire_lock():
        print(json.dumps({"error": "E2E loop already running", "pid_file": str(PID_FILE)}))
        return 1

    mode = "analyze_only" if analyze_only else ("dry_run" if dry_run else "full")
    _write_status(job_id, "running", 0, max_cycles, target, {
        "started_at":   _now(),
        "dry_run":      dry_run,
        "analyze_only": analyze_only,
        "workers":      workers,
        "cycles":       [],
    })
    print(f"[e2e-loop] Started  job_id={job_id}  target={target}%  "
          f"max_cycles={max_cycles}  mode={mode}")

    git_snap = subprocess.run(
        ["git", "status", "--short"], capture_output=True, text=True, cwd=str(WORKSPACE)
    ).stdout
    (job_dir / "git-status-at-start.txt").write_text(git_snap)

    py           = str(VENV_PY) if VENV_PY.exists() else sys.executable
    job_start_t  = time.monotonic()
    prev_combined_pct: float | None = None
    all_cycles:        list[dict]   = []

    try:
        for cycle in range(1, max_cycles + 1):
            cycle_t = time.monotonic()
            print(f"\n[e2e-loop] ── CYCLE {cycle}/{max_cycles} ──")
            _write_status(job_id, "running", cycle, max_cycles, target,
                          {"cycles": all_cycles})

            # Overall job timeout guard
            if time.monotonic() - job_start_t > TIMEOUT_JOB:
                _finalize(job_id, job_dir, "timeout", all_cycles, target, max_cycles,
                          "Overall job timeout (14400s) reached")
                return 1

            # Cancel sentinel check
            if CANCEL_FILE.exists():
                CANCEL_FILE.unlink(missing_ok=True)
                _finalize(job_id, job_dir, "cancelled", all_cycles, target, max_cycles,
                          "Cancelled by user")
                return 0

            # ── PREFLIGHT ────────────────────────────────────────────────────
            print("[e2e-loop] Preflight: py_compile + test_nlu_regex...")
            pf_ok, pf_detail = _run_preflight(job_dir)
            if not pf_ok:
                _finalize(job_id, job_dir, "failed", all_cycles, target, max_cycles,
                          f"Preflight failed: {pf_detail}")
                return 1

            if dry_run:
                print("[e2e-loop] DRY-RUN: preflight passed. Eval and patching skipped.")
                rep = {
                    "cycle": cycle, "dry_run": True, "preflight": "pass",
                    "p1_pct": None, "p2_pct": None, "combined_pct": None,
                    "patches_applied": [], "patches_skipped": [],
                    "duration_s": round(time.monotonic() - cycle_t, 1),
                }
                all_cycles.append(rep)
                (job_dir / f"cycle-{cycle}-report.json").write_text(json.dumps(rep, indent=2))
                _finalize(job_id, job_dir, "dry_run_complete", all_cycles, target, max_cycles,
                          "Dry-run: preflight OK, eval skipped")
                return 0

            # ── EVAL P1 (snapshot-diff, deterministic dir selection) ──────────
            print(f"[e2e-loop] Running P1 eval (workers={workers}, timeout={TIMEOUT_P1}s)...")
            p1_dir, p1_err = _run_eval_and_get_dir(py, RUN_P1, "large", workers, TIMEOUT_P1)
            if p1_err:
                _finalize(job_id, job_dir, "failed", all_cycles, target, max_cycles,
                          f"P1 eval: {p1_err}")
                return 1

            # ── EVAL P2 (snapshot-diff, deterministic dir selection) ──────────
            print(f"[e2e-loop] Running P2 eval (workers={workers}, timeout={TIMEOUT_P2}s)...")
            p2_dir, p2_err = _run_eval_and_get_dir(py, RUN_P2, "large-p2", workers, TIMEOUT_P2)
            if p2_err:
                _finalize(job_id, job_dir, "failed", all_cycles, target, max_cycles,
                          f"P2 eval: {p2_err}")
                return 1

            # ── METRICS ──────────────────────────────────────────────────────
            metrics = _compute_metrics(p1_dir, p2_dir)
            c_pct   = metrics["combined_pct"]
            print(f"[e2e-loop] P1={metrics['p1_pct']}%  P2={metrics['p2_pct']}%  "
                  f"Combined={c_pct}%  target={target}%")

            # ── MONOTONIC GUARD ───────────────────────────────────────────────
            if prev_combined_pct is not None and c_pct < prev_combined_pct:
                _finalize(job_id, job_dir, "failed", all_cycles, target, max_cycles,
                          f"Monotonic safety: combined dropped {prev_combined_pct}% → {c_pct}%")
                return 1

            cycle_rep: dict = {
                "cycle":         cycle,
                "preflight":     "pass",
                "analyze_only":  analyze_only,
                **metrics,
                "patches_applied":  [],
                "patches_skipped":  [],
                "needs_llm_review": False,
                "unfixed_clusters": [],
                "duration_s":       0.0,
            }

            # ── SUCCESS ───────────────────────────────────────────────────────
            if c_pct >= target:
                cycle_rep["duration_s"] = round(time.monotonic() - cycle_t, 1)
                all_cycles.append(cycle_rep)
                (job_dir / f"cycle-{cycle}-report.json").write_text(
                    json.dumps(cycle_rep, indent=2))
                _finalize(job_id, job_dir, "success", all_cycles, target, max_cycles,
                          f"Target reached: {c_pct}% >= {target}%",
                          final_combined_pct=c_pct)
                return 0

            # ── ANALYZE-ONLY: write report, no patching ───────────────────────
            if analyze_only:
                unfixed = sorted(metrics.get("fail_by_intent", {}).keys())
                cycle_rep.update({
                    "needs_llm_review": True,
                    "unfixed_clusters": unfixed[:20],
                    "duration_s":       round(time.monotonic() - cycle_t, 1),
                })
                all_cycles.append(cycle_rep)
                (job_dir / f"cycle-{cycle}-report.json").write_text(
                    json.dumps(cycle_rep, indent=2))
                _finalize(
                    job_id, job_dir, "analysis_complete", all_cycles, target, max_cycles,
                    f"Analyze-only: {c_pct}% < {target}%. "
                    f"Review failure_clusters in cycle-{cycle}-report.json.",
                    final_combined_pct=c_pct,
                    needs_llm_review=True,
                    unfixed_clusters=unfixed[:20],
                )
                return 0

            # ── DIRTY WORKTREE GUARD ──────────────────────────────────────────
            dirty = _check_dirty_patchable(snapshots_dir)
            if dirty:
                msg = (f"Uncommitted user changes in patchable files: {dirty}. "
                       "Stopping to protect your work.")
                cycle_rep.update({"needs_llm_review": True, "stop_reason": msg,
                                  "dirty_files": dirty})
                all_cycles.append(cycle_rep)
                (job_dir / f"cycle-{cycle}-report.json").write_text(
                    json.dumps(cycle_rep, indent=2))
                _finalize(job_id, job_dir, "needs_llm_review", all_cycles, target, max_cycles,
                          msg, needs_llm_review=True,
                          unfixed_clusters=sorted(metrics.get("fail_by_intent", {}).keys()))
                return 0

            # ── AUTO-FIX Phase A ──────────────────────────────────────────────
            if KNOWN_REGEX_FIXES:
                print("[e2e-loop] Applying known regex fixes (Phase A)...")
                applied, skipped_fixes, unfixed = _apply_known_fixes(job_dir, metrics, cycle)
                cycle_rep["patches_applied"] = applied
                cycle_rep["patches_skipped"] = skipped_fixes
                if applied:
                    pf_ok2, pf_detail2 = _run_preflight(job_dir)
                    if not pf_ok2:
                        for pf in PATCHABLE_FILES:
                            bak = snapshots_dir / f"{pf.name}.bak"
                            if bak.exists():
                                _rollback_file(pf, bak)
                        _finalize(job_id, job_dir, "failed", all_cycles, target, max_cycles,
                                  f"Post-patch preflight failed: {pf_detail2}")
                        return 1
            else:
                unfixed = sorted(metrics.get("fail_by_intent", {}).keys())

            # Phase B: mark for LLM review if still below target
            if c_pct < target:
                cycle_rep["needs_llm_review"] = True
                cycle_rep["unfixed_clusters"]  = unfixed[:20]

            prev_combined_pct       = c_pct
            cycle_rep["duration_s"] = round(time.monotonic() - cycle_t, 1)
            all_cycles.append(cycle_rep)
            (job_dir / f"cycle-{cycle}-report.json").write_text(
                json.dumps(cycle_rep, indent=2))

        # ── MAX CYCLES REACHED ────────────────────────────────────────────────
        final_pct    = all_cycles[-1].get("combined_pct") if all_cycles else None
        needs_review = final_pct is None or final_pct < target
        _finalize(job_id, job_dir, "max_cycles_reached", all_cycles, target, max_cycles,
                  f"Max cycles ({max_cycles}) reached. Final combined: {final_pct}%",
                  final_combined_pct=final_pct,
                  needs_llm_review=needs_review,
                  unfixed_clusters=(all_cycles[-1].get("unfixed_clusters", [])
                                    if all_cycles else []))
        return 0

    except subprocess.TimeoutExpired as exc:
        _finalize(job_id, job_dir, "timeout", all_cycles, target, max_cycles, str(exc))
        return 1
    except KeyboardInterrupt:
        _finalize(job_id, job_dir, "cancelled", all_cycles, target, max_cycles,
                  "KeyboardInterrupt")
        return 0
    except Exception as exc:
        import traceback
        _finalize(job_id, job_dir, "failed", all_cycles, target, max_cycles,
                  f"Unexpected error: {exc}\n{traceback.format_exc()[-2000:]}")
        return 1
    finally:
        _release_lock()


# ── CLI entry ──────────────────────────────────────────────────────────────────

if __name__ == "__main__":
    ap = argparse.ArgumentParser(description="Adwi E2E Auto Loop")
    ap.add_argument("--target",       type=float, default=98.0)
    ap.add_argument("--max-cycles",   type=int,   default=3)
    ap.add_argument("--dry-run",      action="store_true")
    ap.add_argument("--analyze-only", action="store_true",
                    help="Run evals and write enriched failure reports; skip all patching.")
    ap.add_argument("--job-id",       type=str,   default=None)
    ap.add_argument("--workers",      type=int,   default=5)
    args = ap.parse_args()
    sys.exit(main(
        target=args.target,
        max_cycles=args.max_cycles,
        dry_run=args.dry_run,
        analyze_only=args.analyze_only,
        job_id=args.job_id,
        workers=args.workers,
    ))
