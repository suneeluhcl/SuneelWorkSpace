"""
test_telegram_upgrade.py — Tests for Wave 4 Telegram bridge additions.

Covers:
  - New Safe API commands: /services /obsidian /git /git_diff /git_log
  - Background job commands: /test_quick /test_nlu /test_obsidian /test_all
  - Job management: /jobs /job /cancel /tests_status
  - Learn/capture: /capture /idea /plan /obsidian_review /obsidian_plan
                   /obsidian_validate /memory_scan
  - Repair gate: /repair_plan /repair_ok
  - Git backup gate: /git_backup /backup_ok
  - UX: /menu MENU_TEXT
  - Job runner: submit / status / list_recent / cancel / tail_log
  - Text helpers: _redact _sanitize_text
  - Confirmation gate: _make_token _consume_token expiry
"""

from __future__ import annotations

import importlib.util
import json
import re
import sys
import time
import unittest
from pathlib import Path
from unittest.mock import MagicMock, patch

# ── Module loader helpers ─────────────────────────────────────────────────────

_ROOT = Path(__file__).resolve().parent.parent.parent  # SuneelWorkSpace
_BOT_PATH = _ROOT / "adwi" / "services" / "telegram-bridge" / "bot.py"
_JR_PATH  = _ROOT / "adwi" / "services" / "telegram-bridge" / "job_runner.py"


def _load(name: str, path: Path):
    spec = importlib.util.spec_from_file_location(name, path)
    mod  = importlib.util.module_from_spec(spec)   # type: ignore[arg-type]
    spec.loader.exec_module(mod)                    # type: ignore[union-attr]
    return mod


bridge = _load("bridge", _BOT_PATH)
jr     = _load("job_runner_mod", _JR_PATH)

# ── Test helpers ──────────────────────────────────────────────────────────────

TOKEN       = "test-token"
ALLOWED_UID = 123456789
SECRET      = "test-secret"


def _make_update(uid: int, text: str) -> dict:
    return {
        "update_id": 1,
        "message": {
            "chat": {"id": uid},
            "from": {"id": uid},
            "text": text,
        },
    }


def _replies(update: dict) -> list[str]:
    """Capture all replies for a given update (mocks both _call_adwi and _send_reply)."""
    sent: list[str] = []
    with patch.object(bridge, "_call_adwi", return_value="mock-api-response"), \
         patch.object(bridge, "_send_reply", lambda t, c, msg: sent.append(msg)):
        bridge._handle_update(update, TOKEN, ALLOWED_UID, SECRET)
    return sent


def _api_calls(update: dict) -> list[str]:
    """Return the list of Safe API routes called for the update."""
    routes: list[str] = []
    with patch.object(bridge, "_call_adwi",
                      side_effect=lambda r, s: routes.append(r) or "mock") as m, \
         patch.object(bridge, "_send_reply", lambda *a: None):
        bridge._handle_update(update, TOKEN, ALLOWED_UID, SECRET)
    return routes


def _local_reply(cmd: str, args: str = "", mock_runner=None) -> str:
    """Run a local command and return the first reply."""
    sent: list[str] = []
    runner = mock_runner or MagicMock()
    with patch.object(bridge, "_JOB_RUNNER", runner), \
         patch.object(bridge, "_send_reply", lambda t, c, msg: sent.append(msg)):
        text = f"{cmd} {args}".strip()
        bridge._handle_local_cmd(cmd, args, TOKEN, ALLOWED_UID, SECRET)
    return sent[0] if sent else ""


# ═══════════════════════════════════════════════════════════════════════════════
# New Safe API commands
# ═══════════════════════════════════════════════════════════════════════════════

class TestNewSafeApiCommands(unittest.TestCase):
    """Wave 4 commands that route through the Safe API (/services, /obsidian, /git, etc.)"""

    def test_services_in_command_table(self):
        self.assertIn("/services", bridge.TELEGRAM_COMMANDS)

    def test_services_routes_to_adwi_services(self):
        self.assertEqual(bridge.TELEGRAM_COMMANDS["/services"], "/adwi-services")

    def test_obsidian_in_command_table(self):
        self.assertIn("/obsidian", bridge.TELEGRAM_COMMANDS)

    def test_obsidian_routes_to_obsidian_status(self):
        self.assertEqual(bridge.TELEGRAM_COMMANDS["/obsidian"], "/adwi-obsidian-status")

    def test_git_alias_in_command_table(self):
        self.assertIn("/git", bridge.TELEGRAM_COMMANDS)

    def test_git_alias_routes_to_workspace_status(self):
        self.assertEqual(bridge.TELEGRAM_COMMANDS["/git"], "/git-status-workspace")

    def test_git_diff_in_command_table(self):
        self.assertIn("/git_diff", bridge.TELEGRAM_COMMANDS)

    def test_git_diff_routes_to_adwi_git_diff(self):
        self.assertEqual(bridge.TELEGRAM_COMMANDS["/git_diff"], "/adwi-git-diff")

    def test_git_log_in_command_table(self):
        self.assertIn("/git_log", bridge.TELEGRAM_COMMANDS)

    def test_git_log_routes_to_adwi_git_log(self):
        self.assertEqual(bridge.TELEGRAM_COMMANDS["/git_log"], "/adwi-git-log")

    def test_services_reaches_api(self):
        calls = _api_calls(_make_update(ALLOWED_UID, "/services"))
        self.assertEqual(calls, ["/adwi-services"])

    def test_obsidian_reaches_api(self):
        calls = _api_calls(_make_update(ALLOWED_UID, "/obsidian"))
        self.assertEqual(calls, ["/adwi-obsidian-status"])

    def test_git_reaches_api(self):
        calls = _api_calls(_make_update(ALLOWED_UID, "/git"))
        self.assertEqual(calls, ["/git-status-workspace"])

    def test_git_diff_reaches_api(self):
        calls = _api_calls(_make_update(ALLOWED_UID, "/git_diff"))
        self.assertEqual(calls, ["/adwi-git-diff"])

    def test_git_log_reaches_api(self):
        calls = _api_calls(_make_update(ALLOWED_UID, "/git_log"))
        self.assertEqual(calls, ["/adwi-git-log"])

    def test_new_routes_not_dangerous(self):
        dangerous = [
            "run-bash", "run-python", "patch-adwi", "self-heal",
            "git-commit", "git-push", "obsidian-write", "backup-now",
        ]
        new_routes = ["/adwi-services", "/adwi-obsidian-status", "/adwi-git-diff", "/adwi-git-log"]
        for route in new_routes:
            for pat in dangerous:
                self.assertNotIn(pat, route, f"Route {route!r} contains dangerous pattern {pat!r}")


# ═══════════════════════════════════════════════════════════════════════════════
# Menu / UX
# ═══════════════════════════════════════════════════════════════════════════════

class TestMenuCommand(unittest.TestCase):
    def test_menu_in_command_table(self):
        self.assertIn("/menu", bridge.TELEGRAM_COMMANDS)

    def test_menu_is_locally_handled(self):
        self.assertIsNone(bridge.TELEGRAM_COMMANDS["/menu"])

    def test_menu_does_not_call_api(self):
        calls = _api_calls(_make_update(ALLOWED_UID, "/menu"))
        self.assertEqual(calls, [])

    def test_menu_returns_reply(self):
        replies = _replies(_make_update(ALLOWED_UID, "/menu"))
        self.assertGreater(len(replies), 0)

    def test_menu_text_mentions_key_sections(self):
        text = bridge.MENU_TEXT
        for section in ["STATUS", "TESTS", "CAPTURE", "REPAIR", "GIT BACKUP"]:
            self.assertIn(section.upper(), text.upper(),
                          f"MENU_TEXT missing section: {section!r}")

    def test_menu_text_mentions_test_commands(self):
        text = bridge.MENU_TEXT
        for cmd in ["/test_quick", "/test_nlu", "/tests_status"]:
            self.assertIn(cmd, text)

    def test_menu_text_mentions_capture(self):
        self.assertIn("/capture", bridge.MENU_TEXT)

    def test_menu_text_shows_command_count(self):
        # MENU_TEXT header should include the total count
        n = str(len(bridge.TELEGRAM_COMMANDS))
        self.assertIn(n, bridge.MENU_TEXT)

    def test_total_command_count_wave4(self):
        self.assertGreaterEqual(len(bridge.TELEGRAM_COMMANDS), 39)


# ═══════════════════════════════════════════════════════════════════════════════
# Test background job commands
# ═══════════════════════════════════════════════════════════════════════════════

class TestBackgroundTestCommands(unittest.TestCase):
    def setUp(self):
        self.mock_runner = MagicMock()
        self.mock_runner.submit.return_value = "test-quick-20260622-101234-ab12"

    def _run_job_cmd(self, cmd: str) -> list[str]:
        sent: list[str] = []
        with patch.object(bridge, "_JOB_RUNNER", self.mock_runner), \
             patch.object(bridge, "_send_reply", lambda t, c, msg: sent.append(msg)):
            bridge._handle_update(_make_update(ALLOWED_UID, cmd), TOKEN, ALLOWED_UID, SECRET)
        return sent

    def test_test_quick_in_table(self):
        self.assertIn("/test_quick", bridge.TELEGRAM_COMMANDS)
        self.assertIsNone(bridge.TELEGRAM_COMMANDS["/test_quick"])

    def test_test_nlu_in_table(self):
        self.assertIn("/test_nlu", bridge.TELEGRAM_COMMANDS)

    def test_test_obsidian_in_table(self):
        self.assertIn("/test_obsidian", bridge.TELEGRAM_COMMANDS)

    def test_test_all_in_table(self):
        self.assertIn("/test_all", bridge.TELEGRAM_COMMANDS)

    def test_tests_status_in_table(self):
        self.assertIn("/tests_status", bridge.TELEGRAM_COMMANDS)

    def test_test_quick_submits_job(self):
        self._run_job_cmd("/test_quick")
        self.mock_runner.submit.assert_called_once()
        name, argv = self.mock_runner.submit.call_args[0]
        self.assertEqual(name, "test-quick")
        self.assertIsInstance(argv, list)

    def test_test_nlu_submits_job(self):
        self._run_job_cmd("/test_nlu")
        self.mock_runner.submit.assert_called_once()
        name, _ = self.mock_runner.submit.call_args[0]
        self.assertEqual(name, "test-nlu")

    def test_test_obsidian_submits_job(self):
        self._run_job_cmd("/test_obsidian")
        self.mock_runner.submit.assert_called_once()
        name, _ = self.mock_runner.submit.call_args[0]
        self.assertEqual(name, "test-obsidian")

    def test_test_all_submits_job(self):
        self._run_job_cmd("/test_all")
        self.mock_runner.submit.assert_called_once()
        name, _ = self.mock_runner.submit.call_args[0]
        self.assertEqual(name, "test-all")

    def test_test_quick_reply_contains_job_id(self):
        replies = self._run_job_cmd("/test_quick")
        job_id  = self.mock_runner.submit.return_value
        self.assertTrue(any(job_id in r for r in replies),
                        f"No reply contained job ID {job_id!r}")

    def test_test_commands_do_not_call_safe_api(self):
        calls = _api_calls(_make_update(ALLOWED_UID, "/test_quick"))
        self.assertEqual(calls, [])

    def test_no_runner_returns_error(self):
        sent: list[str] = []
        with patch.object(bridge, "_JOB_RUNNER", None), \
             patch.object(bridge, "_send_reply", lambda t, c, msg: sent.append(msg)):
            bridge._handle_update(_make_update(ALLOWED_UID, "/test_quick"),
                                  TOKEN, ALLOWED_UID, SECRET)
        self.assertTrue(any("error" in r.lower() for r in sent))


