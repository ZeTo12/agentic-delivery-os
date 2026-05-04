"""Tests for uninstall.py --local mode (T25, T27)."""
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

from tests import make_mock_ados_source


class TestUninstallLocal(unittest.TestCase):
    def setUp(self) -> None:
        self.tmp = tempfile.mkdtemp()
        self.mock_src = make_mock_ados_source(self.tmp)
        self.project = Path(self.tmp) / "project"
        self.project.mkdir()
        (self.project / ".git").mkdir()
        self.original_cwd = os.getcwd()
        os.chdir(self.project)

    def tearDown(self) -> None:
        os.chdir(self.original_cwd)
        import shutil
        shutil.rmtree(self.tmp, ignore_errors=True)

    def _do_install(self) -> None:
        import install
        with patch.dict(os.environ, {"ADOS_SOURCE_DIR": str(self.mock_src)}):
            install.main(["--local", "--no-fetch"])

    # T25: Uninstall --local --force removes all installed files
    def test_local_uninstall_removes_files(self) -> None:
        self._do_install()
        handbook = self.project / "doc" / "documentation-handbook.md"
        self.assertTrue(handbook.exists(), "install should have created handbook")

        import uninstall
        with patch("uninstall.require_project_root"):
            uninstall.main(["--local", "--force"])

        self.assertFalse(handbook.exists(), "handbook should be removed after uninstall")

    # T27: --force bypasses confirmation prompt
    def test_force_skips_prompt(self) -> None:
        self._do_install()
        import uninstall
        with patch("builtins.input") as mock_input, \
             patch("uninstall.require_project_root"):
            uninstall.main(["--local", "--force"])
            mock_input.assert_not_called()

    def test_dry_run_no_removal(self) -> None:
        self._do_install()
        handbook = self.project / "doc" / "documentation-handbook.md"
        self.assertTrue(handbook.exists())

        import uninstall
        with patch("uninstall.require_project_root"):
            uninstall.main(["--local", "--force", "--dry-run"])

        self.assertTrue(handbook.exists(), "dry-run should not remove files")


if __name__ == "__main__":
    unittest.main()
