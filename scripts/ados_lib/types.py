"""Types / dataclasses for ADOS install and uninstall configuration."""
from __future__ import annotations

from dataclasses import dataclass, field


@dataclass
class InstallConfig:
    """Runtime configuration for install.py."""

    mode: str = "local"          # "global" | "local"
    branch: str = "main"
    dry_run: bool = False
    verbose: bool = False
    force: bool = False
    interactive: bool = False
    no_fetch: bool = False
    allow_non_root: bool = False


@dataclass
class UninstallConfig:
    """Runtime configuration for uninstall.py."""

    mode: str = ""               # "global" | "local"
    dry_run: bool = False
    verbose: bool = False
    force: bool = False


@dataclass
class InstallCounters:
    """File-operation counters used during install."""

    added: int = 0
    updated: int = 0
    unchanged: int = 0

    def reset(self) -> None:
        self.added = 0
        self.updated = 0
        self.unchanged = 0


@dataclass
class UninstallCounters:
    """File-operation counters used during uninstall."""

    removed: int = 0
    skipped: int = 0

    def reset(self) -> None:
        self.removed = 0
        self.skipped = 0
