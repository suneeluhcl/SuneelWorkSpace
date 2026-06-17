"""
adwi/simlab/tests/test_gmail_burnin.py

Gmail burn-in test suite — Phase A/B/C (NLU routing + helper function unit tests).

Covers every Gmail intent (40+) with positive routing tests, collision/boundary
tests between adjacent intents, and pure-function unit tests for the four
parsers that are extractable without live API deps.

Run: python3 -m unittest adwi/simlab/tests/test_gmail_burnin.py -v
No Ollama / no external network required.
"""
from __future__ import annotations

import re
import sys
import unittest
from datetime import datetime, timedelta
from pathlib import Path

# ---------------------------------------------------------------------------
# Bootstrap: extract _REGEX_INTENTS without importing adwi_cli.py
# ---------------------------------------------------------------------------

_CLI_PATH = Path(__file__).resolve().parents[3] / "adwi" / "adwi_cli.py"


def _load_regex_intents():
    src = _CLI_PATH.read_text()
    start = src.index("_REGEX_INTENTS = [")
    end   = src.index("\ndef _regex_prefilter")
    ns: dict = {}
    exec(src[start:end], {"re": re}, ns)  # noqa: S102
    return ns["_REGEX_INTENTS"]


_REGEX_INTENTS = _load_regex_intents()


def _classify(text: str) -> str | None:
    for pattern, intent in _REGEX_INTENTS:
        if pattern.search(text):
            return intent
    return None


# ---------------------------------------------------------------------------
# Helper: extract a slice of adwi_cli.py between two top-level defs
# ---------------------------------------------------------------------------

def _extract_between(src: str, start_name: str, end_name: str) -> str:
    m_start = re.search(rf"^def {re.escape(start_name)}\b", src, re.MULTILINE)
    m_end   = re.search(rf"^def {re.escape(end_name)}\b",   src, re.MULTILINE)
    if not m_start:
        raise RuntimeError(f"def {start_name} not found in adwi_cli.py")
    if not m_end:
        raise RuntimeError(f"def {end_name} not found in adwi_cli.py")
    return src[m_start.start():m_end.start()]


def _extract_from_const(src: str, const_name: str, end_name: str) -> str:
    m_start = re.search(rf"^{re.escape(const_name)}\s*=", src, re.MULTILINE)
    m_end   = re.search(rf"^def {re.escape(end_name)}\b",  src, re.MULTILINE)
    if not m_start or not m_end:
        raise RuntimeError(f"Cannot extract {const_name}..{end_name}")
    return src[m_start.start():m_end.start()]


_SRC = _CLI_PATH.read_text()


def _load_parse_task_extraction():
    code = _extract_between(_SRC, "_parse_task_extraction", "_task_list_preview")
    ns: dict = {"re": re}
    exec(code, ns)  # noqa: S102
    return ns["_parse_task_extraction"]


def _load_filter_criteria_to_query():
    code = _extract_between(_SRC, "_filter_criteria_to_query", "_filter_preview")
    ns: dict = {}
    exec(code, ns)  # noqa: S102
    return ns["_filter_criteria_to_query"]


def _load_thread_helpers():
    code = _extract_between(_SRC, "_thread_latest_message", "cmd_gmail_thread_intel")
    ns: dict = {}
    exec(code, ns)  # noqa: S102
    return ns


def _load_schedule_helpers():
    code = _extract_from_const(_SRC, "_DAYS_OF_WEEK", "_load_scheduled_sends")
    ns: dict = {"re": re, "datetime": datetime, "timedelta": timedelta}
    exec(code, ns)  # noqa: S102
    return ns


# ===========================================================================
# 1. CORE INTENT ROUTING — positive match tests for every Gmail intent
# ===========================================================================

