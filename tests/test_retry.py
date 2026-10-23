import unittest
from unittest.mock import patch

from chaoxing_stalker.retry import retry


class RetryTests(unittest.TestCase):
    def test_retries_transient_errors_with_exponential_delays(self):
        attempts = []

        @retry(max_attempts=3, base_delay=2)
        def operation():
            attempts.append(len(attempts) + 1)
            if len(attempts) < 3:
                raise ConnectionError("temporary")
            return "done"

        with patch("retry.time.sleep") as sleep:
            self.assertEqual(operation(), "done")
        self.assertEqual(len(attempts), 3)
        self.assertEqual([call.args[0] for call in sleep.call_args_list], [2, 4])

    def test_non_transient_errors_are_not_retried(self):
        attempts = []

        @retry(max_attempts=3)
        def operation():
            attempts.append(1)
            raise ValueError("invalid")

        with self.assertRaisesRegex(ValueError, "invalid"):
            operation()
        self.assertEqual(len(attempts), 1)


if __name__ == "__main__":
    unittest.main()
