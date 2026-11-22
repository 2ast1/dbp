"""
Tests for system integration, safe_rmtree, resource resolution, and uninstaller.
"""

import inspect
import os
import shutil
import stat
import tempfile
import unittest
from unittest import mock
import warnings

from dbp_core import system


class TestSystem(unittest.TestCase):
    def setUp(self):
        self.temp_dir = tempfile.mkdtemp()
        self.orig_cwd = os.getcwd()

    def tearDown(self):
        os.chdir(self.orig_cwd)
        shutil.rmtree(self.temp_dir, ignore_errors=True)

    def test_safe_rmtree_removes_readonly_tree_without_deprecation_warnings(self):
        root = os.path.join(self.temp_dir, "readonly_tree")
        sub = os.path.join(root, "nested")
        os.makedirs(sub, exist_ok=True)
        ro_file = os.path.join(sub, "locked.txt")
        with open(ro_file, "w", encoding="utf-8") as f:
            f.write("data")
        os.chmod(ro_file, stat.S_IREAD)
        os.chmod(sub, stat.S_IREAD)

        with warnings.catch_warnings(record=True) as caught:
            warnings.simplefilter("always")
            system.safe_rmtree(root)

        self.assertFalse(os.path.exists(root))
        dep_warnings = [w for w in caught if issubclass(w.category, DeprecationWarning)]
        self.assertEqual(dep_warnings, [])

    def test_resource_path_independent_of_cwd(self):
        os.chdir(self.temp_dir)
        ico_path = system.resource_path("besen.ico")
        self.assertTrue(os.path.exists(ico_path))
        self.assertEqual(os.path.basename(ico_path), "besen.ico")

    def test_uninstall_application_signature_and_quiet_cleanup(self):
        sig = inspect.signature(system.uninstall_application)
        self.assertIn("config", sig.parameters)
        self.assertIn("quiet", sig.parameters)

        fake_dbp = os.path.join(self.temp_dir, "DBP_AppData")
        fake_tgt = os.path.join(self.temp_dir, "Archive")
        fake_trash = os.path.join(fake_tgt, "DBP_Trash")
        os.makedirs(fake_dbp, exist_ok=True)
        os.makedirs(fake_trash, exist_ok=True)
        with open(os.path.join(fake_dbp, "config.json"), "w", encoding="utf-8") as f:
            f.write("{}")
        with open(os.path.join(fake_trash, "old.tmp"), "w", encoding="utf-8") as f:
            f.write("trash")

        with mock.patch.object(system, "DBP_DIR", fake_dbp), \
             mock.patch.object(system, "setup_autostart") as m_auto, \
             mock.patch.object(system, "setup_startmenu_shortcut") as m_menu, \
             mock.patch.object(system, "setup_uninstall_registry") as m_reg:
            with self.assertRaises(SystemExit) as cm:
                system.uninstall_application(config={"target_dir": fake_tgt}, quiet=True)

        self.assertEqual(cm.exception.code, 0)
        m_auto.assert_called_once_with(False, show_errors=False)
        m_menu.assert_called_once_with(False)
        m_reg.assert_called_once_with(False)
        self.assertFalse(os.path.exists(fake_trash))
        self.assertFalse(os.path.exists(fake_dbp))


if __name__ == "__main__":
    unittest.main()