# ═══════════════════════════════════════════════════════════════════════════════
# Job management
# ═══════════════════════════════════════════════════════════════════════════════

class TestJobManagement(unittest.TestCase):
    def setUp(self):
        self.mock_runner = MagicMock()

    def _run(self, cmd: str) -> list[str]:
        sent: list[str] = []
        with patch.object(bridge, "_JOB_RUNNER", self.mock_runner), \
             patch.object(bridge, "_send_reply", lambda t, c, msg: sent.append(msg)):
            bridge._handle_update(_make_update(ALLOWED_UID, cmd), TOKEN, ALLOWED_UID, SECRET)
        return sent

    def test_jobs_in_table(self):
        self.assertIn("/jobs", bridge.TELEGRAM_COMMANDS)
        self.assertIsNone(bridge.TELEGRAM_COMMANDS["/jobs"])

    def test_job_in_table(self):
        self.assertIn("/job", bridge.TELEGRAM_COMMANDS)
        self.assertIsNone(bridge.TELEGRAM_COMMANDS["/job"])

    def test_cancel_in_table(self):
        self.assertIn("/cancel", bridge.TELEGRAM_COMMANDS)
        self.assertIsNone(bridge.TELEGRAM_COMMANDS["/cancel"])

    def test_jobs_calls_list_recent(self):
        self.mock_runner.list_recent.return_value = []
        self._run("/jobs")
        self.mock_runner.list_recent.assert_called_once()

    def test_jobs_no_jobs_message(self):
        self.mock_runner.list_recent.return_value = []
        replies = self._run("/jobs")
        self.assertTrue(any("no jobs" in r.lower() for r in replies))

    def test_job_calls_status(self):
        self.mock_runner.status.return_value = {
            "id": "test-123", "type": "test-quick", "status": "succeeded",
            "start_time": "2026-06-22T10:00:00", "end_time": "2026-06-22T10:01:00",
            "returncode": 0, "log_path": "/tmp/test.log",
        }
        self.mock_runner.tail_log.return_value = "all tests passed"
        self._run("/job test-123")
        self.mock_runner.status.assert_called_once_with("test-123")

    def test_job_no_id_returns_usage(self):
        replies = self._run("/job")
        self.assertTrue(any("usage" in r.lower() for r in replies))

    def test_cancel_calls_cancel(self):
        self.mock_runner.cancel.return_value = True
        self._run("/cancel abc-123")
        self.mock_runner.cancel.assert_called_once_with("abc-123")

    def test_cancel_no_id_returns_usage(self):
        replies = self._run("/cancel")
        self.assertTrue(any("usage" in r.lower() for r in replies))

    def test_cancel_success_message(self):
        self.mock_runner.cancel.return_value = True
        replies = self._run("/cancel abc-123")
        self.assertTrue(any("cancel" in r.lower() for r in replies))

    def test_cancel_fail_message(self):
        self.mock_runner.cancel.return_value = False
        replies = self._run("/cancel abc-123")
        self.assertTrue(any("not" in r.lower() or "found" in r.lower() for r in replies))


# ═══════════════════════════════════════════════════════════════════════════════
# Capture command
# ═══════════════════════════════════════════════════════════════════════════════

class TestCaptureCommand(unittest.TestCase):
    def setUp(self):
        self.mock_runner = MagicMock()

    def _run(self, text: str) -> list[str]:
        sent: list[str] = []
        with patch.object(bridge, "_JOB_RUNNER", self.mock_runner), \
             patch.object(bridge, "_run_quick", return_value="captured."), \
             patch.object(bridge, "_send_reply", lambda t, c, msg: sent.append(msg)):
            bridge._handle_update(_make_update(ALLOWED_UID, text), TOKEN, ALLOWED_UID, SECRET)
        return sent

    def test_capture_in_table(self):
        self.assertIn("/capture", bridge.TELEGRAM_COMMANDS)
        self.assertIsNone(bridge.TELEGRAM_COMMANDS["/capture"])

    def test_capture_no_args_shows_usage(self):
        replies = self._run("/capture")
        self.assertTrue(any("usage" in r.lower() or "type" in r.lower() for r in replies))

    def test_capture_invalid_type_shows_error(self):
        replies = self._run("/capture widget some text")
        self.assertTrue(any("unknown" in r.lower() or "invalid" in r.lower() or "type" in r.lower()
                            for r in replies))

    def test_capture_idea_invokes_run_quick(self):
        called = []
        def fake_run_quick(argv, **kw):
            called.append(argv)
            return "ok"
        sent: list[str] = []
        with patch.object(bridge, "_run_quick", fake_run_quick), \
             patch.object(bridge, "_send_reply", lambda t, c, msg: sent.append(msg)):
            bridge._handle_update(_make_update(ALLOWED_UID, "/capture idea Fast PDF summarizer"),
                                  TOKEN, ALLOWED_UID, SECRET)
        self.assertTrue(len(called) > 0)
        argv = called[0]
        self.assertIn("/obsidian-capture", argv)
        self.assertIn("idea", argv)
        self.assertIn("Fast PDF summarizer", argv)

    def test_capture_no_text_shows_usage(self):
        replies = self._run("/capture idea")
        self.assertTrue(any("usage" in r.lower() for r in replies))

    def test_capture_valid_types(self):
        valid_types = ["idea", "decision", "bug", "fix", "note", "approval"]
        for t in valid_types:
            with self.subTest(type=t):
                called = []
                def fake_run(argv, **kw):
                    called.append(argv)
                    return "ok"
                with patch.object(bridge, "_run_quick", fake_run), \
                     patch.object(bridge, "_send_reply", lambda *a: None):
                    bridge._handle_update(_make_update(ALLOWED_UID, f"/capture {t} some text"),
                                          TOKEN, ALLOWED_UID, SECRET)
                self.assertTrue(len(called) > 0, f"No subprocess for type={t!r}")

    def test_capture_sanitizes_control_chars(self):
        captured_argv = []
        def fake_run(argv, **kw):
            captured_argv.extend(argv)
            return "ok"
        with patch.object(bridge, "_run_quick", fake_run), \
             patch.object(bridge, "_send_reply", lambda *a: None):
            bridge._handle_update(
                _make_update(ALLOWED_UID, "/capture idea hello\x00world\x01test"),
                TOKEN, ALLOWED_UID, SECRET,
            )
        # null bytes should be stripped from the argument
        for arg in captured_argv:
            self.assertNotIn("\x00", arg)


# ═══════════════════════════════════════════════════════════════════════════════
# Idea and plan commands
# ═══════════════════════════════════════════════════════════════════════════════

class TestIdeaAndPlanCommands(unittest.TestCase):
    def test_idea_in_table(self):
        self.assertIn("/idea", bridge.TELEGRAM_COMMANDS)
        self.assertIsNone(bridge.TELEGRAM_COMMANDS["/idea"])

    def test_plan_in_table(self):
        self.assertIn("/plan", bridge.TELEGRAM_COMMANDS)
        self.assertIsNone(bridge.TELEGRAM_COMMANDS["/plan"])

    def test_idea_no_text_shows_usage(self):
        sent: list[str] = []
        with patch.object(bridge, "_run_quick", return_value="ok"), \
             patch.object(bridge, "_send_reply", lambda t, c, msg: sent.append(msg)):
            bridge._handle_update(_make_update(ALLOWED_UID, "/idea"), TOKEN, ALLOWED_UID, SECRET)
        self.assertTrue(any("usage" in r.lower() for r in sent))

    def test_plan_no_text_shows_usage(self):
        sent: list[str] = []
        with patch.object(bridge, "_run_quick", return_value="ok"), \
             patch.object(bridge, "_send_reply", lambda t, c, msg: sent.append(msg)):
            bridge._handle_update(_make_update(ALLOWED_UID, "/plan"), TOKEN, ALLOWED_UID, SECRET)
        self.assertTrue(any("usage" in r.lower() for r in sent))

    def test_idea_calls_obsidian_capture(self):
        called = []
        def fake_run(argv, **kw):
            called.append(argv)
            return "captured"
        with patch.object(bridge, "_run_quick", fake_run), \
             patch.object(bridge, "_send_reply", lambda *a: None):
            bridge._handle_update(
                _make_update(ALLOWED_UID, "/idea Build a PDF summarizer"),
                TOKEN, ALLOWED_UID, SECRET,
            )
        self.assertTrue(any("/obsidian-capture" in str(a) for a in called))
        self.assertTrue(any("idea" in str(a) for a in called))


# ═══════════════════════════════════════════════════════════════════════════════
# Obsidian background commands
# ═══════════════════════════════════════════════════════════════════════════════

class TestObsidianBackgroundCommands(unittest.TestCase):
    def setUp(self):
        self.mock_runner = MagicMock()
        self.mock_runner.submit.return_value = "obsidian-review-20260622-101234-ab12"

    def _run(self, cmd: str) -> list[str]:
        sent: list[str] = []
        with patch.object(bridge, "_JOB_RUNNER", self.mock_runner), \
             patch.object(bridge, "_send_reply", lambda t, c, msg: sent.append(msg)):
            bridge._handle_update(_make_update(ALLOWED_UID, cmd), TOKEN, ALLOWED_UID, SECRET)
        return sent

    def test_obsidian_review_in_table(self):
        self.assertIn("/obsidian_review", bridge.TELEGRAM_COMMANDS)

    def test_obsidian_plan_in_table(self):
        self.assertIn("/obsidian_plan", bridge.TELEGRAM_COMMANDS)

    def test_obsidian_validate_in_table(self):
        self.assertIn("/obsidian_validate", bridge.TELEGRAM_COMMANDS)

    def test_memory_scan_in_table(self):
        self.assertIn("/memory_scan", bridge.TELEGRAM_COMMANDS)

    def test_obsidian_review_submits_job(self):
        self._run("/obsidian_review")
        self.mock_runner.submit.assert_called_once()
        name, _ = self.mock_runner.submit.call_args[0]
        self.assertEqual(name, "obsidian-review")

    def test_obsidian_plan_submits_job(self):
        self._run("/obsidian_plan")
        self.mock_runner.submit.assert_called_once()
        name, _ = self.mock_runner.submit.call_args[0]
        self.assertEqual(name, "obsidian-plan")

    def test_obsidian_validate_submits_job(self):
        self._run("/obsidian_validate")
        self.mock_runner.submit.assert_called_once()
        name, _ = self.mock_runner.submit.call_args[0]
        self.assertEqual(name, "obsidian-validate")

    def test_memory_scan_calls_run_quick(self):
        called = []
        with patch.object(bridge, "_run_quick", lambda *a, **k: called.append(a) or "ok"), \
             patch.object(bridge, "_send_reply", lambda *a: None):
            bridge._handle_update(_make_update(ALLOWED_UID, "/memory_scan"),
                                  TOKEN, ALLOWED_UID, SECRET)
        self.assertTrue(len(called) > 0)


# ═══════════════════════════════════════════════════════════════════════════════
# Repair gate
# ═══════════════════════════════════════════════════════════════════════════════

