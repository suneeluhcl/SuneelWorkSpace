"""
adwi/simlab/tests/test_nlu_regex.py

Focused regression tests for _REGEX_INTENTS in adwi/adwi_cli.py.
Tests every confirmed bug from the 2026-06-15 NLU eval master report
plus all Phase B new-intent patterns.

Run: python3 -m unittest adwi/simlab/tests/test_nlu_regex.py -v
"""
from __future__ import annotations

import re
import sys
import unittest
from pathlib import Path

# ---------------------------------------------------------------------------
# Bootstrap: extract _REGEX_INTENTS without importing the full adwi_cli module
# (avoids triggering Ollama, Qdrant, or hardware checks at test time).
# ---------------------------------------------------------------------------

_CLI_PATH = Path(__file__).resolve().parents[3] / "adwi" / "adwi_cli.py"

def _load_regex_intents():
    src = _CLI_PATH.read_text()
    start = src.index("_REGEX_INTENTS = [")
    end   = src.index("\ndef _regex_prefilter")
    ns: dict = {}
    exec(src[start:end], {"re": re}, ns)   # noqa: S102
    return ns["_REGEX_INTENTS"]

_REGEX_INTENTS = _load_regex_intents()


def _classify(text: str) -> str | None:
    """Replicate _regex_prefilter from adwi_cli.py."""
    for pattern, intent in _REGEX_INTENTS:
        if pattern.search(text):
            return intent
    return None


# ---------------------------------------------------------------------------
# Bug 1 — Status regex word-boundary false positives
# ---------------------------------------------------------------------------

class TestBug1StatusWordBoundary(unittest.TestCase):
    """Regex word boundaries prevent 'is'/'are'/'down'/'up' matching as
    substrings inside longer words (list→is, downloads→down, backup→up)."""

    def test_list_files_downloads_no_status(self):
        # Previously "l[is]t files...down[loads]" triggered status.
        result = _classify("list files in my downloads folder")
        self.assertNotEqual(result, "status",
            "'list files in my downloads folder' must NOT route to status")

    def test_downloads_word_no_status(self):
        result = _classify("this downloads fine")
        self.assertNotEqual(result, "status",
            "'this downloads fine' must NOT route to status via 'is'+'down'")

    def test_backup_up_no_status(self):
        # 'back[up]' contains 'up' — must not trigger status.
        result = _classify("is my backup recent")
        self.assertNotEqual(result, "status",
            "'backup' contains 'up' but must NOT trigger status")

    def test_real_status_is_running(self):
        self.assertEqual(_classify("is everything running"), "status")

    def test_real_status_are_services_up(self):
        self.assertEqual(_classify("are services up"), "status")

    def test_real_status_ollama_running(self):
        self.assertEqual(_classify("is ollama running"), "status")

    def test_real_status_is_down(self):
        self.assertEqual(_classify("is the stack down"), "status")


# ---------------------------------------------------------------------------
# Bug 2 — large_files must win over disk_usage
# ---------------------------------------------------------------------------

class TestBug2LargeFilesOrdering(unittest.TestCase):
    """disk_usage previously swallowed 'biggest/largest files' prompts because
    its regex appeared first with a superset pattern."""

    def test_biggest_files(self):
        self.assertEqual(_classify("what are the biggest files"), "large_files")

    def test_largest_files_home(self):
        self.assertEqual(_classify("largest files in my home directory"), "large_files")

    def test_top_n_biggest(self):
        self.assertEqual(_classify("top 10 biggest files"), "large_files")

    def test_huge_files(self):
        self.assertEqual(_classify("show me the huge files"), "large_files")

    def test_files_over_size(self):
        self.assertEqual(_classify("files over 500MB"), "large_files")

    def test_heaviest_on_disk_still_disk_usage(self):
        # "heaviest stuff on disk" — no 'files' object → disk_usage wins
        self.assertEqual(_classify("what's the heaviest stuff on disk"), "disk_usage")

    def test_disk_usage_still_works(self):
        self.assertEqual(_classify("how much disk space do I have"), "disk_usage")

    def test_check_disk(self):
        self.assertEqual(_classify("check my disk"), "disk_usage")

    def test_disk_analysis(self):
        self.assertEqual(_classify("disk space analysis"), "disk_usage")


# ---------------------------------------------------------------------------
# Bug 3 — self_heal must beat status for service-error prompts
# ---------------------------------------------------------------------------

class TestBug3SelfHealBeforeStatus(unittest.TestCase):
    """Status regex fired first on 'docker is not working' because self_heal
    appeared after it and only handled verb-first ordering."""

    def test_docker_not_working_repair(self):
        # Subject-first ordering: docker (subject) + not working (verb)
        self.assertEqual(_classify("docker is not working repair"), "self_heal")

    def test_adwi_isnt_working(self):
        # "isn't" contraction variation
        self.assertEqual(_classify("adwi isn't working properly"), "self_heal")

    def test_ollama_is_broken(self):
        self.assertEqual(_classify("ollama is broken"), "self_heal")

    def test_fix_docker_service(self):
        # Verb-first: fix ... service
        self.assertEqual(_classify("fix the docker service"), "self_heal")

    def test_stack_crashing(self):
        self.assertEqual(_classify("the stack is crashing"), "self_heal")


# ---------------------------------------------------------------------------
# Bug 4 — obsidian_daily must not be swallowed by obsidian_search
# ---------------------------------------------------------------------------

class TestBug4ObsidianDailyGuard(unittest.TestCase):
    """obsidian_search regex '(open|read|show).{0,10}note' previously fired
    on daily-note queries before any obsidian_daily pattern existed."""

    def test_daily_note(self):
        self.assertEqual(_classify("read my daily note"), "obsidian_daily")

    def test_open_todays_note(self):
        self.assertEqual(_classify("open today's note"), "obsidian_daily")

    def test_obsidian_daily_explicit(self):
        self.assertEqual(_classify("open my obsidian daily"), "obsidian_daily")

    def test_obsidian_search_still_works(self):
        # Generic vault search must still reach obsidian_search
        self.assertIn(
            _classify("search my obsidian vault for meeting notes"),
            ("obsidian_search", "rag_search"),
        )

    def test_open_obsidian_notes_is_search(self):
        self.assertEqual(_classify("open my obsidian notes"), "obsidian_search")


# ---------------------------------------------------------------------------
# Bug 7 — git_status regex broadened
# ---------------------------------------------------------------------------

