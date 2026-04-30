"""Argument parsing for install.py and uninstall.py.

Flags match the Bash originals exactly (same short and long forms, same defaults).
"""
from __future__ import annotations

import argparse
import os
from typing import List, Optional

from ados_lib import __version__
from ados_lib.types import InstallConfig, UninstallConfig

_APP_INSTALL = "ados-install"
_APP_UNINSTALL = "ados-uninstall"


def _bool_env(name: str) -> bool:
    """Return True when env var *name* is set to 'true' (case-insensitive)."""
    return os.environ.get(name, "").lower() == "true"


def parse_install_args(argv: Optional[List[str]] = None) -> InstallConfig:
    """Parse install.py command-line arguments and return an InstallConfig."""
    parser = argparse.ArgumentParser(
        prog=_APP_INSTALL,
        description=(
            "Install or update Agentic Delivery OS (ADOS) globally or into a local project.\n"
            "Re-running is safe and idempotent — only changed files are updated."
        ),
        formatter_class=argparse.RawDescriptionHelpFormatter,
        add_help=True,
    )

    mode_group = parser.add_mutually_exclusive_group()
    mode_group.add_argument(
        "-g", "--global",
        dest="mode_global",
        action="store_true",
        default=False,
        help="Clone/update ADOS repo and install agent/command definitions globally.",
    )
    mode_group.add_argument(
        "-l", "--local",
        dest="mode_local",
        action="store_true",
        default=False,
        help="Copy ADOS artifacts into the current project (default).",
    )

    parser.add_argument(
        "-b", "--branch",
        dest="branch",
        default=os.environ.get("ADOS_BRANCH", "main"),
        metavar="<name>",
        help="Install from a specific branch (default: main).",
    )
    parser.add_argument("-n", "--dry-run", action="store_true", default=_bool_env("DRY_RUN"),
                        help="Show what would be done without doing it.")
    parser.add_argument("-v", "--verbose", action="store_true", default=_bool_env("VERBOSE"),
                        help="Enable debug output.")
    parser.add_argument("-f", "--force", action="store_true", default=_bool_env("FORCE"),
                        help="Overwrite ALL existing files.")
    parser.add_argument("-i", "--interactive", action="store_true", default=_bool_env("INTERACTIVE"),
                        help="Show diff and prompt before overwriting changed files.")
    parser.add_argument("--no-fetch", action="store_true", default=_bool_env("NO_FETCH"),
                        help="Skip auto-fetching latest ADOS source before local install.")
    parser.add_argument("--allow-non-root", action="store_true", default=_bool_env("ALLOW_NON_ROOT"),
                        help="Allow local install in a subdirectory (for monorepo subprojects).")
    parser.add_argument("-V", "--version", action="version",
                        version=f"{_APP_INSTALL} {__version__}")

    args = parser.parse_args(argv)

    # Determine mode
    if args.mode_global:
        mode = "global"
    else:
        mode = "local"  # default

    return InstallConfig(
        mode=mode,
        branch=args.branch,
        dry_run=args.dry_run,
        verbose=args.verbose,
        force=args.force,
        interactive=args.interactive,
        no_fetch=args.no_fetch,
        allow_non_root=args.allow_non_root,
    )


def parse_uninstall_args(argv: Optional[List[str]] = None) -> UninstallConfig:
    """Parse uninstall.py command-line arguments and return an UninstallConfig."""
    parser = argparse.ArgumentParser(
        prog=_APP_UNINSTALL,
        description="Remove Agentic Delivery OS (ADOS) from global or local install.",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        add_help=True,
    )

    mode_group = parser.add_mutually_exclusive_group(required=True)
    mode_group.add_argument(
        "-g", "--global",
        dest="mode_global",
        action="store_true",
        default=False,
        help="Remove ADOS agent/command files from global config and delete ~/.ados/.",
    )
    mode_group.add_argument(
        "-l", "--local",
        dest="mode_local",
        action="store_true",
        default=False,
        help="Remove ADOS artifacts from the current project.",
    )

    parser.add_argument("-n", "--dry-run", action="store_true", default=_bool_env("DRY_RUN"),
                        help="Show what would be removed without doing it.")
    parser.add_argument("-v", "--verbose", action="store_true", default=_bool_env("VERBOSE"),
                        help="Enable debug output.")
    parser.add_argument("-f", "--force", action="store_true", default=_bool_env("FORCE"),
                        help="Skip confirmation prompt.")
    parser.add_argument("-V", "--version", action="version",
                        version=f"{_APP_UNINSTALL} {__version__}")

    args = parser.parse_args(argv)

    mode = "global" if args.mode_global else "local"

    return UninstallConfig(
        mode=mode,
        dry_run=args.dry_run,
        verbose=args.verbose,
        force=args.force,
    )