class TestRepairGate(unittest.TestCase):
    def test_repair_plan_in_table(self):
        self.assertIn("/repair_plan", bridge.TELEGRAM_COMMANDS)
        self.assertIsNone(bridge.TELEGRAM_COMMANDS["/repair_plan"])

    def test_repair_ok_in_table(self):
        self.assertIn("/repair_ok", bridge.TELEGRAM_COMMANDS)
        self.assertIsNone(bridge.TELEGRAM_COMMANDS["/repair_ok"])

    def test_repair_plan_generates_token(self):
        sent: list[str] = []
        mock_runner = MagicMock()
        with patch.object(bridge, "_JOB_RUNNER", mock_runner), \
             patch.object(bridge, "_send_reply", lambda t, c, msg: sent.append(msg)), \
             patch("py_compile.compile"):
            bridge._handle_update(_make_update(ALLOWED_UID, "/repair_plan"),
                                  TOKEN, ALLOWED_UID, SECRET)
        combined = " ".join(sent)
        self.assertIn("/repair_ok", combined)
        # Should contain an 8-char hex token
        tokens = re.findall(r'/repair_ok\s+([0-9a-f]{8})', combined)
        self.assertTrue(len(tokens) > 0, f"No token found in: {combined!r}")

    def test_repair_ok_invalid_token_rejected(self):
        sent: list[str] = []
        mock_runner = MagicMock()
        with patch.object(bridge, "_JOB_RUNNER", mock_runner), \
             patch.object(bridge, "_send_reply", lambda t, c, msg: sent.append(msg)):
            bridge._handle_update(_make_update(ALLOWED_UID, "/repair_ok badtoken"),
                                  TOKEN, ALLOWED_UID, SECRET)
        combined = " ".join(sent).lower()
        self.assertTrue("invalid" in combined or "expired" in combined,
                        f"Expected rejection message, got: {combined!r}")

    def test_repair_ok_without_token_shows_usage(self):
        sent: list[str] = []
        mock_runner = MagicMock()
        with patch.object(bridge, "_JOB_RUNNER", mock_runner), \
             patch.object(bridge, "_send_reply", lambda t, c, msg: sent.append(msg)):
            bridge._handle_update(_make_update(ALLOWED_UID, "/repair_ok"),
                                  TOKEN, ALLOWED_UID, SECRET)
        combined = " ".join(sent).lower()
        self.assertTrue("usage" in combined or "token" in combined)

    def test_repair_ok_valid_token_starts_job(self):
        mock_runner = MagicMock()
        mock_runner.submit.return_value = "repair-20260622-ab12"

        # First get a valid token
        sent_plan: list[str] = []
        with patch.object(bridge, "_JOB_RUNNER", mock_runner), \
             patch.object(bridge, "_send_reply", lambda t, c, msg: sent_plan.append(msg)), \
             patch("py_compile.compile"):
            bridge._handle_update(_make_update(ALLOWED_UID, "/repair_plan"),
                                  TOKEN, ALLOWED_UID, SECRET)

        tokens = re.findall(r'/repair_ok\s+([0-9a-f]{8})', " ".join(sent_plan))
        self.assertTrue(tokens, "repair_plan did not produce a token")
        token = tokens[0]

        # Now confirm with the token
        sent_confirm: list[str] = []
        with patch.object(bridge, "_JOB_RUNNER", mock_runner), \
             patch.object(bridge, "_send_reply", lambda t, c, msg: sent_confirm.append(msg)):
            bridge._handle_update(_make_update(ALLOWED_UID, f"/repair_ok {token}"),
                                  TOKEN, ALLOWED_UID, SECRET)

        mock_runner.submit.assert_called_once()
        combined = " ".join(sent_confirm).lower()
        self.assertTrue("repair" in combined or "job" in combined)

    def test_repair_ok_token_single_use(self):
        mock_runner = MagicMock()
        mock_runner.submit.return_value = "repair-20260622-ab12"

        sent_plan: list[str] = []
        with patch.object(bridge, "_JOB_RUNNER", mock_runner), \
             patch.object(bridge, "_send_reply", lambda t, c, msg: sent_plan.append(msg)), \
             patch("py_compile.compile"):
            bridge._handle_update(_make_update(ALLOWED_UID, "/repair_plan"),
                                  TOKEN, ALLOWED_UID, SECRET)

        tokens = re.findall(r'/repair_ok\s+([0-9a-f]{8})', " ".join(sent_plan))
        self.assertTrue(tokens)
        token = tokens[0]

        # First use — should succeed
        with patch.object(bridge, "_JOB_RUNNER", mock_runner), \
             patch.object(bridge, "_send_reply", lambda *a: None):
            bridge._handle_update(_make_update(ALLOWED_UID, f"/repair_ok {token}"),
                                  TOKEN, ALLOWED_UID, SECRET)

        # Second use — token consumed, should be rejected
        sent2: list[str] = []
        with patch.object(bridge, "_JOB_RUNNER", mock_runner), \
             patch.object(bridge, "_send_reply", lambda t, c, msg: sent2.append(msg)):
            bridge._handle_update(_make_update(ALLOWED_UID, f"/repair_ok {token}"),
                                  TOKEN, ALLOWED_UID, SECRET)
        combined = " ".join(sent2).lower()
        self.assertTrue("invalid" in combined or "expired" in combined)

    def test_repair_does_not_call_safe_api(self):
        routes = _api_calls(_make_update(ALLOWED_UID, "/repair_plan"))
        self.assertEqual(routes, [])

        routes2 = _api_calls(_make_update(ALLOWED_UID, "/repair_ok badtoken"))
        self.assertEqual(routes2, [])


# ═══════════════════════════════════════════════════════════════════════════════
# Git backup gate
# ═══════════════════════════════════════════════════════════════════════════════

class TestGitBackupGate(unittest.TestCase):
    def test_git_backup_in_table(self):
        self.assertIn("/git_backup", bridge.TELEGRAM_COMMANDS)
        self.assertIsNone(bridge.TELEGRAM_COMMANDS["/git_backup"])

    def test_backup_ok_in_table(self):
        self.assertIn("/backup_ok", bridge.TELEGRAM_COMMANDS)
        self.assertIsNone(bridge.TELEGRAM_COMMANDS["/backup_ok"])

    def test_git_backup_generates_token(self):
        sent: list[str] = []
        mock_runner = MagicMock()
        with patch.object(bridge, "_JOB_RUNNER", mock_runner), \
             patch.object(bridge, "_send_reply", lambda t, c, msg: sent.append(msg)), \
             patch("subprocess.run") as mock_sub:
            mock_sub.return_value = MagicMock(stdout="M file.py\n", returncode=0)
            bridge._handle_update(_make_update(ALLOWED_UID, "/git_backup"),
                                  TOKEN, ALLOWED_UID, SECRET)
        combined = " ".join(sent)
        self.assertIn("/backup_ok", combined)

    def test_backup_ok_invalid_token_rejected(self):
        sent: list[str] = []
        mock_runner = MagicMock()
        with patch.object(bridge, "_JOB_RUNNER", mock_runner), \
             patch.object(bridge, "_send_reply", lambda t, c, msg: sent.append(msg)):
            bridge._handle_update(_make_update(ALLOWED_UID, "/backup_ok badbad"),
                                  TOKEN, ALLOWED_UID, SECRET)
        combined = " ".join(sent).lower()
        self.assertTrue("invalid" in combined or "expired" in combined)

    def test_backup_ok_without_token_shows_usage(self):
        sent: list[str] = []
        mock_runner = MagicMock()
        with patch.object(bridge, "_JOB_RUNNER", mock_runner), \
             patch.object(bridge, "_send_reply", lambda t, c, msg: sent.append(msg)):
            bridge._handle_update(_make_update(ALLOWED_UID, "/backup_ok"),
                                  TOKEN, ALLOWED_UID, SECRET)
        combined = " ".join(sent).lower()
        self.assertTrue("usage" in combined or "token" in combined)

    def test_backup_gate_names_not_dangerous(self):
        dangerous = ["backup-now", "git-push", "git-commit"]
        for key in ["/git_backup", "/backup_ok"]:
            for pat in dangerous:
                self.assertNotIn(pat, key,
                                 f"Command {key!r} contains dangerous pattern {pat!r}")


# ═══════════════════════════════════════════════════════════════════════════════
# Confirmation gate internals
# ═══════════════════════════════════════════════════════════════════════════════

class TestConfirmationGate(unittest.TestCase):
    def setUp(self):
        bridge._PENDING.clear()

    def test_make_token_returns_8_hex(self):
        token = bridge._make_token("test_action")
        self.assertRegex(token, r'^[0-9a-f]{8}$')

    def test_consume_token_valid(self):
        token = bridge._make_token("my_action", {"k": "v"})
        result = bridge._consume_token(token)
        self.assertIsNotNone(result)
        self.assertEqual(result["action"], "my_action")
        self.assertEqual(result["meta"], {"k": "v"})

    def test_consume_token_single_use(self):
        token = bridge._make_token("my_action")
        bridge._consume_token(token)
        result2 = bridge._consume_token(token)
        self.assertIsNone(result2)

    def test_consume_token_invalid_returns_none(self):
        result = bridge._consume_token("deadbeef")
        self.assertIsNone(result)

    def test_consume_token_expired(self):
        # Artificially create an expired entry
        bridge._PENDING["expiredtok"] = {
            "action":     "test",
            "expires_at": time.time() - 10,   # already expired
            "meta":       {},
        }
        result = bridge._consume_token("expiredtok")
        self.assertIsNone(result, "Expired token should be rejected")

    def test_expire_tokens_cleans_up(self):
        bridge._PENDING["old1"] = {"action": "x", "expires_at": time.time() - 100, "meta": {}}
        bridge._PENDING["old2"] = {"action": "x", "expires_at": time.time() - 100, "meta": {}}
        tok = bridge._make_token("fresh")
        bridge._expire_tokens()
        self.assertNotIn("old1", bridge._PENDING)
        self.assertNotIn("old2", bridge._PENDING)
        self.assertIn(tok, bridge._PENDING)


# ═══════════════════════════════════════════════════════════════════════════════
# Text helpers
# ═══════════════════════════════════════════════════════════════════════════════

class TestTextHelpers(unittest.TestCase):
    def test_redact_tg_token(self):
        text = "Token: 1234567890:ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghi"
        result = bridge._redact(text)
        self.assertNotIn("ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghi", result)
        self.assertIn("[TOKEN-REDACTED]", result)

    def test_redact_api_key_env_pattern(self):
        text = "API_KEY=supersecretvalue123"
        result = bridge._redact(text)
        self.assertIn("[REDACTED]", result)
        self.assertNotIn("supersecretvalue123", result)

    def test_redact_secret_env_pattern(self):
        text = "ADWI_LOCAL=mypassword"
        result = bridge._redact(text)
        self.assertIn("[REDACTED]", result)

    def test_redact_passes_normal_text(self):
        text = "Adwi status: all systems nominal"
        self.assertEqual(bridge._redact(text), text)

    def test_sanitize_text_strips_null(self):
        result = bridge._sanitize_text("hello\x00world")
        self.assertNotIn("\x00", result)

    def test_sanitize_text_strips_control_chars(self):
        result = bridge._sanitize_text("hello\x01\x02world")
        self.assertNotIn("\x01", result)
        self.assertNotIn("\x02", result)

    def test_sanitize_text_truncates(self):
        long_text = "a" * 1000
        result    = bridge._sanitize_text(long_text)
        self.assertLessEqual(len(result), bridge._MAX_ARG_LEN + 10)

    def test_sanitize_text_preserves_normal(self):
        text   = "Build a fast PDF summarizer"
        result = bridge._sanitize_text(text)
        self.assertEqual(result, text)