class TestBug7GitStatusBroadened(unittest.TestCase):
    """git_status only caught 'git <subcommand>' and 3 literal phrases;
    11 common git queries routed to chat/memory/disk."""

    def test_show_recent_commits(self):
        self.assertEqual(_classify("show recent commits"), "git_status")

    def test_uncommitted_changes(self):
        self.assertEqual(_classify("are there uncommitted changes"), "git_status")

    def test_current_branch(self):
        self.assertEqual(_classify("what's the current branch"), "git_status")

    def test_unstaged_changes(self):
        self.assertEqual(_classify("show unstaged changes"), "git_status")

    def test_is_repo_clean(self):
        self.assertEqual(_classify("is the repo clean"), "git_status")

    def test_git_stat(self):
        self.assertEqual(_classify("git stat"), "git_status")

    def test_staged_files(self):
        self.assertEqual(_classify("show staged files"), "git_status")

    def test_explicit_git_status_still_works(self):
        self.assertEqual(_classify("run git status"), "git_status")

    def test_git_log(self):
        self.assertEqual(_classify("git log"), "git_status")


# ---------------------------------------------------------------------------
# Phase B — New intent patterns
# ---------------------------------------------------------------------------

class TestPhaseB_Nightly(unittest.TestCase):
    def test_nightly_status(self):
        self.assertEqual(_classify("nightly status"), "nightly_status")

    def test_when_nightly_ran(self):
        self.assertEqual(_classify("when did nightly last run"), "nightly_status")

    def test_show_nightly_log(self):
        self.assertEqual(_classify("show nightly log"), "nightly_status")

    def test_run_nightly(self):
        self.assertEqual(_classify("run nightly"), "nightly_run")

    def test_trigger_nightly_maintenance(self):
        self.assertEqual(_classify("trigger nightly maintenance"), "nightly_run")


class TestPhaseB_ModelSwitching(unittest.TestCase):
    def test_what_model_am_i_using(self):
        self.assertEqual(_classify("what model am I using"), "model_status")

    def test_which_model_active(self):
        self.assertEqual(_classify("which model is active"), "model_status")

    def test_show_model_status(self):
        self.assertEqual(_classify("show model status"), "model_status")

    def test_switch_to_local_model(self):
        self.assertEqual(_classify("switch to local model"), "use_local")

    def test_use_local_llm(self):
        self.assertEqual(_classify("use local llm"), "use_local")

    def test_use_qwen(self):
        self.assertEqual(_classify("use qwen"), "use_local")

    def test_switch_to_cloud(self):
        self.assertEqual(_classify("switch to cloud"), "use_cloud")

    def test_use_gemini(self):
        self.assertEqual(_classify("use gemini"), "use_cloud")


class TestPhaseB_Voice(unittest.TestCase):
    def test_voice_input(self):
        self.assertEqual(_classify("listen to my voice input"), "voice_in")

    def test_start_voice_recording(self):
        self.assertEqual(_classify("start voice recording"), "voice_in")

    def test_text_to_speech(self):
        self.assertEqual(_classify("text to speech"), "voice_out")

    def test_read_this_aloud(self):
        self.assertEqual(_classify("read this aloud"), "voice_out")

    def test_say_out_loud(self):
        self.assertEqual(_classify("say this out loud"), "voice_out")


class TestPhaseB_BackupOps(unittest.TestCase):
    def test_backup_status(self):
        self.assertEqual(_classify("backup status"), "backup_status")

    def test_last_backup_time(self):
        self.assertEqual(_classify("when was the last backup"), "backup_status")

    def test_is_backup_recent(self):
        self.assertEqual(_classify("is my backup recent"), "backup_status")

    def test_show_backup_log(self):
        self.assertEqual(_classify("show backup log"), "backup_log")

    def test_backup_history(self):
        self.assertEqual(_classify("backup history"), "backup_log")


class TestPhaseB_FileOps(unittest.TestCase):
    def test_list_files_downloads(self):
        # This was the Bug1 victim; now correctly → file_list
        self.assertEqual(_classify("list files in my downloads folder"), "file_list")

    def test_ls_documents(self):
        self.assertEqual(_classify("ls my documents folder"), "file_list")

    def test_what_files_in_tmp(self):
        self.assertEqual(_classify("what files are in /tmp"), "file_list")

    def test_read_py_file(self):
        self.assertEqual(_classify("read adwi_cli.py"), "file_read")

    def test_show_contents(self):
        self.assertEqual(_classify("show me the contents of .gitignore"), "file_read")

    def test_search_for_files(self):
        self.assertEqual(_classify("search for python files in my workspace"), "file_search")

    def test_find_all_yaml(self):
        self.assertEqual(_classify("find all yaml files"), "file_search")

    def test_locate_config(self):
        self.assertEqual(_classify("find files named config.yaml"), "file_search")


class TestPhaseB_EvalTest(unittest.TestCase):
    def test_eval_routing(self):
        self.assertEqual(_classify("run routing tests"), "eval_routing")

    def test_test_adwi(self):
        self.assertEqual(_classify("run adwi tests"), "test_adwi")

    def test_eval_adwi(self):
        self.assertEqual(_classify("evaluate adwi performance"), "eval_adwi")


# ---------------------------------------------------------------------------
# Regressions — patterns that must not change after patching
# ---------------------------------------------------------------------------

class TestRegressions(unittest.TestCase):
    """Guard against fixes that accidentally break previously working routes."""

    def test_disk_usage_basic(self):
        self.assertEqual(_classify("check my disk"), "disk_usage")

    def test_disk_usage_how_much(self):
        self.assertEqual(_classify("how much disk space do I have"), "disk_usage")

    def test_disk_usage_storage(self):
        self.assertEqual(_classify("storage usage breakdown"), "disk_usage")

    def test_generate_image(self):
        self.assertEqual(_classify("generate an image of a cat"), "generate_image")

    def test_generate_image_draw(self):
        self.assertEqual(_classify("draw me a picture of a sunset"), "generate_image")

    def test_git_status_explicit(self):
        self.assertEqual(_classify("run git status"), "git_status")

    def test_git_log(self):
        self.assertEqual(_classify("git log"), "git_status")

    def test_gmail_check(self):
        self.assertEqual(_classify("check my email"), "gmail")

    def test_web_search(self):
        self.assertEqual(_classify("search the web for llama3 benchmarks"), "web_search")

    def test_memory_recall(self):
        self.assertEqual(_classify("what do you remember about my setup?"), "memory_recall")

    def test_old_files(self):
        self.assertEqual(_classify("files I haven't opened in a year"), "old_files")

    def test_obsidian_search(self):
        self.assertEqual(_classify("search my obsidian notes for python"), "obsidian_search")

    def test_run_code(self):
        self.assertEqual(_classify("run this python script"), "run_code")

    def test_doctor_full_health_check(self):
        self.assertEqual(_classify("run a full health check"), "doctor")

    def test_doctor_deep_diagnostic(self):
        self.assertEqual(_classify("deep diagnostic please"), "doctor")


