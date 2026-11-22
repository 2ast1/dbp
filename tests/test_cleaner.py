"""
Tests for Core Cleanup Engine, subfolder recursive cleanup, and safety guards.
"""

import datetime
import os
import shutil
import stat
import tempfile
import time
import unittest
from unittest import mock

from dbp_core import cleaner, config
from dbp_core.cleaner import (
    check_interval,
    enforce_log_size,
    get_unique_path,
    is_dangerous_source_dir,
    is_same_or_subpath,
    perform_cleanup,
    perform_cleanup_detailed,
    safe_move,
)


class TestCleaner(unittest.TestCase):
    def setUp(self):
        self.base_dir = tempfile.mkdtemp()
        self.appdata_dir = os.path.join(self.base_dir, "AppData")
        self.src_dir = os.path.join(self.base_dir, "Downloads")
        self.tgt_dir = os.path.join(self.base_dir, "Archive")
        os.makedirs(self.appdata_dir, exist_ok=True)
        os.makedirs(self.src_dir, exist_ok=True)
        os.makedirs(self.tgt_dir, exist_ok=True)

        self.orig_cfg_dbp = config.DBP_DIR
        self.orig_cfg_file = config.CONFIG_FILE
        self.orig_cln_dbp = cleaner.DBP_DIR
        self.orig_cln_log = cleaner.LOG_FILE

        config.DBP_DIR = self.appdata_dir
        config.CONFIG_FILE = os.path.join(self.appdata_dir, "config.json")
        cleaner.DBP_DIR = self.appdata_dir
        cleaner.LOG_FILE = os.path.join(self.appdata_dir, "history.log")

    def tearDown(self):
        config.DBP_DIR = self.orig_cfg_dbp
        config.CONFIG_FILE = self.orig_cfg_file
        cleaner.DBP_DIR = self.orig_cln_dbp
        cleaner.LOG_FILE = self.orig_cln_log
        shutil.rmtree(self.base_dir, ignore_errors=True)

    def _write_file(self, folder, relative_path, content="test content", age_seconds=None):
        p = os.path.join(folder, relative_path)
        os.makedirs(os.path.dirname(p), exist_ok=True)
        with open(p, "w", encoding="utf-8") as f:
            f.write(content)
        if age_seconds is not None:
            past = time.time() - age_seconds
            os.utime(p, (past, past))
        return p

    def test_recursive_subfolder_cleanup(self):
        self._write_file(self.src_dir, "doc1.pdf")
        self._write_file(self.src_dir, "temp.junk")
        self._write_file(self.src_dir, os.path.join("SubFolder1", "nested_doc.pdf"))
        self._write_file(self.src_dir, os.path.join("SubFolder1", "DeepSub", "deep_junk.junk"))
        self._write_file(self.src_dir, os.path.join("SubFolder2", "Rechnung_2026.other"))
        self._write_file(self.src_dir, "downloading_file.iso.crdownload")

        cfg = {
            "source_dir": self.src_dir,
            "target_dir": self.tgt_dir,
            "extensions": ".pdf",
            "smart_trash": True,
            "include_subfolders": True,
            "clean_empty_folders": True,
            "protect_recent_hours": 0,
            "max_log_size": "0.5",
        }

        perform_cleanup(cfg, is_portable=False)

        self.assertTrue(os.path.exists(os.path.join(self.tgt_dir, "doc1.pdf")))
        self.assertTrue(os.path.exists(os.path.join(self.tgt_dir, "nested_doc.pdf")))
        self.assertTrue(os.path.exists(os.path.join(self.tgt_dir, "Rechnung_2026.other")))
        self.assertTrue(os.path.exists(os.path.join(self.src_dir, "downloading_file.iso.crdownload")))

        trash_dir = os.path.join(self.tgt_dir, "DBP_Trash")
        self.assertTrue(os.path.exists(os.path.join(trash_dir, "temp.junk")))
        self.assertTrue(os.path.exists(os.path.join(trash_dir, "deep_junk.junk")))

        self.assertFalse(os.path.exists(os.path.join(self.src_dir, "SubFolder1", "DeepSub")))
        self.assertFalse(os.path.exists(os.path.join(self.src_dir, "SubFolder1")))
        self.assertFalse(os.path.exists(os.path.join(self.src_dir, "SubFolder2")))

    def test_portable_mode_permanent_deletion(self):
        self._write_file(self.src_dir, "keep.pdf")
        self._write_file(self.src_dir, "junk.xyz")
        self._write_file(self.src_dir, os.path.join("SubDir", "sub_junk.xyz"))

        cfg = {
            "source_dir": self.src_dir,
            "target_dir": self.tgt_dir,
            "extensions": ".pdf",
            "smart_trash": False,
            "include_subfolders": True,
            "clean_empty_folders": True,
        }

        perform_cleanup(cfg, is_portable=True)

        self.assertTrue(os.path.exists(os.path.join(self.tgt_dir, "keep.pdf")))
        self.assertFalse(os.path.exists(os.path.join(self.src_dir, "junk.xyz")))
        self.assertFalse(os.path.exists(os.path.join(self.src_dir, "SubDir")))
        self.assertFalse(os.path.exists(os.path.join(self.tgt_dir, "DBP_Trash")))

    def test_non_recursive_never_deletes_nonempty_subfolders(self):
        # Ungescannte nicht-leere Unterordner dürfen NIEMALS blind gelöscht oder verschoben werden
        self._write_file(self.src_dir, "root.junk")
        kept_file = self._write_file(self.src_dir, os.path.join("ImportantProject", "important.pdf"))
        empty_dir = os.path.join(self.src_dir, "EmptyFolder")
        os.makedirs(empty_dir, exist_ok=True)

        for portable_mode in (False, True):
            with self.subTest(portable=portable_mode):
                self._write_file(self.src_dir, "root.junk")
                os.makedirs(empty_dir, exist_ok=True)
                cfg = {
                    "source_dir": self.src_dir,
                    "target_dir": self.tgt_dir,
                    "extensions": ".pdf",
                    "smart_trash": False,
                    "include_subfolders": False,
                    "clean_empty_folders": True,
                }
                perform_cleanup(cfg, is_portable=portable_mode)
                self.assertTrue(os.path.exists(kept_file))
                self.assertFalse(os.path.exists(empty_dir))
                self.assertFalse(os.path.exists(os.path.join(self.src_dir, "root.junk")))

    def test_recursive_cleanup_empties_downloads_completely(self):
        self._write_file(self.src_dir, os.path.join("A", "B", "desktop.ini"), "subdesktop")
        self._write_file(self.src_dir, os.path.join("A", "B", "Thumbs.db"), "thumbs")
        self._write_file(self.src_dir, os.path.join("A", "recent_setup.exe"), "bin", age_seconds=60)
        self._write_file(self.src_dir, os.path.join("C", "old_junk.xyz"), "junk", age_seconds=200000)

        cfg = {
            "source_dir": self.src_dir,
            "target_dir": self.tgt_dir,
            "extensions": ".pdf",
            "smart_trash": True,
            "include_subfolders": True,
            "clean_empty_folders": True,
            "protect_recent_hours": 24,
        }
        perform_cleanup(cfg, is_portable=False)

        # Downloads muss komplett leer sein, neue Datei liegt im Archiv
        self.assertEqual(os.listdir(self.src_dir), [])
        self.assertTrue(os.path.exists(os.path.join(self.tgt_dir, "recent_setup.exe")))

    def test_root_desktop_ini_preserved(self):
        root_ini = self._write_file(self.src_dir, "desktop.ini", "[.ShellClassInfo]")
        self._write_file(self.src_dir, "temp.xyz", "junk", age_seconds=200000)

        cfg = {
            "source_dir": self.src_dir,
            "target_dir": self.tgt_dir,
            "extensions": ".pdf",
            "smart_trash": False,
            "include_subfolders": True,
            "clean_empty_folders": True,
        }
        perform_cleanup(cfg, is_portable=False)

        self.assertTrue(os.path.exists(root_ini))
        self.assertFalse(os.path.exists(os.path.join(self.src_dir, "temp.xyz")))

    def test_source_inside_target_still_cleans(self):
        # Zielordner ist Elternordner von Quelle
        nested_src = os.path.join(self.tgt_dir, "SubDownloads")
        self._write_file(nested_src, "doc.pdf")
        self._write_file(nested_src, os.path.join("Inner", "junk.xyz"))

        cfg = {
            "source_dir": nested_src,
            "target_dir": self.tgt_dir,
            "extensions": ".pdf",
            "smart_trash": False,
            "include_subfolders": True,
            "clean_empty_folders": True,
        }
        perform_cleanup(cfg, is_portable=False)

        self.assertTrue(os.path.exists(os.path.join(self.tgt_dir, "doc.pdf")))
        self.assertTrue(os.path.exists(os.path.join(self.tgt_dir, "DBP_Trash", "junk.xyz")))
        self.assertEqual(os.listdir(nested_src), [])

    def test_safety_target_nested_in_source(self):
        nested_target = os.path.join(self.src_dir, "Archived_Files")
        self._write_file(self.src_dir, "doc.pdf")
        self._write_file(nested_target, "previously_archived.pdf")

        cfg = {
            "source_dir": self.src_dir,
            "target_dir": nested_target,
            "extensions": ".pdf",
            "include_subfolders": True,
            "clean_empty_folders": True,
        }

        perform_cleanup(cfg, is_portable=False)

        self.assertTrue(os.path.exists(os.path.join(nested_target, "previously_archived.pdf")))
        self.assertTrue(os.path.exists(os.path.join(nested_target, "doc.pdf")))

    def test_safety_deeply_nested_target_protects_ancestor(self):
        deep_target = os.path.join(self.src_dir, "Keep", "Archive")
        self._write_file(self.src_dir, "doc.pdf")
        self._write_file(deep_target, "old.pdf")

        cfg = {
            "source_dir": self.src_dir,
            "target_dir": deep_target,
            "extensions": ".pdf",
            "include_subfolders": True,
            "clean_empty_folders": True,
        }
        perform_cleanup(cfg, is_portable=False)

        self.assertTrue(os.path.exists(os.path.join(deep_target, "old.pdf")))
        self.assertTrue(os.path.exists(os.path.join(deep_target, "doc.pdf")))
        self.assertTrue(os.path.exists(os.path.join(self.src_dir, "Keep")))

    def test_active_downloads_skipped_before_ext_list_and_without_smart_trash(self):
        lock_doc = self._write_file(self.src_dir, "~$Vertrag.docx", "lock")
        cr_dl = self._write_file(self.src_dir, "video.mp4.crdownload", "partial")
        op_dl = self._write_file(self.src_dir, "installer.exe.opdownload", "partial")

        cfg = {
            "source_dir": self.src_dir,
            "target_dir": self.tgt_dir,
            "extensions": ".docx",
            "smart_trash": False,
            "include_subfolders": True,
            "clean_empty_folders": True,
        }
        perform_cleanup(cfg, is_portable=True)

        self.assertTrue(os.path.exists(lock_doc))
        self.assertTrue(os.path.exists(cr_dl))
        self.assertTrue(os.path.exists(op_dl))
        self.assertFalse(os.path.exists(os.path.join(self.tgt_dir, "~$Vertrag.docx")))

    def test_is_same_or_subpath_dotdot_prefix_folder(self):
        parent = os.path.join(self.base_dir, "Downloads")
        weird_sibling = os.path.join(self.base_dir, "..weird_folder")
        self.assertFalse(is_same_or_subpath(weird_sibling, parent))
        self.assertTrue(is_same_or_subpath(os.path.join(parent, "..weird_sub"), parent))

    def test_process_trash_runs_before_moving_new_files_and_deletes_readonly(self):
        trash_dir = os.path.join(self.tgt_dir, "DBP_Trash")
        os.makedirs(trash_dir, exist_ok=True)

        # Alte Datei im Trash (>= 8 Tage) mit Schreibschutz -> muss gelöscht werden
        old_trash = self._write_file(trash_dir, "expired.tmp", "old", age_seconds=8 * 86400)
        os.chmod(old_trash, stat.S_IREAD)

        # Alter schreibgeschützter Ordner im Trash (>= 8 Tage) -> muss gelöscht werden
        old_dir = os.path.join(trash_dir, "expired_dir")
        nested_old = self._write_file(old_dir, "inside.txt", "old", age_seconds=8 * 86400)
        os.chmod(nested_old, stat.S_IREAD)
        past = time.time() - 8 * 86400
        os.utime(old_dir, (past, past))

        # Neu verschobene Datei mit altem mtime: selbst wenn os.utime fehlschlägt,
        # darf sie nicht im selben Lauf gelöscht werden
        self._write_file(self.src_dir, "freshly_trashed.xyz", "data", age_seconds=30 * 86400)

        cfg = {
            "source_dir": self.src_dir,
            "target_dir": self.tgt_dir,
            "extensions": ".pdf",
            "smart_trash": False,
            "include_subfolders": True,
            "clean_empty_folders": True,
        }
        with mock.patch("dbp_core.cleaner.os.utime", side_effect=OSError("utime unsupported")):
            perform_cleanup(cfg, is_portable=False)

        self.assertFalse(os.path.exists(old_trash))
        self.assertFalse(os.path.exists(old_dir))
        self.assertTrue(os.path.exists(os.path.join(trash_dir, "freshly_trashed.xyz")))

    def test_enforce_log_size_no_double_cr(self):
        log_path = cleaner.LOG_FILE
        chunk = ("--- Run on 2026-11-22 12:00:00 ---\r\n" + ("ARCHIVE: a.pdf\r\n" * 5000))
        with open(log_path, "w", encoding="utf-8", newline="") as f:
            for _ in range(15):
                f.write(chunk)

        enforce_log_size("0.5")
        with open(log_path, "rb") as f:
            raw = f.read()
        self.assertNotIn(b"\r\r\n", raw)

    def test_check_interval_edge_cases(self):
        self.assertTrue(check_interval("daily", None))
        self.assertTrue(check_interval("daily", 12345))
        tomorrow = (datetime.date.today() + datetime.timedelta(days=1)).strftime("%Y-%m-%d")
        self.assertTrue(check_interval("daily", tomorrow))
        today = datetime.date.today().strftime("%Y-%m-%d")
        self.assertFalse(check_interval("daily", today))

    def test_is_dangerous_source_dir(self):
        if os.name == "nt":
            self.assertTrue(is_dangerous_source_dir("C:\\"))
            self.assertTrue(is_dangerous_source_dir("C:\\Windows"))
        else:
            self.assertTrue(is_dangerous_source_dir("/"))
            self.assertTrue(is_dangerous_source_dir("/etc"))
        self.assertTrue(is_dangerous_source_dir(os.path.expanduser("~")))
        self.assertFalse(is_dangerous_source_dir(self.src_dir))

    def test_safe_move_readonly_and_cross_device_rollback(self):
        ro_file = self._write_file(self.src_dir, "readonly.txt", "content")
        os.chmod(ro_file, stat.S_IREAD)
        dst = os.path.join(self.tgt_dir, "readonly.txt")
        safe_move(ro_file, dst)
        self.assertFalse(os.path.exists(ro_file))
        self.assertTrue(os.path.exists(dst))
        os.chmod(dst, stat.S_IWRITE)

        # Rollback bei Fehler nach Kopie im Cross-Drive-Fallback
        src2 = self._write_file(self.src_dir, "fail_src.txt", "content")
        dst2 = os.path.join(self.tgt_dir, "fail_src.txt")
        with mock.patch("dbp_core.cleaner.os.rename", side_effect=OSError("EXDEV")), \
             mock.patch("dbp_core.cleaner.safe_remove_file", side_effect=[PermissionError("locked"), None]):
            with self.assertRaises(PermissionError):
                safe_move(src2, dst2)
        self.assertTrue(os.path.exists(src2))

    def test_preserves_existing_autostart_on_last_run_update(self):
        existing = config.load_config()
        existing["source_dir"] = self.src_dir
        existing["target_dir"] = self.tgt_dir
        existing["autostart"] = True
        config.save_config(existing)

        self._write_file(self.src_dir, "doc.pdf")
        partial_cfg = {
            "source_dir": self.src_dir,
            "target_dir": self.tgt_dir,
            "extensions": ".pdf",
        }
        res = perform_cleanup_detailed(partial_cfg, is_portable=False)
        self.assertTrue(res["success"])

        reloaded = config.load_config()
        self.assertTrue(reloaded["autostart"])
        self.assertTrue(bool(reloaded["last_run_cleanup"]))

    def test_unique_path_generation(self):
        self._write_file(self.tgt_dir, "report.pdf")
        new_p = get_unique_path(self.tgt_dir, "report.pdf")
        self.assertEqual(os.path.basename(new_p), "report_1.pdf")

        self._write_file(self.tgt_dir, "report_1.pdf")
        new_p2 = get_unique_path(self.tgt_dir, "report.pdf")
        self.assertEqual(os.path.basename(new_p2), "report_2.pdf")


if __name__ == "__main__":
    unittest.main()