# ═══════════════════════════════════════════════════════════════════════════════
# JobRunner unit tests
# ═══════════════════════════════════════════════════════════════════════════════

class TestJobRunner(unittest.TestCase):
    def setUp(self):
        import tempfile
        self.tmpdir = tempfile.TemporaryDirectory()
        self._orig_jobs_dir  = jr.JOBS_DIR
        self._orig_jobs_file = jr.JOBS_FILE
        jr.JOBS_DIR  = Path(self.tmpdir.name)
        jr.JOBS_FILE = Path(self.tmpdir.name) / "jobs.json"
        self.runner  = jr.JobRunner()

    def tearDown(self):
        jr.JOBS_DIR  = self._orig_jobs_dir
        jr.JOBS_FILE = self._orig_jobs_file
        self.tmpdir.cleanup()

    @staticmethod
    def _wait_done(runner, job_id: str, timeout: float = 5.0) -> dict | None:
        """Poll until a job leaves queued/running. Prevents tearDown tmpdir race."""
        deadline = time.time() + timeout
        while time.time() < deadline:
            j = runner.status(job_id)
            if j and j["status"] not in ("queued", "running"):
                return j
            time.sleep(0.05)
        return runner.status(job_id)

    def test_submit_returns_job_id(self):
        job_id = self.runner.submit("echo-test", [sys.executable, "-c", "print('hello')"])
        self.assertIsInstance(job_id, str)
        self.assertTrue(job_id.startswith("echo-test-"))
        self._wait_done(self.runner, job_id)  # let thread finish before tmpdir cleanup

    def test_submit_creates_job_record(self):
        job_id = self.runner.submit("mytest", [sys.executable, "-c", "pass"])
        time.sleep(0.2)
        j = self.runner.status(job_id)
        self.assertIsNotNone(j)
        self.assertEqual(j["type"], "mytest")
        self.assertIn(j["status"], ("queued", "running", "succeeded", "failed"))

    def test_successful_job_status(self):
        job_id = self.runner.submit("true-test", [sys.executable, "-c", "pass"])
        for _ in range(40):
            time.sleep(0.1)
            j = self.runner.status(job_id)
            if j and j["status"] not in ("queued", "running"):
                break
        j = self.runner.status(job_id)
        self.assertEqual(j["status"], "succeeded")
        self.assertEqual(j["returncode"], 0)

    def test_failed_job_status(self):
        job_id = self.runner.submit("false-test", [sys.executable, "-c", "import sys; sys.exit(1)"])
        for _ in range(40):
            time.sleep(0.1)
            j = self.runner.status(job_id)
            if j and j["status"] not in ("queued", "running"):
                break
        j = self.runner.status(job_id)
        self.assertEqual(j["status"], "failed")
        self.assertNotEqual(j["returncode"], 0)

    def test_job_output_in_log(self):
        job_id = self.runner.submit("echo-test", [sys.executable, "-c", "print('hello world')"])
        for _ in range(30):
            time.sleep(0.1)
            j = self.runner.status(job_id)
            if j and j["status"] not in ("queued", "running"):
                break
        tail = self.runner.tail_log(job_id)
        self.assertIn("hello world", tail)

    def test_list_recent_returns_jobs(self):
        j1 = self.runner.submit("j1", [sys.executable, "-c", "pass"])
        j2 = self.runner.submit("j2", [sys.executable, "-c", "pass"])
        self._wait_done(self.runner, j1)
        self._wait_done(self.runner, j2)
        jobs = self.runner.list_recent(5)
        self.assertGreaterEqual(len(jobs), 2)

    def test_status_unknown_id_returns_none(self):
        result = self.runner.status("no-such-job")
        self.assertIsNone(result)

    def test_tail_log_unknown_id(self):
        result = self.runner.tail_log("no-such-job")
        self.assertIn("not found", result.lower())

    def test_cancel_non_existent_returns_false(self):
        result = self.runner.cancel("no-such-job")
        self.assertFalse(result)

    def test_state_persists_to_json(self):
        job_id = self.runner.submit("persist-test", [sys.executable, "-c", "pass"])
        self._wait_done(self.runner, job_id)
        self.assertTrue(jr.JOBS_FILE.exists())
        data = json.loads(jr.JOBS_FILE.read_text())
        self.assertIn(job_id, data)


# ═══════════════════════════════════════════════════════════════════════════════
# Test job argv sanity (Wave 5 regression — prevents pytest-only flags in unittest jobs)
# ═══════════════════════════════════════════════════════════════════════════════

class TestTestJobArgvSanity(unittest.TestCase):
    """Ensure _TEST_JOBS argv lists contain no pytest-only flags."""

    # Flags that are valid for pytest but cause "unrecognized arguments" in python -m unittest
    PYTEST_ONLY_FLAGS = ("--tb=", "--cov=", "--cov-report", "--cache-show",
                         "--lf", "--ff", "--sw", "--randomly")

    def test_no_pytest_flags_in_any_test_job(self):
        for cmd, (name, argv) in bridge._TEST_JOBS.items():
            for arg in argv:
                for flag in self.PYTEST_ONLY_FLAGS:
                    self.assertFalse(
                        arg.startswith(flag),
                        f"_TEST_JOBS[{cmd!r}] argv contains pytest-only flag "
                        f"{arg!r} (would fail python -m unittest)",
                    )

    def test_unittest_jobs_use_unittest_runner(self):
        for cmd, (name, argv) in bridge._TEST_JOBS.items():
            if "-m" in argv:
                m_idx = argv.index("-m")
                runner = argv[m_idx + 1] if m_idx + 1 < len(argv) else ""
                self.assertEqual(runner, "unittest",
                                 f"_TEST_JOBS[{cmd!r}] uses -m {runner!r}, expected 'unittest'")

    def test_all_test_job_argv_are_lists(self):
        for cmd, (name, argv) in bridge._TEST_JOBS.items():
            self.assertIsInstance(argv, list,
                                  f"_TEST_JOBS[{cmd!r}] argv must be a list, not {type(argv)}")
            self.assertGreater(len(argv), 0,
                               f"_TEST_JOBS[{cmd!r}] argv must be non-empty")

    def test_test_job_argv_smoke_via_subprocess(self):
        """Quick real subprocess: python -c 'import unittest; unittest.main()' with --help exits 0."""
        import tempfile
        import subprocess as _sp
        # Verify that python3 -m unittest --help succeeds (exit 0) — proves runner invocation works
        result = _sp.run(
            [sys.executable, "-m", "unittest", "--help"],
            capture_output=True, timeout=10,
        )
        self.assertEqual(result.returncode, 0,
                         f"python -m unittest --help failed: {result.stderr.decode()[:200]}")


# ═══════════════════════════════════════════════════════════════════════════════
# Loop foundation commands (Wave 5)
# ═══════════════════════════════════════════════════════════════════════════════

class TestLoopCommands(unittest.TestCase):
    def setUp(self):
        self.mock_runner = MagicMock()
        self.mock_runner.submit.return_value = "learn-nlu-20260622-ab12"
        bridge._PENDING.clear()

    def _run(self, text: str) -> list[str]:
        sent: list[str] = []
        with patch.object(bridge, "_JOB_RUNNER", self.mock_runner), \
             patch.object(bridge, "_send_reply", lambda t, c, msg: sent.append(msg)):
            bridge._handle_update(_make_update(ALLOWED_UID, text), TOKEN, ALLOWED_UID, SECRET)
        return sent

    def test_learn_plan_in_table(self):
        self.assertIn("/learn_plan", bridge.TELEGRAM_COMMANDS)
        self.assertIsNone(bridge.TELEGRAM_COMMANDS["/learn_plan"])

    def test_learn_ok_in_table(self):
        self.assertIn("/learn_ok", bridge.TELEGRAM_COMMANDS)
        self.assertIsNone(bridge.TELEGRAM_COMMANDS["/learn_ok"])

    def test_implement_plan_in_table(self):
        self.assertIn("/implement_plan", bridge.TELEGRAM_COMMANDS)
        self.assertIsNone(bridge.TELEGRAM_COMMANDS["/implement_plan"])

    def test_implement_ok_in_table(self):
        self.assertIn("/implement_ok", bridge.TELEGRAM_COMMANDS)
        self.assertIsNone(bridge.TELEGRAM_COMMANDS["/implement_ok"])

    def test_loop_status_in_table(self):
        self.assertIn("/loop_status", bridge.TELEGRAM_COMMANDS)
        self.assertIsNone(bridge.TELEGRAM_COMMANDS["/loop_status"])

    def test_learn_plan_generates_token(self):
        replies = self._run("/learn_plan")
        combined = " ".join(replies)
        self.assertIn("/learn_ok", combined)
        tokens = re.findall(r'/learn_ok\s+([0-9a-f]{8})', combined)
        self.assertTrue(len(tokens) > 0, f"No token found in: {combined!r}")

    def test_learn_ok_invalid_token_rejected(self):
        replies = self._run("/learn_ok deadbeef")
        combined = " ".join(replies).lower()
        self.assertTrue("invalid" in combined or "expired" in combined)

    def test_learn_ok_no_token_shows_usage(self):
        replies = self._run("/learn_ok")
        combined = " ".join(replies).lower()
        self.assertTrue("usage" in combined or "token" in combined)

    def test_learn_ok_valid_token_starts_job(self):
        sent_plan: list[str] = []
        with patch.object(bridge, "_JOB_RUNNER", self.mock_runner), \
             patch.object(bridge, "_send_reply", lambda t, c, msg: sent_plan.append(msg)):
            bridge._handle_update(_make_update(ALLOWED_UID, "/learn_plan"),
                                  TOKEN, ALLOWED_UID, SECRET)
        tokens = re.findall(r'/learn_ok\s+([0-9a-f]{8})', " ".join(sent_plan))
        self.assertTrue(tokens, "learn_plan did not produce a token")

        sent_confirm: list[str] = []
        with patch.object(bridge, "_JOB_RUNNER", self.mock_runner), \
             patch.object(bridge, "_send_reply", lambda t, c, msg: sent_confirm.append(msg)):
            bridge._handle_update(_make_update(ALLOWED_UID, f"/learn_ok {tokens[0]}"),
                                  TOKEN, ALLOWED_UID, SECRET)
        self.mock_runner.submit.assert_called_once()
        name, argv = self.mock_runner.submit.call_args[0]
        self.assertEqual(name, "learn-nlu")
        self.assertNotIn("--tb=short", argv)

    def test_implement_plan_no_goal_shows_usage(self):
        replies = self._run("/implement_plan")
        combined = " ".join(replies).lower()
        self.assertTrue("usage" in combined or "goal" in combined)

    def test_implement_plan_generates_token(self):
        replies = self._run("/implement_plan Build a voice input feature")
        combined = " ".join(replies)
        self.assertIn("/implement_ok", combined)
        tokens = re.findall(r'/implement_ok\s+([0-9a-f]{8})', combined)
        self.assertTrue(len(tokens) > 0)

    def test_implement_ok_valid_token_records_to_obsidian(self):
        sent_plan: list[str] = []
        with patch.object(bridge, "_JOB_RUNNER", self.mock_runner), \
             patch.object(bridge, "_send_reply", lambda t, c, msg: sent_plan.append(msg)):
            bridge._handle_update(
                _make_update(ALLOWED_UID, "/implement_plan Add voice input"),
                TOKEN, ALLOWED_UID, SECRET,
            )
        tokens = re.findall(r'/implement_ok\s+([0-9a-f]{8})', " ".join(sent_plan))
        self.assertTrue(tokens)

        with patch.object(bridge, "_JOB_RUNNER", self.mock_runner), \
             patch.object(bridge, "_send_reply", lambda *a: None):
            bridge._handle_update(_make_update(ALLOWED_UID, f"/implement_ok {tokens[0]}"),
                                  TOKEN, ALLOWED_UID, SECRET)
        self.mock_runner.submit.assert_called()
        name, argv = self.mock_runner.submit.call_args[0]
        self.assertEqual(name, "implement-capture")
        self.assertIn("/obsidian-capture", argv)
        self.assertIn("approval", argv)
        self.assertTrue(any("IMPLEMENT:" in a for a in argv))

    def test_implement_ok_token_single_use(self):
        sent_plan: list[str] = []
        with patch.object(bridge, "_JOB_RUNNER", self.mock_runner), \
             patch.object(bridge, "_send_reply", lambda t, c, msg: sent_plan.append(msg)):
            bridge._handle_update(
                _make_update(ALLOWED_UID, "/implement_plan Test goal"),
                TOKEN, ALLOWED_UID, SECRET,
            )
        tokens = re.findall(r'/implement_ok\s+([0-9a-f]{8})', " ".join(sent_plan))
        self.assertTrue(tokens)
        tok = tokens[0]

        with patch.object(bridge, "_JOB_RUNNER", self.mock_runner), \
             patch.object(bridge, "_send_reply", lambda *a: None):
            bridge._handle_update(_make_update(ALLOWED_UID, f"/implement_ok {tok}"),
                                  TOKEN, ALLOWED_UID, SECRET)

        sent2: list[str] = []
        with patch.object(bridge, "_JOB_RUNNER", self.mock_runner), \
             patch.object(bridge, "_send_reply", lambda t, c, msg: sent2.append(msg)):
            bridge._handle_update(_make_update(ALLOWED_UID, f"/implement_ok {tok}"),
                                  TOKEN, ALLOWED_UID, SECRET)
        combined = " ".join(sent2).lower()
        self.assertTrue("invalid" in combined or "expired" in combined)

    def test_loop_status_returns_reply(self):
        self.mock_runner.list_recent.return_value = []
        replies = self._run("/loop_status")
        self.assertGreater(len(replies), 0)

    def test_loop_commands_do_not_call_safe_api(self):
        for cmd in ["/learn_plan", "/loop_status"]:
            with self.subTest(cmd=cmd):
                routes = _api_calls(_make_update(ALLOWED_UID, cmd))
                self.assertEqual(routes, [])

    def test_implement_plan_sanitizes_goal(self):
        replies = self._run("/implement_plan hello\x00world\x01test")
        combined = " ".join(replies)
        self.assertNotIn("\x00", combined)