# ---------------------------------------------------------------------------
# Gmail Phases 1–3: read / open / thread / summarize / list_category
#                   archive / trash / mark_read / mark_unread / confirm / cancel
#                   draft_reply / compose / send / cancel_draft / show_draft
# ---------------------------------------------------------------------------

class TestGmailRoutingPhases1to3(unittest.TestCase):
    """Routing for Gmail Phases 1-3 — no Ollama required; pure regex."""

    # ── Phase 1 read / open ─────────────────────────────────────────────────

    def test_open_email_from_sender(self):
        self.assertEqual(_classify("open the email from Rahul"), "gmail_open")

    def test_open_latest_from(self):
        self.assertEqual(_classify("open the latest email from Priya"), "gmail_open")

    def test_read_email_number(self):
        self.assertEqual(_classify("read #3"), "gmail_read")

    def test_read_first(self):
        self.assertEqual(_classify("open the latest email"), "gmail_read")

    def test_summarize_this_email(self):
        self.assertEqual(_classify("summarize this email"), "gmail_summarize")

    def test_summarize_it_followup(self):
        # Classic multi-turn follow-up after opening an email
        self.assertEqual(_classify("summarize it"), "gmail_summarize")

    def test_tldr_that(self):
        self.assertEqual(_classify("tldr that"), "gmail_summarize")

    def test_tldr_thread(self):
        self.assertEqual(_classify("tldr the thread"), "gmail_summarize")

    def test_show_thread(self):
        self.assertEqual(_classify("show the thread"), "gmail_thread")

    def test_open_conversation(self):
        self.assertEqual(_classify("open the email conversation"), "gmail_thread")

    def test_list_promotions(self):
        self.assertEqual(_classify("show my promotions"), "gmail_list_category")

    def test_list_spam(self):
        self.assertEqual(_classify("show spam"), "gmail_list_category")

    def test_list_social(self):
        self.assertEqual(_classify("list social emails"), "gmail_list_category")

    # ── Phase 2 mutations ───────────────────────────────────────────────────

    def test_archive_promotions(self):
        self.assertEqual(_classify("archive all my promotions"), "gmail_archive")

    def test_archive_those(self):
        self.assertEqual(_classify("archive those emails"), "gmail_archive")

    def test_archive_from(self):
        self.assertEqual(_classify("archive emails from newsletters"), "gmail_archive")

    def test_trash_spam(self):
        self.assertEqual(_classify("trash all spam emails"), "gmail_trash")

    def test_trash_those(self):
        self.assertEqual(_classify("trash those messages"), "gmail_trash")

    def test_delete_promo_emails(self):
        self.assertEqual(_classify("delete all promotional emails"), "gmail_trash")

    def test_mark_as_read(self):
        self.assertEqual(_classify("mark all as read"), "gmail_mark_read")

    def test_mark_them_read(self):
        self.assertEqual(_classify("mark them as read"), "gmail_mark_read")

    def test_mark_as_unread(self):
        self.assertEqual(_classify("mark this as unread"), "gmail_mark_unread")

    def test_confirm_standalone(self):
        self.assertEqual(_classify("confirm"), "gmail_confirm")

    def test_yes_do_it(self):
        self.assertEqual(_classify("yes do it"), "gmail_confirm")

    def test_cancel_mutation(self):
        self.assertEqual(_classify("cancel"), "gmail_cancel")

    def test_never_mind(self):
        self.assertEqual(_classify("never mind"), "gmail_cancel")

    # ── Phase 3 draft / compose / send ──────────────────────────────────────

    def test_draft_reply_explicit(self):
        self.assertEqual(_classify("draft a reply"), "gmail_draft_reply")

    def test_reply_saying(self):
        self.assertEqual(_classify("reply saying I'll get back to you"), "gmail_draft_reply")

    def test_respond_saying(self):
        self.assertEqual(_classify("respond saying sounds good"), "gmail_draft_reply")

    def test_write_back_that(self):
        self.assertEqual(_classify("write back that I received it"), "gmail_draft_reply")

    def test_compose_new_email(self):
        self.assertEqual(_classify("compose a new email"), "gmail_compose")

    def test_write_email(self):
        self.assertEqual(_classify("write an email to Priya"), "gmail_compose")

    def test_email_saying(self):
        self.assertEqual(_classify("email Rahul saying thanks for the update"), "gmail_compose")

    def test_send_it(self):
        self.assertEqual(_classify("send it"), "gmail_send_draft")

    def test_send_the_draft(self):
        self.assertEqual(_classify("send the draft"), "gmail_send_draft")

    def test_go_ahead_send(self):
        self.assertEqual(_classify("go ahead and send it"), "gmail_send_draft")

    def test_send_the_reply(self):
        self.assertEqual(_classify("send the reply"), "gmail_send_draft")

    def test_cancel_draft(self):
        self.assertEqual(_classify("cancel the draft"), "gmail_cancel_draft")

    def test_discard_draft(self):
        self.assertEqual(_classify("discard the draft"), "gmail_cancel_draft")

    def test_show_draft(self):
        self.assertEqual(_classify("show the draft"), "gmail_show_draft")

    def test_preview_draft(self):
        self.assertEqual(_classify("preview the draft"), "gmail_show_draft")

    def test_what_does_draft_say(self):
        self.assertEqual(_classify("what does the draft say"), "gmail_show_draft")

    # ── cancel vs cancel_draft ordering ─────────────────────────────────────

    def test_cancel_vs_cancel_draft_mutation(self):
        # Bare "cancel" → gmail_cancel (mutation cancel, NOT draft cancel)
        self.assertEqual(_classify("cancel"), "gmail_cancel")

    def test_cancel_draft_not_cancel(self):
        # "cancel the draft" must NOT hit gmail_cancel (hits gmail_cancel_draft)
        result = _classify("cancel the draft")
        self.assertEqual(result, "gmail_cancel_draft")
        self.assertNotEqual(result, "gmail_cancel")


# ---------------------------------------------------------------------------
# Gmail Phases 4–7: rewrite / CC-BCC / inbound attachments / outbound attachments
# ---------------------------------------------------------------------------

