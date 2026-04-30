#!/usr/bin/env python3
"""install.py — Install or update Agentic Delivery OS (ADOS) globally or into a local project.

Python port of scripts/install.sh — functionally identical, natively cross-platform.

Usage:
    python3 scripts/install.py [--global|--local] [options]

Exit codes:
    0 - Success
    2 - Usage error
    3 - Configuration error
    4 - Runtime error
    5 - External dependency missing
"""
from __future__ import annotations

import os
import signal
import sys
from pathlib import Path

# Ensure scripts/ directory is on sys.path when run directly.
_SCRIPTS_DIR = str(Path(__file__).resolve().parent)
if _SCRIPTS_DIR not in sys.path:
    sys.path.insert(0, _SCRIPTS_DIR)

from ados_lib import __version__
from ados_lib.cli import parse_install_args
from ados_lib.file_ops import copy_file_with_diff, copy_updatable_file, ensure_dir
from ados_lib.git_ops import (
    auto_fetch_source,
    clone_or_update_repo,
    require_git,
    require_project_root,
    resolve_source_dir,
)
from ados_lib.gitignore import ensure_gitignore_entry
from ados_lib.logger import log_debug, log_err, log_info, log_warn
from ados_lib.manifest import (
    LOCAL_DIRS,
    PROJECT_FILES,
    TEMPLATE_DIR,
    UPDATABLE_FILES,
)
from ados_lib.platform_paths import (
    get_ados_home,
    get_ados_repo_dir,
    get_ados_raw_url,
    get_opencode_global_dir,
)
from ados_lib.safety import validate_paths
from ados_lib.types import InstallConfig, InstallCounters

_TAG = "ados-install"


def _handle_interrupt(signum: int, frame: object) -> None:  # type: ignore[misc]
    log_warn(_TAG, "Interrupted")
    sys.exit(130)


def install_global_files(config: InstallConfig, counters: InstallCounters) -> None:
    """Copy agent and command .md files from the cloned repo to the global opencode dir."""
    repo_dir = get_ados_repo_dir()
    opencode_dir = get_opencode_global_dir()

    agent_src = repo_dir / ".opencode" / "agent"
    command_src = repo_dir / ".opencode" / "command"
    agent_dest = opencode_dir / "agent"
    command_dest = opencode_dir / "command"

    ensure_dir(agent_dest, "~/.config/opencode/agent", config)
    ensure_dir(command_dest, "~/.config/opencode/command", config)

    if agent_src.is_dir():
        for agent_file in sorted(agent_src.glob("*.md")):
            name = agent_file.name
            copy_file_with_diff(agent_file, agent_dest / name, f"agent/{name}", config, counters)
    else:
        log_warn(_TAG, f"Agent source directory not found: {agent_src}")

    if command_src.is_dir():
        for cmd_file in sorted(command_src.glob("*.md")):
            name = cmd_file.name
            copy_file_with_diff(cmd_file, command_dest / name, f"command/{name}", config, counters)
    else:
        log_warn(_TAG, f"Command source directory not found: {command_src}")


def install_local_files(
    source_dir: Path,
    config: InstallConfig,
    counters: InstallCounters,
) -> None:
    """Copy all local install artifacts from *source_dir* into CWD."""
    # Project-specific files (preserve local edits)
    for rel in PROJECT_FILES:
        copy_file_with_diff(source_dir / rel, Path(rel), rel, config, counters)

    # Updatable files (always track upstream)
    for rel in UPDATABLE_FILES:
        copy_updatable_file(source_dir / rel, Path(rel), rel, config, counters)

    # Templates (always track upstream)
    tmpl_src = source_dir / TEMPLATE_DIR
    if tmpl_src.is_dir():
        ensure_dir(Path(TEMPLATE_DIR), TEMPLATE_DIR, config)
        for tmpl_file in sorted(tmpl_src.glob("*.md")):
            name = tmpl_file.name
            rel = f"{TEMPLATE_DIR}/{name}"
            copy_updatable_file(tmpl_file, Path(rel), rel, config, counters)
    else:
        log_warn(_TAG, f"Templates directory not found: {tmpl_src}")

    # Directory stubs
    for rel in LOCAL_DIRS:
        ensure_dir(Path(rel), rel, config)

    # .gitignore entries
    gitignore = Path(".gitignore")
    ensure_gitignore_entry(gitignore, ".ai/local/", config)
    ensure_gitignore_entry(gitignore, ".ai/local", config)