# ═══════════════════════════════════════════════════════════════════════════════
# /telegram_smoke command (Wave 6)
# ═══════════════════════════════════════════════════════════════════════════════

class TestTelegramSmokeCommand(unittest.TestCase):
    """Tests for the /telegram_smoke background command."""

    def setUp(self):
        self.mock_runner = MagicMock()
        self.mock_runner.submit.return_value = "telegram-smoke-20260622-ab12"

    def _run(self, text: str) -> list[str]:
        sent: list[str] = []
        with patch.object(bridge, "_JOB_RUNNER", self.mock_runner), \
             patch.object(bridge, "_send_reply", lambda t, c, msg: sent.append(msg)):
            bridge._handle_update(_make_update(ALLOWED_UID, text), TOKEN, ALLOWED_UID, SECRET)
        return sent

    def test_telegram_smoke_in_table(self):
        self.assertIn("/telegram_smoke", bridge.TELEGRAM_COMMANDS)
        self.assertIsNone(bridge.TELEGRAM_COMMANDS["/telegram_smoke"])

    def test_telegram_smoke_submits_job(self):
        self._run("/telegram_smoke")
        self.mock_runner.submit.assert_called_once()
        name, argv = self.mock_runner.submit.call_args[0]
        self.assertEqual(name, "telegram-smoke")
        self.assertIsInstance(argv, list)

    def test_telegram_smoke_argv_includes_smoke_script(self):
        self._run("/telegram_smoke")
        _, argv = self.mock_runner.submit.call_args[0]
        script_arg = " ".join(argv)
        self.assertIn("smoke_telegram_jobs.py", script_arg)

    def test_telegram_smoke_uses_quick_mode(self):
        """Default Telegram invocation uses --quick so /test_all doesn't block for 3 min."""
        self._run("/telegram_smoke")
        _, argv = self.mock_runner.submit.call_args[0]
        self.assertIn("--quick", argv)

    def test_telegram_smoke_reply_contains_job_id(self):
        replies = self._run("/telegram_smoke")
        job_id = self.mock_runner.submit.return_value
        self.assertTrue(any(job_id in r for r in replies),
                        f"No reply contained job ID {job_id!r}")

    def test_telegram_smoke_no_runner_returns_error(self):
        sent: list[str] = []
        with patch.object(bridge, "_JOB_RUNNER", None), \
             patch.object(bridge, "_send_reply", lambda t, c, msg: sent.append(msg)):
            bridge._handle_update(_make_update(ALLOWED_UID, "/telegram_smoke"),
                                  TOKEN, ALLOWED_UID, SECRET)
        self.assertTrue(any("error" in r.lower() for r in sent))

    def test_telegram_smoke_does_not_call_safe_api(self):
        routes = _api_calls(_make_update(ALLOWED_UID, "/telegram_smoke"))
        self.assertEqual(routes, [])

    def test_telegram_smoke_in_menu(self):
        self.assertIn("/telegram_smoke", bridge.MENU_TEXT)


# ═══════════════════════════════════════════════════════════════════════════════
# Smoke script structural checks (Wave 6)
# ═══════════════════════════════════════════════════════════════════════════════

class TestSmokeScriptStructure(unittest.TestCase):
    """Verify smoke_telegram_jobs.py loads real _TEST_JOBS and has correct structure."""

    _SMOKE_PATH = _ROOT / "adwi" / "scripts" / "smoke_telegram_jobs.py"

    def test_smoke_script_exists(self):
        self.assertTrue(self._SMOKE_PATH.exists(),
                        f"smoke_telegram_jobs.py not found at {self._SMOKE_PATH}")

    def test_smoke_script_compiles(self):
        import py_compile
        try:
            py_compile.compile(str(self._SMOKE_PATH), doraise=True)
        except py_compile.PyCompileError as exc:
            self.fail(f"smoke_telegram_jobs.py has syntax error: {exc}")

    def test_smoke_script_references_test_jobs(self):
        """The smoke script must load _TEST_JOBS from bot.py, not use synthetic argv."""
        source = self._SMOKE_PATH.read_text(encoding="utf-8")
        self.assertIn("_TEST_JOBS", source,
                      "smoke script must reference _TEST_JOBS from bot.py")
        self.assertIn("BOT_PATH", source,
                      "smoke script must load bot.py to read _TEST_JOBS")

    def test_smoke_script_uses_tmpdir(self):
        """Must redirect jobs to tmpdir to avoid polluting adwi/logs/telegram-jobs/."""
        source = self._SMOKE_PATH.read_text(encoding="utf-8")
        self.assertIn("TemporaryDirectory", source,
                      "smoke script must redirect JobRunner to a temp dir")

    def test_smoke_script_has_phase2(self):
        source = self._SMOKE_PATH.read_text(encoding="utf-8")
        self.assertIn("Phase 2", source,
                      "smoke script must have a Phase 2 section that exercises _TEST_JOBS")

    def test_smoke_script_supports_quick_flag(self):
        source = self._SMOKE_PATH.read_text(encoding="utf-8")
        self.assertIn("--quick", source,
                      "smoke script must support --quick to skip /test_all")

    def test_test_jobs_all_referenced_in_smoke_timeouts(self):
        """Every _TEST_JOBS key should have an explicit timeout in the smoke script."""
        source = self._SMOKE_PATH.read_text(encoding="utf-8")
        for tg_cmd in bridge._TEST_JOBS:
            self.assertIn(tg_cmd, source,
                          f"smoke script missing explicit handling for {tg_cmd!r}")


# ═══════════════════════════════════════════════════════════════════════════════
# /telegram_smoke_full (Wave 7)
# ═══════════════════════════════════════════════════════════════════════════════

class TestTelegramSmokeFull(unittest.TestCase):
    """Tests for the /telegram_smoke_full background command."""

    def setUp(self):
        self.mock_runner = MagicMock()
        self.mock_runner.submit.return_value = "telegram-smoke-full-20260622-ab12"

    def _run(self, text: str) -> list[str]:
        sent: list[str] = []
        with patch.object(bridge, "_JOB_RUNNER", self.mock_runner), \
             patch.object(bridge, "_send_reply", lambda t, c, msg: sent.append(msg)):
            bridge._handle_update(_make_update(ALLOWED_UID, text), TOKEN, ALLOWED_UID, SECRET)
        return sent

    def test_telegram_smoke_full_in_table(self):
        self.assertIn("/telegram_smoke_full", bridge.TELEGRAM_COMMANDS)
        self.assertIsNone(bridge.TELEGRAM_COMMANDS["/telegram_smoke_full"])

    def test_telegram_smoke_full_submits_job(self):
        self._run("/telegram_smoke_full")
        self.mock_runner.submit.assert_called_once()
        name, argv = self.mock_runner.submit.call_args[0]
        self.assertEqual(name, "telegram-smoke-full")

    def test_telegram_smoke_full_does_not_use_quick(self):
        """Full smoke must NOT pass --quick so /test_all is included."""
        self._run("/telegram_smoke_full")
        _, argv = self.mock_runner.submit.call_args[0]
        self.assertNotIn("--quick", argv)

    def test_telegram_smoke_full_argv_includes_smoke_script(self):
        self._run("/telegram_smoke_full")
        _, argv = self.mock_runner.submit.call_args[0]
        self.assertIn("smoke_telegram_jobs.py", " ".join(argv))

    def test_telegram_smoke_full_reply_contains_job_id(self):
        replies = self._run("/telegram_smoke_full")
        job_id = self.mock_runner.submit.return_value
        self.assertTrue(any(job_id in r for r in replies))

    def test_telegram_smoke_full_does_not_call_safe_api(self):
        routes = _api_calls(_make_update(ALLOWED_UID, "/telegram_smoke_full"))
        self.assertEqual(routes, [])

    def test_telegram_smoke_full_in_menu(self):
        self.assertIn("/telegram_smoke_full", bridge.MENU_TEXT)


# ═══════════════════════════════════════════════════════════════════════════════
# /telegram_validate (Wave 7)
# ═══════════════════════════════════════════════════════════════════════════════

