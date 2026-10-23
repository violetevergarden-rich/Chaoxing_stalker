import unittest

from chaoxing_stalker.app import run_once


class FakeProvider:
    def __init__(self, username, password):
        self.assignment = {
            "course_name": "Math",
            "course_id": "10",
            "class_id": "20",
            "title": "Homework",
            "work_id": "42",
            "answer_id": "7",
            "deadline": "2026-10-30 23:59",
            "url": "https://example.com/work",
        }

    def get_unsubmitted_assignments(self):
        return [self.assignment]


class FakeNotifier:
    def send(self, subject, message):
        return True


class AppTests(unittest.TestCase):
    def test_run_once_processes_users_without_state_file_parameter(self):
        config = {
            "users": [
                {
                    "name": "Test user",
                    "chaoxing": {"username": "user", "password": "password"},
                    "notification_behaviour": {"notify_when_empty": False},
                }
            ]
        }
        run_once(
            config,
            assignment_provider_factory=FakeProvider,
            notifier_factory=lambda user: [FakeNotifier()],
        )


if __name__ == "__main__":
    unittest.main()
