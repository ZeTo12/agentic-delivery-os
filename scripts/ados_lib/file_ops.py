"""File operations: copy-with-diff, dir helpers, file removal.

All operations respect ``config.dry_run`` — nothing is written when it is True.
"""
from __future__ import annotations

import difflib
import filecmp
import shutil
import sys
from pathlib import Path

from ados_lib.logger import log_debug, log_info, log_warn
from ados_lib.types import InstallConfig, InstallCounters, UninstallConfig, UninstallCounters

_TAG = "ados-install"


def prompt_diff_overwrite(src: Path, dest: Path, label: str) -> bool:
    """Show a unified diff between *dest* and *src* then ask the user.

    Returns ``True`` if the user wants to overwrite.
    """
    src_lines = src.read_text(encoding="utf-8", errors="replace").splitlines(keepends=True)
    dest_lines = dest.read_text(encoding="utf-8", errors="replace").splitlines(keepends=True)

    diff = list(difflib.unified_diff(
        dest_lines, src_lines,
        fromfile=str(dest),
        tofile=str(src),
    ))

    print(f"\n--- {label} differs from upstream ---")
    sys.stdout.writelines(diff)
    print()

    answer = input(f"Overwrite {label} with upstream version? [y/n]: ").strip().lower()
    return answer in ("y", "yes")


def copy_file_with_diff(
    src: Path,
    dest: Path,
    label: str,
    config: InstallConfig,
    counters: InstallCounters,
    updatable: bool = False,
) -> None:
    """Copy *src* to *dest* with change detection and mode-based resolution.

    Implements the same 8-scenario logic as the Bash ``copy_file_with_diff``:

    1. Source missing    → warn, skip
    2. Dest is symlink   → replace with real copy (update counter)
    3. Dest identical    → skip (unchanged counter)
    4. Dest differs, global/force mode → overwrite (update counter)
    5. Dest differs, interactive mode  → show diff, prompt
    6. Dest differs, updatable         → auto-overwrite (update counter)
    7. Dest differs, project-specific  → preserve (unchanged counter)
    8. Dest missing      → create new (added counter)
    """
    if not src.is_file():
        log_warn(_TAG, f"Source file not found: {src}")
        return

    if dest.is_symlink():
        if not config.dry_run:
            dest.unlink()
            shutil.copy2(src, dest)
        log_info(_TAG, f"update {label} (replaced symlink with copy)")
        counters.updated += 1
        return

    if dest.is_file():
        if filecmp.cmp(src, dest, shallow=False):
            log_debug(_TAG, f"skip   {label} (already up to date)", config.verbose)
            counters.unchanged += 1
            return

        # Files differ
        if config.force or config.mode == "global":
            if not config.dry_run:
                shutil.copy2(src, dest)
            log_info(_TAG, f"update {label}")
            counters.updated += 1
        elif config.interactive:
            if prompt_diff_overwrite(src, dest, label):
                if not config.dry_run:
                    shutil.copy2(src, dest)
                log_info(_TAG, f"update {label}")
                counters.updated += 1
            else:
                log_info(_TAG, f"skip   {label} (kept local version)")
                counters.unchanged += 1
        elif updatable:
            if not config.dry_run:
                shutil.copy2(src, dest)
            log_info(_TAG, f"update {label}")
            counters.updated += 1
        else:
            log_info(_TAG, f"skip   {label} (local changes; use --force or --interactive)")
            counters.unchanged += 1
        return

    # New file
    if config.dry_run:
        log_info(_TAG, f"[DRY-RUN] Would add {label}")
    else:
        dest.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(src, dest)
    log_info(_TAG, f"add    {label}")
    counters.added += 1


def copy_updatable_file(
    src: Path,
    dest: Path,
    label: str,
    config: InstallConfig,
    counters: InstallCounters,
) -> None:
    """Copy an updatable file (always tracks upstream)."""
    copy_file_with_diff(src, dest, label, config, counters, updatable=True)


def ensure_dir(dir_path: Path, label: str, config: InstallConfig) -> None:
    """Create *dir_path* if it does not exist (dry-run aware)."""
    if dir_path.is_dir():
        log_debug(_TAG, f"skip   {label}/ (already exists)", config.verbose)
        return
    if config.dry_run:
        log_info(_TAG, f"[DRY-RUN] Would create {label}/")
    else:
        dir_path.mkdir(parents=True, exist_ok=True)
    log_info(_TAG, f"create {label}/")


def remove_file(
    path: Path,
    label: str,
    config: UninstallConfig,
    counters: UninstallCounters,
) -> None:
    """Remove *path* if it exists (dry-run aware)."""
    if path.is_file() or path.is_symlink():
        if config.dry_run:
            log_info(_TAG, f"[DRY-RUN] Would remove {label}")
        else:
            path.unlink(missing_ok=True)
        log_info(_TAG, f"remove {label}")
        counters.removed += 1
    else:
        log_debug(_TAG, f"skip   {label} (not found)", config.verbose)
        counters.skipped += 1
