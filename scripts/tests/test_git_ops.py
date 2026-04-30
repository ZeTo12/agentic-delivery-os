"""Tests for ados_lib.git_ops (T16–T20)."""
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

from ados_lib.git_ops import (
    auto_fetch_source,
    clone_or_update_repo,
    get_current_branch,
    get_short_sha,
    require_git,
    resolve_source_dir,
)
from ados_lib.types import InstallConfig


def _make_completed(returncode: int = 0, stdout: str = "", stderr: str = "") -> MagicMock:
    m = MagicMock()
    m.returncode = returncode
    m.stdout = stdout
    m.stderr = stderr
    return m


class TestRequireGit(unittest.TestCase):
    def test_exits_when_git_missing(self) -> None:
        with patch("shutil.which", return_value=None), self.assertRaises(SystemExit) as ctx:
            require_git()
        self.assertEqual(ctx.exception.code, 5)

    def test_passes_when_git_present(self) -> None:
        with patch("shutil.which", return_value="/usr/bin/git"):
            require_git()  # should not raise


class TestCloneOrUpdateRepo(unittest.TestCase):
    # T16: Clone when repo absent
    def test_clones_when_repo_absent(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            repo_dir = Path(tmp) / "a" / "b" / "c" / "repo"
            config = InstallConfig(branch="main")
            with patch("ados_lib.platform_paths.get_ados_repo_dir", return_value=repo_dir), \
                 patch("ados_lib.platform_paths.get_ados_home", return_value=Path(tmp) / "a" / "b" / "c"), \
                 patch("ados_lib.platform_paths.get_ados_repo_url", return_value="https://example.com/repo.git"), \
                 patch("ados_lib.git_ops.git_run") as mock_git:
                mock_git.return_value = _make_completed()
                clone_or_update_repo(config)
                # git clone should have been called
                calls = [str(c) for c in mock_git.call_args_list]
                self.assertTrue(any("clone" in c for c in calls))

    # T17: Pull when repo present
    def test_pulls_when_repo_present(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            repo_dir = Path(tmp) / "a" / "b" / "c" / "repo"
            (repo_dir / ".git").mkdir(parents=True, exist_ok=True)
            config = InstallConfig(branch="main")
            with patch("ados_lib.platform_paths.get_ados_repo_dir", return_value=repo_dir), \
                 patch("ados_lib.platform_paths.get_ados_home", return_value=Path(tmp) / "a" / "b" / "c"), \
                 patch("ados_lib.platform_paths.get_ados_repo_url", return_value="https://example.com/repo.git"), \
                 patch("ados_lib.git_ops.git_run") as mock_git, \
                 patch("ados_lib.git_ops.get_short_sha", return_value="abc1234"), \
                 patch("ados_lib.git_ops.get_current_branch", return_value="main"):
                mock_git.return_value = _make_completed()
                clone_or_update_repo(config)
                calls = [str(c) for c in mock_git.call_args_list]
                self.assertTrue(any("pull" in c for c in calls))

    # T18: Branch switch when needed
    def test_switches_branch_when_needed(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            repo_dir = Path(tmp) / "a" / "b" / "c" / "repo"
            (repo_dir / ".git").mkdir(parents=True, exist_ok=True)
            config = InstallConfig(branch="develop")
            with patch("ados_lib.platform_paths.get_ados_repo_dir", return_value=repo_dir), \
                 patch("ados_lib.platform_paths.get_ados_home", return_value=Path(tmp) / "a" / "b" / "c"), \
                 patch("ados_lib.platform_paths.get_ados_repo_url", return_value="https://example.com/repo.git"), \
                 patch("ados_lib.git_ops.git_run") as mock_git, \
                 patch("ados_lib.git_ops.get_short_sha", return_value="abc1234"), \
                 patch("ados_lib.git_ops.get_current_branch", return_value="main"):
                mock_git.return_value = _make_completed()
                clone_or_update_repo(config)
                calls = [str(c) for c in mock_git.call_args_list]
                self.assertTrue(any("checkout" in c for c in calls))


class TestResolveSourceDir(unittest.TestCase):
    # T19: ADOS_SOURCE_DIR env takes priority
    def test_env_takes_priority(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            with patch.dict(os.environ, {"ADOS_SOURCE_DIR": tmp}):
                result = resolve_source_dir(InstallConfig())
                self.assertEqual(result, Path(tmp))

    def test_env_nonexistent_exits(self) -> None:
        with patch.dict(os.environ, {"ADOS_SOURCE_DIR": "/nonexistent/path/that/does/not/exist"}):
            with self.assertRaises(SystemExit) as ctx:
                resolve_source_dir(InstallConfig())
            self.assertEqual(ctx.exception.code, 3)

    # T20: Falls back to script's own repo (this repo IS the ADOS repo)
    def test_falls_back_to_own_repo(self) -> None:
        with patch.dict(os.environ, {}, clear=False):
            os.environ.pop("ADOS_SOURCE_DIR", None)
            # git_ops.py is in scripts/ados_lib/ → parent.parent.parent = repo root
            result = resolve_source_dir(InstallConfig())
            self.assertTrue((result / "AGENTS.md").is_file())


class TestAutoFetchSource(unittest.TestCase):
    def test_skips_when_no_fetch(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            config = InstallConfig(no_fetch=True)
            with patch("ados_lib.git_ops.git_run") as mock_git:
                auto_fetch_source(Path(tmp), config)
                mock_git.assert_not_called()

    def test_skips_when_ados_source_dir_set(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            config = InstallConfig()
            with patch.dict(os.environ, {"ADOS_SOURCE_DIR": tmp}), \
                 patch("ados_lib.git_ops.git_run") as mock_git:
                auto_fetch_source(Path(tmp), config)
                mock_git.assert_not_called()

    def test_skips_when_not_git_repo(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            config = InstallConfig()
            with patch.dict(os.environ, {}, clear=False):
                os.environ.pop("ADOS_SOURCE_DIR", None)
                with patch("ados_lib.git_ops.git_run") as mock_git:
                    auto_fetch_source(Path(tmp), config)
                    mock_git.assert_not_called()


if __name__ == "__main__":
    unittest.main()