class TestTelegramValidateCommand(unittest.TestCase):
    """Tests for the /telegram_validate background command."""

    def setUp(self):
        self.mock_runner = MagicMock()
        self.mock_runner.submit.return_value = "telegram-validate-20260622-cd34"

    def _run(self, text: str) -> list[str]:
        sent: list[str] = []
        with patch.object(bridge, "_JOB_RUNNER", self.mock_runner), \
             patch.object(bridge, "_send_reply", lambda t, c, msg: sent.append(msg)):
            bridge._handle_update(_make_update(ALLOWED_UID, text), TOKEN, ALLOWED_UID, SECRET)
        return sent

    def test_telegram_validate_in_table(self):
        self.assertIn("/telegram_validate", bridge.TELEGRAM_COMMANDS)
        self.assertIsNone(bridge.TELEGRAM_COMMANDS["/telegram_validate"])

    def test_telegram_validate_submits_job(self):
        self._run("/telegram_validate")
        self.mock_runner.submit.assert_called_once()
        name, argv = self.mock_runner.submit.call_args[0]
        self.assertEqual(name, "telegram-validate")

    def test_telegram_validate_argv_includes_validate_script(self):
        self._run("/telegram_validate")
        _, argv = self.mock_runner.submit.call_args[0]
        self.assertIn("validate_telegram_bridge.py", " ".join(argv))

    def test_telegram_validate_reply_contains_job_id(self):
        replies = self._run("/telegram_validate")
        job_id = self.mock_runner.submit.return_value
        self.assertTrue(any(job_id in r for r in replies))

    def test_telegram_validate_does_not_call_safe_api(self):
        routes = _api_calls(_make_update(ALLOWED_UID, "/telegram_validate"))
        self.assertEqual(routes, [])

    def test_telegram_validate_in_menu(self):
        self.assertIn("/telegram_validate", bridge.MENU_TEXT)


# ═══════════════════════════════════════════════════════════════════════════════
# Validator script structural checks (Wave 7)
# ═══════════════════════════════════════════════════════════════════════════════

class TestValidateScriptStructure(unittest.TestCase):
    """Verify validate_telegram_bridge.py exists and has correct structure."""

    _VALIDATE_PATH = _ROOT / "adwi" / "scripts" / "validate_telegram_bridge.py"

    def test_validate_script_exists(self):
        self.assertTrue(self._VALIDATE_PATH.exists(),
                        f"validate_telegram_bridge.py not found at {self._VALIDATE_PATH}")

    def test_validate_script_compiles(self):
        import py_compile
        try:
            py_compile.compile(str(self._VALIDATE_PATH), doraise=True)
        except py_compile.PyCompileError as exc:
            self.fail(f"validate_telegram_bridge.py has syntax error: {exc}")

    def test_validate_script_is_stdlib_only(self):
        """Must not import third-party packages — only stdlib is available standalone."""
        source = self._VALIDATE_PATH.read_text(encoding="utf-8")
        third_party = ["requests", "flask", "aiohttp", "pydantic", "httpx"]
        for pkg in third_party:
            self.assertNotIn(f"import {pkg}", source,
                             f"validate_telegram_bridge.py must not import {pkg!r}")

    def test_validate_script_checks_telegram_commands(self):
        source = self._VALIDATE_PATH.read_text(encoding="utf-8")
        self.assertIn("TELEGRAM_COMMANDS", source)

    def test_validate_script_checks_allowed_commands(self):
        source = self._VALIDATE_PATH.read_text(encoding="utf-8")
        self.assertIn("ALLOWED_COMMANDS", source)

    def test_validate_script_checks_forbidden_routes(self):
        source = self._VALIDATE_PATH.read_text(encoding="utf-8")
        self.assertIn("run-bash", source,
                      "validator must check for forbidden route patterns")

    def test_validate_script_exits_nonzero_on_failure(self):
        """Script must call sys.exit(1) or return non-zero on failure."""
        source = self._VALIDATE_PATH.read_text(encoding="utf-8")
        self.assertIn("sys.exit", source)


# ═══════════════════════════════════════════════════════════════════════════════
# Existing invariants still hold
# ═══════════════════════════════════════════════════════════════════════════════

class TestExistingInvariantsStillHold(unittest.TestCase):
    """Sanity-check that the safety constraints from earlier waves are untouched."""

    FORBIDDEN_FROM_TELEGRAM = {
        "/adwi-e2e-auto-loop-start",
        "/adwi-e2e-auto-loop-cancel",
        "/adwi-backup",
        "/adwi-nightly",
        "/adwi-self-heal",
        "/auto-ai-maintenance",
    }

    def test_forbidden_routes_not_in_telegram(self):
        tg_routes = set(bridge.TELEGRAM_COMMANDS.values())
        for route in self.FORBIDDEN_FROM_TELEGRAM:
            self.assertNotIn(route, tg_routes,
                             f"Forbidden route {route!r} found in TELEGRAM_COMMANDS values")

    def test_ping_still_returns_pong(self):
        replies = _replies(_make_update(ALLOWED_UID, "/ping"))
        self.assertTrue(any("pong" in r.lower() for r in replies))

    def test_help_still_lists_status(self):
        replies = _replies(_make_update(ALLOWED_UID, "/help"))
        combined = " ".join(replies)
        self.assertIn("/status", combined)
        self.assertIn("/doctor", combined)

    def test_unknown_sender_silently_dropped(self):
        sent: list[str] = []
        with patch.object(bridge, "_send_reply", lambda t, c, msg: sent.append(msg)):
            bridge._handle_update(_make_update(999999, "/status"), TOKEN, ALLOWED_UID, SECRET)
        self.assertEqual(sent, [])

    def test_new_locally_handled_cmds_do_not_call_safe_api(self):
        locally_handled = [
            "/menu", "/test_quick", "/test_nlu", "/test_obsidian", "/test_all",
            "/tests_status", "/jobs", "/repair_plan", "/repair_ok",
            "/git_backup", "/backup_ok",
            "/learn_plan", "/loop_status", "/telegram_smoke",
            "/telegram_smoke_full", "/telegram_validate",
            "/e2e_plan", "/e2e_ok", "/e2e_report",
            "/e2e_cancel_plan", "/e2e_cancel_ok",
            "/e2e_preflight", "/control_center",
        ]
        for cmd in locally_handled:
            with self.subTest(cmd=cmd):
                routes = _api_calls(_make_update(ALLOWED_UID, cmd))
                self.assertEqual(routes, [],
                                 f"{cmd} must not dispatch to Safe API")


# ═══════════════════════════════════════════════════════════════════════════════
# /e2e_plan command (Wave 8)
# ═══════════════════════════════════════════════════════════════════════════════

class TestE2EPlanCommand(unittest.TestCase):
    """Tests for /e2e_plan — read-only, generates confirmation token."""

    def _plan_reply(self, args: str = "") -> str:
        return _local_reply("/e2e_plan", args)

    def test_e2e_plan_in_table(self):
        self.assertIn("/e2e_plan", bridge.TELEGRAM_COMMANDS)
        self.assertIsNone(bridge.TELEGRAM_COMMANDS["/e2e_plan"])

    def test_e2e_plan_default_mode_is_analyze(self):
        reply = self._plan_reply()
        self.assertIn("ANALYZE", reply)

    def test_e2e_plan_reply_contains_confirm_token(self):
        reply = self._plan_reply()
        self.assertIn("/e2e_ok", reply)
        # Token pattern: /e2e_ok followed by 8 hex chars
        self.assertRegex(reply, r"/e2e_ok\s+[0-9a-f]{8}")

    def test_e2e_plan_default_target_98(self):
        reply = self._plan_reply()
        self.assertIn("98", reply)

    def test_e2e_plan_default_cycles_1(self):
        reply = self._plan_reply()
        self.assertIn("Max cycles: 1", reply)

    def test_e2e_plan_dry_run_mode(self):
        reply = self._plan_reply("dry-run 95 2")
        self.assertIn("DRY-RUN", reply)
        self.assertIn("95", reply)
        self.assertIn("Max cycles: 2", reply)

    def test_e2e_plan_full_mode_warns_mutating(self):
        reply = self._plan_reply("full 98 3")
        self.assertIn("FULL", reply)
        self.assertIn("WARNING", reply)
        self.assertIn("MUTATING", reply)

    def test_e2e_plan_analyze_no_warning(self):
        reply = self._plan_reply("analyze")
        self.assertNotIn("WARNING", reply)

    def test_e2e_plan_target_clamped_high(self):
        """Target above 100 is clamped to 100."""
        mode, target, _ = bridge._parse_e2e_args("analyze 999 1")
        self.assertEqual(target, 100.0)

    def test_e2e_plan_target_clamped_low(self):
        """Target below 80 is clamped to 80."""
        mode, target, _ = bridge._parse_e2e_args("analyze 10 1")
        self.assertEqual(target, 80.0)

    def test_e2e_plan_cycles_clamped_high(self):
        mode, _, cycles = bridge._parse_e2e_args("analyze 98 99")
        self.assertEqual(cycles, 5)

    def test_e2e_plan_cycles_clamped_low(self):
        mode, _, cycles = bridge._parse_e2e_args("analyze 98 0")
        self.assertEqual(cycles, 1)

    def test_e2e_plan_does_not_call_safe_api(self):
        routes = _api_calls(_make_update(ALLOWED_UID, "/e2e_plan"))
        self.assertEqual(routes, [])

    def test_e2e_plan_in_menu(self):
        self.assertIn("/e2e_plan", bridge.MENU_TEXT)


# ═══════════════════════════════════════════════════════════════════════════════
# /e2e_ok command (Wave 8)
# ═══════════════════════════════════════════════════════════════════════════════

