"""
Tests for Smart Trash functionality and in-progress download protection.
"""

import os
import shutil
import tempfile
import time
import unittest

from dbp_core.smart_trash import (
    evaluate_file_importance,
    is_in_progress_download,
    is_system_metadata_file,
)


class TestSmartTrash(unittest.TestCase):
    def setUp(self):
        self.test_dir = tempfile.mkdtemp()

    def tearDown(self):
        shutil.rmtree(self.test_dir, ignore_errors=True)

    def _create_file(self, filename, content="dummy content", age_seconds=0):
        p = os.path.join(self.test_dir, filename)
        with open(p, "w", encoding="utf-8") as f:
            f.write(content)
        if age_seconds != 0:
            target_time = time.time() - age_seconds
            os.utime(p, (target_time, target_time))
        return p

    def test_in_progress_downloads(self):
        active_names = [
            "document.pdf.crdownload",
            "archive.zip.part",
            "~$WordDocument.docx",
            ".~lock.Spreadsheet.xlsx#",
            "installer.exe.opdownload",
            "movie.mkv.partial",
            "transfer.bin.filepart",
            "ubuntu.iso.aria2",
            "distro.iso.!qb",
        ]
        for name in active_names:
            with self.subTest(name=name):
                p = self._create_file(name)
                self.assertTrue(is_in_progress_download(p))
                is_imp, _reason, is_active = evaluate_file_importance(p)
                self.assertTrue(is_active)
                self.assertFalse(is_imp)

    def test_important_keywords_and_umlauts(self):
        p1 = self._create_file("Rechnung_Telekom_Oktober.other", age_seconds=200000)
        p2 = self._create_file("steuerbescheid_2025.dat", age_seconds=200000)
        p3 = self._create_file("my_employment_contract.bin", age_seconds=200000)
        p4 = self._create_file("Bestätigung_Anmeldung.dat", age_seconds=200000)
        p5 = self._create_file("Kündigung_Strom_2026.dat", age_seconds=200000)
        p6 = self._create_file("Rückerstattung_2026.dat", age_seconds=200000)

        is_imp1, reason1, _ = evaluate_file_importance(p1, protect_recent_hours=0)
        is_imp2, reason2, _ = evaluate_file_importance(p2, protect_recent_hours=0)
        is_imp3, reason3, _ = evaluate_file_importance(p3, protect_recent_hours=0)
        is_imp4, reason4, _ = evaluate_file_importance(p4, protect_recent_hours=0)
        is_imp5, reason5, _ = evaluate_file_importance(p5, protect_recent_hours=0)
        is_imp6, reason6, _ = evaluate_file_importance(p6, protect_recent_hours=0)

        self.assertTrue(is_imp1)
        self.assertIn("rechnung", reason1.lower())
        self.assertTrue(is_imp2)
        self.assertIn("steuer", reason2.lower())
        self.assertTrue(is_imp3)
        self.assertIn("contract", reason3.lower())
        self.assertTrue(is_imp4)
        self.assertIn("bestätigung", reason4.lower())
        self.assertTrue(is_imp5)
        self.assertIn("kündigung", reason5.lower())
        self.assertTrue(is_imp6)
        self.assertIn("rückerstattung", reason6.lower())

    def test_word_boundary_prevents_false_positives(self):
        false_positives = [
            "recorder_setup.exe",
            "syntax.bin",
            "border_icon.bin",
            "policeman_game.dat",
        ]
        for fname in false_positives:
            with self.subTest(false_positive=fname):
                p = self._create_file(fname, age_seconds=200000)
                is_imp, _reason, _ = evaluate_file_importance(p, protect_recent_hours=0)
                self.assertFalse(is_imp)

        true_positives = [
            "tax_2026.dat",
            "order_1234.bin",
            "Beleg_01.dat",
            "salary_slip.dat",
        ]
        for fname in true_positives:
            with self.subTest(true_positive=fname):
                p = self._create_file(fname, age_seconds=200000)
                is_imp, _reason, _ = evaluate_file_importance(p, protect_recent_hours=0)
                self.assertTrue(is_imp)

    def test_important_extensions(self):
        p_py = self._create_file("script.py", age_seconds=100000)
        p_csv = self._create_file("data.csv", age_seconds=100000)
        p_odt = self._create_file("notes.odt", age_seconds=100000)

        is_imp1, _, _ = evaluate_file_importance(p_py, protect_recent_hours=0)
        is_imp2, _, _ = evaluate_file_importance(p_csv, protect_recent_hours=0)
        is_imp3, _, _ = evaluate_file_importance(p_odt, protect_recent_hours=0)

        self.assertTrue(is_imp1)
        self.assertTrue(is_imp2)
        self.assertTrue(is_imp3)

    def test_junk_extensions(self):
        p_tmp = self._create_file("cache.tmp")
        p_old = self._create_file("backup.old")

        is_imp1, reason1, _ = evaluate_file_importance(p_tmp)
        is_imp2, reason2, _ = evaluate_file_importance(p_old)

        self.assertFalse(is_imp1)
        self.assertIn("Junk", reason1)
        self.assertFalse(is_imp2)
        self.assertIn("Junk", reason2)

    def test_recent_file_grace_period_and_future_timestamp(self):
        p_recent = self._create_file("custom_tool.xyz", age_seconds=3600)
        p_old = self._create_file("custom_tool_old.xyz", age_seconds=100000)
        p_future = self._create_file("future_tool.xyz", age_seconds=-3600)

        is_imp_recent, reason_recent, _ = evaluate_file_importance(p_recent, protect_recent_hours=24)
        is_imp_old, _reason_old, _ = evaluate_file_importance(p_old, protect_recent_hours=24)
        is_imp_future, reason_future, _ = evaluate_file_importance(p_future, protect_recent_hours=24)

        self.assertTrue(is_imp_recent)
        self.assertIn("Recent", reason_recent)
        self.assertFalse(is_imp_old)
        self.assertTrue(is_imp_future)
        self.assertIn("Recent", reason_future)

    def test_system_metadata_detection(self):
        self.assertTrue(is_system_metadata_file("desktop.ini"))
        self.assertTrue(is_system_metadata_file("Thumbs.db"))
        self.assertTrue(is_system_metadata_file(".DS_Store"))


if __name__ == "__main__":
    unittest.main()
