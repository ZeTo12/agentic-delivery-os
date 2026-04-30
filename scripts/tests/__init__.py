"""Test package for ADOS Python scripts."""
from __future__ import annotations

import os
import shutil
import tempfile
from pathlib import Path


def make_mock_ados_source(tmp_dir: str) -> Path:
    """Create a minimal fake ADOS repo tree under *tmp_dir*.

    The resulting directory contains the files that install.py expects to
    copy into a target project:
      - .opencode/agent/*.md
      - .opencode/command/*.md
      - doc/templates/*.md
      - doc/documentation-handbook.md
      - doc/00-index.md
      - doc/guides/*.md
      - doc/decisions/README.md
      - doc/decisions/00-index.md
      - .ai/rules/README.md
      - AGENTS.md  (sentinel for resolve_source_dir)
    """
    root = Path(tmp_dir) / "mock_ados_source"
    root.mkdir(parents=True, exist_ok=True)

    def _write(rel: str, content: str = "stub\n") -> None:
        p = root / rel
        p.parent.mkdir(parents=True, exist_ok=True)
        p.write_text(content, encoding="utf-8")

    # Sentinel
    _write("AGENTS.md", "# AGENTS\n")

    # Agent definitions
    for name in ["pm.md", "coder.md", "reviewer.md", "committer.md"]:
        _write(f".opencode/agent/{name}", f"# {name}\nagent stub\n")

    # Command definitions
    for name in ["write-spec.md", "run-plan.md", "commit.md"]:
        _write(f".opencode/command/{name}", f"# {name}\ncommand stub\n")

    # Updatable files
    _write("doc/documentation-handbook.md", "# Handbook\n")
    _write("doc/00-index.md", "# Index\n")
    _write("doc/guides/change-lifecycle.md", "# Change lifecycle\n")
    _write("doc/guides/unified-change-convention-tracker-agnostic-specification.md", "# Convention\n")
    _write("doc/guides/decision-records-management.md", "# Decisions\n")
    _write("doc/guides/opencode-agents-and-commands-guide.md", "# Agents guide\n")
    _write("doc/guides/opencode-model-configuration.md", "# Models\n")
    _write("doc/guides/tools-convention.md", "# Tools\n")
    _write("doc/guides/copywriting.md", "# Copywriting\n")
    _write("doc/guides/system-dependencies.md", "# System deps\n")
    _write("doc/guides/onboarding-existing-project.md", "# Onboarding\n")
    _write("doc/decisions/README.md", "# Decisions README\n")
    _write("doc/decisions/00-index.md", "# Decisions index\n")
    _write(".ai/rules/README.md", "# Rules README\n")

    # Templates
    for name in [
        "north-star-template.md",
        "README.md",
        "implementation-plan-template.md",
        "test-plan-template.md",
        "test-spec-template.md",
        "feature-spec-template.md",
        "decision-record-template.md",
        "change-spec-template.md",
    ]:
        _write(f"doc/templates/{name}", f"# {name}\ntemplate stub\n")

    return root