class TestGmailNLUCore(unittest.TestCase):
    """One or two canonical positive-match tests per Gmail intent."""

    # ── inbox listing ────────────────────────────────────────────────────────
    def test_gmail_list_inbox(self):
        self.assertEqual(_classify("show my inbox"), "gmail")

    def test_gmail_list_unread(self):
        self.assertEqual(_classify("show unread emails"), "gmail")

    def test_gmail_check_email(self):
        self.assertEqual(_classify("check my email"), "gmail")

    # ── gmail_open (search + open first result) ───────────────────────────
    def test_gmail_open_from(self):
        self.assertEqual(_classify("open the email from Rahul"), "gmail_open")

    def test_gmail_open_about(self):
        self.assertEqual(_classify("open the email about the budget"), "gmail_open")

    # ── gmail_read (specific email by number/keyword) ─────────────────────
    def test_gmail_read_number(self):
        self.assertEqual(_classify("open 3"), "gmail_read")

    def test_gmail_read_latest(self):
        self.assertEqual(_classify("read the latest email"), "gmail_read")

    def test_gmail_read_this(self):
        self.assertEqual(_classify("read this email"), "gmail_read")

    # ── gmail_thread ──────────────────────────────────────────────────────
    def test_gmail_thread_show(self):
        self.assertEqual(_classify("show the thread"), "gmail_thread")

    def test_gmail_thread_conversation(self):
        self.assertEqual(_classify("open the conversation"), "gmail_thread")

    # ── gmail_summarize ───────────────────────────────────────────────────
    def test_gmail_summarize_email(self):
        self.assertEqual(_classify("summarize this email"), "gmail_summarize")

    def test_gmail_summarize_tldr(self):
        self.assertEqual(_classify("tldr"), "gmail_summarize")

    def test_gmail_summarize_thread(self):
        self.assertEqual(_classify("summarize the thread"), "gmail_summarize")

    # ── gmail_list_category ───────────────────────────────────────────────
    def test_gmail_promotions(self):
        self.assertEqual(_classify("show promotions"), "gmail_list_category")

    def test_gmail_spam(self):
        self.assertEqual(_classify("check spam folder"), "gmail_list_category")

    def test_gmail_social(self):
        self.assertEqual(_classify("show social emails"), "gmail_list_category")

    # ── gmail_archive ─────────────────────────────────────────────────────
    def test_gmail_archive_those(self):
        self.assertEqual(_classify("archive those emails"), "gmail_archive")

    def test_gmail_archive_promos(self):
        self.assertEqual(_classify("archive all promotions"), "gmail_archive")

    # ── gmail_trash ───────────────────────────────────────────────────────
    def test_gmail_trash_these(self):
        self.assertEqual(_classify("trash these emails"), "gmail_trash")

    def test_gmail_delete_emails(self):
        self.assertEqual(_classify("delete these emails"), "gmail_trash")

    # ── gmail_mark_read / unread ──────────────────────────────────────────
    def test_gmail_mark_read(self):
        self.assertEqual(_classify("mark as read"), "gmail_mark_read")

    def test_gmail_mark_unread(self):
        self.assertEqual(_classify("mark as unread"), "gmail_mark_unread")

    # ── gmail_triage ──────────────────────────────────────────────────────
    def test_gmail_triage_basic(self):
        self.assertEqual(_classify("triage my inbox"), "gmail_triage")

    def test_gmail_triage_needs_reply(self):
        self.assertEqual(_classify("which emails need my reply"), "gmail_triage")

    def test_gmail_triage_action_needed(self):
        self.assertEqual(_classify("what needs my attention today"), "gmail_triage")

    # ── gmail_draft_reply ─────────────────────────────────────────────────
    def test_gmail_draft_reply_basic(self):
        self.assertEqual(_classify("draft a reply"), "gmail_draft_reply")

    def test_gmail_draft_reply_saying(self):
        self.assertEqual(_classify("reply saying I'll review it tonight"), "gmail_draft_reply")

    # ── gmail_compose ─────────────────────────────────────────────────────
    def test_gmail_compose(self):
        self.assertEqual(_classify("compose an email to Priya"), "gmail_compose")

    def test_gmail_compose_write(self):
        self.assertEqual(_classify("write a new email to the team"), "gmail_compose")

    # ── gmail_show_draft ─────────────────────────────────────────────────
    def test_gmail_show_draft(self):
        self.assertEqual(_classify("show the draft"), "gmail_show_draft")

    def test_gmail_preview_draft(self):
        self.assertEqual(_classify("preview my draft"), "gmail_show_draft")

    # ── gmail_send_draft ─────────────────────────────────────────────────
    def test_gmail_send_draft(self):
        self.assertEqual(_classify("send the draft"), "gmail_send_draft")

    def test_gmail_send_it(self):
        self.assertEqual(_classify("send it"), "gmail_send_draft")

    # ── gmail_cancel_draft ────────────────────────────────────────────────
    def test_gmail_cancel_draft(self):
        self.assertEqual(_classify("cancel the draft"), "gmail_cancel_draft")

    def test_gmail_discard_draft(self):
        self.assertEqual(_classify("discard the draft"), "gmail_cancel_draft")

    # ── gmail_rewrite_draft ───────────────────────────────────────────────
    def test_gmail_rewrite_shorter(self):
        self.assertEqual(_classify("make the draft shorter"), "gmail_rewrite_draft")

    def test_gmail_rewrite_formal(self):
        self.assertEqual(_classify("rewrite it more formally"), "gmail_rewrite_draft")

    # ── gmail_update_subject ─────────────────────────────────────────────
    def test_gmail_update_subject(self):
        self.assertEqual(_classify("update the subject line"), "gmail_update_subject")

    def test_gmail_better_subject(self):
        self.assertEqual(_classify("give me a better subject"), "gmail_update_subject")

    # ── gmail_add_cc / bcc ────────────────────────────────────────────────
    def test_gmail_add_cc(self):
        self.assertEqual(_classify("add cc Priya"), "gmail_add_cc")

    def test_gmail_add_bcc(self):
        self.assertEqual(_classify("add bcc me"), "gmail_add_bcc")

    # ── attachment intents ────────────────────────────────────────────────
    def test_gmail_list_attachments(self):
        self.assertEqual(_classify("show attachments"), "gmail_list_attachments")

    def test_gmail_save_attachment(self):
        self.assertEqual(_classify("download the PDF"), "gmail_save_attachment")

    def test_gmail_attach_file(self):
        self.assertEqual(_classify("attach the report PDF to this draft"), "gmail_attach_file")

    def test_gmail_remove_attachment(self):
        self.assertEqual(_classify("remove the attachment"), "gmail_remove_attachment")

    def test_gmail_summarize_attachment(self):
        self.assertEqual(_classify("summarize the attached PDF"), "gmail_summarize_attachment")

    # ── gmail_list_drafts / open_draft / delete_draft ─────────────────────
    def test_gmail_list_drafts(self):
        self.assertEqual(_classify("show my drafts"), "gmail_list_drafts")

    def test_gmail_open_draft_number(self):
        self.assertEqual(_classify("open draft 2"), "gmail_open_draft")

    def test_gmail_open_draft_first(self):
        self.assertEqual(_classify("switch to the first draft"), "gmail_open_draft")

    def test_gmail_delete_draft_number(self):
        self.assertEqual(_classify("delete draft 1"), "gmail_delete_draft")

    # ── gmail_schedule_send ───────────────────────────────────────────────
    def test_gmail_schedule_send_tomorrow(self):
        self.assertEqual(_classify("send this tomorrow morning"), "gmail_schedule_send")

    def test_gmail_schedule_send_friday(self):
        self.assertEqual(_classify("send it on Friday at 9 AM"), "gmail_schedule_send")

    def test_gmail_schedule_later(self):
        self.assertEqual(_classify("schedule send for Monday"), "gmail_schedule_send")

    # ── gmail_list_scheduled / cancel_scheduled / reschedule ─────────────
    def test_gmail_list_scheduled(self):
        self.assertEqual(_classify("show my scheduled emails"), "gmail_list_scheduled")

    def test_gmail_cancel_scheduled(self):
        self.assertEqual(_classify("cancel the scheduled send"), "gmail_cancel_scheduled_send")

    def test_gmail_cancel_scheduled_draft(self):
        self.assertEqual(_classify("cancel that scheduled draft"), "gmail_cancel_scheduled_send")

    # ── gmail_followup_reminder ───────────────────────────────────────────
    def test_gmail_followup_remind_me(self):
        self.assertEqual(_classify("remind me to follow up on this"), "gmail_followup_reminder")

    def test_gmail_followup_if_no_reply(self):
        self.assertEqual(_classify("remind me if no reply in 3 days"), "gmail_followup_reminder")

    def test_gmail_followup_set_reminder(self):
        self.assertEqual(_classify("set a follow-up for Friday"), "gmail_followup_reminder")

    # ── gmail_list_followups / cancel_followup ────────────────────────────
    def test_gmail_list_followups(self):
        self.assertEqual(_classify("show my follow-ups"), "gmail_list_followups")

    def test_gmail_cancel_followup(self):
        self.assertEqual(_classify("cancel the follow-up reminder"), "gmail_cancel_followup")

    # ── gmail_thread_intel ────────────────────────────────────────────────
    def test_gmail_thread_intel_action_items(self):
        self.assertEqual(_classify("action items"), "gmail_thread_intel")

    def test_gmail_thread_intel_what_changed(self):
        self.assertEqual(_classify("what changed in the last reply"), "gmail_thread_intel")

    def test_gmail_thread_intel_decisions(self):
        self.assertEqual(_classify("decisions in this thread"), "gmail_thread_intel")

    def test_gmail_thread_intel_do_i_owe(self):
        self.assertEqual(_classify("do I owe a reply"), "gmail_thread_intel")

    # ── gmail_forward ─────────────────────────────────────────────────────
    def test_gmail_forward_to(self):
        self.assertEqual(_classify("forward this to Rahul"), "gmail_forward")

    def test_gmail_fwd(self):
        self.assertEqual(_classify("fwd it to the team"), "gmail_forward")

    # ── gmail_extract_tasks ───────────────────────────────────────────────
    def test_gmail_extract_tasks_turn_into(self):
        self.assertEqual(_classify("turn this email into tasks"), "gmail_extract_tasks")

    def test_gmail_extract_tasks_extract_action(self):
        self.assertEqual(_classify("extract action items from this email"), "gmail_extract_tasks")

    def test_gmail_extract_tasks_extract_deadlines(self):
        self.assertEqual(_classify("extract the deadlines"), "gmail_extract_tasks")

    def test_gmail_extract_tasks_what_deadlines(self):
        self.assertEqual(_classify("what deadlines are mentioned here"), "gmail_extract_tasks")

    def test_gmail_extract_tasks_what_dates(self):
        self.assertEqual(_classify("what dates are in this thread"), "gmail_extract_tasks")

    def test_gmail_extract_tasks_make_checklist(self):
        self.assertEqual(_classify("make a follow-up checklist"), "gmail_extract_tasks")

    def test_gmail_extract_tasks_summarize_as_tasks(self):
        self.assertEqual(_classify("summarize this email as tasks"), "gmail_extract_tasks")

    def test_gmail_extract_tasks_what_followups(self):
        self.assertEqual(_classify("what follow-ups should I put on my list"), "gmail_extract_tasks")

    def test_gmail_extract_tasks_task_list(self):
        self.assertEqual(_classify("make a task list"), "gmail_extract_tasks")

    def test_gmail_extract_tasks_turn_thread(self):
        self.assertEqual(_classify("turn this thread into a checklist"), "gmail_extract_tasks")

    # ── gmail_tasks_save ─────────────────────────────────────────────────
    def test_gmail_tasks_save_to_obsidian(self):
        self.assertEqual(_classify("save tasks to Obsidian"), "gmail_tasks_save")

    def test_gmail_tasks_save_those(self):
        self.assertEqual(_classify("save those action items"), "gmail_tasks_save")

    def test_gmail_tasks_save_export(self):
        self.assertEqual(_classify("export the extracted tasks"), "gmail_tasks_save")

    def test_gmail_tasks_save_add_to_notes(self):
        self.assertEqual(_classify("add tasks to my notes"), "gmail_tasks_save")

    # ── gmail_tasks_remind ────────────────────────────────────────────────
    def test_gmail_tasks_remind_create(self):
        self.assertEqual(_classify("create reminders for those action items"), "gmail_tasks_remind")

    def test_gmail_tasks_remind_set_for_tasks(self):
        self.assertEqual(_classify("set reminders for the deadlines"), "gmail_tasks_remind")

    def test_gmail_tasks_remind_remind_me_about(self):
        self.assertEqual(_classify("remind me about those action items"), "gmail_tasks_remind")

    # ── gmail_filter_build / apply / cancel / list ────────────────────────
    def test_gmail_filter_build_always_label(self):
        self.assertEqual(_classify("always label invoices as Finance"), "gmail_filter_build")

    def test_gmail_filter_build_create_rule(self):
        self.assertEqual(_classify("create a rule to archive newsletters"), "gmail_filter_build")

    def test_gmail_filter_apply(self):
        self.assertEqual(_classify("create that rule"), "gmail_filter_apply")

    def test_gmail_filter_cancel(self):
        self.assertEqual(_classify("cancel the filter"), "gmail_filter_cancel")

    def test_gmail_filter_list(self):
        self.assertEqual(_classify("show my rules"), "gmail_filter_list")


