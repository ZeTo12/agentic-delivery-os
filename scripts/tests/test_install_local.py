"""Tests for install.py --local mode (T21, T23, T24)."""
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


class TestInstallLocal(unittest.TestCase):
    def setUp(self) -> None:
        self.tmp = tempfile.mkdtemp()
        self.mock_src = make_mock_ados_source(self.tmp)
        # Create a fake project root with .git
        self.project = Path(self.tmp) / "project"
        self.project.mkdir()
        (self.project / ".git").mkdir()
        self.original_cwd = os.getcwd()
        os.chdir(self.project)

    def tearDown(self) -> None:
        os.chdir(self.original_cwd)
        import shutil
        shutil.rmtree(self.tmp, ignore_errors=True)

    # T21: Full local install round-trip
    def test_local_install_full(self) -> None:
        import install
        with patch.dict(os.environ, {"ADOS_SOURCE_DIR": str(self.mock_src)}):
            install.main(["--local", "--no-fetch"])

        # Check a sample of expected files
        self.assertTrue((self.project / "doc" / "documentation-handbook.md").exists())
        self.assertTrue((self.project / "doc" / "00-index.md").exists())
        self.assertTrue((self.project / "doc" / "guides" / "change-lifecycle.md").exists())
        self.assertTrue((self.project / ".ai" / "rules" / "README.md").exists())
        # Template dir
        self.assertTrue((self.project / "doc" / "templates" / "README.md").exists())
        # Directory stubs
        self.assertTrue((self.project / "doc" / "overview").is_dir())
        self.assertTrue((self.project / ".ai" / "local").is_dir())

    # T23: Second run is idempotent
    def test_local_install_idempotent(self) -> None:
        import install
        from ados_lib.types import InstallCounters
        with patch.dict(os.environ, {"ADOS_SOURCE_DIR": str(self.mock_src)}):
            install.main(["--local", "--no-fetch"])
            # Capture counters on second run
            captured: list[InstallCounters] = []

            original_install_local = install.install_local_files

            def capturing_install(source_dir, config, counters):
                original_install_local(source_dir, config, counters)
                captured.append(InstallCounters(
                    added=counters.added,
                    updated=counters.updated,
                    unchanged=counters.unchanged,
                ))

            with patch.object(install, "install_local_files", side_effect=capturing_install):
                install.main(["--local", "--no-fetch"])

        if captured:
            c = captured[0]
            self.assertEqual(c.added, 0, f"Second run added {c.added} files (expected 0)")
            self.assertEqual(c.updated, 0, f"Second run updated {c.updated} files (expected 0)")

    # T24: --dry-run makes no filesystem changes
    def test_local_dry_run_no_changes(self) -> None:
        import install
        with patch.dict(os.environ, {"ADOS_SOURCE_DIR": str(self.mock_src)}):
            install.main(["--local", "--no-fetch", "--dry-run"])
        # No actual files should have been created (other than dirs)
        handbook = self.project / "doc" / "documentation-handbook.md"
        self.assertFalse(handbook.exists(), "dry-run should not create files")


if __name__ == "__main__":
    unittest.main()
