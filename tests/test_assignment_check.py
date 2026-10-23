import contextlib
import io
import unittest
from unittest.mock import patch

from chaoxing_stalker.notifiers.factory import create_notifiers
from chaoxing_stalker.services.assignment_check import check_and_notify


USER_CONFIG = {
    "name": "Test user",
    "chaoxing": {"username": "user", "password": "password"},
    "notification_behaviour": {
        "notify_when_empty": False,
        "notify_on_error": True,
    },
}
ASSIGNMENT = {
    "course_name": "Math",
    "course_id": "10",
    "class_id": "20",
    "title": "Homework",
    "work_id": "42",
    "answer_id": "7",
    "deadline": "2026-10-30 23:59",
    "url": "https://example.com/work",
}


class FakeProvider:
    def __init__(self, assignments=None, error=None):
        self.assignments = assignments or []
        self.error = error

    def get_unsubmitted_assignments(self):
        if self.error:
            raise self.error
        return self.assignments


class FakeNotifier:
    def __init__(self):
        self.messages = []

    def send(self, subject, message):
        self.messages.append((subject, message))
        return True


def provider_factory(provider):
    return lambda username, password: provider


class AssignmentCheckTests(unittest.TestCase):
    def test_sticky_notes_are_only_written_when_enabled(self):
        with patch("services.assignment_check.write_sticky_notes") as write_notes:
            check_and_notify(
                {
                    **USER_CONFIG,
                    "sticky_note": {"enabled": True, "folder_name": "课程任务"},
                },
                [],
                provider_factory(FakeProvider([ASSIGNMENT])),
            )
            write_notes.assert_called_once_with(
                "Test user", [ASSIGNMENT], folder_name="课程任务"
            )

            write_notes.reset_mock()
            check_and_notify(
                USER_CONFIG,
                [],
                provider_factory(FakeProvider([ASSIGNMENT])),
            )
            write_notes.assert_not_called()

    def test_sticky_notes_follow_deadline_order(self):
        later = {**ASSIGNMENT, "title": "Later", "deadline": "2026-11-01 23:59"}
        sooner = {**ASSIGNMENT, "title": "Sooner", "deadline": "2026-10-25 23:59"}
        with patch("services.assignment_check.write_sticky_notes") as write_notes:
            check_and_notify(
                {
                    **USER_CONFIG,
                    "sticky_note": {"enabled": True},
                },
                [],
                provider_factory(FakeProvider([later, sooner])),
            )
        self.assertEqual(write_notes.call_args.args[1], [sooner, later])

    def test_check_sends_full_list(self):
        notifier = FakeNotifier()
        success = check_and_notify(
            USER_CONFIG,
            [notifier],
            provider_factory(FakeProvider([ASSIGNMENT])),
        )
        self.assertTrue(success)
        self.assertEqual(len(notifier.messages), 1)

    def test_every_check_sends_all_unsubmitted_assignments(self):
        notifier = FakeNotifier()
        for _ in range(2):
            success = check_and_notify(
                USER_CONFIG,
                [notifier],
                provider_factory(FakeProvider([ASSIGNMENT])),
            )
            self.assertTrue(success)
        self.assertEqual(len(notifier.messages), 2)
        self.assertIn("[Math] Homework", notifier.messages[0][1])

    def test_message_lists_existing_and_new_assignments_together(self):
        notifier = FakeNotifier()
        first_assignment = {**ASSIGNMENT, "work_id": "old"}
        second_assignment = {**ASSIGNMENT, "work_id": "new"}
        check_and_notify(
            USER_CONFIG,
            [notifier],
            provider_factory(FakeProvider([first_assignment, second_assignment])),
        )
        self.assertEqual(len(notifier.messages), 1)
        self.assertIn("1. [Math] Homework", notifier.messages[0][1])
        self.assertIn("2. [Math] Homework", notifier.messages[0][1])
        self.assertNotIn("新增未提交作业", notifier.messages[0][1])

    def test_fetch_error_sends_error_notification_and_returns_failure(self):
        notifier = FakeNotifier()
        success = check_and_notify(
            USER_CONFIG,
            [notifier],
            provider_factory(FakeProvider(error=ValueError("fetch failed"))),
        )
        self.assertFalse(success)
        self.assertEqual(len(notifier.messages), 1)
        self.assertIn("检查失败", notifier.messages[0][0])

    def test_empty_assignments_can_send_configured_notice(self):
        notifier = FakeNotifier()
        config = {
            **USER_CONFIG,
            "notification_behaviour": {"notify_when_empty": True},
        }
        success = check_and_notify(
            config,
            [notifier],
            provider_factory(FakeProvider()),
        )
        self.assertTrue(success)
        self.assertEqual(len(notifier.messages), 1)

    def test_no_enabled_channel_prints_full_assignment_notification(self):
        output = io.StringIO()
        with contextlib.redirect_stdout(output):
            check_and_notify(
                USER_CONFIG,
                create_notifiers({"notifications": {}}),
                provider_factory(FakeProvider([ASSIGNMENT])),
            )
        self.assertIn("超星作业提醒", output.getvalue())
        self.assertIn("[Math] Homework", output.getvalue())


if __name__ == "__main__":
    unittest.main()