class TestGmailRoutingPhases4to7(unittest.TestCase):
    """Routing for Gmail Phases 4-7 — pure regex, no Ollama needed."""

    # ── Phase 4 rewrite ─────────────────────────────────────────────────────

    def test_make_it_shorter(self):
        self.assertEqual(_classify("make it shorter"), "gmail_rewrite_draft")

    def test_rewrite_professional(self):
        self.assertEqual(_classify("rewrite the draft to be more professional"), "gmail_rewrite_draft")

    def test_make_email_briefer(self):
        self.assertEqual(_classify("make the email briefer"), "gmail_rewrite_draft")

    def test_edit_more_direct(self):
        self.assertEqual(_classify("edit this to be more direct"), "gmail_rewrite_draft")

    def test_mention_in_email(self):
        self.assertEqual(_classify("mention the deadline in the email"), "gmail_rewrite_draft")

    def test_add_note_to_draft(self):
        # "add a note about X to the draft" → rewrite_draft (no file-type keyword)
        self.assertEqual(_classify("add a note about shipping costs to the draft"), "gmail_rewrite_draft")

    # ── Phase 5 CC / BCC ────────────────────────────────────────────────────

    def test_add_cc(self):
        self.assertEqual(_classify("add cc Priya"), "gmail_add_cc")

    def test_cc_on_draft(self):
        self.assertEqual(_classify("cc Priya on this draft"), "gmail_add_cc")

    def test_cc_on_this_email(self):
        self.assertEqual(_classify("cc me on the email"), "gmail_add_cc")

    def test_add_bcc(self):
        self.assertEqual(_classify("add bcc myself"), "gmail_add_bcc")

    def test_bcc_on_draft(self):
        self.assertEqual(_classify("bcc Rahul on this draft"), "gmail_add_bcc")

    def test_bcc_to_message(self):
        self.assertEqual(_classify("bcc me to the message"), "gmail_add_bcc")

    # ── Phase 6 inbound attachments ─────────────────────────────────────────

    def test_show_attachments(self):
        self.assertEqual(_classify("show attachments"), "gmail_list_attachments")

    def test_list_attachments(self):
        self.assertEqual(_classify("list attachments on this email"), "gmail_list_attachments")

    def test_any_attachments(self):
        self.assertEqual(_classify("any attachments?"), "gmail_list_attachments")

    def test_what_files_attached(self):
        self.assertEqual(_classify("what files are attached"), "gmail_list_attachments")

    def test_save_pdf(self):
        self.assertEqual(_classify("save the PDF"), "gmail_save_attachment")

    def test_download_invoice(self):
        self.assertEqual(_classify("download the invoice"), "gmail_save_attachment")

    def test_save_first_attachment(self):
        self.assertEqual(_classify("save the first attachment"), "gmail_save_attachment")

    def test_summarize_attached_pdf(self):
        self.assertEqual(_classify("summarize the attached PDF"), "gmail_summarize_attachment")

    def test_whats_in_attachment(self):
        self.assertEqual(_classify("what's in the attachment"), "gmail_summarize_attachment")

    def test_tldr_invoice(self):
        self.assertEqual(_classify("tldr the invoice"), "gmail_summarize_attachment")

    # ── Phase 7 outbound attach ─────────────────────────────────────────────

    def test_attach_pdf_to_draft(self):
        self.assertEqual(_classify("attach the PDF to this draft"), "gmail_attach_file")

    def test_attach_invoice_bare(self):
        self.assertEqual(_classify("attach the invoice"), "gmail_attach_file")

    def test_add_spreadsheet_to_email(self):
        self.assertEqual(_classify("add the spreadsheet to this email"), "gmail_attach_file")

    def test_include_report_in_the_draft(self):
        self.assertEqual(_classify("include the report in the draft"), "gmail_attach_file")

    def test_include_report_in_this_draft(self):
        self.assertEqual(_classify("include the report in this draft"), "gmail_attach_file")

    def test_attach_saved_attachment(self):
        self.assertEqual(_classify("attach that saved attachment"), "gmail_attach_file")

    def test_attach_deck_to_reply(self):
        self.assertEqual(_classify("attach the deck to this reply"), "gmail_attach_file")

    def test_attach_document(self):
        self.assertEqual(_classify("attach the document"), "gmail_attach_file")

    # ── Ordering guards: Phase 7 must beat Phase 4 ─────────────────────────

    def test_add_pdf_beats_rewrite(self):
        # gmail_attach_file must win over gmail_rewrite_draft
        result = _classify("add the PDF to this draft")
        self.assertEqual(result, "gmail_attach_file")
        self.assertNotEqual(result, "gmail_rewrite_draft")

    def test_include_invoice_beats_rewrite(self):
        result = _classify("include the invoice in the email")
        self.assertEqual(result, "gmail_attach_file")
        self.assertNotEqual(result, "gmail_rewrite_draft")

    def test_text_only_add_is_rewrite(self):
        # No file-type keyword → gmail_rewrite_draft, not gmail_attach_file
        result = _classify("add a paragraph about the timeline to the email")
        self.assertEqual(result, "gmail_rewrite_draft")
        self.assertNotEqual(result, "gmail_attach_file")

    # ── Phase 6 inbound must not bleed into Phase 7 outbound ───────────────

    def test_save_attachment_not_attach_file(self):
        # save/download → gmail_save_attachment, not gmail_attach_file
        result = _classify("save the attached document")
        self.assertEqual(result, "gmail_save_attachment")
        self.assertNotEqual(result, "gmail_attach_file")

    def test_summarize_pdf_not_attach_file(self):
        result = _classify("summarize the PDF")
        self.assertEqual(result, "gmail_summarize_attachment")
        self.assertNotEqual(result, "gmail_attach_file")

    def test_list_attachments_not_attach_file(self):
        result = _classify("show attachments on this email")
        self.assertEqual(result, "gmail_list_attachments")
        self.assertNotEqual(result, "gmail_attach_file")


