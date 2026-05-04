"""Integration tests — full uninstall round-trip."""
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


class TestUninstallIntegration(unittest.TestCase):
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

    def test_install_then_uninstall_removes_all_files(self) -> None:
        """Install first, then uninstall, verify all installed files are gone."""
        import install
        import uninstall

        # Install
        with patch.dict(os.environ, {"ADOS_SOURCE_DIR": str(self.mock_src)}):
            install.main(["--local", "--no-fetch"])

        handbook = self.project / "doc" / "documentation-handbook.md"
        index = self.project / "doc" / "00-index.md"
        self.assertTrue(handbook.exists(), "handbook should exist after install")

        # Uninstall
        with patch("uninstall.require_project_root"):
            uninstall.main(["--local", "--force"])

        self.assertFalse(handbook.exists(), "handbook should be removed after uninstall")
        self.assertFalse(index.exists(), "index should be removed after uninstall")

    def test_uninstall_dry_run_keeps_files(self) -> None:
        import install
        import uninstall

        with patch.dict(os.environ, {"ADOS_SOURCE_DIR": str(self.mock_src)}):
            install.main(["--local", "--no-fetch"])

        handbook = self.project / "doc" / "documentation-handbook.md"
        with patch("uninstall.require_project_root"):
            uninstall.main(["--local", "--force", "--dry-run"])

        self.assertTrue(handbook.exists(), "dry-run should not remove files")


if __name__ == "__main__":
    unittest.main()
