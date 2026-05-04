"""Tests for ados_lib.platform_paths (T1)."""
from __future__ import annotations

import os
import sys
import unittest
from pathlib import Path
from unittest.mock import patch


# Ensure scripts/ is on sys.path so `ados_lib` can be imported from repo root
_SCRIPTS_DIR = str(Path(__file__).resolve().parent.parent)
if _SCRIPTS_DIR not in sys.path:
    sys.path.insert(0, _SCRIPTS_DIR)

from ados_lib import platform_paths


class TestGetAdosHome(unittest.TestCase):
    def test_default(self) -> None:
        with patch.dict(os.environ, {}, clear=False):
            os.environ.pop("ADOS_HOME", None)
            result = platform_paths.get_ados_home()
            self.assertEqual(result, Path.home() / ".ados")

    def test_env_override(self) -> None:
        with patch.dict(os.environ, {"ADOS_HOME": "/custom/ados"}):
            result = platform_paths.get_ados_home()
            self.assertEqual(result, Path("/custom/ados"))


class TestGetAdosRepoDir(unittest.TestCase):
    def test_default(self) -> None:
        with patch.dict(os.environ, {}, clear=False):
            os.environ.pop("ADOS_REPO_DIR", None)
            os.environ.pop("ADOS_HOME", None)
            result = platform_paths.get_ados_repo_dir()
            self.assertEqual(result, Path.home() / ".ados" / "repo")

    def test_env_override(self) -> None:
        with patch.dict(os.environ, {"ADOS_REPO_DIR": "/custom/repo"}):
            result = platform_paths.get_ados_repo_dir()
            self.assertEqual(result, Path("/custom/repo"))


class TestGetOpencodeGlobalDir(unittest.TestCase):
    def test_env_override(self) -> None:
        with patch.dict(os.environ, {"OPENCODE_GLOBAL_DIR": "/my/opencode"}):
            result = platform_paths.get_opencode_global_dir()
            self.assertEqual(result, Path("/my/opencode"))

    def test_linux_default(self) -> None:
        env_clean = {k: v for k, v in os.environ.items()
                     if k not in {"OPENCODE_GLOBAL_DIR", "XDG_CONFIG_HOME"}}
        with patch.dict(os.environ, env_clean, clear=True), \
                patch.object(sys, "platform", "linux"):
            result = platform_paths.get_opencode_global_dir()
            self.assertEqual(result, Path.home() / ".config" / "opencode")

    def test_linux_xdg_override(self) -> None:
        env_clean = {k: v for k, v in os.environ.items()
                     if k not in {"OPENCODE_GLOBAL_DIR"}}
        env_clean["XDG_CONFIG_HOME"] = "/xdg/cfg"
        with patch.dict(os.environ, env_clean, clear=True), \
                patch.object(sys, "platform", "linux"):
            result = platform_paths.get_opencode_global_dir()
            self.assertEqual(result, Path("/xdg/cfg") / "opencode")

    def test_macos_default(self) -> None:
        env_clean = {k: v for k, v in os.environ.items()
                     if k not in {"OPENCODE_GLOBAL_DIR", "XDG_CONFIG_HOME"}}
        with patch.dict(os.environ, env_clean, clear=True), \
                patch.object(sys, "platform", "darwin"):
            result = platform_paths.get_opencode_global_dir()
            self.assertEqual(result, Path.home() / ".config" / "opencode")

    def test_windows_default(self) -> None:
        appdata = "C:\\Users\\TestUser\\AppData\\Roaming"
        env_clean = {k: v for k, v in os.environ.items()
                     if k not in {"OPENCODE_GLOBAL_DIR"}}
        env_clean["APPDATA"] = appdata
        with patch.dict(os.environ, env_clean, clear=True), \
                patch.object(sys, "platform", "win32"):
            result = platform_paths.get_opencode_global_dir()
            self.assertEqual(result, Path(appdata) / "opencode")


class TestUrls(unittest.TestCase):
    def test_default_repo_url(self) -> None:
        with patch.dict(os.environ, {}, clear=False):
            os.environ.pop("ADOS_REPO_URL", None)
            url = platform_paths.get_ados_repo_url()
            self.assertIn("juliusz-cwiakalski", url)
            self.assertTrue(url.endswith(".git"))

    def test_env_override_repo_url(self) -> None:
        with patch.dict(os.environ, {"ADOS_REPO_URL": "https://example.com/repo.git"}):
            self.assertEqual(platform_paths.get_ados_repo_url(), "https://example.com/repo.git")


if __name__ == "__main__":
    unittest.main()