# ===========================================================================
# 2. COLLISION / BOUNDARY TESTS — intent X must beat intent Y
# ===========================================================================

class TestGmailNLUCollisions(unittest.TestCase):
    """Explicit collision tests. Each verifies that the correct intent fires
    when two patterns could compete."""

    # ── Phase 17 vs Phase 15 (extract vs thread-intel) ───────────────────
    def test_extract_beats_thread_intel_for_extract_keyword(self):
        # "extract action items" should route to gmail_extract_tasks
        # Phase 17 extract pattern must precede Phase 15 action_items pattern
        result = _classify("extract action items from this email")
        self.assertEqual(result, "gmail_extract_tasks",
            "extract + action_items must route to gmail_extract_tasks, not gmail_thread_intel")

    def test_extract_deadlines_beats_thread_intel(self):
        result = _classify("extract all deadlines from this thread")
        self.assertEqual(result, "gmail_extract_tasks")

    def test_bare_action_items_still_thread_intel(self):
        # Without "extract" verb, "action items" → gmail_thread_intel (Phase 15 fast path)
        result = _classify("action items in this email")
        self.assertEqual(result, "gmail_thread_intel",
            "bare 'action items' should still route to gmail_thread_intel")

    def test_summarize_as_tasks_beats_summarize(self):
        # "summarize ... as tasks" → gmail_extract_tasks, NOT gmail_summarize
        result = _classify("summarize this email as action items")
        self.assertEqual(result, "gmail_extract_tasks",
            "summarize-as-tasks must beat bare gmail_summarize")

    # ── Phase 17 tasks_save vs obsidian_daily ────────────────────────────
    def test_tasks_save_to_daily_note_beats_obsidian_daily(self):
        result = _classify("add tasks to my daily note")
        self.assertEqual(result, "gmail_tasks_save",
            "add tasks to daily note must route to gmail_tasks_save, not obsidian_daily")

    def test_save_checklist_to_daily_note_beats_obsidian(self):
        result = _classify("save the checklist to daily note")
        self.assertEqual(result, "gmail_tasks_save")

    def test_bare_add_to_daily_note_goes_obsidian(self):
        # Without tasks/checklist anchor, "add to daily note" → obsidian_daily
        result = _classify("add this to my daily note")
        self.assertEqual(result, "obsidian_daily",
            "bare 'add to daily note' without task anchor should be obsidian_daily")

    # ── Phase 17 tasks_remind vs Phase 11 followup_reminder ─────────────
    def test_tasks_remind_beats_followup_reminder_for_those_items(self):
        result = _classify("create reminders for those action items")
        self.assertEqual(result, "gmail_tasks_remind",
            "create reminders for those action items → gmail_tasks_remind not gmail_followup_reminder")

    def test_set_reminders_each_beats_followup(self):
        result = _classify("set reminders for each of those tasks")
        self.assertEqual(result, "gmail_tasks_remind")

    def test_bare_remind_me_stays_followup_reminder(self):
        # "remind me about this thread in 3 days" → followup_reminder (no tasks anchor)
        result = _classify("remind me about this thread in 3 days")
        self.assertEqual(result, "gmail_followup_reminder",
            "bare 'remind me' without action-items/deadlines anchor → gmail_followup_reminder")

    def test_bare_set_reminder_stays_followup(self):
        result = _classify("set a reminder for Friday")
        self.assertEqual(result, "gmail_followup_reminder",
            "bare 'set a reminder' without tasks anchor → gmail_followup_reminder")

    # ── gmail_cancel_draft vs gmail_filter_cancel vs gmail_cancel ─────────
    def test_cancel_draft_not_filter_cancel(self):
        result = _classify("cancel the draft")
        self.assertEqual(result, "gmail_cancel_draft",
            "cancel draft must route to gmail_cancel_draft, not gmail_filter_cancel")

    def test_cancel_filter_not_cancel_draft(self):
        result = _classify("cancel rule creation")
        self.assertEqual(result, "gmail_filter_cancel",
            "cancel rule/filter must route to gmail_filter_cancel")

    def test_cancel_followup_beats_cancel_scheduled(self):
        # "cancel the follow-up" must beat gmail_cancel_scheduled_send
        result = _classify("cancel the follow-up reminder")
        self.assertEqual(result, "gmail_cancel_followup")

    # ── gmail_send_draft vs gmail_schedule_send ───────────────────────────
    def test_send_now_beats_schedule_send(self):
        result = _classify("send it")
        self.assertEqual(result, "gmail_send_draft",
            "bare 'send it' must route to gmail_send_draft, not gmail_schedule_send")

    def test_send_tomorrow_is_schedule(self):
        result = _classify("send it tomorrow morning")
        self.assertEqual(result, "gmail_schedule_send",
            "send + temporal indicator → gmail_schedule_send")

    def test_send_draft_keyword_is_send_draft(self):
        result = _classify("send the draft")
        self.assertEqual(result, "gmail_send_draft")

    # ── gmail_forward vs gmail_compose ───────────────────────────────────
    def test_forward_beats_compose(self):
        result = _classify("forward this to Rahul")
        self.assertEqual(result, "gmail_forward",
            "forward must beat gmail_compose")

    # ── gmail_filter_build vs gmail_archive ───────────────────────────────
    def test_always_archive_is_filter_not_bare_archive(self):
        result = _classify("always archive newsletters")
        self.assertEqual(result, "gmail_filter_build",
            "'always archive' → gmail_filter_build, not gmail_archive")

    def test_bare_archive_emails_is_archive(self):
        result = _classify("archive those emails")
        self.assertEqual(result, "gmail_archive",
            "bare 'archive those emails' without 'always' → gmail_archive")

    # ── gmail_filter_apply vs gmail_filter_build ──────────────────────────
    def test_create_that_rule_is_filter_apply(self):
        result = _classify("create that rule")
        self.assertEqual(result, "gmail_filter_apply",
            "'create that rule' → gmail_filter_apply, not gmail_filter_build")

    def test_create_a_rule_for_is_filter_build(self):
        result = _classify("create a rule to archive newsletters")
        self.assertEqual(result, "gmail_filter_build",
            "'create a rule to...' → gmail_filter_build")

    # ── gmail_thread_intel early guard vs git_status/web_search ──────────
    def test_what_changed_in_reply_beats_git_status(self):
        result = _classify("what changed in the last reply")
        self.assertEqual(result, "gmail_thread_intel",
            "'what changed in the last reply' must beat git_status 'what changed'")

    def test_what_changed_in_code_is_not_gmail(self):
        result = _classify("what changed in the code yesterday")
        self.assertNotEqual(result, "gmail_thread_intel",
            "'what changed in the code' should NOT route to gmail_thread_intel")

    # ── gmail_delete_draft vs gmail_trash ─────────────────────────────────
    def test_delete_draft_1_is_delete_draft(self):
        result = _classify("delete draft 1")
        self.assertEqual(result, "gmail_delete_draft",
            "delete draft N → gmail_delete_draft, not gmail_trash")

    def test_delete_emails_is_trash(self):
        result = _classify("delete those emails")
        self.assertEqual(result, "gmail_trash",
            "delete emails → gmail_trash, not gmail_delete_draft")

    # ── gmail_list_scheduled vs gmail_list_drafts ─────────────────────────
    def test_list_scheduled_not_list_drafts(self):
        result = _classify("show scheduled emails")
        self.assertEqual(result, "gmail_list_scheduled")

    def test_list_drafts_not_list_scheduled(self):
        result = _classify("show my drafts")
        self.assertEqual(result, "gmail_list_drafts")

    # ── gmail_summarize vs gmail_summarize_attachment ─────────────────────
    def test_summarize_pdf_is_attachment(self):
        result = _classify("summarize the attached PDF")
        self.assertEqual(result, "gmail_summarize_attachment")

    def test_summarize_email_is_summarize(self):
        result = _classify("summarize this email")
        self.assertEqual(result, "gmail_summarize")

    # ── attach_file vs rewrite_draft (both have "add/include") ───────────
    def test_attach_file_beats_rewrite(self):
        result = _classify("attach the report PDF to this draft")
        self.assertEqual(result, "gmail_attach_file",
            "attach file must beat gmail_rewrite_draft's 'add to draft' pattern")

    def test_add_mention_in_draft_is_rewrite(self):
        result = _classify("add a thank you note in the draft")
        self.assertEqual(result, "gmail_rewrite_draft")


