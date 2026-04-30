"""Tests for uninstall.py --global mode (T26)."""
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


class TestUninstallGlobal(unittest.TestCase):
    def setUp(self) -> None:
        self.tmp = tempfile.mkdtemp()
        self.mock_src = make_mock_ados_source(self.tmp)
        self.ados_home = Path(self.tmp) / "a" / "b" / "c" / "ados_home"
        self.repo_dir = self.ados_home / "repo"
        self.opencode_dir = Path(self.tmp) / "a" / "b" / "c" / "opencode"

        # Simulate a global install by creating stub agent/command files
        agent_dir = self.opencode_dir / "agent"
        agent_dir.mkdir(parents=True, exist_ok=True)
        (agent_dir / "pm.md").write_text("# pm\n", encoding="utf-8")
        (agent_dir / "coder.md").write_text("# coder\n", encoding="utf-8")

        command_dir = self.opencode_dir / "command"
        command_dir.mkdir(parents=True, exist_ok=True)
        (command_dir / "commit.md").write_text("# commit\n", encoding="utf-8")

        self.ados_home.mkdir(parents=True, exist_ok=True)

    def tearDown(self) -> None:
        import shutil
        shutil.rmtree(self.tmp, ignore_errors=True)

    # T26: global uninstall removes agent/command files
    def test_global_uninstall_removes_agent_and_command_files(self) -> None:
        import uninstall

        with patch.dict(os.environ, {
            "ADOS_HOME": str(self.ados_home),
            "OPENCODE_GLOBAL_DIR": str(self.opencode_dir),
        }):
            uninstall.main(["--global", "--force"])

        # Agent files should be removed
        self.assertFalse((self.opencode_dir / "agent" / "pm.md").exists())
        self.assertFalse((self.opencode_dir / "agent" / "coder.md").exists())
        # Command files should be removed
        self.assertFalse((self.opencode_dir / "command" / "commit.md").exists())
        # ados_home should be removed
        self.assertFalse(self.ados_home.exists())


if __name__ == "__main__":
    unittest.main()
