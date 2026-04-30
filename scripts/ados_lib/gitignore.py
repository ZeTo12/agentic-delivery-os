"""gitignore manipulation helpers."""
from __future__ import annotations

from pathlib import Path

from ados_lib.logger import log_debug, log_info
from ados_lib.types import InstallConfig

_TAG = "ados-install"


def file_contains_line(file_path: Path, pattern: str) -> bool:
    """Return True if *pattern* appears as a substring in any line of *file_path*."""
    if not file_path.is_file():
        return False
    try:
        return pattern in file_path.read_text(encoding="utf-8", errors="replace")
    except OSError:
        return False


def ensure_gitignore_entry(
    gitignore_path: Path,
    entry: str,
    config: InstallConfig,
) -> None:
    """Append *entry* to *gitignore_path* if it is not already present."""
    if file_contains_line(gitignore_path, entry):
        log_debug(_TAG, f"skip   .gitignore entry '{entry}' (already present)", config.verbose)
        return

    if config.dry_run:
        log_info(_TAG, f"[DRY-RUN] Would add '{entry}' to {gitignore_path}")
        return

    if not gitignore_path.is_file():
        gitignore_path.write_text(f"{entry}\n", encoding="utf-8")
    else:
        with gitignore_path.open("a", encoding="utf-8") as fh:
            fh.write(f"\n{entry}\n")

    log_info(_TAG, f"add    .gitignore entry '{entry}'")