# ===========================================================================
# 3. KNOWN GAPS — inputs that are expected to route to gmail_extract_tasks
#    but currently FAIL due to missing pattern coverage.
#    These tests drive the next set of pattern fixes.
# ===========================================================================

class TestGmailNLUKnownGaps(unittest.TestCase):
    """Expose pattern gaps identified during Phase A audit.
    All of these should be gmail_extract_tasks.
    These will FAIL until patterns are patched in adwi_cli.py."""

    def test_gap_create_checklist_from_email(self):
        # GAP-1: "create a checklist from this email" — no pattern matches "create...checklist"
        result = _classify("create a checklist from this email")
        self.assertEqual(result, "gmail_extract_tasks",
            "GAP-1: 'create a checklist from this email' should route to gmail_extract_tasks")

    def test_gap_build_checklist_from_thread(self):
        # GAP-2: similar gap with "build...checklist"
        result = _classify("build a checklist from this thread")
        self.assertEqual(result, "gmail_extract_tasks",
            "GAP-2: 'build a checklist from this thread' should route to gmail_extract_tasks")

    def test_gap_make_todo_list(self):
        # GAP-3: "todo list" is not in the task_list pattern (only "task list")
        result = _classify("make a todo list from this email")
        self.assertEqual(result, "gmail_extract_tasks",
            "GAP-3: 'make a todo list from this email' should route to gmail_extract_tasks")

    def test_gap_write_todo_list(self):
        # GAP-4: "write" verb not in the make/create/build alternation
        result = _classify("write a todo list for this thread")
        self.assertEqual(result, "gmail_extract_tasks",
            "GAP-4: 'write a todo list for this thread' should route to gmail_extract_tasks")

    def test_gap_convert_email_to_tasks(self):
        # GAP-5: "convert" not in the turn/into pattern
        result = _classify("convert this email to tasks")
        self.assertEqual(result, "gmail_extract_tasks",
            "GAP-5: 'convert this email to tasks' should route to gmail_extract_tasks")

    def test_gap_generate_task_list(self):
        # GAP-6: "generate" verb not in the make/create/build alternation
        result = _classify("generate a task list from this thread")
        self.assertEqual(result, "gmail_extract_tasks",
            "GAP-6: 'generate a task list from this thread' should route to gmail_extract_tasks")

    def test_gap_extract_dates_from_email(self):
        # GAP-7: "extract dates" — "dates" not in extract pattern (only "due dates")
        result = _classify("extract dates from this email")
        self.assertEqual(result, "gmail_extract_tasks",
            "GAP-7: 'extract dates from this email' should route to gmail_extract_tasks")