class TestE2EConfirm(unittest.TestCase):
    """Tests for /e2e_ok — token validation and job submission."""

    def _make_e2e_token(self, mode="analyze", target=98.0, cycles=1) -> str:
        return bridge._make_token("e2e", {"mode": mode, "target": target, "max_cycles": cycles})

    def _confirm(self, token_val: str, mock_runner=None) -> str:
        return _local_reply("/e2e_ok", token_val, mock_runner=mock_runner)

    def test_e2e_ok_rejects_empty_token(self):
        reply = self._confirm("")
        self.assertIn("Usage", reply)

    def test_e2e_ok_rejects_invalid_token(self):
        reply = self._confirm("deadbeef")
        self.assertIn("Invalid or expired", reply)

    def test_e2e_ok_rejects_expired_token(self):
        token = bridge._make_token("e2e", {"mode": "analyze", "target": 98.0, "max_cycles": 1})
        bridge._PENDING[token]["expires_at"] = time.time() - 1
        reply = self._confirm(token)
        self.assertIn("Invalid or expired", reply)

    def test_e2e_ok_rejects_wrong_action_token(self):
        token = bridge._make_token("repair", {})
        reply = self._confirm(token)
        self.assertIn("different action", reply)

    def test_e2e_ok_analyze_argv_has_analyze_only(self):
        token      = self._make_e2e_token(mode="analyze")
        mock_r     = MagicMock()
        mock_r.submit.return_value = "e2e-analyze-test-id"
        self._confirm(token, mock_runner=mock_r)
        _, argv = mock_r.submit.call_args[0]
        self.assertIn("--analyze-only", argv)
        self.assertNotIn("--dry-run", argv)

    def test_e2e_ok_dry_run_argv_has_dry_run(self):
        token  = self._make_e2e_token(mode="dry-run")
        mock_r = MagicMock()
        mock_r.submit.return_value = "e2e-dry-run-test-id"
        self._confirm(token, mock_runner=mock_r)
        _, argv = mock_r.submit.call_args[0]
        self.assertIn("--dry-run", argv)
        self.assertNotIn("--analyze-only", argv)

    def test_e2e_ok_full_argv_has_no_flag(self):
        token  = self._make_e2e_token(mode="full")
        mock_r = MagicMock()
        mock_r.submit.return_value = "e2e-full-test-id"
        self._confirm(token, mock_runner=mock_r)
        _, argv = mock_r.submit.call_args[0]
        self.assertNotIn("--analyze-only", argv)
        self.assertNotIn("--dry-run", argv)

    def test_e2e_ok_job_name_analyze(self):
        token  = self._make_e2e_token(mode="analyze")
        mock_r = MagicMock()
        mock_r.submit.return_value = "e2e-analyze-test-id"
        self._confirm(token, mock_runner=mock_r)
        name, _ = mock_r.submit.call_args[0]
        self.assertEqual(name, "e2e-analyze")

    def test_e2e_ok_job_name_dry_run(self):
        token  = self._make_e2e_token(mode="dry-run")
        mock_r = MagicMock()
        mock_r.submit.return_value = "e2e-dry-run-test-id"
        self._confirm(token, mock_runner=mock_r)
        name, _ = mock_r.submit.call_args[0]
        self.assertEqual(name, "e2e-dry-run")

    def test_e2e_ok_job_name_full(self):
        token  = self._make_e2e_token(mode="full")
        mock_r = MagicMock()
        mock_r.submit.return_value = "e2e-full-test-id"
        self._confirm(token, mock_runner=mock_r)
        name, _ = mock_r.submit.call_args[0]
        self.assertEqual(name, "e2e-full")

    def test_e2e_ok_argv_includes_target(self):
        token  = self._make_e2e_token(mode="analyze", target=95.0)
        mock_r = MagicMock()
        mock_r.submit.return_value = "e2e-analyze-test-id"
        self._confirm(token, mock_runner=mock_r)
        _, argv = mock_r.submit.call_args[0]
        self.assertIn("95.0", argv)

    def test_e2e_ok_argv_includes_max_cycles(self):
        token  = self._make_e2e_token(mode="analyze", cycles=3)
        mock_r = MagicMock()
        mock_r.submit.return_value = "e2e-analyze-test-id"
        self._confirm(token, mock_runner=mock_r)
        _, argv = mock_r.submit.call_args[0]
        self.assertIn("3", argv)

    def test_e2e_ok_reply_contains_job_id(self):
        token  = self._make_e2e_token()
        mock_r = MagicMock()
        mock_r.submit.return_value = "e2e-analyze-abc12345"
        reply  = self._confirm(token, mock_runner=mock_r)
        self.assertIn("e2e-analyze-abc12345", reply)

    def test_e2e_ok_token_is_single_use(self):
        """After consuming a token, a second /e2e_ok with the same token is rejected."""
        token  = self._make_e2e_token()
        mock_r = MagicMock()
        mock_r.submit.return_value = "some-id"
        self._confirm(token, mock_runner=mock_r)    # first: OK
        reply2 = self._confirm(token, mock_runner=mock_r)   # second: rejected
        self.assertIn("Invalid or expired", reply2)

    def test_e2e_ok_does_not_call_safe_api(self):
        routes = _api_calls(_make_update(ALLOWED_UID, "/e2e_ok"))
        self.assertEqual(routes, [])


# ═══════════════════════════════════════════════════════════════════════════════
# /e2e_report command (Wave 8)
# ═══════════════════════════════════════════════════════════════════════════════

class TestE2EReport(unittest.TestCase):
    """Tests for /e2e_report — read-only summary."""

    def test_e2e_report_in_table(self):
        self.assertIn("/e2e_report", bridge.TELEGRAM_COMMANDS)
        self.assertIsNone(bridge.TELEGRAM_COMMANDS["/e2e_report"])

    def test_e2e_report_does_not_call_safe_api(self):
        routes = _api_calls(_make_update(ALLOWED_UID, "/e2e_report"))
        self.assertEqual(routes, [])

    def test_e2e_report_calls_summary_script(self):
        """_e2e_report runs telegram_e2e_summary.py via _run_quick."""
        calls: list[list] = []
        with patch.object(bridge, "_run_quick",
                          side_effect=lambda argv, **kw: calls.append(argv) or "ok"), \
             patch.object(bridge, "_send_reply", lambda *a: None):
            bridge._do_e2e_report(TOKEN, ALLOWED_UID)
        self.assertTrue(any("telegram_e2e_summary.py" in " ".join(a) for a in calls),
                        "e2e_report must invoke telegram_e2e_summary.py")

    def test_e2e_report_in_menu(self):
        self.assertIn("/e2e_report", bridge.MENU_TEXT)


# ═══════════════════════════════════════════════════════════════════════════════
# /e2e_cancel_plan and /e2e_cancel_ok (Wave 8)
# ═══════════════════════════════════════════════════════════════════════════════

class TestE2ECancelFlow(unittest.TestCase):
    """Tests for the E2E cancel gate."""

    def _cancel_plan_reply(self) -> str:
        return _local_reply("/e2e_cancel_plan", "")

    def _cancel_ok_reply(self, token_val: str) -> str:
        with patch.object(bridge, "_run_quick", return_value='{"ok": true, "message": "Sentinel written."}'), \
             patch.object(bridge, "_send_reply", lambda t, c, msg: setattr(self, "_last", msg)):
            bridge._do_e2e_cancel_confirm(token_val, TOKEN, ALLOWED_UID)
        return getattr(self, "_last", "")

    def test_e2e_cancel_plan_in_table(self):
        self.assertIn("/e2e_cancel_plan", bridge.TELEGRAM_COMMANDS)
        self.assertIsNone(bridge.TELEGRAM_COMMANDS["/e2e_cancel_plan"])

    def test_e2e_cancel_ok_in_table(self):
        self.assertIn("/e2e_cancel_ok", bridge.TELEGRAM_COMMANDS)
        self.assertIsNone(bridge.TELEGRAM_COMMANDS["/e2e_cancel_ok"])

    def test_e2e_cancel_plan_generates_token(self):
        reply = self._cancel_plan_reply()
        self.assertIn("/e2e_cancel_ok", reply)
        self.assertRegex(reply, r"/e2e_cancel_ok\s+[0-9a-f]{8}")

    def test_e2e_cancel_ok_rejects_empty_token(self):
        reply = _local_reply("/e2e_cancel_ok", "")
        self.assertIn("Usage", reply)

    def test_e2e_cancel_ok_rejects_invalid_token(self):
        reply = _local_reply("/e2e_cancel_ok", "deadbeef")
        self.assertIn("Invalid or expired", reply)

    def test_e2e_cancel_ok_rejects_wrong_action(self):
        """An e2e (non-cancel) token must be rejected by /e2e_cancel_ok."""
        wrong_token = bridge._make_token("e2e", {"mode": "analyze"})
        reply = _local_reply("/e2e_cancel_ok", wrong_token)
        self.assertIn("different action", reply)

    def test_e2e_cancel_ok_valid_writes_sentinel(self):
        token = bridge._make_token("e2e_cancel", {})
        reply = self._cancel_ok_reply(token)
        self.assertIn("cancel", reply.lower())

    def test_e2e_cancel_ok_token_is_single_use(self):
        token = bridge._make_token("e2e_cancel", {})
        self._cancel_ok_reply(token)
        second_reply = _local_reply("/e2e_cancel_ok", token)
        self.assertIn("Invalid or expired", second_reply)

    def test_e2e_cancel_plan_does_not_call_safe_api(self):
        routes = _api_calls(_make_update(ALLOWED_UID, "/e2e_cancel_plan"))
        self.assertEqual(routes, [])

    def test_e2e_cancel_ok_does_not_call_safe_api(self):
        routes = _api_calls(_make_update(ALLOWED_UID, "/e2e_cancel_ok"))
        self.assertEqual(routes, [])


# ═══════════════════════════════════════════════════════════════════════════════
# /loop_status with e2e jobs (Wave 8)
# ═══════════════════════════════════════════════════════════════════════════════

class TestLoopStatusE2E(unittest.TestCase):
    """Verify /loop_status surfaces e2e- prefixed jobs."""

    def _make_job(self, type_: str) -> dict:
        return {"id": f"{type_}-test", "type": type_, "status": "succeeded",
                "start_time": "2026-06-22T10:00:00", "end_time": None}

    def test_loop_status_includes_e2e_analyze(self):
        mock_r = MagicMock()
        mock_r.list_recent.return_value = [self._make_job("e2e-analyze")]
        with patch.object(bridge, "_JOB_RUNNER", mock_r):
            result = bridge._format_loop_status()
        self.assertIn("e2e-analyze", result)

    def test_loop_status_includes_e2e_dry_run(self):
        mock_r = MagicMock()
        mock_r.list_recent.return_value = [self._make_job("e2e-dry-run")]
        with patch.object(bridge, "_JOB_RUNNER", mock_r):
            result = bridge._format_loop_status()
        self.assertIn("e2e-dry-run", result)

    def test_loop_status_hints_e2e_report_when_e2e_job_present(self):
        mock_r = MagicMock()
        mock_r.list_recent.return_value = [self._make_job("e2e-full")]
        with patch.object(bridge, "_JOB_RUNNER", mock_r):
            result = bridge._format_loop_status()
        self.assertIn("/e2e_report", result)

    def test_loop_status_no_e2e_report_hint_for_learn_only(self):
        mock_r = MagicMock()
        mock_r.list_recent.return_value = [self._make_job("learn-nlu")]
        with patch.object(bridge, "_JOB_RUNNER", mock_r):
            result = bridge._format_loop_status()
        self.assertNotIn("/e2e_report", result)


# ═══════════════════════════════════════════════════════════════════════════════
# E2E summary script structure (Wave 8)
# ═══════════════════════════════════════════════════════════════════════════════

class TestE2ESummaryScript(unittest.TestCase):
    """Verify telegram_e2e_summary.py exists and has correct structure."""

    _SUMMARY_PATH = _ROOT / "adwi" / "scripts" / "telegram_e2e_summary.py"

    def test_summary_script_exists(self):
        self.assertTrue(self._SUMMARY_PATH.exists())

    def test_summary_script_compiles(self):
        import py_compile
        try:
            py_compile.compile(str(self._SUMMARY_PATH), doraise=True)
        except py_compile.PyCompileError as exc:
            self.fail(f"telegram_e2e_summary.py syntax error: {exc}")

    def test_summary_script_is_stdlib_only(self):
        source = self._SUMMARY_PATH.read_text(encoding="utf-8")
        for pkg in ("requests", "flask", "aiohttp", "httpx"):
            self.assertNotIn(f"import {pkg}", source)

    def test_summary_script_exits_0_when_no_job(self):
        """Script must exit 0 (not crash) when no status.json exists."""
        import subprocess as _sub
        result = _sub.run(
            [sys.executable, str(self._SUMMARY_PATH)],
            capture_output=True, text=True,
            env={**__import__("os").environ,
                 "HOME": str(_ROOT)},   # point HOME to workspace — no status.json there
        )
        self.assertEqual(result.returncode, 0,
                         f"script exited {result.returncode}: {result.stderr}")
        self.assertIn("No E2E", result.stdout)

    def test_summary_script_does_not_print_secrets(self):
        source = self._SUMMARY_PATH.read_text(encoding="utf-8")
        for pattern in ("TOKEN", "SECRET", "PASSWORD", "API_KEY"):
            # printing of these patterns should not appear
            self.assertNotIn(f'print({pattern}', source.replace(" ", ""))


