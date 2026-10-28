import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from chaoxing_stalker.refresh_sticky_notes import refresh_sticky_notes
from chaoxing_stalker.sticky_notes import (
    REFRESH_SHELL_SCRIPT,
    REFRESH_WINDOWS_SCRIPT,
)


USER_CONFIG = {
    "name": "Test user",
    "chaoxing": {"username": "user", "password": "password"},
    "notifications": {},
    "sticky_note": {"enabled": True, "folder_name": "学习通作业"},
}


class FakeProvider:
    def __init__(self, assignments=None, error=None):
        self.assignments = assignments or []
        self.error = error

    def get_unsubmitted_assignments(self):
        if self.error:
            raise self.error
        return self.assignments


def no_wait_retry(*args, **kwargs):
    return lambda function: function


class RefreshStickyNotesTests(unittest.TestCase):
    def test_refresh_recreates_notes_without_notification_dependency(self):
        assignment = {"title": "Homework", "deadline": "2026-10-30 23:59"}
        with tempfile.TemporaryDirectory() as directory:
            notes_directory = Path(directory) / "学习通作业"
            notes_directory.mkdir()
            (notes_directory / "manual.txt").write_text("remove me", encoding="utf-8")
            (notes_directory / "subfolder").mkdir()
            (notes_directory / REFRESH_SHELL_SCRIPT).write_text("launcher", encoding="utf-8")
            (notes_directory / REFRESH_WINDOWS_SCRIPT).write_text("launcher", encoding="utf-8")
            provider = FakeProvider([assignment])
            with (
                patch(
                    "chaoxing_stalker.refresh_sticky_notes.load_config",
                    return_value={"users": [USER_CONFIG]},
                ),
                patch("chaoxing_stalker.refresh_sticky_notes.ChaoXingClient", return_value=provider),
                patch("chaoxing_stalker.refresh_sticky_notes.retry", no_wait_retry),
            ):
                refresh_sticky_notes("unused.json", notes_directory)

            self.assertEqual(
                {path.name for path in notes_directory.iterdir()},
                {"00_Homework.txt", REFRESH_SHELL_SCRIPT, REFRESH_WINDOWS_SCRIPT},
            )
            self.assertIn("Homework", (notes_directory / "00_Homework.txt").read_text(encoding="utf-8"))

    def test_disabled_or_missing_folder_configuration_fails_before_clearing(self):
        with tempfile.TemporaryDirectory() as directory:
            notes_directory = Path(directory) / "学习通作业"
            notes_directory.mkdir()
            note = notes_directory / "old.txt"
            note.write_text("keep until config is valid", encoding="utf-8")
            with patch(
                "chaoxing_stalker.refresh_sticky_notes.load_config",
                return_value={"users": [{**USER_CONFIG, "sticky_note": {"enabled": False}}]},
            ):
                with self.assertRaisesRegex(ValueError, "没有启用目标文件夹"):
                    refresh_sticky_notes("unused.json", notes_directory)
            self.assertTrue(note.exists())

    def test_fetch_failure_exits_with_error_and_preserves_launchers(self):
        with tempfile.TemporaryDirectory() as directory:
            notes_directory = Path(directory) / "学习通作业"
            notes_directory.mkdir()
            old_note = notes_directory / "old.txt"
            old_note.write_text("old", encoding="utf-8")
            for launcher in (REFRESH_SHELL_SCRIPT, REFRESH_WINDOWS_SCRIPT):
                (notes_directory / launcher).write_text("launcher", encoding="utf-8")
            provider = FakeProvider(error=RuntimeError("network down"))
            with (
                patch(
                    "chaoxing_stalker.refresh_sticky_notes.load_config",
                    return_value={"users": [USER_CONFIG]},
                ),
                patch("chaoxing_stalker.refresh_sticky_notes.ChaoXingClient", return_value=provider),
                patch("chaoxing_stalker.refresh_sticky_notes.retry", no_wait_retry),
            ):
                with self.assertRaisesRegex(RuntimeError, "network down"):
                    refresh_sticky_notes("unused.json", notes_directory)
            self.assertFalse(old_note.exists())
            for launcher in (REFRESH_SHELL_SCRIPT, REFRESH_WINDOWS_SCRIPT):
                self.assertTrue((notes_directory / launcher).exists())

    def test_invalid_config_fails_before_clearing(self):
        with tempfile.TemporaryDirectory() as directory:
            notes_directory = Path(directory) / "学习通作业"
            notes_directory.mkdir()
            note = notes_directory / "old.txt"
            note.write_text("keep until config is valid", encoding="utf-8")
            with (
                patch(
                    "chaoxing_stalker.refresh_sticky_notes.load_config",
                    return_value={"users": []},
                ),
                self.assertRaisesRegex(ValueError, "users 不能为空"),
            ):
                refresh_sticky_notes("unused.json", notes_directory)
            self.assertTrue(note.exists())


if __name__ == "__main__":
    unittest.main()