class TestGmailRoutingPhase8(unittest.TestCase):
    """Phase 8 — undo, remove_attachment, send_email NLU patterns. No Ollama."""

    # ── gmail_undo ─────────────────────────────────────────────────────────────

    def test_bare_undo(self):
        self.assertEqual(_classify("undo"), "gmail_undo")

    def test_undo_that(self):
        self.assertEqual(_classify("undo that"), "gmail_undo")

    def test_undo_the_archive(self):
        self.assertEqual(_classify("undo the archive"), "gmail_undo")

    def test_undo_that_trash(self):
        self.assertEqual(_classify("undo that trash"), "gmail_undo")

    def test_undo_last_action(self):
        self.assertEqual(_classify("undo last action"), "gmail_undo")

    def test_bring_back_those(self):
        self.assertEqual(_classify("bring back those emails"), "gmail_undo")

    def test_restore_those_emails(self):
        self.assertEqual(_classify("restore those emails"), "gmail_undo")

    def test_undo_not_cancel(self):
        result = _classify("undo")
        self.assertEqual(result, "gmail_undo")
        self.assertNotEqual(result, "gmail_cancel")

    # ── gmail_remove_attachment ─────────────────────────────────────────────

    def test_remove_pdf_from_draft(self):
        self.assertEqual(_classify("remove the PDF from the draft"), "gmail_remove_attachment")

    def test_detach_attachment(self):
        self.assertEqual(_classify("detach the attachment"), "gmail_remove_attachment")

    def test_drop_invoice_from_email(self):
        self.assertEqual(_classify("drop the invoice from the email"), "gmail_remove_attachment")

    def test_remove_attachment_ordinal(self):
        self.assertEqual(_classify("remove attachment 1"), "gmail_remove_attachment")

    def test_detach_pdf(self):
        self.assertEqual(_classify("detach the PDF"), "gmail_remove_attachment")

    def test_remove_not_attach(self):
        # "remove" verb beats "attach" intent
        result = _classify("remove the PDF from the draft")
        self.assertEqual(result, "gmail_remove_attachment")
        self.assertNotEqual(result, "gmail_attach_file")

    # ── gmail_send_draft extended patterns ────────────────────────────────────

    def test_send_the_email(self):
        self.assertEqual(_classify("send the email"), "gmail_send_draft")

    def test_send_the_message(self):
        self.assertEqual(_classify("send the message"), "gmail_send_draft")

    def test_looks_good_send_it(self):
        self.assertEqual(_classify("looks good, send it"), "gmail_send_draft")

    def test_lgtm_send(self):
        self.assertEqual(_classify("lgtm send it"), "gmail_send_draft")

    def test_good_to_go_send(self):
        self.assertEqual(_classify("good to go, send the email"), "gmail_send_draft")

    def test_approved_send(self):
        self.assertEqual(_classify("approved, send it"), "gmail_send_draft")

    # ── Ordering guards ───────────────────────────────────────────────────────

    def test_remove_attachment_before_attach_file(self):
        # "remove the document" should NOT match gmail_attach_file
        result = _classify("remove the document from the draft")
        self.assertEqual(result, "gmail_remove_attachment")
        self.assertNotEqual(result, "gmail_attach_file")

    def test_undo_archive_before_archive_pattern(self):
        # "undo the archive" must go to gmail_undo, not gmail_archive
        result = _classify("undo the archive")
        self.assertEqual(result, "gmail_undo")
        self.assertNotEqual(result, "gmail_archive")


class TestGmailRoutingPhase9(unittest.TestCase):
    """Phase 9: gmail_triage NLU routing — inbox triage intelligence."""

    # ── Core triage phrases ───────────────────────────────────────────────────

    def test_what_needs_my_reply(self):
        self.assertEqual(_classify("what needs my reply"), "gmail_triage")

    def test_which_emails_need_my_reply(self):
        self.assertEqual(_classify("which emails need my reply"), "gmail_triage")

    def test_triage_my_inbox(self):
        self.assertEqual(_classify("triage my inbox"), "gmail_triage")

    def test_inbox_triage_bare(self):
        self.assertEqual(_classify("inbox triage"), "gmail_triage")

    def test_email_triage_bare(self):
        self.assertEqual(_classify("email triage"), "gmail_triage")

    def test_what_needs_attention(self):
        self.assertEqual(_classify("what needs attention"), "gmail_triage")

    def test_what_needs_my_attention_today(self):
        self.assertEqual(_classify("what needs my attention today"), "gmail_triage")

    def test_show_urgent_emails(self):
        self.assertEqual(_classify("show urgent emails"), "gmail_triage")

    def test_show_action_needed_emails(self):
        self.assertEqual(_classify("show action-needed emails"), "gmail_triage")

    def test_what_should_i_answer(self):
        self.assertEqual(_classify("what should I answer"), "gmail_triage")

    def test_what_should_i_respond_to(self):
        self.assertEqual(_classify("what should I respond to"), "gmail_triage")

    def test_which_emails_are_urgent(self):
        self.assertEqual(_classify("which emails are urgent"), "gmail_triage")

    def test_emails_waiting_on_me(self):
        self.assertEqual(_classify("emails waiting on me"), "gmail_triage")

    def test_inbox_waiting_for_me(self):
        self.assertEqual(_classify("inbox waiting for me"), "gmail_triage")

    def test_which_threads_am_i_waiting_on(self):
        self.assertEqual(_classify("which threads am I waiting on"), "gmail_triage")

    # ── Ordering guards ───────────────────────────────────────────────────────

    def test_triage_beats_gmail_open(self):
        # "what needs my reply" must NOT go to gmail_read or gmail_open
        result = _classify("what needs my reply")
        self.assertNotEqual(result, "gmail_open")
        self.assertNotEqual(result, "gmail_read")

    def test_urgent_emails_not_archive(self):
        # "show urgent emails" must NOT go to gmail_archive
        result = _classify("show urgent emails")
        self.assertEqual(result, "gmail_triage")
        self.assertNotEqual(result, "gmail_archive")

    def test_show_important_emails_not_gmail(self):
        # "find important emails" must go to triage, not gmail bare
        result = _classify("find important emails")
        self.assertIn(result, ("gmail_triage", None))


