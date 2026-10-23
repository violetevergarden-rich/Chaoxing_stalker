import json
import os
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from chaoxing_stalker.config import CONFIG_TEMPLATE, generate_config_template, load_config, validate_config


def valid_config():
    return {
        "users": [
            {
                "name": "Test user",
                "chaoxing": {"username": "user", "password": "password"},
                "notifications": {
                    "email": {
                        "enabled": True,
                        "smtp_host": "smtp.example.com",
                        "smtp_port": 465,
                        "sender": "sender@example.com",
                        "authorization_code": "code",
                        "recipients": ["receiver@example.com"],
                    }
                },
            }
        ]
    }


class ConfigTests(unittest.TestCase):
    def test_valid_config_passes_validation(self):
        validate_config(valid_config())

    def test_config_without_enabled_notifier_passes_validation(self):
        config = valid_config()
        config["users"][0]["notifications"] = {
            "email": {"enabled": False},
            "serverchan": {"enabled": False},
        }
        validate_config(config)

    def test_missing_users_is_rejected(self):
        with self.assertRaisesRegex(ValueError, "users 不能为空"):
            validate_config({"users": []})

    def test_duplicate_usernames_are_rejected(self):
        config = valid_config()
        config["users"].append(valid_config()["users"][0])
        with self.assertRaisesRegex(ValueError, "重复"):
            validate_config(config)

    def test_environment_config_takes_precedence(self):
        expected = valid_config()
        with patch.dict(os.environ, {"CONFIG_JSON": json.dumps(expected)}):
            self.assertEqual(load_config("missing.json"), expected)

    def test_template_contains_no_schedule_settings(self):
        self.assertNotIn("schedule", CONFIG_TEMPLATE)
        self.assertNotIn("run_hours", CONFIG_TEMPLATE["users"][0])

    def test_sticky_note_folder_has_default_name(self):
        self.assertEqual(
            CONFIG_TEMPLATE["users"][0]["sticky_note"]["folder_name"], "学习通作业"
        )

    def test_template_is_written_as_json(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "config.json"
            generate_config_template(str(path))
            self.assertEqual(json.loads(path.read_text(encoding="utf-8")), CONFIG_TEMPLATE)


if __name__ == "__main__":
    unittest.main()
