"""File manifest — what gets installed and uninstalled.

Lists are kept 1-to-1 with the Bash originals in install.sh / uninstall.sh.
"""
from __future__ import annotations

# ---------------------------------------------------------------------------
# Install manifest
# ---------------------------------------------------------------------------

# Files that ALWAYS track upstream ADOS (auto-updated on re-run)
UPDATABLE_FILES: list[str] = [
    "doc/documentation-handbook.md",
    "doc/00-index.md",
    "doc/guides/change-lifecycle.md",
    "doc/guides/unified-change-convention-tracker-agnostic-specification.md",
    "doc/guides/decision-records-management.md",
    "doc/guides/opencode-agents-and-commands-guide.md",
    "doc/guides/opencode-model-configuration.md",
    "doc/guides/tools-convention.md",
    "doc/guides/copywriting.md",
    "doc/guides/system-dependencies.md",
    "doc/guides/onboarding-existing-project.md",
    "doc/decisions/README.md",
    "doc/decisions/00-index.md",
    ".ai/rules/README.md",
]

# Template directory (glob all *.md from here)
TEMPLATE_DIR: str = "doc/templates"

# Files that are PROJECT-SPECIFIC (skip if exists, preserve local edits)
# Intentionally empty: all ADOS-managed files are updatable; project-specific
# customisation files (e.g. north-star, ADRs) are not copied by the installer.
PROJECT_FILES: list[str] = []

# Directories to create as empty stubs
LOCAL_DIRS: list[str] = [
    "doc/overview",
    "doc/spec/features",
    "doc/decisions",
    "doc/changes",
    "doc/guides",
    ".ai/agent",
    ".ai/local",
    ".ai/rules",
]

# ---------------------------------------------------------------------------
# Uninstall manifest
# ---------------------------------------------------------------------------

# Known ADOS agent files (installed globally)
AGENT_FILES: list[str] = [
    "bootstrapper.md",
    "doc-syncer.md",
    "test-plan-writer.md",
    "plan-writer.md",
    "spec-writer.md",
    "architect.md",
    "pm.md",
    "image-reviewer.md",
    "image-generator.md",
    "toolsmith.md",
    "committer.md",
    "designer.md",
    "reviewer.md",
    "runner.md",
    "coder.md",
    "fixer.md",
    "pr-manager.md",
    "external-researcher.md",
    "editor.md",
    "review-feedback-applier.md",
]

# Known ADOS command files (installed globally)
COMMAND_FILES: list[str] = [
    "bootstrap.md",
    "plan-decision.md",
    "write-decision.md",
    "plan-change.md",
    "review.md",
    "commit.md",
    "pr.md",
    "run-plan.md",
    "check.md",
    "design.md",
    "write-spec.md",
    "review-deep.md",
    "write-plan.md",
    "write-test-plan.md",
    "sync-docs.md",
    "check-fix.md",
    "apply-review-feedback.md",
]

# Known ADOS local updatable files (removed by uninstall --local)
LOCAL_UPDATABLE_FILES: list[str] = UPDATABLE_FILES.copy()

# Known ADOS local template files (removed by uninstall --local)
LOCAL_TEMPLATE_FILES: list[str] = [
    "doc/templates/north-star-template.md",
    "doc/templates/README.md",
    "doc/templates/implementation-plan-template.md",
    "doc/templates/test-plan-template.md",
    "doc/templates/test-spec-template.md",
    "doc/templates/feature-spec-template.md",
    "doc/templates/decision-record-template.md",
    "doc/templates/change-spec-template.md",
]