# ===========================================================================
# 4. EDGE CASES & ROBUSTNESS
# ===========================================================================

class TestGmailNLUEdgeCases(unittest.TestCase):
    """Typos, multi-clause inputs, short inputs, and non-Gmail sentences."""

    def test_typo_summerize(self):
        # Typo: "summerize" — should NOT incorrectly match gmail_summarize
        result = _classify("summerize this email")
        # Acceptable: either None or something non-gmail (regex won't match typo)
        self.assertNotEqual(result, "gmail_summarize")

    def test_gmail_with_preamble(self):
        # Intent buried after preamble
        result = _classify("hey, can you summarize this email for me please?")
        self.assertEqual(result, "gmail_summarize")

    def test_schedule_with_time_and_day(self):
        result = _classify("send this on Monday at 9 AM")
        self.assertEqual(result, "gmail_schedule_send")

    def test_open_draft_by_name(self):
        result = _classify("open the Rahul draft")
        self.assertEqual(result, "gmail_open_draft")

    def test_delete_old_draft(self):
        result = _classify("cancel that old draft")
        self.assertEqual(result, "gmail_delete_draft")

    def test_not_gmail_for_general_task(self):
        # Generic task management question not in Gmail context
        result = _classify("what's on my todo list")
        self.assertNotEqual(result, "gmail_extract_tasks",
            "'what's on my todo list' should NOT route to gmail_extract_tasks")

    def test_not_gmail_for_obsidian_note(self):
        result = _classify("open today's obsidian note")
        self.assertNotEqual(result, "gmail_extract_tasks")

    def test_short_send_now(self):
        result = _classify("send now")
        self.assertEqual(result, "gmail_send_draft")

    def test_go_ahead_send(self):
        result = _classify("go ahead and send it")
        self.assertEqual(result, "gmail_send_draft")

    def test_extract_decisions_not_thread_intel(self):
        # "extract decisions" → gmail_extract_tasks even though "decisions" is also in thread_intel
        result = _classify("extract all decisions from this thread")
        self.assertEqual(result, "gmail_extract_tasks")

    def test_any_attachments_query(self):
        result = _classify("are there any attachments?")
        self.assertEqual(result, "gmail_list_attachments")

    def test_cancel_scheduled_not_cancel_draft(self):
        result = _classify("cancel scheduled email")
        self.assertEqual(result, "gmail_cancel_scheduled_send")

    def test_mark_github_read_is_filter_not_mark_read(self):
        # "automatically mark github notifications as read" → gmail_filter_build
        result = _classify("automatically mark github notifications as read")
        self.assertEqual(result, "gmail_filter_build")

    def test_mark_the_email_as_read_is_mark_read(self):
        # "mark the email as read" (no always/auto prefix) → gmail_mark_read
        result = _classify("mark the email as read")
        self.assertEqual(result, "gmail_mark_read")

    def test_bcc_on_draft(self):
        result = _classify("bcc Rahul on this draft")
        self.assertEqual(result, "gmail_add_bcc")

    def test_cc_on_email(self):
        result = _classify("cc Priya on this email")
        self.assertEqual(result, "gmail_add_cc")