def do_global_install(config: InstallConfig) -> None:
    """Perform a global ADOS install."""
    require_git()
    validate_paths(get_ados_home(), get_opencode_global_dir(), "")

    log_info(_TAG, "=== ADOS Global Install ===")
    log_info(_TAG, f"ADOS_HOME:           {get_ados_home()}")
    log_info(_TAG, f"ADOS_REPO_DIR:       {get_ados_repo_dir()}")
    log_info(_TAG, f"OPENCODE_GLOBAL_DIR: {get_opencode_global_dir()}")
    if config.branch != "main":
        log_info(_TAG, f"Branch:              {config.branch}")

    clone_or_update_repo(config)

    counters = InstallCounters()
    install_global_files(config, counters)

    print()
    log_info(_TAG, f"Done — {counters.added} added, {counters.updated} updated, {counters.unchanged} unchanged")
    log_info(_TAG, "ADOS agents and commands are now available globally")
    print()
    log_info(_TAG, "To update: re-run this same command (idempotent — only changed files are updated)")
    log_info(_TAG, f"To set up a project: run '{get_ados_repo_dir()}/scripts/install.py --local' in a project root")


def do_local_install(config: InstallConfig) -> None:
    """Perform a local project ADOS install."""
    require_project_root(config.allow_non_root, config)
    validate_paths(get_ados_home(), get_opencode_global_dir(), "")

    source_dir = resolve_source_dir(config)
    auto_fetch_source(source_dir, config)

    log_info(_TAG, "=== ADOS Local Install ===")
    log_info(_TAG, f"Source:  {source_dir}")
    log_info(_TAG, f"Target:  {Path.cwd()}")
    if config.branch != "main":
        log_info(_TAG, f"Branch:  {config.branch}")
    if config.force:
        log_info(_TAG, "Mode:    force (overwrite existing files)")
    if config.interactive:
        log_info(_TAG, "Mode:    interactive (prompt on diff)")

    counters = InstallCounters()
    install_local_files(source_dir, config, counters)

    print()
    log_info(_TAG, f"Done — {counters.added} added, {counters.updated} updated, {counters.unchanged} unchanged")
    print()
    if counters.added > 0:
        log_info(_TAG, "Next steps:")
        log_info(_TAG, "  1. Open this project in OpenCode (https://opencode.ai)")
        log_info(_TAG, "  2. Run /bootstrap to complete setup with AI-guided configuration")
        log_info(_TAG, "     The bootstrapper will detect your tracker, generate PM instructions,")
        log_info(_TAG, "     and customize AGENTS.md for your project.")
    else:
        log_info(_TAG, "Project artifacts updated to latest ADOS version")
        log_info(_TAG, "Templates, guides, and handbook updated; project-specific files preserved")


def main(argv: list[str] | None = None) -> None:
    """Testable entry-point."""
    signal.signal(signal.SIGINT, _handle_interrupt)

    config = parse_install_args(argv)

    log_debug(_TAG, f"INSTALL_MODE={config.mode}", config.verbose)
    log_debug(_TAG, f"ADOS_BRANCH={config.branch}", config.verbose)
    log_debug(_TAG, f"DRY_RUN={config.dry_run}", config.verbose)
    log_debug(_TAG, f"VERBOSE={config.verbose}", config.verbose)
    log_debug(_TAG, f"FORCE={config.force}", config.verbose)
    log_debug(_TAG, f"INTERACTIVE={config.interactive}", config.verbose)
    log_debug(_TAG, f"NO_FETCH={config.no_fetch}", config.verbose)

    if config.mode == "global":
        do_global_install(config)
    else:
        do_local_install(config)


if __name__ == "__main__":
    main()