class TestGmailRoutingPhase10(unittest.TestCase):
    """Phase 10: gmail_schedule_send / gmail_list_scheduled / gmail_cancel_scheduled_send routing."""

    # ── schedule_send: explicit time phrases ─────────────────────────────────

    def test_send_tomorrow_morning(self):
        self.assertEqual(_classify("send this tomorrow morning"), "gmail_schedule_send")

    def test_send_tomorrow_no_qualifier(self):
        self.assertEqual(_classify("send this tomorrow"), "gmail_schedule_send")

    def test_schedule_monday_at_nine(self):
        self.assertEqual(_classify("schedule for Monday at 9"), "gmail_schedule_send")

    def test_send_at_3pm(self):
        self.assertEqual(_classify("send the draft at 3 PM"), "gmail_schedule_send")

    def test_send_at_3pm_lowercase(self):
        self.assertEqual(_classify("send this at 3pm"), "gmail_schedule_send")

    def test_schedule_this_for_friday(self):
        self.assertEqual(_classify("schedule it for Friday at 8"), "gmail_schedule_send")

    def test_send_in_2_hours(self):
        self.assertEqual(_classify("send in 2 hours"), "gmail_schedule_send")

    def test_delay_send(self):
        self.assertEqual(_classify("delay send until tomorrow"), "gmail_schedule_send")

    def test_send_later(self):
        self.assertEqual(_classify("send later"), "gmail_schedule_send")

    def test_schedule_the_email(self):
        self.assertEqual(_classify("schedule the email"), "gmail_schedule_send")

    def test_send_tomorrow_afternoon(self):
        self.assertEqual(_classify("send the draft tomorrow afternoon"), "gmail_schedule_send")

    def test_send_next_week(self):
        self.assertEqual(_classify("send this next week"), "gmail_schedule_send")

    # ── Ordering guard: schedule beats send_draft ─────────────────────────────

    def test_schedule_beats_send_draft_tomorrow(self):
        result = _classify("send this tomorrow morning")
        self.assertEqual(result, "gmail_schedule_send")
        self.assertNotEqual(result, "gmail_send_draft")

    def test_schedule_beats_send_draft_friday(self):
        result = _classify("schedule for Friday")
        self.assertEqual(result, "gmail_schedule_send")
        self.assertNotEqual(result, "gmail_send_draft")

    # ── Bare "send it" still goes to gmail_send_draft (no time phrase) ────────

    def test_bare_send_it_not_scheduled(self):
        result = _classify("send it")
        self.assertEqual(result, "gmail_send_draft")
        self.assertNotEqual(result, "gmail_schedule_send")

    def test_lgtm_send_not_scheduled(self):
        result = _classify("lgtm send it")
        self.assertEqual(result, "gmail_send_draft")
        self.assertNotEqual(result, "gmail_schedule_send")

    # ── list_scheduled ────────────────────────────────────────────────────────

    def test_show_scheduled_emails(self):
        self.assertEqual(_classify("show scheduled emails"), "gmail_list_scheduled")

    def test_list_scheduled_sends(self):
        self.assertEqual(_classify("list scheduled sends"), "gmail_list_scheduled")

    def test_what_emails_are_scheduled(self):
        self.assertEqual(_classify("what emails are scheduled"), "gmail_list_scheduled")

    # ── cancel_scheduled_send ─────────────────────────────────────────────────

    def test_cancel_scheduled_send(self):
        self.assertEqual(_classify("cancel the scheduled send"), "gmail_cancel_scheduled_send")

    def test_cancel_scheduled_email(self):
        self.assertEqual(_classify("cancel scheduled email"), "gmail_cancel_scheduled_send")

    def test_unschedule_that(self):
        self.assertEqual(_classify("unschedule that"), "gmail_cancel_scheduled_send")

    def test_dont_send_that(self):
        result = _classify("don't send that")
        self.assertEqual(result, "gmail_cancel_scheduled_send")

    def test_cancel_scheduled_beats_cancel(self):
        # "cancel the scheduled send" must go to cancel_scheduled, not gmail_cancel
        result = _classify("cancel the scheduled send")
        self.assertEqual(result, "gmail_cancel_scheduled_send")
        self.assertNotEqual(result, "gmail_cancel")


class TestGmailRoutingPhase11(unittest.TestCase):
    """Phase 11: follow-up reminder routing tests."""

    # ── gmail_followup_reminder ───────────────────────────────────────────────
    def test_remind_me_if_no_reply(self):
        self.assertEqual(_classify("remind me if no reply in 3 days"), "gmail_followup_reminder")

    def test_if_no_reply(self):
        self.assertEqual(_classify("if no reply by Monday remind me"), "gmail_followup_reminder")

    def test_set_followup_reminder(self):
        self.assertEqual(_classify("set a follow-up reminder"), "gmail_followup_reminder")

    def test_remind_me_to_followup(self):
        self.assertEqual(_classify("remind me to follow up"), "gmail_followup_reminder")

    def test_followup_on_this_if_no_reply(self):
        self.assertEqual(_classify("follow up on this if no reply"), "gmail_followup_reminder")

    def test_followup_on_this_thread(self):
        self.assertEqual(_classify("follow up on this thread Friday morning if they don't answer"), "gmail_followup_reminder")

    def test_if_they_havent_replied(self):
        self.assertEqual(_classify("if they haven't replied in 2 days ping me"), "gmail_followup_reminder")

    def test_if_they_dont_respond(self):
        self.assertEqual(_classify("if they don't respond by Friday"), "gmail_followup_reminder")

    # ── gmail_list_followups ──────────────────────────────────────────────────
    def test_show_my_followups(self):
        self.assertEqual(_classify("show my follow-ups"), "gmail_list_followups")

    def test_list_pending_reminders(self):
        self.assertEqual(_classify("list pending follow-up reminders"), "gmail_list_followups")

    def test_what_am_i_waiting_on(self):
        self.assertEqual(_classify("what am I waiting on?"), "gmail_list_followups")

    def test_what_threads_am_i_following(self):
        self.assertEqual(_classify("what threads am I following up on"), "gmail_list_followups")

    def test_who_hasnt_replied(self):
        self.assertEqual(_classify("who hasn't replied"), "gmail_list_followups")

    def test_open_followups(self):
        self.assertEqual(_classify("open follow-ups"), "gmail_list_followups")

    def test_pending_followups(self):
        self.assertEqual(_classify("pending follow-ups"), "gmail_list_followups")

    # ── gmail_cancel_followup ─────────────────────────────────────────────────
    def test_cancel_followup(self):
        self.assertEqual(_classify("cancel the follow-up"), "gmail_cancel_followup")

    def test_cancel_reminder_2(self):
        self.assertEqual(_classify("cancel reminder 2"), "gmail_cancel_followup")

    def test_remove_that_reminder(self):
        self.assertEqual(_classify("remove that reminder"), "gmail_cancel_followup")

    def test_stop_followup_reminder(self):
        self.assertEqual(_classify("stop the follow-up reminder"), "gmail_cancel_followup")

    def test_delete_reminder(self):
        self.assertEqual(_classify("delete reminder"), "gmail_cancel_followup")

    # ── Non-bleed guards ──────────────────────────────────────────────────────
    def test_cancel_followup_beats_cancel_scheduled(self):
        # "cancel the follow-up" must NOT go to gmail_cancel_scheduled_send
        result = _classify("cancel the follow-up reminder")
        self.assertEqual(result, "gmail_cancel_followup")
        self.assertNotEqual(result, "gmail_cancel_scheduled_send")

    def test_followup_reminder_beats_schedule_send(self):
        # "remind me" must go to followup, not schedule_send
        result = _classify("remind me if no reply in 3 days")
        self.assertEqual(result, "gmail_followup_reminder")
        self.assertNotEqual(result, "gmail_schedule_send")

    def test_in_3_days_parser(self):
        # "in N days" time phrase belongs to followup, not schedule_send
        result = _classify("remind me if no reply in 3 days")
        self.assertNotEqual(result, "gmail_schedule_send")