# ===========================================================================
# 5. UNIT TESTS — _parse_task_extraction
# ===========================================================================

_parse_task_extraction = _load_parse_task_extraction()


class TestParseTaskExtraction(unittest.TestCase):
    """Unit tests for the pure _parse_task_extraction() function."""

    def _full_extraction(self, text: str, subject: str = "Test") -> dict:
        return _parse_task_extraction(text, "full", subject)

    def test_full_mode_action_items(self):
        raw = "ACTION ITEMS:\n- Review the proposal\n- Send feedback by Friday\n"
        result = self._full_extraction(raw)
        self.assertEqual(result["action_items"], ["Review the proposal", "Send feedback by Friday"])
        self.assertEqual(result["deadlines"], [])

    def test_full_mode_deadlines_with_date(self):
        raw = "DEADLINES:\n- Submit report | due: June 20\n- Pay invoice | due: June 30\n"
        result = self._full_extraction(raw)
        self.assertEqual(len(result["deadlines"]), 2)
        self.assertEqual(result["deadlines"][0]["item"], "Submit report")
        self.assertEqual(result["deadlines"][0]["date_str"], "June 20")
        self.assertEqual(result["deadlines"][1]["date_str"], "June 30")

    def test_full_mode_decisions(self):
        raw = "DECISIONS:\n- Approved Q3 budget\n- Switched to Notion\n"
        result = self._full_extraction(raw)
        self.assertEqual(result["decisions"], ["Approved Q3 budget", "Switched to Notion"])

    def test_full_mode_asks(self):
        raw = "ASKS:\n- Can you review the deck?\n- Please confirm attendance\n"
        result = self._full_extraction(raw)
        self.assertEqual(result["asks"], ["Can you review the deck?", "Please confirm attendance"])

    def test_full_mode_none_noise_filtered(self):
        raw = "ACTION ITEMS:\n- None found.\nDECISIONS:\n- N/A\n"
        result = self._full_extraction(raw)
        self.assertEqual(result["action_items"], [])
        self.assertEqual(result["decisions"], [])

    def test_full_mode_short_items_filtered(self):
        # Items with <= 3 chars should be filtered
        raw = "ACTION ITEMS:\n- ok\n- Review the full proposal\n"
        result = self._full_extraction(raw)
        self.assertEqual(result["action_items"], ["Review the full proposal"])

    def test_action_items_mode(self):
        raw = "- First task\n- Second task\n- Third task\n"
        result = _parse_task_extraction(raw, "action_items", "Test")
        self.assertEqual(len(result["action_items"]), 3)
        self.assertEqual(result["decisions"], [])

    def test_deadlines_mode(self):
        raw = "- Submit PR | due: June 15\n- Deploy to prod | due: June 22\n"
        result = _parse_task_extraction(raw, "deadlines", "Deploy checklist")
        self.assertEqual(len(result["deadlines"]), 2)
        self.assertEqual(result["deadlines"][0]["date_str"], "June 15")

    def test_decisions_mode(self):
        raw = "- Go with Option A\n- Skip Phase 2\n"
        result = _parse_task_extraction(raw, "decisions", "Meeting notes")
        self.assertEqual(result["decisions"], ["Go with Option A", "Skip Phase 2"])

    def test_asks_mode(self):
        raw = "- Please send the contract\n- Can you join Thursday?\n"
        result = _parse_task_extraction(raw, "asks", "Request email")
        self.assertEqual(len(result["asks"]), 2)

    def test_source_subject_preserved(self):
        result = _parse_task_extraction("ACTION ITEMS:\n- Do something\n", "full", "My Email")
        self.assertEqual(result["source_subject"], "My Email")

    def test_mode_preserved(self):
        result = _parse_task_extraction("- Do A\n- Do B\n", "action_items", "S")
        self.assertEqual(result["mode"], "action_items")

    def test_deadline_without_date_str(self):
        raw = "DEADLINES:\n- Submit something\n"
        result = self._full_extraction(raw)
        # deadline without | due: should have empty date_str
        if result["deadlines"]:
            self.assertEqual(result["deadlines"][0]["date_str"], "")

    def test_star_bullets_also_work(self):
        raw = "ACTION ITEMS:\n* Schedule meeting\n* Send agenda\n"
        result = self._full_extraction(raw)
        self.assertEqual(len(result["action_items"]), 2)

    def test_empty_input_returns_empty_lists(self):
        result = self._full_extraction("")
        self.assertEqual(result["action_items"], [])
        self.assertEqual(result["deadlines"], [])
        self.assertEqual(result["decisions"], [])
        self.assertEqual(result["asks"], [])


