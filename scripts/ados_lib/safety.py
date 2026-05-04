"""Safety guards for destructive file-system operations."""
from __future__ import annotations

import shutil
import sys
from pathlib import Path

from ados_lib.logger import log_debug, log_err, log_info, log_warn
from ados_lib.types import UninstallConfig

_TAG = "ados-uninstall"


def validate_paths(
    ados_home: Path,
    opencode_global_dir: Path,
    ados_repo_url: str,
) -> None:
    """Warn if ADOS paths are outside $HOME or repo URL is non-HTTPS."""
    home = Path.home().resolve()

    try:
        resolved_ados = ados_home.resolve()
        if resolved_ados.parts[:len(home.parts)] != home.parts:
            log_warn(_TAG, f"ADOS_HOME is outside $HOME: {ados_home}")
    except Exception:
        pass

    try:
        resolved_opencode = opencode_global_dir.resolve()
        if resolved_opencode.parts[:len(home.parts)] != home.parts:
            log_warn(_TAG, f"OPENCODE_GLOBAL_DIR is outside $HOME: {opencode_global_dir}")
    except Exception:
        pass

    if ados_repo_url and not ados_repo_url.startswith("https://"):
        log_warn(_TAG, f"ADOS_REPO_URL does not use HTTPS: {ados_repo_url}")


def safe_rmdir(dir_path: Path, label: str, config: UninstallConfig) -> None:
    """Remove *dir_path* recursively with safety guards.

    Raises RuntimeError for:
    - empty path
    - root path
    - home directory
    - path with fewer than 3 resolved components
    """
    dir_str = str(dir_path).strip()
    if not dir_str or dir_str in (".", ""):
        raise RuntimeError("Refusing to remove dangerous path: ''")

    # Also reject if the path string itself is empty (Path("") resolves to CWD)
    if not dir_path.parts:
        raise RuntimeError("Refusing to remove dangerous path: ''")

    resolved = dir_path.resolve()
    home = Path.home().resolve()
    root = Path(resolved.anchor)

    if resolved == root or resolved == home:
        raise RuntimeError(f"Refusing to remove dangerous path: '{dir_path}'")

    # On Windows paths look like C:\Users\foo (3 parts: C:\, Users, foo)
    # On Unix /home/user/dir = 3 parts (/, home, user, dir → 4 parts)
    # Minimum: len(resolved.parts) >= 4 on Unix, >= 4 on Windows (C:\, Users, name, dir)
    # We mirror the Bash heuristic: require >= 3 slash separators on Unix,
    # which translates to len(parts) >= 4. On Windows require >= 4 parts as well.
    if len(resolved.parts) < 4:
        raise RuntimeError(
            f"Refusing to remove shallow path (depth {len(resolved.parts)}): '{dir_path}'"
        )

    if dir_path.is_dir():
        if config.dry_run:
            log_info(_TAG, f"[DRY-RUN] Would remove {label}/")
        else:
            shutil.rmtree(dir_path)
            log_info(_TAG, f"remove {label}/")
    else:
        log_debug(_TAG, f"skip   {label}/ (not found)", config.verbose)
