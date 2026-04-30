#!/usr/bin/env python3
"""bootstrap.py — Standalone one-liner bootstrapper for Agentic Delivery OS.

Clones the ADOS repo and runs install.py --global.  This file has NO dependency
on ados_lib and can be piped directly from the internet:

    curl -fsSL https://raw.githubusercontent.com/juliusz-cwiakalski/agentic-delivery-os/main/scripts/bootstrap.py | python3 -

Windows PowerShell:
    irm https://raw.githubusercontent.com/juliusz-cwiakalski/agentic-delivery-os/main/scripts/bootstrap.py | python -

Requirements: Python >= 3.8, git
"""
from __future__ import annotations

import os
import shutil
import subprocess
import sys
from pathlib import Path


def main() -> None:
    # Verify git is available
    if not shutil.which("git"):
        print("[ERROR] git is not installed or not on PATH. Please install git first.", file=sys.stderr)
        sys.exit(5)

    repo_url = os.environ.get(
        "ADOS_REPO_URL",
        "https://github.com/juliusz-cwiakalski/agentic-delivery-os.git",
    )
    ados_home = Path(os.environ.get("ADOS_HOME", str(Path.home() / ".ados")))
    repo_dir = Path(os.environ.get("ADOS_REPO_DIR", str(ados_home / "repo")))

    if not (repo_dir / ".git").is_dir():
        print(f"[INFO]  (ados-bootstrap) Cloning ADOS repo to {repo_dir}...")
        ados_home.mkdir(parents=True, exist_ok=True)
        result = subprocess.run(
            ["git", "clone", repo_url, str(repo_dir)],
            check=False,
        )
        if result.returncode != 0:
            print("[ERROR] git clone failed. Check your network connection and git installation.", file=sys.stderr)
            sys.exit(4)
    else:
        print(f"[INFO]  (ados-bootstrap) ADOS repo already cloned at {repo_dir}, updating...")
        subprocess.run(["git", "-C", str(repo_dir), "pull", "--ff-only"], check=False)

    install_script = repo_dir / "scripts" / "install.py"
    if not install_script.is_file():
        print(f"[ERROR] install.py not found at {install_script}", file=sys.stderr)
        sys.exit(4)

    print("[INFO]  (ados-bootstrap) Running global install...")
    result = subprocess.run(
        [sys.executable, str(install_script), "--global"],
        check=False,
    )
    sys.exit(result.returncode)


if __name__ == "__main__":
    main()
