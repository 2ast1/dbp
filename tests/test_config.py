"""
Tests for configuration loading, validation, backup recovery, and persistence.
"""

import json
import os
import shutil
import tempfile
import unittest

from dbp_core import config


class TestConfig(unittest.TestCase):
    def setUp(self):
        self.temp_dir = tempfile.mkdtemp()
        self.orig_dbp_dir = config.DBP_DIR
        self.orig_config_file = config.CONFIG_FILE
        config.DBP_DIR = self.temp_dir
        config.CONFIG_FILE = os.path.join(self.temp_dir, "config.json")

    def tearDown(self):
        config.DBP_DIR = self.orig_dbp_dir
        config.CONFIG_FILE = self.orig_config_file
        shutil.rmtree(self.temp_dir, ignore_errors=True)

    def test_load_default_config(self):
        cfg = config.load_config()
        self.assertEqual(cfg["language"], "English")
        self.assertTrue(cfg["smart_trash"])
        self.assertTrue(cfg["include_subfolders"])
        self.assertTrue(cfg["clean_empty_folders"])
        self.assertEqual(cfg["protect_recent_hours"], 24)

    def test_save_and_reload_config(self):
        cfg = config.load_config()
        cfg["language"] = "Deutsch"
        cfg["source_dir"] = r"C:\TestDownloads"
        cfg["target_dir"] = r"C:\TestArchive"
        cfg["smart_trash"] = True
        cfg["include_subfolders"] = True
        cfg["autostart"] = True

        config.save_config(cfg)
        loaded = config.load_config()

        self.assertEqual(loaded["language"], "Deutsch")
        self.assertEqual(loaded["source_dir"], r"C:\TestDownloads")
        self.assertEqual(loaded["target_dir"], r"C:\TestArchive")
        self.assertTrue(loaded["smart_trash"])
        self.assertTrue(loaded["autostart"])

    def test_backup_recovery_on_corrupt_config(self):
        cfg = config.load_config()
        cfg["source_dir"] = r"C:\Users\Test\Downloads"
        cfg["target_dir"] = r"D:\Archive"
        cfg["autostart"] = True
        config.save_config(cfg)

        # Zweites Speichern legt config.json.bak mit dem gültigen Vorgängerstand an
        cfg["interval"] = "daily"
        config.save_config(cfg)

        with open(config.CONFIG_FILE, "w", encoding="utf-8") as f:
            f.write("{corrupt json !!!")

        recovered = config.load_config()
        self.assertEqual(recovered["source_dir"], r"C:\Users\Test\Downloads")
        self.assertEqual(recovered["target_dir"], r"D:\Archive")
        self.assertTrue(recovered["autostart"])

    def test_legacy_interval_migration_and_invalid_values(self):
        legacy_cases = {
            "Bei jedem Start": "startup",
            "At every startup": "startup",
            "Täglich": "daily",
            "Daily": "daily",
            "Wöchentlich": "weekly",
            "Weekly": "weekly",
            "Monatlich": "monthly",
            "Monthly": "monthly",
            "totally_invalid": "startup",
        }
        for raw_val, expected in legacy_cases.items():
            with self.subTest(interval=raw_val):
                with open(config.CONFIG_FILE, "w", encoding="utf-8") as f:
                    json.dump(
                        {
                            "interval": raw_val,
                            "max_log_size": "999",
                            "protect_recent_hours": -5,
                        },
                        f,
                    )
                loaded = config.load_config()
                self.assertEqual(loaded["interval"], expected)
                self.assertEqual(loaded["max_log_size"], "0.5")
                self.assertEqual(loaded["protect_recent_hours"], 24)

        with open(config.CONFIG_FILE, "w", encoding="utf-8") as f:
            json.dump({"protect_recent_hours": True}, f)
        self.assertEqual(config.load_config()["protect_recent_hours"], 24)


if __name__ == "__main__":
    unittest.main()
