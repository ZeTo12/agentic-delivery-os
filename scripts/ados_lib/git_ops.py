"""Git operations for ADOS — all subprocess calls use list form (no shell=True)."""
from __future__ import annotations

import shutil
import subprocess
import sys
from pathlib import Path
from typing import Optional

from ados_lib.logger import log_debug, log_err, log_info, log_warn
from ados_lib.types import InstallConfig

_TAG = "ados-install"


def require_git() -> None:
    """Exit with code 5 if git is not available on PATH."""
    if not shutil.which("git"):
        log_err(_TAG, "Required command not found: git")
        sys.exit(5)


def git_run(
    args: list[str],
    cwd: Optional[Path] = None,
    check: bool = True,
    capture: bool = True,
) -> subprocess.CompletedProcess:
    """Run a git command safely (list form — never shell=True).

    Args:
        args: git sub-command and arguments (without the leading "git").
        cwd:  working directory for the command.
        check: raise CalledProcessError on non-zero exit when True.
        capture: capture stdout/stderr when True.
    """
    cmd = ["git"] + args
    return subprocess.run(
        cmd,
        cwd=str(cwd) if cwd else None,
        check=check,
        capture_output=capture,
        encoding="utf-8",
        errors="replace",
    )


def get_short_sha(repo_dir: Path) -> Optional[str]:
    """Return the short HEAD SHA for *repo_dir*, or None on failure."""
    try:
        result = git_run(["rev-parse", "--short", "HEAD"], cwd=repo_dir, check=False)
        if result.returncode == 0:
            return result.stdout.strip() or None
    except Exception:
        pass
    return None


def get_current_branch(repo_dir: Path) -> Optional[str]:
    """Return the current branch name for *repo_dir*, or None on failure."""
    try:
        result = git_run(["rev-parse", "--abbrev-ref", "HEAD"], cwd=repo_dir, check=False)
        if result.returncode == 0:
            return result.stdout.strip() or None
    except Exception:
        pass
    return None


def clone_or_update_repo(config: InstallConfig) -> None:
    """Clone the ADOS repo or update it if it already exists."""
    from ados_lib.platform_paths import get_ados_home, get_ados_repo_dir, get_ados_repo_url

    repo_dir = get_ados_repo_dir()
    ados_home = get_ados_home()
    repo_url = get_ados_repo_url()
    branch = config.branch

    if (repo_dir / ".git").is_dir():
        before_sha = get_short_sha(repo_dir)
        log_info(_TAG, f"Updating existing ADOS repo at {repo_dir} (current: {before_sha or 'unknown'})")

        current_branch = get_current_branch(repo_dir)
        if current_branch and current_branch != branch:
            log_info(_TAG, f"Switching branch: {current_branch} → {branch}")
            if not config.dry_run:
                git_run(["fetch", "origin"], cwd=repo_dir, check=False)
                result = git_run(["checkout", branch], cwd=repo_dir, check=False)
                if result.returncode != 0:
                    git_run([
                        "checkout", "-b", branch, f"origin/{branch}"
                    ], cwd=repo_dir, check=False)

        if not config.dry_run:
            git_run(["pull", "--ff-only"], cwd=repo_dir, check=False)
    else:
        log_info(_TAG, f"Cloning ADOS repo to {repo_dir} (branch: {branch})")
        if not config.dry_run:
            ados_home.mkdir(parents=True, exist_ok=True)
            git_run(["clone", "--branch", branch, repo_url, str(repo_dir)])
            return

    if not config.dry_run:
        after_sha = get_short_sha(repo_dir)
        after_branch = get_current_branch(repo_dir)
        if after_sha:
            log_info(_TAG, f"Installed at: {after_sha} ({after_branch})")


