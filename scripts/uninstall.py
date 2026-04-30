#!/usr/bin/env python3
"""uninstall.py — Remove Agentic Delivery OS (ADOS) from global or local install.

Python port of scripts/uninstall.sh — functionally identical, natively cross-platform.

Usage:
    python3 scripts/uninstall.py [--global|--local] [options]

Exit codes:
    0 - Success
    2 - Usage error
    3 - Configuration error
    4 - Runtime error
    5 - External dependency missing
"""
from __future__ import annotations

import signal
import sys
from pathlib import Path

# Ensure scripts/ directory is on sys.path when run directly.
_SCRIPTS_DIR = str(Path(__file__).resolve().parent)
if _SCRIPTS_DIR not in sys.path:
    sys.path.insert(0, _SCRIPTS_DIR)

from ados_lib.cli import parse_uninstall_args
from ados_lib.file_ops import remove_file
from ados_lib.git_ops import require_project_root
from ados_lib.logger import log_debug, log_info, log_warn
from ados_lib.manifest import (
    AGENT_FILES,
    COMMAND_FILES,
    LOCAL_TEMPLATE_FILES,
    LOCAL_UPDATABLE_FILES,
)
from ados_lib.platform_paths import get_ados_home, get_opencode_global_dir
from ados_lib.safety import safe_rmdir
from ados_lib.types import UninstallConfig, UninstallCounters

_TAG = "ados-uninstall"


def _handle_interrupt(signum: int, frame: object) -> None:  # type: ignore[misc]
    log_warn(_TAG, "Interrupted")
    sys.exit(130)


def confirm_action(message: str, config: UninstallConfig) -> bool:
    """Ask the user to confirm *message*.

    Returns True immediately when config.force or config.dry_run is set.
    """
    if config.force or config.dry_run:
        return True
    answer = input(f"{message} [y/N] ").strip().lower()
    return answer in ("y", "yes")


def remove_global_agents(config: UninstallConfig, counters: UninstallCounters) -> None:
    """Remove ADOS agent .md files from the global opencode agent directory."""
    agent_dir = get_opencode_global_dir() / "agent"
    if not agent_dir.is_dir():
        log_debug(_TAG, f"Agent directory not found: {agent_dir}", config.verbose)
        return
    for name in AGENT_FILES:
        remove_file(agent_dir / name, f"agent/{name}", config, counters)


def remove_global_commands(config: UninstallConfig, counters: UninstallCounters) -> None:
    """Remove ADOS command .md files from the global opencode command directory."""
    command_dir = get_opencode_global_dir() / "command"
    if not command_dir.is_dir():
        log_debug(_TAG, f"Command directory not found: {command_dir}", config.verbose)
        return
    for name in COMMAND_FILES:
        remove_file(command_dir / name, f"command/{name}", config, counters)


def remove_local_files(config: UninstallConfig, counters: UninstallCounters) -> None:
    """Remove all ADOS local files from the current project directory."""
    from ados_lib.manifest import LOCAL_UPDATABLE_FILES, LOCAL_TEMPLATE_FILES

    # Updatable files
    for rel in LOCAL_UPDATABLE_FILES:
        remove_file(Path(rel), rel, config, counters)

    # Template files
    for rel in LOCAL_TEMPLATE_FILES:
        remove_file(Path(rel), rel, config, counters)

    # Remove empty directories (cross-platform: no ls -A)
    empty_dirs = [
        "doc/templates",
        "doc/overview",
        "doc/spec/features",
        "doc/spec",
        "doc/decisions",
        "doc/changes",
        "doc/guides",
        ".ai/agent",
        ".ai/rules",
        ".ai/local",
        ".ai",
    ]
    for rel in empty_dirs:
        d = Path(rel)
        if d.is_dir():
            if not any(d.iterdir()):
                if config.dry_run:
                    log_info(_TAG, f"[DRY-RUN] Would remove {rel}/ (empty)")
                else:
                    d.rmdir()
                log_info(_TAG, f"remove {rel}/ (empty)")
            else:
                log_debug(_TAG, f"skip   {rel}/ (not empty)", config.verbose)


def do_global_uninstall(config: UninstallConfig) -> None:
    """Perform a global ADOS uninstall."""
    ados_home = get_ados_home()
    opencode_dir = get_opencode_global_dir()

    log_info(_TAG, "=== ADOS Global Uninstall ===")
    log_info(_TAG, f"ADOS_HOME:           {ados_home}")
    log_info(_TAG, f"OPENCODE_GLOBAL_DIR: {opencode_dir}")

    if not confirm_action(
        f"Remove ADOS global installation? This will delete agent/command files and {ados_home}",
        config,
    ):
        log_info(_TAG, "Aborted")
        return

    counters = UninstallCounters()
    remove_global_agents(config, counters)
    remove_global_commands(config, counters)

    try:
        safe_rmdir(ados_home, "~/.ados", config)
    except RuntimeError as exc:
        log_warn(_TAG, str(exc))

    print()
    log_info(_TAG, f"Done — {counters.removed} files removed, {counters.skipped} not found")
    log_info(_TAG, "ADOS global installation has been removed")


def do_local_uninstall(config: UninstallConfig) -> None:
    """Perform a local project ADOS uninstall."""
    require_project_root(allow_non_root=False, verbose=config.verbose)

    log_info(_TAG, "=== ADOS Local Uninstall ===")
    log_info(_TAG, f"Project: {Path.cwd()}")

    if not confirm_action("Remove ADOS artifacts from this project?", config):
        log_info(_TAG, "Aborted")
        return

    counters = UninstallCounters()
    remove_local_files(config, counters)

    print()
    log_info(_TAG, f"Done — {counters.removed} files removed, {counters.skipped} not found")
    log_info(_TAG, "Note: .gitignore entries for .ai/local/ were NOT removed (manual cleanup if needed)")


def main(argv: list[str] | None = None) -> None:
    """Testable entry-point."""
    signal.signal(signal.SIGINT, _handle_interrupt)

    config = parse_uninstall_args(argv)

    log_debug(_TAG, f"UNINSTALL_MODE={config.mode}", config.verbose)
    log_debug(_TAG, f"DRY_RUN={config.dry_run}", config.verbose)
    log_debug(_TAG, f"VERBOSE={config.verbose}", config.verbose)
    log_debug(_TAG, f"FORCE={config.force}", config.verbose)

    if config.mode == "global":
        do_global_uninstall(config)
    else:
        do_local_uninstall(config)


if __name__ == "__main__":
    main()