# ===========================================================================
# 6. UNIT TESTS — _filter_criteria_to_query
# ===========================================================================

_filter_criteria_to_query = _load_filter_criteria_to_query()


class TestFilterCriteriaToQuery(unittest.TestCase):
    """Unit tests for _filter_criteria_to_query()."""

    def test_from_only(self):
        q = _filter_criteria_to_query({"from_": "noreply@github.com", "to": "", "subject": "", "query": ""})
        self.assertEqual(q, "from:noreply@github.com")

    def test_subject_only(self):
        q = _filter_criteria_to_query({"from_": "", "to": "", "subject": "invoice", "query": ""})
        self.assertEqual(q, "subject:invoice")

    def test_from_and_subject(self):
        q = _filter_criteria_to_query({"from_": "@amazon.com", "to": "", "subject": "order", "query": ""})
        self.assertIn("from:@amazon.com", q)
        self.assertIn("subject:order", q)

    def test_raw_query(self):
        q = _filter_criteria_to_query({"from_": "", "to": "", "subject": "", "query": "category:promotions"})
        self.assertEqual(q, "category:promotions")

    def test_all_empty(self):
        q = _filter_criteria_to_query({"from_": "", "to": "", "subject": "", "query": ""})
        self.assertEqual(q, "")

    def test_to_field(self):
        q = _filter_criteria_to_query({"from_": "", "to": "me@example.com", "subject": "", "query": ""})
        self.assertEqual(q, "to:me@example.com")

    def test_combined_order(self):
        # from comes before subject
        q = _filter_criteria_to_query({"from_": "a@b.com", "to": "", "subject": "foo", "query": "label:X"})
        parts = q.split()
        self.assertEqual(parts[0], "from:a@b.com")
        self.assertEqual(parts[1], "subject:foo")
        self.assertEqual(parts[2], "label:X")


# ===========================================================================
# 7. UNIT TESTS — _thread_latest_message, _thread_build_context
# ===========================================================================

_thread_helpers = _load_thread_helpers()
_thread_latest_message = _thread_helpers["_thread_latest_message"]
_thread_build_context  = _thread_helpers["_thread_build_context"]