def auto_fetch_source(source_dir: Path, config: InstallConfig) -> None:
    """Pull latest changes in *source_dir* unless auto-fetch is disabled.

    Mirrors the Bash ``auto_fetch_source`` function exactly:
    - Skip when ``config.no_fetch`` is True
    - Skip when ``ADOS_SOURCE_DIR`` env var is set (user controls source)
    - Skip when *source_dir* is not a git repo
    """
    import os

    if config.no_fetch:
        log_debug(_TAG, "Auto-fetch disabled (--no-fetch)", config.verbose)
        return

    if os.environ.get("ADOS_SOURCE_DIR"):
        log_debug(_TAG, "Auto-fetch skipped (ADOS_SOURCE_DIR is set by user)", config.verbose)
        return

    if not (source_dir / ".git").is_dir():
        log_debug(_TAG, "Auto-fetch skipped (source is not a git repo)", config.verbose)
        return

    log_info(_TAG, "Fetching latest ADOS source...")

    current_branch = get_current_branch(source_dir)
    if current_branch and current_branch != config.branch:
        log_info(_TAG, f"Switching source branch: {current_branch} → {config.branch}")
        if not config.dry_run:
            git_run(["fetch", "origin"], cwd=source_dir, check=False)
            result = git_run(["checkout", config.branch], cwd=source_dir, check=False)
            if result.returncode != 0:
                result2 = git_run(
                    ["checkout", "-b", config.branch, f"origin/{config.branch}"],
                    cwd=source_dir,
                    check=False,
                )
                if result2.returncode != 0:
                    log_warn(_TAG, f"Could not switch to branch {config.branch}")

    if not config.dry_run:
        result = git_run(["pull", "--ff-only"], cwd=source_dir, check=False)
        if result.returncode != 0:
            log_warn(_TAG, "Auto-fetch failed (continuing with current version; use --no-fetch to suppress)")
        else:
            log_debug(_TAG, "Auto-fetch completed", config.verbose)

        short_sha = get_short_sha(source_dir)
        if short_sha:
            log_info(_TAG, f"Source version: {short_sha}")


def resolve_source_dir(config: InstallConfig) -> Path:
    """Resolve the ADOS source directory.

    Priority (mirrors Bash ``resolve_source_dir``):
    1. ``ADOS_SOURCE_DIR`` environment variable
    2. Script's own repo (``__file__`` → parent → parent)
    3. Global install location (``ADOS_REPO_DIR``)
    """
    import os
    from ados_lib.platform_paths import get_ados_repo_dir

    env_src = os.environ.get("ADOS_SOURCE_DIR", "")
    if env_src:
        p = Path(env_src)
        if p.is_dir():
            return p
        log_err(_TAG, f"ADOS_SOURCE_DIR does not exist: {env_src}")
        sys.exit(3)

    # Script lives at scripts/ados_lib/git_ops.py → parent=ados_lib → parent=scripts → parent=repo root
    candidate = Path(__file__).resolve().parent.parent.parent
    if (candidate / "AGENTS.md").is_file() and (candidate / ".opencode" / "agent").is_dir():
        return candidate

    repo_dir = get_ados_repo_dir()
    if (repo_dir / ".opencode" / "agent").is_dir():
        return repo_dir

    log_err(_TAG, "Cannot find ADOS source. Install globally first (--global) or set ADOS_SOURCE_DIR")
    sys.exit(3)


def require_project_root(allow_non_root: bool, verbose: bool = False) -> None:
    """Verify the CWD is a git project root (or a valid sub-dir when allowed).

    Mirrors ``require_project_root`` in both install.sh and uninstall.sh.
    """
    cwd = Path.cwd()

    if (cwd / ".git").is_dir():
        return

    # Check if inside a git repo at all
    result = git_run(["rev-parse", "--show-toplevel"], cwd=Path.cwd(), check=False)
    git_root = result.stdout.strip() if result.returncode == 0 else ""

    if not git_root:
        log_err(_TAG, "Not inside a git repository. Run from a project directory.")
        sys.exit(2)

    if allow_non_root:
        log_warn(_TAG, f"Not at git root. Installing into subdirectory: {cwd}")
        log_warn(_TAG, f"Git root is: {git_root}")
        return

    log_err(_TAG, "Not a project root (no .git directory in current directory).")
    log_err(_TAG, f"  Current directory: {cwd}")
    log_err(_TAG, f"  Git root:          {git_root}")
    log_err(_TAG, "")
    log_err(_TAG, "If you want to install into this subdirectory (e.g., monorepo subproject),")
    log_err(_TAG, "add --allow-non-root to the command.")
    sys.exit(2)
