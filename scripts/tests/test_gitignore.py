"""Tests for ados_lib.gitignore (T14–T15)."""
from __future__ import annotations

import sys
import tempfile
import unittest
from pathlib import Path

_SCRIPTS_DIR = str(Path(__file__).resolve().parent.parent)
if _SCRIPTS_DIR not in sys.path:
    sys.path.insert(0, _SCRIPTS_DIR)

from ados_lib.gitignore import ensure_gitignore_entry, file_contains_line
from ados_lib.types import InstallConfig


class TestFileContainsLine(unittest.TestCase):
    def test_contains_pattern(self) -> None:
        with tempfile.NamedTemporaryFile(mode="w", suffix=".gitignore", delete=False) as f:
            f.write(".ai/local/\n")
            name = f.name
        self.assertTrue(file_contains_line(Path(name), ".ai/local/"))
        Path(name).unlink()

    def test_missing_file_returns_false(self) -> None:
        self.assertFalse(file_contains_line(Path("/nonexistent/.gitignore"), "anything"))


class TestEnsureGitignoreEntry(unittest.TestCase):
    def setUp(self) -> None:
        self.tmp = tempfile.mkdtemp()
        self.gitignore = Path(self.tmp) / ".gitignore"

    def tearDown(self) -> None:
        import shutil
        shutil.rmtree(self.tmp, ignore_errors=True)

    # T14: Entry appended when absent
    def test_entry_appended(self) -> None:
        config = InstallConfig()
        ensure_gitignore_entry(self.gitignore, ".ai/local/", config)
        self.assertIn(".ai/local/", self.gitignore.read_text(encoding="utf-8"))

    # T15: Duplicate skipped
    def test_duplicate_skipped(self) -> None:
        self.gitignore.write_text(".ai/local/\n", encoding="utf-8")
        config = InstallConfig()
        ensure_gitignore_entry(self.gitignore, ".ai/local/", config)
        content = self.gitignore.read_text(encoding="utf-8")
        self.assertEqual(content.count(".ai/local/"), 1)

    def test_creates_gitignore_if_missing(self) -> None:
        config = InstallConfig()
        ensure_gitignore_entry(self.gitignore, ".ai/local", config)
        self.assertTrue(self.gitignore.exists())

    def test_dry_run_no_write(self) -> None:
        config = InstallConfig(dry_run=True)
        ensure_gitignore_entry(self.gitignore, ".ai/local/", config)
        self.assertFalse(self.gitignore.exists())


if __name__ == "__main__":
    unittest.main()
