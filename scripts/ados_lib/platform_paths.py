"""Platform-specific path resolution for ADOS.

Priority rules (same as Bash originals):

  ADOS_HOME          env → ~/.ados
  ADOS_REPO_DIR      env → <ADOS_HOME>/repo
  OPENCODE_GLOBAL_DIR
    Windows  → %APPDATA%/opencode
    Linux    → $XDG_CONFIG_HOME/opencode  or  ~/.config/opencode
    macOS    → ~/.config/opencode
"""
from __future__ import annotations

import os
import sys
from pathlib import Path

_DEFAULT_REPO_URL = (
    "https://github.com/juliusz-cwiakalski/agentic-delivery-os.git"
)
_DEFAULT_RAW_URL = (
    "https://raw.githubusercontent.com/"
    "juliusz-cwiakalski/agentic-delivery-os/main"
)


def get_ados_home() -> Path:
    """Return the ADOS home directory (``~/.ados`` by default)."""
    env = os.environ.get("ADOS_HOME", "")
    if env:
        return Path(env)
    return Path.home() / ".ados"


def get_ados_repo_dir() -> Path:
    """Return the cloned ADOS repo directory (``<ados_home>/repo`` by default)."""
    env = os.environ.get("ADOS_REPO_DIR", "")
    if env:
        return Path(env)
    return get_ados_home() / "repo"


def get_opencode_global_dir() -> Path:
    """Return the opencode global config directory (platform-specific).

    - Windows:  ``%APPDATA%/opencode``
    - Linux:    ``$XDG_CONFIG_HOME/opencode`` → ``~/.config/opencode``
    - macOS:    ``~/.config/opencode``
    """
    env = os.environ.get("OPENCODE_GLOBAL_DIR", "")
    if env:
        return Path(env)

    if sys.platform == "win32":
        appdata = os.environ.get("APPDATA", "")
        if appdata:
            return Path(appdata) / "opencode"
        return Path.home() / "AppData" / "Roaming" / "opencode"

    # Linux: honour XDG_CONFIG_HOME
    xdg = os.environ.get("XDG_CONFIG_HOME", "")
    if xdg:
        return Path(xdg) / "opencode"

    return Path.home() / ".config" / "opencode"


def get_ados_repo_url() -> str:
    """Return the ADOS git clone URL."""
    return os.environ.get("ADOS_REPO_URL", _DEFAULT_REPO_URL)


def get_ados_raw_url() -> str:
    """Return the raw GitHub content base URL."""
    return os.environ.get("ADOS_RAW_URL", _DEFAULT_RAW_URL)
