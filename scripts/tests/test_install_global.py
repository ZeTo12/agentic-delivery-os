"""Tests for install.py --global mode (T22)."""
from __future__ import annotations

import os
import sys
import tempfile
import unittest
from pathlib import Path
from unittest.mock import MagicMock, patch

_SCRIPTS_DIR = str(Path(__file__).resolve().parent.parent)
if _SCRIPTS_DIR not in sys.path:
    sys.path.insert(0, _SCRIPTS_DIR)

from tests import make_mock_ados_source


class TestInstallGlobal(unittest.TestCase):
    def setUp(self) -> None:
        self.tmp = tempfile.mkdtemp()
        self.mock_src = make_mock_ados_source(self.tmp)
        self.ados_home = Path(self.tmp) / "ados_home"
        self.repo_dir = self.ados_home / "repo"
        self.opencode_dir = Path(self.tmp) / "opencode"
        # Simulate a cloned repo by copying mock_src to repo_dir
        import shutil
        shutil.copytree(str(self.mock_src), str(self.repo_dir))

    def tearDown(self) -> None:
        import shutil
        shutil.rmtree(self.tmp, ignore_errors=True)

    # T22: Global install copies agent and command files
    def test_global_install_copies_files(self) -> None:
        import install

        def fake_clone_or_update(config):
            pass  # repo already "cloned" in setUp

        with patch.dict(os.environ, {
            "ADOS_HOME": str(self.ados_home),
            "ADOS_REPO_DIR": str(self.repo_dir),
            "OPENCODE_GLOBAL_DIR": str(self.opencode_dir),
        }), patch("install.clone_or_update_repo", side_effect=fake_clone_or_update), \
             patch("install.require_git"):
            install.main(["--global"])

        # Agent files should be copied
        agent_dest = self.opencode_dir / "agent"
        self.assertTrue(agent_dest.is_dir())
        self.assertTrue(any(agent_dest.glob("*.md")))

        # Command files should be copied
        command_dest = self.opencode_dir / "command"
        self.assertTrue(command_dest.is_dir())
        self.assertTrue(any(command_dest.glob("*.md")))


if __name__ == "__main__":
    unittest.main()
