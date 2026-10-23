import tempfile
import unittest
from pathlib import Path

from chaoxing_stalker.sticky_notes import _validate_prefixes, desktop_directory, write_sticky_notes


class StickyNoteTests(unittest.TestCase):
    def test_writes_one_stable_file_per_assignment_and_updates_it(self):
        with tempfile.TemporaryDirectory() as directory:
            first = {
                "course_name": "Math",
                "title": "Homework",
                "work_id": "42",
                "deadline": "2026-10-30 23:59",
                "url": "https://example.com/42",
            }
            write_sticky_notes("Alice", [first], directory)
            note_directory = Path(directory) / "学习通作业"
            path = note_directory / "00_Homework.txt"
            self.assertTrue(path.exists())

            updated = {**first, "deadline": "2026-11-01 23:59"}
            write_sticky_notes(
                "Alice",
                [updated, {**first, "title": "Other homework", "work_id": "43"}],
                directory,
            )

            self.assertEqual(len(list(note_directory.glob("*.txt"))), 2)
            self.assertIn("2026-11-01 23:59", path.read_text(encoding="utf-8"))
            self.assertNotIn("剩余", path.read_text(encoding="utf-8"))

    def test_missing_work_id_uses_stable_course_and_title_hash(self):
        with tempfile.TemporaryDirectory() as directory:
            assignment = {"course_name": "Math", "course_id": "10", "title": "A/B"}
            write_sticky_notes("Alice", [assignment], directory)
            write_sticky_notes("Alice", [assignment], directory)
            files = list((Path(directory) / "学习通作业").glob("*.txt"))
            self.assertEqual(len(files), 1)
            self.assertIn("截止时间: 未知", files[0].read_text(encoding="utf-8"))

    def test_filename_sanitizes_windows_reserved_characters(self):
        with tempfile.TemporaryDirectory() as directory:
            write_sticky_notes(
                "A/B", [{"title": "x", "work_id": "a:b?c"}], directory
            )
            filename = next((Path(directory) / "学习通作业").iterdir()).name
            self.assertNotRegex(filename, r'[<>:"/\\|?*]')
            self.assertEqual(filename, "00_x.txt")

    def test_linux_uses_xdg_desktop_path_or_default(self):
        with tempfile.TemporaryDirectory() as directory:
            home = Path(directory)
            config = home / ".config"
            config.mkdir()
            (config / "user-dirs.dirs").write_text(
                'XDG_DESKTOP_DIR="$HOME/桌面文件"\n', encoding="utf-8"
            )
            self.assertEqual(
                desktop_directory(home, "posix", {"HOME": str(home)}),
                home / "桌面文件",
            )
            (config / "user-dirs.dirs").unlink()
            self.assertEqual(
                desktop_directory(home, "posix", {"HOME": str(home)}), home / "Desktop"
            )

    def test_windows_prefers_existing_onedrive_desktop(self):
        with tempfile.TemporaryDirectory() as directory:
            home = Path(directory) / "home"
            onedrive = Path(directory) / "OneDrive"
            (onedrive / "Desktop").mkdir(parents=True)
            result = desktop_directory(
                home, "nt", {"USERPROFILE": str(home), "OneDrive": str(onedrive)}
            )
            self.assertEqual(result, onedrive / "Desktop")

    def test_same_title_in_different_courses_gets_disambiguated_names(self):
        with tempfile.TemporaryDirectory() as directory:
            write_sticky_notes(
                "Alice",
                [
                    {"title": "Essay", "course_name": "Math", "work_id": "1"},
                    {"title": "Essay", "course_name": "History", "work_id": "2"},
                ],
                directory,
            )
            self.assertEqual(
                {
                    path.name
                    for path in (Path(directory) / "学习通作业").glob("*.txt")
                },
                {"00_Essay - Math.txt", "01_Essay - History.txt"},
            )

    def test_custom_folder_name_is_created_and_contains_notes(self):
        with tempfile.TemporaryDirectory() as directory:
            write_sticky_notes(
                "Alice",
                [{"title": "Homework", "work_id": "1"}],
                directory,
                folder_name="课程提醒",
            )
            self.assertTrue(
                (Path(directory) / "课程提醒" / "00_Homework.txt").is_file()
            )

    def test_old_generated_notes_are_removed_but_other_text_is_preserved(self):
        with tempfile.TemporaryDirectory() as directory:
            folder = Path(directory) / "学习通作业"
            folder.mkdir()
            (folder / "Homework.txt").write_text(
                "课程: Math\n作业: Homework\n截止时间: 未知\n链接: 未知\n",
                encoding="utf-8",
            )
            (folder / "my-note.txt").write_text("personal note", encoding="utf-8")
            write_sticky_notes("Alice", [{"title": "Homework", "work_id": "1"}], directory)
            self.assertFalse((folder / "Homework.txt").exists())
            self.assertTrue((folder / "my-note.txt").exists())
            self.assertTrue((folder / "00_Homework.txt").exists())

    def test_duplicate_numeric_prefixes_raise(self):
        with self.assertRaisesRegex(ValueError, "编号重复"):
            _validate_prefixes(["00", "00"])

    def test_more_than_100_assignments_raises_without_creating_folder(self):
        with tempfile.TemporaryDirectory() as directory:
            assignments = [{"title": f"Homework {i}"} for i in range(101)]
            with self.assertRaisesRegex(ValueError, "最多支持 100 项"):
                write_sticky_notes("Alice", assignments, directory)
            self.assertFalse((Path(directory) / "学习通作业").exists())


if __name__ == "__main__":
    unittest.main()
