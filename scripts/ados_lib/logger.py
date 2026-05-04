"""Logging primitives for ADOS scripts.

Output format mirrors the Bash originals:
  [INFO]  (ados-install) message
  [WARN]  (ados-install) message
  [ERROR] (ados-install) message
  [DEBUG] (ados-install) message

Colour is emitted only when the target stream is a real TTY.
"""
from __future__ import annotations

import sys

# ANSI colour codes
_RESET = "\033[0m"
_YELLOW = "\033[33m"
_RED = "\033[31m"
_CYAN = "\033[36m"


def _colour(stream: object, code: str, text: str) -> str:
    """Wrap *text* in *code* only when *stream* is a TTY."""
    if hasattr(stream, "isatty") and stream.isatty():
        return f"{code}{text}{_RESET}"
    return text


def log_info(tag: str, msg: str) -> None:
    """Print an [INFO] line to stdout."""
    print(f"[INFO]  ({tag}) {msg}", flush=True)


def log_warn(tag: str, msg: str) -> None:
    """Print a [WARN] line to stderr."""
    line = _colour(sys.stderr, _YELLOW, f"[WARN]  ({tag}) {msg}")
    print(line, file=sys.stderr, flush=True)


def log_err(tag: str, msg: str) -> None:
    """Print an [ERROR] line to stderr."""
    line = _colour(sys.stderr, _RED, f"[ERROR] ({tag}) {msg}")
    print(line, file=sys.stderr, flush=True)


def log_debug(tag: str, msg: str, verbose: bool = False) -> None:
    """Print a [DEBUG] line to stdout, gated on *verbose*."""
    if verbose:
        line = _colour(sys.stdout, _CYAN, f"[DEBUG] ({tag}) {msg}")
        print(line, flush=True)