class TestThreadHelpers(unittest.TestCase):

    def _make_thread(self, *bodies: str) -> dict:
        return {
            "messages": [
                {"from": f"sender{i}@x.com", "date": f"2026-06-{i+1:02d}", "body": b}
                for i, b in enumerate(bodies)
            ]
        }

    def test_latest_message_returns_last(self):
        thread = self._make_thread("first", "second", "third")
        msg = _thread_latest_message(thread)
        self.assertEqual(msg["body"], "third")

    def test_latest_message_empty_thread(self):
        self.assertIsNone(_thread_latest_message({"messages": []}))

    def test_latest_message_missing_key(self):
        self.assertIsNone(_thread_latest_message({}))

    def test_build_context_single_message(self):
        thread = self._make_thread("Hello there")
        ctx = _thread_build_context(thread)
        self.assertIn("Hello there", ctx)
        self.assertIn("sender0@x.com", ctx)

    def test_build_context_chronological_order(self):
        # Output is chronological (oldest first) — iteration is newest-first for
        # budget allocation, but parts.reverse() restores chronological order.
        thread = self._make_thread("first msg", "latest msg")
        ctx = _thread_build_context(thread)
        pos_first  = ctx.index("first msg")
        pos_latest = ctx.index("latest msg")
        self.assertLess(pos_first, pos_latest,
            "chronological order: oldest message should appear before newest")

    def test_build_context_budget_truncation(self):
        # With 3 messages and a tight budget, the oldest is omitted entirely.
        # The sentinel "[earlier messages omitted]" marks that at least one
        # message was dropped rather than truncated.
        thread = self._make_thread("first msg body here", "second msg body here", "third msg here")
        ctx = _thread_build_context(thread, max_chars=80)
        self.assertIn("earlier messages omitted", ctx)

    def test_build_context_empty_thread(self):
        self.assertEqual(_thread_build_context({"messages": []}), "")

    def test_build_context_separator(self):
        thread = self._make_thread("A", "B")
        ctx = _thread_build_context(thread)
        self.assertIn("---", ctx)


# ===========================================================================
# 8. UNIT TESTS — _resolve_schedule_time
# ===========================================================================

_sched_ns = _load_schedule_helpers()
_resolve_schedule_time = _sched_ns["_resolve_schedule_time"]


class TestResolveScheduleTime(unittest.TestCase):
    """Tests for the date/time parser used in Phase 10 schedule-send."""

    def _dt(self, text: str):
        dt, label = _resolve_schedule_time(text)
        return dt, label

    def test_in_minutes(self):
        dt, label = self._dt("in 30 minutes")
        self.assertIsNotNone(dt)
        diff = dt - datetime.now()
        self.assertAlmostEqual(diff.total_seconds() / 60, 30, delta=1)

    def test_in_hours(self):
        dt, label = self._dt("in 2 hours")
        self.assertIsNotNone(dt)
        diff = dt - datetime.now()
        self.assertAlmostEqual(diff.total_seconds() / 3600, 2, delta=0.05)

    def test_tomorrow_defaults_9am(self):
        dt, label = self._dt("tomorrow")
        self.assertIsNotNone(dt)
        self.assertEqual(dt.hour, 9)
        tomorrow = (datetime.now() + timedelta(days=1)).date()
        self.assertEqual(dt.date(), tomorrow)

    def test_tomorrow_morning(self):
        dt, label = self._dt("tomorrow morning")
        self.assertIsNotNone(dt)
        self.assertEqual(dt.hour, 9)

    def test_tomorrow_afternoon(self):
        dt, label = self._dt("tomorrow afternoon")
        self.assertIsNotNone(dt)
        self.assertEqual(dt.hour, 14)

    def test_explicit_time_pm(self):
        dt, label = self._dt("at 3 PM")
        self.assertIsNotNone(dt)
        self.assertEqual(dt.hour, 15)

    def test_explicit_time_am(self):
        dt, label = self._dt("at 9 AM")
        self.assertIsNotNone(dt)
        self.assertEqual(dt.hour, 9)

    def test_explicit_time_ambiguous_small_hour(self):
        # "at 3" (no AM/PM, hour < 8) → 3 PM = 15
        dt, label = self._dt("at 3")
        self.assertIsNotNone(dt)
        self.assertEqual(dt.hour, 15)

    def test_friday_resolves_to_future_friday(self):
        dt, label = self._dt("Friday at 9 AM")
        self.assertIsNotNone(dt)
        self.assertEqual(dt.weekday(), 4)  # 4 = Friday

    def test_eod(self):
        dt, label = self._dt("EOD")
        self.assertIsNotNone(dt)
        self.assertEqual(dt.hour, 17)

    def test_next_week(self):
        dt, label = self._dt("next week")
        self.assertIsNotNone(dt)
        diff = dt - datetime.now()
        self.assertGreater(diff.days, 5)

    def test_unresolvable_returns_none_dt(self):
        dt, label = self._dt("sometime soon maybe")
        self.assertIsNone(dt)
        self.assertIsInstance(label, str)
        self.assertGreater(len(label), 0)  # error message present

    def test_label_is_string(self):
        dt, label = self._dt("tomorrow")
        self.assertIsInstance(label, str)
        self.assertGreater(len(label), 0)

    def test_in_a_day(self):
        dt, label = self._dt("in a day")
        self.assertIsNotNone(dt)
        diff = dt - datetime.now()
        self.assertAlmostEqual(diff.days, 1, delta=1)


if __name__ == "__main__":
    unittest.main(verbosity=2)