class TestGmailRoutingPhase12(unittest.TestCase):
    """Phase 12: multi-draft management routing tests."""

    # ── gmail_list_drafts ─────────────────────────────────────────────────────
    def test_show_my_drafts(self):
        self.assertEqual(_classify("show my drafts"), "gmail_list_drafts")

    def test_list_drafts(self):
        self.assertEqual(_classify("list drafts"), "gmail_list_drafts")

    def test_show_all_drafts(self):
        self.assertEqual(_classify("show all drafts"), "gmail_list_drafts")

    def test_show_scheduled_drafts(self):
        self.assertEqual(_classify("show scheduled drafts"), "gmail_list_drafts")

    def test_show_unscheduled_drafts(self):
        self.assertEqual(_classify("show unscheduled drafts"), "gmail_list_drafts")

    def test_what_drafts_do_i_have(self):
        self.assertEqual(_classify("what drafts do I have"), "gmail_list_drafts")

    def test_show_draft_singular_stays_show_draft(self):
        # "show my draft" (singular) must NOT go to gmail_list_drafts
        result = _classify("show my draft")
        self.assertNotEqual(result, "gmail_list_drafts")

    # ── gmail_open_draft ──────────────────────────────────────────────────────
    def test_open_draft_2(self):
        self.assertEqual(_classify("open draft 2"), "gmail_open_draft")

    def test_open_the_second_draft(self):
        self.assertEqual(_classify("open the second draft"), "gmail_open_draft")

    def test_go_back_to_invoice_draft(self):
        self.assertEqual(_classify("go back to the invoice draft"), "gmail_open_draft")

    def test_switch_to_rahul_draft(self):
        self.assertEqual(_classify("switch to the Rahul draft"), "gmail_open_draft")

    def test_send_the_second_draft(self):
        result = _classify("send the second draft")
        self.assertEqual(result, "gmail_open_draft")
        self.assertNotEqual(result, "gmail_send_draft")

    def test_send_draft_2(self):
        result = _classify("send draft 2")
        self.assertEqual(result, "gmail_open_draft")
        self.assertNotEqual(result, "gmail_send_draft")

    def test_send_the_rahul_draft(self):
        result = _classify("send the Rahul draft")
        self.assertEqual(result, "gmail_open_draft")

    def test_load_draft_1(self):
        self.assertEqual(_classify("load draft 1"), "gmail_open_draft")

    # ── gmail_delete_draft ────────────────────────────────────────────────────
    def test_delete_draft_1(self):
        self.assertEqual(_classify("delete draft 1"), "gmail_delete_draft")

    def test_delete_second_draft(self):
        self.assertEqual(_classify("delete the second draft"), "gmail_delete_draft")

    def test_delete_named_draft(self):
        self.assertEqual(_classify("delete the Rahul draft"), "gmail_delete_draft")

    def test_cancel_old_draft(self):
        self.assertEqual(_classify("cancel the old draft"), "gmail_delete_draft")

    def test_remove_draft_2(self):
        self.assertEqual(_classify("remove draft 2"), "gmail_delete_draft")

    # ── Non-bleed guards ──────────────────────────────────────────────────────
    def test_send_it_still_send_draft(self):
        # "send it" must NOT go to gmail_open_draft
        result = _classify("send it")
        self.assertEqual(result, "gmail_send_draft")

    def test_send_the_draft_still_send_draft(self):
        # "send the draft" (plain, no name/ordinal) must go to gmail_send_draft
        result = _classify("send the draft")
        self.assertEqual(result, "gmail_send_draft")
        self.assertNotEqual(result, "gmail_open_draft")

    def test_delete_the_draft_stays_cancel_draft(self):
        # "delete the draft" (plain) must go to gmail_cancel_draft, not gmail_delete_draft
        result = _classify("delete the draft")
        self.assertEqual(result, "gmail_cancel_draft")
        self.assertNotEqual(result, "gmail_delete_draft")

    def test_list_drafts_beats_show_draft(self):
        # "show my drafts" must go to list, not show_draft
        result = _classify("show my drafts")
        self.assertEqual(result, "gmail_list_drafts")
        self.assertNotEqual(result, "gmail_show_draft")


class TestGmailRoutingPhase14(unittest.TestCase):
    """Phase 14 — smart-compose polish: subject update + extended rewrite routing."""

    # ── gmail_update_subject ───────────────────────────────────────────────────

    def test_make_subject_clearer(self):
        self.assertEqual(_classify("make the subject clearer"), "gmail_update_subject")

    def test_rewrite_the_subject(self):
        self.assertEqual(_classify("rewrite the subject"), "gmail_update_subject")

    def test_update_subject(self):
        self.assertEqual(_classify("update the subject"), "gmail_update_subject")

    def test_give_me_better_subject(self):
        self.assertEqual(_classify("give me a better subject"), "gmail_update_subject")

    def test_subject_sounds_weak(self):
        self.assertEqual(_classify("the subject sounds weak"), "gmail_update_subject")

    def test_write_stronger_subject(self):
        self.assertEqual(_classify("write a stronger subject"), "gmail_update_subject")

    def test_improve_subject_line(self):
        self.assertEqual(_classify("improve the subject line"), "gmail_update_subject")

    def test_change_subject(self):
        self.assertEqual(_classify("change the subject"), "gmail_update_subject")

    def test_subject_not_body_rewrite(self):
        # subject update must not bleed into rewrite_draft
        result = _classify("make the subject clearer")
        self.assertNotEqual(result, "gmail_rewrite_draft")

    # ── gmail_rewrite_draft (extended) ────────────────────────────────────────

    def test_make_it_more_polite(self):
        self.assertEqual(_classify("make it more polite"), "gmail_rewrite_draft")

    def test_make_it_less_robotic(self):
        self.assertEqual(_classify("make it sound less robotic"), "gmail_rewrite_draft")

    def test_make_it_more_natural(self):
        self.assertEqual(_classify("make it more natural"), "gmail_rewrite_draft")

    def test_turn_this_into_update(self):
        self.assertEqual(_classify("turn this into a concise update"), "gmail_rewrite_draft")

    def test_write_shorter_version(self):
        self.assertEqual(_classify("write a shorter version"), "gmail_rewrite_draft")

    def test_write_more_professional_reply(self):
        self.assertEqual(_classify("write a more professional reply"), "gmail_rewrite_draft")

    def test_make_it_less_formal(self):
        self.assertEqual(_classify("make it less formal"), "gmail_rewrite_draft")

    def test_update_subject_beats_rewrite_draft(self):
        # "update the subject" → subject update, not body rewrite
        self.assertEqual(_classify("update the subject"), "gmail_update_subject")
        self.assertNotEqual(_classify("update the subject"), "gmail_rewrite_draft")


