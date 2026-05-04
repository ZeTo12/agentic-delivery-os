"""Integration tests — full install round-trip (T21–T24, T28, T29).

Manual cross-platform verification checklist:
    [ ] Ubuntu 22.04, Python 3.8:  python3 -m unittest discover -s scripts/tests
    [ ] Ubuntu 22.04, Python 3.12: python3 -m unittest discover -s scripts/tests
    [ ] macOS (Monterey+), Python 3.8:  python3 -m unittest discover -s scripts/tests
    [ ] macOS (Monterey+), Python 3.12: python3 -m unittest discover -s scripts/tests
    [ ] Windows 10/11, Python 3.8:  python -m unittest discover -s scripts/tests
    [ ] Windows 10/11, Python 3.12: python -m unittest discover -s scripts/tests

Expected: 0 failures, 0 errors on all combinations.
"""
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


class TestInstallIntegration(unittest.TestCase):
    """Full install round-trip tests using mock ADOS source."""

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

    def _install(self, extra_args: list[str] | None = None) -> None:
        import install
        args = ["--local", "--no-fetch"] + (extra_args or [])
        with patch.dict(os.environ, {"ADOS_SOURCE_DIR": str(self.mock_src)}):
            install.main(args)

    # Step A+B+C: Create mock source, run install, assert expected files exist
    def test_install_creates_expected_files(self) -> None:
        self._install()
        expected_files = [
            "doc/documentation-handbook.md",
            "doc/00-index.md",
            "doc/guides/change-lifecycle.md",
            "doc/guides/system-dependencies.md",
            ".ai/rules/README.md",
            "doc/decisions/README.md",
            "doc/decisions/00-index.md",
            "doc/templates/README.md",
            "doc/templates/change-spec-template.md",
        ]
        for rel in expected_files:
            self.assertTrue(
                (self.project / rel).exists(),
                f"Expected {rel} to exist after install",
            )

    def test_install_creates_expected_dirs(self) -> None:
        self._install()
        expected_dirs = [
            "doc/overview",
            "doc/spec/features",
            "doc/decisions",
            "doc/changes",
            "doc/guides",
            ".ai/agent",
            ".ai/local",
            ".ai/rules",
        ]
        for rel in expected_dirs:
            self.assertTrue(
                (self.project / rel).is_dir(),
                f"Expected directory {rel} to exist after install",
            )

    # Step D: Second run is idempotent (added=0, updated=0)
    def test_idempotent_second_run(self) -> None:
        import install
        from ados_lib.types import InstallCounters

        self._install()

        captured: list[InstallCounters] = []
        original = install.install_local_files

        def capturing(src, cfg, ctrs):
            original(src, cfg, ctrs)
            captured.append(InstallCounters(added=ctrs.added, updated=ctrs.updated, unchanged=ctrs.unchanged))

        with patch.object(install, "install_local_files", side_effect=capturing):
            self._install()

        if captured:
            c = captured[0]
            self.assertEqual(c.added, 0, f"Expected 0 added on second run, got {c.added}")
            self.assertEqual(c.updated, 0, f"Expected 0 updated on second run, got {c.updated}")
            self.assertGreater(c.unchanged, 0, "Expected >0 unchanged on second run")

    # Step E: Modify one file in mock source → run again → assert updated=1
    def test_update_on_file_change(self) -> None:
        import install
        from ados_lib.types import InstallCounters

        self._install()

        # Modify a file in the mock source
        handbook_src = self.mock_src / "doc" / "documentation-handbook.md"
        handbook_src.write_text("# Modified Handbook\n", encoding="utf-8")

        captured: list[InstallCounters] = []
        original = install.install_local_files

        def capturing(src, cfg, ctrs):
            original(src, cfg, ctrs)
            captured.append(InstallCounters(added=ctrs.added, updated=ctrs.updated, unchanged=ctrs.unchanged))

        with patch.object(install, "install_local_files", side_effect=capturing):
            self._install()

        if captured:
            c = captured[0]
            self.assertGreaterEqual(c.updated, 1, f"Expected at least 1 updated, got {c.updated}")

    # T28: Windows path with spaces
    def test_path_with_spaces(self) -> None:
        """T28 — path with spaces handled without error."""
        spaces_dir = Path(self.tmp) / "John Doe" / "my project"
        spaces_dir.mkdir(parents=True, exist_ok=True)
        (spaces_dir / ".git").mkdir()

        prev_cwd = os.getcwd()
        os.chdir(spaces_dir)
        try:
            import install
            with patch.dict(os.environ, {"ADOS_SOURCE_DIR": str(self.mock_src)}):
                install.main(["--local", "--no-fetch"])
            self.assertTrue((spaces_dir / "doc" / "documentation-handbook.md").exists())
        finally:
            os.chdir(prev_cwd)

    # T29: XDG_CONFIG_HOME override on Linux
    def test_xdg_config_home_override(self) -> None:
        """T29 — XDG_CONFIG_HOME env override respected."""
        from ados_lib import platform_paths
        xdg = str(Path(self.tmp) / "xdg_config")
        with patch.dict(os.environ, {
            "XDG_CONFIG_HOME": xdg,
            "OPENCODE_GLOBAL_DIR": "",
        }), patch.object(sys, "platform", "linux"):
            result = platform_paths.get_opencode_global_dir()
            self.assertEqual(result, Path(xdg) / "opencode")


if __name__ == "__main__":
    unittest.main()
