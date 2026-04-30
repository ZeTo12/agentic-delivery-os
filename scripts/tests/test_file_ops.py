"""Tests for ados_lib.file_ops (T3–T9)."""
from __future__ import annotations

import os
import sys
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

_SCRIPTS_DIR = str(Path(__file__).resolve().parent.parent)
if _SCRIPTS_DIR not in sys.path:
    sys.path.insert(0, _SCRIPTS_DIR)

from ados_lib.file_ops import copy_file_with_diff, copy_updatable_file, ensure_dir, remove_file
from ados_lib.types import InstallConfig, InstallCounters, UninstallConfig, UninstallCounters


class TestCopyFileWithDiff(unittest.TestCase):
    def setUp(self) -> None:
        self.tmp = tempfile.mkdtemp()
        self.src = Path(self.tmp) / "src.md"
        self.dest = Path(self.tmp) / "dest.md"
        self.src.write_text("content A\n", encoding="utf-8")

    def tearDown(self) -> None:
        import shutil
        shutil.rmtree(self.tmp, ignore_errors=True)

    def _config(self, **kwargs: object) -> InstallConfig:
        return InstallConfig(**kwargs)  # type: ignore[arg-type]

    # T3: New file created
    def test_new_file_created(self) -> None:
        config = self._config()
        counters = InstallCounters()
        copy_file_with_diff(self.src, self.dest, "dest.md", config, counters)
        self.assertTrue(self.dest.exists())
        self.assertEqual(counters.added, 1)
        self.assertEqual(counters.updated, 0)

    # T4: Identical file skipped
    def test_identical_file_skipped(self) -> None:
        self.dest.write_text("content A\n", encoding="utf-8")
        config = self._config()
        counters = InstallCounters()
        copy_file_with_diff(self.src, self.dest, "dest.md", config, counters)
        self.assertEqual(counters.unchanged, 1)
        self.assertEqual(counters.updated, 0)

    # T5: Force-update on diff
    def test_force_update(self) -> None:
        self.dest.write_text("content B\n", encoding="utf-8")
        config = self._config(force=True)
        counters = InstallCounters()
        copy_file_with_diff(self.src, self.dest, "dest.md", config, counters)
        self.assertEqual(self.dest.read_text(encoding="utf-8"), "content A\n")
        self.assertEqual(counters.updated, 1)

    # T6: Interactive mode prompts — user says yes
    def test_interactive_mode_yes(self) -> None:
        self.dest.write_text("content B\n", encoding="utf-8")
        config = self._config(interactive=True)
        counters = InstallCounters()
        with patch("builtins.input", return_value="y"):
            copy_file_with_diff(self.src, self.dest, "dest.md", config, counters)
        self.assertEqual(self.dest.read_text(encoding="utf-8"), "content A\n")
        self.assertEqual(counters.updated, 1)

    # T6: Interactive mode prompts — user says no
    def test_interactive_mode_no(self) -> None:
        self.dest.write_text("content B\n", encoding="utf-8")
        config = self._config(interactive=True)
        counters = InstallCounters()
        with patch("builtins.input", return_value="n"):
            copy_file_with_diff(self.src, self.dest, "dest.md", config, counters)
        self.assertEqual(self.dest.read_text(encoding="utf-8"), "content B\n")
        self.assertEqual(counters.unchanged, 1)

    # T7: Updatable file auto-updated
    def test_updatable_auto_update(self) -> None:
        self.dest.write_text("content B\n", encoding="utf-8")
        config = self._config()
        counters = InstallCounters()
        copy_updatable_file(self.src, self.dest, "dest.md", config, counters)
        self.assertEqual(self.dest.read_text(encoding="utf-8"), "content A\n")
        self.assertEqual(counters.updated, 1)

    # T8: Project-specific file preserved (not updatable, not force)
    def test_project_specific_preserved(self) -> None:
        self.dest.write_text("content B\n", encoding="utf-8")
        config = self._config()
        counters = InstallCounters()
        copy_file_with_diff(self.src, self.dest, "dest.md", config, counters, updatable=False)
        self.assertEqual(self.dest.read_text(encoding="utf-8"), "content B\n")
        self.assertEqual(counters.unchanged, 1)

    # T9: Symlink replaced with real copy (Unix only)
    @unittest.skipIf(sys.platform == "win32", "symlinks require elevated permissions on Windows")
    def test_symlink_replaced(self) -> None:
        other = Path(self.tmp) / "other.md"
        other.write_text("other\n", encoding="utf-8")
        self.dest.symlink_to(other)
        config = self._config()
        counters = InstallCounters()
        copy_file_with_diff(self.src, self.dest, "dest.md", config, counters)
        self.assertFalse(self.dest.is_symlink())
        self.assertEqual(self.dest.read_text(encoding="utf-8"), "content A\n")
        self.assertEqual(counters.updated, 1)

    def test_dry_run_no_write(self) -> None:
        config = self._config(dry_run=True)
        counters = InstallCounters()
        copy_file_with_diff(self.src, self.dest, "dest.md", config, counters)
        self.assertFalse(self.dest.exists())
        self.assertEqual(counters.added, 1)


class TestEnsureDir(unittest.TestCase):
    def setUp(self) -> None:
        self.tmp = tempfile.mkdtemp()

    def tearDown(self) -> None:
        import shutil
        shutil.rmtree(self.tmp, ignore_errors=True)

    def test_creates_missing_dir(self) -> None:
        target = Path(self.tmp) / "new" / "nested"
        config = InstallConfig()
        ensure_dir(target, "new/nested", config)
        self.assertTrue(target.is_dir())

    def test_skips_existing_dir(self) -> None:
        target = Path(self.tmp)
        config = InstallConfig()
        ensure_dir(target, "existing", config)  # should not raise


class TestRemoveFile(unittest.TestCase):
    def setUp(self) -> None:
        self.tmp = tempfile.mkdtemp()

    def tearDown(self) -> None:
        import shutil
        shutil.rmtree(self.tmp, ignore_errors=True)

    def test_removes_existing_file(self) -> None:
        f = Path(self.tmp) / "file.md"
        f.write_text("x", encoding="utf-8")
        config = UninstallConfig()
        counters = UninstallCounters()
        remove_file(f, "file.md", config, counters)
        self.assertFalse(f.exists())
        self.assertEqual(counters.removed, 1)

    def test_skips_missing_file(self) -> None:
        f = Path(self.tmp) / "missing.md"
        config = UninstallConfig()
        counters = UninstallCounters()
        remove_file(f, "missing.md", config, counters)
        self.assertEqual(counters.skipped, 1)


if __name__ == "__main__":
    unittest.main()