class TestGmailRoutingPhase13(unittest.TestCase):
    """Phase 13 — reschedule/open scheduled sends NLU routing."""

    # ── gmail_reschedule_send ──────────────────────────────────────────────────

    def test_reschedule_bare_word(self):
        self.assertEqual(_classify("reschedule the scheduled send to tomorrow morning"), "gmail_reschedule_send")

    def test_reschedule_to_monday(self):
        self.assertEqual(_classify("reschedule to Monday at 9"), "gmail_reschedule_send")

    def test_reschedule_that_to_friday(self):
        self.assertEqual(_classify("reschedule that to Friday"), "gmail_reschedule_send")

    def test_reschedule_named_send(self):
        self.assertEqual(_classify("reschedule the Rahul send to next week"), "gmail_reschedule_send")

    def test_move_scheduled_email(self):
        self.assertEqual(_classify("move the scheduled email to Friday afternoon"), "gmail_reschedule_send")

    def test_change_scheduled_send_time(self):
        self.assertEqual(_classify("change the scheduled send time to tomorrow"), "gmail_reschedule_send")

    def test_postpone_email(self):
        self.assertEqual(_classify("postpone the email to Monday"), "gmail_reschedule_send")

    def test_push_scheduled_send(self):
        self.assertEqual(_classify("push the scheduled send to in 2 hours"), "gmail_reschedule_send")

    def test_reschedule_not_schedule_send(self):
        # "reschedule" must NOT bleed into gmail_schedule_send
        self.assertEqual(_classify("reschedule this to tomorrow"), "gmail_reschedule_send")
        self.assertNotEqual(_classify("reschedule this to tomorrow"), "gmail_schedule_send")

    def test_reschedule_not_cancel_scheduled(self):
        # reschedule must not bleed into cancel
        result = _classify("reschedule to Friday")
        self.assertEqual(result, "gmail_reschedule_send")
        self.assertNotEqual(result, "gmail_cancel_scheduled_send")

    # ── gmail_open_scheduled_draft ────────────────────────────────────────────

    def test_open_scheduled_invoice_draft(self):
        self.assertEqual(_classify("open the scheduled invoice draft"), "gmail_open_scheduled_draft")

    def test_reopen_scheduled_email(self):
        self.assertEqual(_classify("reopen the scheduled Rahul email"), "gmail_open_scheduled_draft")

    def test_switch_to_scheduled_draft(self):
        self.assertEqual(_classify("switch to the scheduled draft"), "gmail_open_scheduled_draft")

    def test_load_scheduled_send_draft(self):
        self.assertEqual(_classify("load the scheduled send draft"), "gmail_open_scheduled_draft")

    def test_open_scheduled_send_ordinal(self):
        self.assertEqual(_classify("open scheduled send 2"), "gmail_open_scheduled_draft")

    def test_open_scheduled_email_draft(self):
        self.assertEqual(_classify("open the scheduled email draft"), "gmail_open_scheduled_draft")

    def test_open_scheduled_draft_beats_open_draft(self):
        # "open the scheduled draft" must go to open_scheduled_draft, not open_draft
        result = _classify("open the scheduled draft")
        self.assertEqual(result, "gmail_open_scheduled_draft")
        self.assertNotEqual(result, "gmail_open_draft")

    def test_open_scheduled_draft_beats_list_scheduled(self):
        # "open the scheduled invoice draft" must not go to list_scheduled
        result = _classify("open the scheduled invoice draft")
        self.assertNotEqual(result, "gmail_list_scheduled")


class TestGmailRoutingPhase15(unittest.TestCase):
    """Phase 15: gmail_thread_intel and gmail_forward NLU routing."""

    # ── gmail_thread_intel ───────────────────────────────────────────────────

    def test_action_items_bare(self):
        self.assertEqual(_classify("what action items are in this thread"), "gmail_thread_intel")

    def test_action_items_short(self):
        self.assertEqual(_classify("action items in this email chain"), "gmail_thread_intel")

    def test_decisions_in_thread(self):
        self.assertEqual(_classify("what decisions were made in this thread"), "gmail_thread_intel")

    def test_decisions_with_chain(self):
        self.assertEqual(_classify("decisions made in this conversation"), "gmail_thread_intel")

    def test_do_i_owe_reply(self):
        self.assertEqual(_classify("do I owe a reply here"), "gmail_thread_intel")

    def test_should_i_reply(self):
        self.assertEqual(_classify("should I reply to this"), "gmail_thread_intel")

    def test_is_reply_needed(self):
        self.assertEqual(_classify("is a reply needed"), "gmail_thread_intel")

    def test_what_changed(self):
        self.assertEqual(_classify("what changed in the last reply"), "gmail_thread_intel")

    def test_latest_reply(self):
        self.assertEqual(_classify("what's the latest update in this thread"), "gmail_thread_intel")

    def test_summarize_latest_reply(self):
        self.assertEqual(_classify("summarize the latest reply"), "gmail_thread_intel")

    def test_summarize_latest_message(self):
        self.assertEqual(_classify("summarize the latest message"), "gmail_thread_intel")

    def test_questions_waiting(self):
        self.assertEqual(_classify("questions waiting on me"), "gmail_thread_intel")

    def test_questions_outstanding(self):
        self.assertEqual(_classify("questions outstanding for me"), "gmail_thread_intel")

    def test_what_do_i_owe(self):
        self.assertEqual(_classify("what do I owe in this thread"), "gmail_thread_intel")

    def test_intel_beats_draft_reply(self):
        # "do I owe a reply" must not go to gmail_draft_reply
        result = _classify("do I owe a reply here")
        self.assertNotEqual(result, "gmail_draft_reply")

    def test_intel_beats_summarize(self):
        # "summarize the latest reply" must not go to gmail_summarize
        result = _classify("summarize the latest reply")
        self.assertNotEqual(result, "gmail_summarize")

    # ── gmail_forward ────────────────────────────────────────────────────────

    def test_forward_to_name(self):
        self.assertEqual(_classify("forward to Rahul"), "gmail_forward")

    def test_forward_to_email(self):
        self.assertEqual(_classify("forward this to priya@example.com"), "gmail_forward")

    def test_fwd_to_team(self):
        self.assertEqual(_classify("fwd this to the team"), "gmail_forward")

    def test_forward_email_to_manager(self):
        self.assertEqual(_classify("forward the email to my manager"), "gmail_forward")

    def test_forward_with_summary(self):
        self.assertEqual(_classify("forward this with a summary"), "gmail_forward")

    def test_forward_beats_compose(self):
        # "forward to Rahul" must not go to gmail_compose
        result = _classify("forward to Rahul")
        self.assertNotEqual(result, "gmail_compose")

    def test_forward_it_to_boss(self):
        self.assertEqual(_classify("forward it to boss"), "gmail_forward")


if __name__ == "__main__":
    unittest.main(verbosity=2)
