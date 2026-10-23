import contextlib
import io
import unittest

from chaoxing_stalker.compat import ChaoXingStalker, main as chaoxing_main
from chaoxing_stalker.chaoxing.client import ChaoXingClient
from chaoxing_stalker.notifiers import Notifier, create_notifiers
from chaoxing_stalker.notifiers.base import Notifier as BaseNotifier
from chaoxing_stalker.notifiers.console_notifier import ConsoleNotifier
from chaoxing_stalker.__main__ import main as stalker_main


class CompatibilityTests(unittest.TestCase):
    def test_legacy_scraper_class_name_remains_available(self):
        self.assertTrue(issubclass(ChaoXingStalker, ChaoXingClient))

    def test_notifier_package_exports_are_preserved(self):
        self.assertIs(Notifier, BaseNotifier)
        self.assertTrue(callable(create_notifiers))

    def test_no_enabled_channel_uses_console_notifier(self):
        notifiers = create_notifiers({"notifications": {}})
        self.assertEqual(len(notifiers), 1)
        self.assertIsInstance(notifiers[0], ConsoleNotifier)

    def test_scraper_cli_reports_missing_credentials_without_network_access(self):
        output = io.StringIO()
        with contextlib.redirect_stdout(output):
            self.assertEqual(chaoxing_main([]), 1)
        self.assertIn("<用户名> <密码>", output.getvalue())

    def test_stalker_cli_help_exits_without_loading_config(self):
        output = io.StringIO()
        with contextlib.redirect_stdout(output), self.assertRaises(SystemExit) as raised:
            stalker_main(["--help"])
        self.assertEqual(raised.exception.code, 0)
        self.assertIn("--init-config", output.getvalue())
        self.assertIn("--config", output.getvalue())


if __name__ == "__main__":
    unittest.main()