# ═══════════════════════════════════════════════════════════════════════════════
# /e2e_preflight command (Wave 9)
# ═══════════════════════════════════════════════════════════════════════════════

class TestE2EPreflight(unittest.TestCase):
    """Tests for /e2e_preflight — read-only readiness check."""

    def test_e2e_preflight_in_table(self):
        self.assertIn("/e2e_preflight", bridge.TELEGRAM_COMMANDS)
        self.assertIsNone(bridge.TELEGRAM_COMMANDS["/e2e_preflight"])

    def test_e2e_preflight_does_not_call_safe_api(self):
        routes = _api_calls(_make_update(ALLOWED_UID, "/e2e_preflight"))
        self.assertEqual(routes, [])

    def test_e2e_preflight_returns_string(self):
        """Handler must reply with a non-empty string (no crash)."""
        sent: list[str] = []
        with patch.object(bridge, "_send_reply", lambda t, c, msg: sent.append(msg)), \
             patch.object(bridge, "_e2e_preflight_checks", return_value=[
                 ("PASS", "e2e_auto_loop.py", ""),
                 ("PASS", "VENV_PY", ""),
                 ("WARN", "Ollama not reachable", "start Ollama"),
                 ("WARN", "llama3.1:8b", "cannot check"),
                 ("PASS", "Loop not running", "status=no_job"),
                 ("PASS", "Git dirty files", "clean"),
                 ("PASS", "Command registry", "57 commands registered"),
             ]):
            bridge._handle_local_cmd("/e2e_preflight", "", "tok", 123, "sec")
        self.assertTrue(sent, "handler must send at least one reply")
        self.assertGreater(len(sent[0]), 0)

    def test_e2e_preflight_contains_result_line(self):
        sent: list[str] = []
        with patch.object(bridge, "_send_reply", lambda t, c, msg: sent.append(msg)), \
             patch.object(bridge, "_e2e_preflight_checks", return_value=[
                 ("PASS", "e2e_auto_loop.py", ""),
                 ("PASS", "VENV_PY", ""),
                 ("PASS", "Loop not running", "status=no_job"),
                 ("PASS", "Ollama reachable", "3 model(s)"),
                 ("PASS", "llama3.1:8b", "present"),
                 ("PASS", "Git dirty files", "clean"),
                 ("PASS", "Command registry", "57 commands"),
             ]):
            bridge._handle_local_cmd("/e2e_preflight", "", "tok", 123, "sec")
        combined = " ".join(sent)
        self.assertIn("Result", combined)

    def test_e2e_preflight_ollama_unavailable_is_warn_not_fail(self):
        """Ollama not reachable must produce WARN, not FAIL — analyze still allowed."""
        all_checks = [
            ("PASS", "e2e_auto_loop.py", ""),
            ("PASS", "adwi-e2e-status-reader", ""),
            ("PASS", "telegram_e2e_summary.py", ""),
            ("PASS", "VENV_PY", ""),
            ("PASS", "Loop not running", "status=no_job"),
            ("WARN", "Ollama not reachable", "start Ollama"),
            ("WARN", "llama3.1:8b", "cannot check"),
            ("PASS", "Git dirty files", "clean"),
            ("PASS", "Command registry", "57 commands"),
        ]
        sent: list[str] = []
        with patch.object(bridge, "_send_reply", lambda t, c, msg: sent.append(msg)), \
             patch.object(bridge, "_e2e_preflight_checks", return_value=all_checks):
            bridge._handle_local_cmd("/e2e_preflight", "", "tok", 123, "sec")
        combined = " ".join(sent)
        self.assertIn("WARN", combined)
        self.assertNotIn("FAIL", combined)

    def test_e2e_preflight_model_detected_from_ollama_response(self):
        """If Ollama tags contain llama3.1:8b, check shows PASS."""
        # Simulate _e2e_preflight_checks returning PASS for llama3.1:8b
        checks_with_model = [
            ("PASS", "e2e_auto_loop.py", ""),
            ("PASS", "Loop not running", "status=no_job"),
            ("PASS", "Ollama reachable", "2 model(s)"),
            ("PASS", "llama3.1:8b", "present"),
            ("PASS", "Git dirty files", "clean"),
            ("PASS", "Command registry", "57 commands"),
        ]
        sent: list[str] = []
        with patch.object(bridge, "_send_reply", lambda t, c, msg: sent.append(msg)), \
             patch.object(bridge, "_e2e_preflight_checks", return_value=checks_with_model):
            bridge._handle_local_cmd("/e2e_preflight", "", "tok", 123, "sec")
        combined = " ".join(sent)
        self.assertIn("llama3.1:8b", combined)
        self.assertIn("present", combined)

    def test_e2e_preflight_summary_ok(self):
        with patch.object(bridge, "_e2e_preflight_checks", return_value=[
            ("PASS", "a", ""), ("PASS", "b", ""),
        ]):
            self.assertEqual(bridge._e2e_preflight_summary(), "OK")

    def test_e2e_preflight_summary_warn(self):
        with patch.object(bridge, "_e2e_preflight_checks", return_value=[
            ("PASS", "a", ""), ("WARN", "Ollama not reachable", "x"),
        ]):
            result = bridge._e2e_preflight_summary()
            self.assertIn("WARN", result)

    def test_e2e_preflight_summary_fail(self):
        with patch.object(bridge, "_e2e_preflight_checks", return_value=[
            ("FAIL", "e2e_auto_loop.py", "not found"), ("PASS", "b", ""),
        ]):
            result = bridge._e2e_preflight_summary()
            self.assertIn("FAIL", result)

    def test_e2e_preflight_in_menu(self):
        self.assertIn("/e2e_preflight", bridge.MENU_TEXT)


# ═══════════════════════════════════════════════════════════════════════════════
# /e2e_plan preflight integration (Wave 9)
# ═══════════════════════════════════════════════════════════════════════════════

class TestE2EPlanPreflight(unittest.TestCase):
    """Verify /e2e_plan includes preflight line and full-mode extra warning."""

    def _plan_reply(self, args: str = "", preflight: str = "OK") -> str:
        sent: list[str] = []
        with patch.object(bridge, "_e2e_preflight_summary", return_value=preflight), \
             patch.object(bridge, "_send_reply", lambda t, c, msg: sent.append(msg)):
            bridge._do_e2e_plan(args, TOKEN, ALLOWED_UID)
        return sent[0] if sent else ""

    def test_e2e_plan_contains_preflight_line(self):
        reply = self._plan_reply("analyze 98 1", preflight="OK")
        self.assertIn("Preflight", reply)
        self.assertIn("OK", reply)

    def test_e2e_plan_preflight_warn_shown(self):
        reply = self._plan_reply("analyze 98 1", preflight="WARN — Ollama not reachable")
        self.assertIn("WARN", reply)

    def test_e2e_plan_full_preflight_fail_adds_strong_warning(self):
        reply = self._plan_reply("full 98 1", preflight="WARN — Ollama not reachable")
        self.assertIn("STRONG WARNING", reply)

    def test_e2e_plan_full_preflight_ok_no_strong_warning(self):
        reply = self._plan_reply("full 98 1", preflight="OK")
        self.assertNotIn("STRONG WARNING", reply)

    def test_e2e_plan_analyze_preflight_fail_no_strong_warning(self):
        """analyze mode should not get STRONG WARNING even with bad preflight."""
        reply = self._plan_reply("analyze 98 1", preflight="WARN — Ollama not reachable")
        self.assertNotIn("STRONG WARNING", reply)


# ═══════════════════════════════════════════════════════════════════════════════
# /control_center command (Wave 9)
# ═══════════════════════════════════════════════════════════════════════════════

class TestControlCenter(unittest.TestCase):
    """Tests for /control_center — read-only ops dashboard."""

    def _run(self, mock_runner=None) -> str:
        sent: list[str] = []
        if mock_runner is None:
            runner = MagicMock()
            runner.list_recent.return_value = []
        else:
            runner = mock_runner
        with patch.object(bridge, "_JOB_RUNNER", runner), \
             patch.object(bridge, "_send_reply", lambda t, c, msg: sent.append(msg)):
            bridge._handle_local_cmd("/control_center", "", TOKEN, ALLOWED_UID, SECRET)
        return sent[0] if sent else ""

    def test_control_center_in_table(self):
        self.assertIn("/control_center", bridge.TELEGRAM_COMMANDS)
        self.assertIsNone(bridge.TELEGRAM_COMMANDS["/control_center"])

    def test_control_center_does_not_call_safe_api(self):
        routes = _api_calls(_make_update(ALLOWED_UID, "/control_center"))
        self.assertEqual(routes, [])

    def test_control_center_includes_command_count(self):
        reply = self._run()
        self.assertIn(str(len(bridge.TELEGRAM_COMMANDS)), reply)

    def test_control_center_includes_job_summary(self):
        mock_r = MagicMock()
        mock_r.list_recent.return_value = [
            {"id": "test-id-1", "type": "test-quick", "status": "succeeded",
             "start_time": "2026-06-22T10:00:00", "end_time": None},
        ]
        reply = self._run(mock_runner=mock_r)
        self.assertIn("test-quick", reply)

    def test_control_center_includes_suggested_commands(self):
        reply = self._run()
        self.assertIn("/telegram_validate", reply)
        self.assertIn("/e2e_preflight", reply)
        self.assertIn("/e2e_report", reply)
        self.assertIn("/loop_status", reply)

    def test_control_center_no_e2e_job_message(self):
        """When no status.json exists, should say 'no loop run yet'."""
        import tempfile, os as _os
        # Override _E2E_STATUS_DIR to a non-existent dir
        with patch.object(bridge, "_E2E_STATUS_DIR",
                          Path(tempfile.mkdtemp()) / "nonexistent"):
            reply = self._run()
        self.assertIn("no loop", reply.lower())

    def test_control_center_in_menu(self):
        self.assertIn("/control_center", bridge.MENU_TEXT)

    def test_control_center_reply_fits_telegram(self):
        """Output must fit within REPLY_MAX_LEN."""
        reply = self._run()
        self.assertLessEqual(len(reply), bridge.REPLY_MAX_LEN)


# ═══════════════════════════════════════════════════════════════════════════════
# Wave 9 doc drift checks
# ═══════════════════════════════════════════════════════════════════════════════

class TestWave9DocDrift(unittest.TestCase):
    """Verify stale loop_status references are fixed in bot.py."""

    def test_menu_text_loop_status_mentions_e2e(self):
        """MENU_TEXT /loop_status description must mention E2E."""
        self.assertIn("E2E", bridge.MENU_TEXT)
        # The /loop_status line should reference E2E
        for line in bridge.MENU_TEXT.splitlines():
            if "/loop_status" in line:
                self.assertIn("E2E", line.upper(),
                              f"MENU_TEXT /loop_status line must mention E2E: {line!r}")
                break


if __name__ == "__main__":
    unittest.main()
