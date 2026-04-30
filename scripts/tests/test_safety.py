"""Tests for ados_lib.safety (T10–T13)."""
from __future__ import annotations

import sys
import tempfile
import unittest
from pathlib import Path

_SCRIPTS_DIR = str(Path(__file__).resolve().parent.parent)
if _SCRIPTS_DIR not in sys.path:
    sys.path.insert(0, _SCRIPTS_DIR)

from ados_lib.safety import safe_rmdir
from ados_lib.types import UninstallConfig


class TestSafeRmdir(unittest.TestCase):
    # T10: Root path rejected
    def test_root_rejected(self) -> None:
        config = UninstallConfig()
        root = Path("/") if sys.platform != "win32" else Path("C:\\")
        with self.assertRaises(RuntimeError):
            safe_rmdir(root, "root", config)

    # T11: Home directory rejected
    def test_home_rejected(self) -> None:
        config = UninstallConfig()
        with self.assertRaises(RuntimeError):
            safe_rmdir(Path.home(), "home", config)

    # T12: Shallow path (fewer than 4 parts) rejected
    def test_shallow_path_rejected(self) -> None:
        config = UninstallConfig()
        # On Unix /tmp has 2 parts (/, tmp) — too shallow
        # On Windows C:\tmp has 3 parts (C:\, tmp) — too shallow
        shallow = Path("/tmp") if sys.platform != "win32" else Path("C:\\tmp")
        with self.assertRaises(RuntimeError):
            safe_rmdir(shallow, "shallow", config)

    # T13: Valid deep path removed
    def test_valid_path_removed(self) -> None:
        with tempfile.TemporaryDirectory() as outer:
            deep = Path(outer) / "a" / "b" / "c"
            deep.mkdir(parents=True, exist_ok=True)
            config = UninstallConfig()
            safe_rmdir(deep, "a/b/c", config)
            self.assertFalse(deep.exists())

    def test_empty_path_raises(self) -> None:
        config = UninstallConfig()
        with self.assertRaises(RuntimeError):
            safe_rmdir(Path(""), "empty", config)

    def test_dry_run_does_not_remove(self) -> None:
        with tempfile.TemporaryDirectory() as outer:
            deep = Path(outer) / "a" / "b" / "c"
            deep.mkdir(parents=True, exist_ok=True)
            config = UninstallConfig(dry_run=True)
            safe_rmdir(deep, "a/b/c", config)
            self.assertTrue(deep.exists())


if __name__ == "__main__":
    unittest.main()
