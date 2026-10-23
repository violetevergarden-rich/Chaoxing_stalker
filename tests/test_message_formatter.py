import unittest

from chaoxing_stalker.message_formatter import format_message


class MessageFormatterTests(unittest.TestCase):
    def test_formats_assignment_details_and_user_name(self):
        assignment = {
            "course_name": "Math",
            "title": "Homework 1",
            "deadline": "2026-10-30 23:59",
            "url": "https://example.com/work",
        }
        message = format_message(
            [assignment], "2026-10-23 12:00:00", user_name="Alice"
        )
        self.assertIn("用户: Alice", message)
        self.assertIn("[Math] Homework 1", message)
        self.assertIn("截止时间: 2026-10-30 23:59", message)
        self.assertNotIn("剩余", message)
        self.assertIn("链接: https://example.com/work", message)

    def test_message_contains_all_assignments_without_added_section(self):
        assignment = {"course_name": "Math", "title": "Homework 1"}
        message = format_message([assignment], "now")
        self.assertNotIn("新增未提交作业", message)
        self.assertIn("全部未提交作业", message)
        self.assertIn("截止时间: 未知", message)

    def test_message_sorts_deadlines_ascending_and_unknown_last(self):
        assignments = [
            {"course_name": "Math", "title": "Later", "deadline": "2026-11-02 10:00"},
            {"course_name": "Math", "title": "Unknown", "deadline": ""},
            {"course_name": "Math", "title": "Sooner", "deadline": "2026-10-25 10:00"},
        ]
        message = format_message(assignments, "now")
        self.assertLess(message.index("Sooner"), message.index("Later"))
        self.assertLess(message.index("Later"), message.index("Unknown"))


if __name__ == "__main__":
    unittest.main()
