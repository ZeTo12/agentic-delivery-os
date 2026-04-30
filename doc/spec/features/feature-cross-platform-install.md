---
# Copyright (c) 2025-2026 Juliusz Ćwiąkalski (https://www.cwiakalski.com | https://www.linkedin.com/in/juliusz-cwiakalski/ | https://x.com/cwiakalski)
# MIT License - see LICENSE file for full terms
source: https://github.com/juliusz-cwiakalski/agentic-delivery-os/blob/main/doc/spec/features/feature-cross-platform-install.md

id: SPEC-CROSS-PLATFORM-INSTALL
status: Current
created: 2026-04-30
last_updated: 2026-04-30
owners: [juliusz-cwiakalski]
service: scripts
links:
  related_changes: ["GH-1"]
  decisions: []
  contracts: []
summary: "Cross-platform Python 3 install and uninstall scripts (stdlib only) that provide full functional parity with the Bash originals on Windows, Linux, and macOS."
---

# Feature Specification: Cross-Platform Install / Uninstall Scripts

## 1. Overview

ADOS provides Python 3 installation and uninstallation scripts (`scripts/install.py`, `scripts/uninstall.py`) that are functionally equivalent to the existing Bash scripts (`install.sh`, `uninstall.sh`) but run natively on Windows, Linux, and macOS without requiring WSL, Git Bash, or any third-party Python packages. A shared library (`scripts/ados_lib/`) supplies all platform-agnostic primitives. A minimal one-liner bootstrap script (`scripts/bootstrap.py`) enables a single `curl | python3 -` command on Linux and macOS, and an equivalent PowerShell one-liner on Windows.

The Bash scripts remain in place in parallel; no existing Unix workflow is broken. Python 3.8 (or later) is the only new runtime prerequisite.

## 2. Business Context

### 2.1 Problem Statement

- **Problem:** The original install and uninstall scripts are Bash-only, making them unavailable to native Windows users without WSL or a Bash emulator.
- **Affected Users:** Windows developers and contributors evaluating or adopting ADOS; CI pipelines running on Windows agents.
- **Business Impact:** Blocked adoption path for a significant fraction of potential users; manual workarounds (WSL setup) add friction that prevents evaluation.

### 2.2 Goals & Success Metrics

- **Primary Goal:** Any user with Python ≥ 3.8 and `git` can install or uninstall ADOS without a Unix shell.

| Metric | Target |
|--------|--------|
| CLI flag parity (Python vs Bash) | 100% of flags |
| Environment variable parity | 100% of env vars |
| Exit code parity | All 5 exit codes |
| Platform coverage | Windows 10+, Ubuntu 20.04+, macOS 12+ |
| Python version coverage | CPython 3.8 and 3.12 |
| External package dependencies | 0 (stdlib only) |
| `safe_rmdir` dangerous-path blocks | 100% on all platforms |

## 3. User Experience & Functionality

### 3.1 Capabilities

- **Global install (`--global`):** Clones or updates the ADOS repo to `~/.ados/repo` then copies agent and command `.md` files to the platform-appropriate opencode global config directory.
- **Local install (`--local`):** Copies ADOS project artifacts into the current git project directory, creates required directory stubs, and adds required `.gitignore` entries. Default mode when neither `--global` nor `--local` is passed.
- **Global uninstall (`--global`):** Removes agent and command files from the opencode global config directory and safely removes the ADOS home directory.
- **Local uninstall (`--local`):** Removes all ADOS-managed project files and cleans up empty ADOS directories; non-ADOS files are not touched.
- **Dry-run mode (`--dry-run`):** Plans and logs all operations without making any filesystem changes; output is marked with `[DRY-RUN]`.
- **Force mode (`--force`):** Overwrites differing files silently and skips confirmation prompts.
- **Interactive mode (`--interactive`):** Shows a unified diff for each differing file and prompts for confirmation.
- **Idempotent re-install:** Running `install.py --local` on an already-installed project reports 0 added, 0 updated, N unchanged — no side effects.
- **One-liner bootstrap:** `scripts/bootstrap.py` (no `ados_lib` dependency, ~30 lines) enables `curl -fsSL <url> | python3 -` installation.
- **Full environment variable override:** All overrides from the Bash version are supported (`ADOS_REPO_URL`, `ADOS_HOME`, `ADOS_SOURCE_DIR`, `DRY_RUN`, `VERBOSE`, `FORCE`, `INTERACTIVE`, `NO_FETCH`, `ADOS_BRANCH`, `ALLOW_NON_ROOT`, and others).

### 3.2 User Flows

```
Flow 1: Global install (new machine)
  python3 scripts/install.py --global
  → Validates git is available
  → Validates target paths
  → Clones ADOS repo to ~/.ados/repo (or pulls if exists)
  → Copies agent + command .md files to platform opencode global dir
  → Prints summary (added / updated / unchanged)
  → Exit 0

Flow 2: Local install (project onboarding)
  python3 scripts/install.py --local
  → Verifies current directory is a git project root
  → Resolves source dir (ADOS_SOURCE_DIR → local repo → ~/.ados/repo)
  → Auto-fetches latest source (unless --no-fetch)
  → Copies project files, updatable files, templates; creates dir stubs
  → Ensures .gitignore entries
  → Prints summary + next-steps
  → Exit 0

Flow 3: One-liner global install (Linux/macOS)
  curl -fsSL <raw-url>/scripts/bootstrap.py | python3 - --global
  → bootstrap.py clones ADOS repo to ~/.ados/repo
  → Invokes install.py --global (Flow 1)

Flow 4: Dry-run preview
  python3 scripts/install.py --local --dry-run
  → Executes Flow 2 logic without writing any files
  → All planned operations logged with [DRY-RUN]
  → Exit 0

Flow 5: Global uninstall
  python3 scripts/uninstall.py --global
  → Prompts for confirmation (skipped with --force or --dry-run)
  → Removes agent files from opencode global dir
  → Removes command files from opencode global dir
  → Calls safe_rmdir on ADOS home
  → Prints removal summary
  → Exit 0

Flow 6: Local uninstall
  python3 scripts/uninstall.py --local
  → Verifies current directory is git project root (strict)
  → Prompts for confirmation
  → Removes project-specific, updatable, and template files
  → Removes empty ADOS directories
  → Prints removal summary
  → Exit 0
```

### 3.3 UI States & References

The scripts are CLI tools; output goes to stdout/stderr.

- **Normal:** `[INFO]  (ados-install) message` — colour-coded when output is a TTY.
- **Warning:** `[WARN]  (ados-install) message`
- **Error:** `[ERR]   (ados-install) message`
- **Dry-run:** operations prefixed with `[DRY-RUN]`
- **Summary line:** `Install complete: 12 added, 0 updated, 0 unchanged` (or equivalent for uninstall).

### 3.4 Edge Cases & Error Handling

| Situation | Behaviour |
|-----------|-----------|
| `git` not on PATH | Exit 5 (external command failure) with clear error |
| Target path not a git project root (local mode) | Exit 3 (configuration error) |
| `safe_rmdir` called with root / home / shallow path | Raises hard error; no deletion |
| Destination is a symlink | Replaced with a regular file copy |
| Differing file in default mode (not force, not interactive, not updatable) | Skipped; warning logged |
| Second install run, no changes | Reports 0 added, 0 updated, N unchanged |
| `--dry-run` | Zero filesystem mutations; all operations logged |

## 4. Technical Architecture & Codebase Map

### 4.1 High-Level Design

The implementation follows a shared-library pattern: all platform-agnostic primitives live in `scripts/ados_lib/` (a Python package), and the two entry-point scripts (`install.py`, `uninstall.py`) import from it. `bootstrap.py` is deliberately kept dependency-free (no `ados_lib` import) so it can be piped directly from a URL.

### 4.2 Core Components & Directory Structure

| Path | Component | Responsibility |
|------|-----------|----------------|
| `scripts/install.py` | Install entry point | CLI parsing, orchestration of global/local install flows |
| `scripts/uninstall.py` | Uninstall entry point | CLI parsing, orchestration of global/local uninstall flows |
| `scripts/bootstrap.py` | Bootstrap entry point | Minimal one-liner: clone repo + invoke `install.py --global` |
| `scripts/ados_lib/__init__.py` | Package root | Package marker; version constant |
| `scripts/ados_lib/types.py` | Config dataclasses | `InstallConfig`, `UninstallConfig`, `Counters` |
| `scripts/ados_lib/logger.py` | Structured logging | Emits `[LEVEL]  (tag) message`; TTY colour detection |
| `scripts/ados_lib/platform_paths.py` | Platform path resolution | Maps opencode global dir per OS; resolves `ADOS_HOME` |
| `scripts/ados_lib/manifest.py` | File manifests | `UPDATABLE_FILES`, `PROJECT_FILES`, `AGENT_FILES`, `COMMAND_FILES`, etc. |
| `scripts/ados_lib/file_ops.py` | File operations | `copy_file_with_diff`, `copy_updatable_file`, symlink handling |
| `scripts/ados_lib/gitignore.py` | `.gitignore` management | Idempotent entry insertion |
| `scripts/ados_lib/safety.py` | Path safety guards | `safe_rmdir` with depth + home/root checks |
| `scripts/ados_lib/git_ops.py` | Git subprocess wrappers | `clone_or_update_repo`, `resolve_source_dir`; no `shell=True` |
| `scripts/ados_lib/cli.py` | Argument parsing | `argparse`-based parsers for install and uninstall |
| `scripts/tests/` | Test suite | 63 tests across unit and integration layers using stdlib `unittest` |

### 4.3 Key Classes & Functions

| Symbol | Module | Description |
|--------|--------|-------------|
| `InstallConfig` | `ados_lib.types` | Dataclass: mode, branch, dry_run, verbose, force, interactive, no_fetch, allow_non_root |
| `UninstallConfig` | `ados_lib.types` | Dataclass: mode, dry_run, verbose, force |
| `Counters` | `ados_lib.types` | Tracks added/updated/unchanged (install) or removed/skipped (uninstall) |
| `get_opencode_global_dir()` | `ados_lib.platform_paths` | Returns platform-appropriate opencode config directory |
| `get_ados_home()` | `ados_lib.platform_paths` | Returns `ADOS_HOME` env override or `~/.ados` |
| `copy_file_with_diff()` | `ados_lib.file_ops` | Copies file; respects force/interactive/updatable/project-specific logic |
| `safe_rmdir()` | `ados_lib.safety` | Removes directory only after validating depth, root, home constraints |
| `ensure_gitignore_entry()` | `ados_lib.gitignore` | Appends entry to `.gitignore` only if not already present |
| `clone_or_update_repo()` | `ados_lib.git_ops` | Clones or pulls ADOS repo; argument-list subprocess calls |
| `resolve_source_dir()` | `ados_lib.git_ops` | Resolves ADOS source: `ADOS_SOURCE_DIR` → script repo → `~/.ados/repo` |

### 4.4 Data Architecture

No persistent data storage. The relevant in-memory data structures are:

| Element | Description |
|---------|-------------|
| `InstallConfig` | Resolved configuration for a single install invocation |
| `UninstallConfig` | Resolved configuration for a single uninstall invocation |
| `Counters` (install) | Per-run tally: added, updated, unchanged |
| `Counters` (uninstall) | Per-run tally: removed, skipped |
| `manifest.py` constants | Named lists of files managed by install/uninstall (1:1 parity with Bash variable arrays) |

### 4.5 API & Interface Contracts

**CLI — install.py**

```
python3 scripts/install.py [--global | --local]
    [-b BRANCH] [-n] [-v] [-f] [-i] [--no-fetch] [--allow-non-root]
    [-h] [-V]
```

**CLI — uninstall.py**

```
python3 scripts/uninstall.py [--global | --local]
    [-n] [-v] [-f] [-h] [-V]
```

**CLI — bootstrap.py**

```
curl -fsSL <url>/scripts/bootstrap.py | python3 - [--global]
```

**Environment variables (full set)**

`ADOS_REPO_URL`, `ADOS_RAW_URL`, `ADOS_HOME`, `ADOS_REPO_DIR`, `OPENCODE_GLOBAL_DIR`, `ADOS_SOURCE_DIR`, `DRY_RUN`, `VERBOSE`, `FORCE`, `INTERACTIVE`, `NO_FETCH`, `ADOS_BRANCH`, `ALLOW_NON_ROOT`

**Exit codes**

| Code | Meaning |
|------|---------|
| 0 | Success |
| 2 | Usage error |
| 3 | Configuration error |
| 4 | Runtime error |
| 5 | External command failure |

**Platform path resolution**

| Platform | opencode global dir |
|----------|---------------------|
| Windows | `%APPDATA%\opencode` |
| Linux | `$XDG_CONFIG_HOME/opencode` or `~/.config/opencode` |
| macOS | `~/.config/opencode` |

## 5. Non-Functional Requirements

### 5.1 Security & Privacy

- `safe_rmdir` enforces minimum path depth (≥ 3 resolved parts) and blocks root and home directory paths on all platforms.
- All subprocess invocations use argument lists (`shell=False`), preventing shell injection via crafted environment variable values or branch names.
- No external packages required; stdlib-only approach eliminates supply-chain risk.
- Scripts operate with user-level filesystem permissions; no privilege escalation is performed.
- No user data is collected or transmitted; network access is limited to cloning/pulling the public ADOS GitHub repository.

### 5.2 Performance & Scalability

- `python3 scripts/install.py --help` must return within 2 seconds on any supported platform.
- Scripts are CLI tools; no scalability concerns beyond local filesystem performance.

### 5.3 Localization & Accessibility

- All path operations use `pathlib.Path` — never string concatenation — ensuring correct handling of Unicode filenames and paths with spaces on Windows.
- Log output uses `os.isatty()` to gate colour codes, ensuring clean output when piped.

## 6. Quality Assurance Strategy

### 6.1 Testing Approach

| Level | Location | Scope / Goal |
|-------|----------|--------------|
| Unit | `scripts/tests/test_*.py` | Each `ados_lib` module tested in isolation with mocked dependencies |
| Integration | `scripts/tests/test_*_integration.py` (named `test_install_local.py`, `test_install_global.py`, etc.) | Full install/uninstall roundtrip in `tempfile.mkdtemp()`; git mocked via `unittest.mock.patch` |
| Manual / Smoke | N/A | One-liner bootstrap on live Linux/macOS; interactive mode; cross-platform Python 3.8 / 3.12 runs |

**Run command:** `python -m unittest discover -s scripts/tests`

### 6.2 Test Data & Scenarios

- Integration tests use `tempfile.mkdtemp()` for full filesystem isolation.
- A helper (`scripts/tests/__init__.py → make_mock_ados_source()`) creates a mock ADOS source tree with placeholder `.md` files.
- Env vars are patched with `unittest.mock.patch.dict(os.environ, ...)` to prevent inter-test leakage.
- See `doc/quality/test-specs/test-spec-cross-platform-install.md` for full scenario coverage.

## 7. Operational & Support

### 7.1 Configuration

All configuration is via CLI flags and environment variables (see §4.5). No config files or feature flags.

### 7.2 Observability

- **Log levels:** `[INFO]`, `[WARN]`, `[ERR]`, `[DEBUG]` — consumable by shell pipelines and CI log parsers.
- **Exit codes:** `0`, `2`, `3`, `4`, `5` — enable automated success/failure detection.
- **Summary counters:** Printed at completion (added/updated/unchanged for install; removed/skipped for uninstall).

### 7.3 Cost & Infrastructure

No infrastructure cost — scripts are CLI tools distributed as part of the ADOS repository.

## 8. Dependencies & Risks

**Runtime dependencies**

| Dependency | Notes |
|------------|-------|
| Python ≥ 3.8 (CPython) | New prerequisite; documented in `doc/guides/system-dependencies.md` and `README.md` |
| `git` CLI on PATH | Existing prerequisite; unchanged |

**Key risks**

| Risk | Mitigation |
|------|-----------|
| `python` vs `python3` alias varies by platform | Use `#!/usr/bin/env python3`; document `py -3` for Windows |
| Windows paths with spaces or Unicode causing failures | `pathlib.Path` throughout; explicit test (TC-XPLAT-002) |
| `subprocess.run` Windows quoting differences | Argument-list calls only; `shell=False` enforced |
| Bash/Python behavioral divergence | Bash scripts remain as reference; idempotency + parity tests |
| Python 3.8 EOL (Oct 2024) | Minimum version may need revisiting in a future change |

**Parallel Bash scripts**

`scripts/install.sh` and `scripts/uninstall.sh` remain in place. A project installed by the Bash version can be updated or uninstalled by the Python version and vice versa (no format or manifest differences). Bash script retirement is deferred to a future work item pending production validation of the Python version.

## 9. Glossary & References

| Term | Definition |
|------|------------|
| ados_lib | Shared Python library package (`scripts/ados_lib/`) — platform-agnostic primitives |
| Global install | Copies ADOS agent/command files to the system-level opencode config directory (all projects) |
| Local install | Copies ADOS artifacts into the current project directory |
| Dry-run | Execution mode where all operations are planned and logged but no filesystem changes are made |
| Updatable file | A file ADOS manages and auto-updates on re-run (e.g., documentation handbook, guides) |
| Project-specific file | A file installed by ADOS that is preserved and never overwritten on re-run |
| safe_rmdir | Library function that removes a directory only after validating it is not a dangerous path |
| XDG | X Desktop Group standard defining config directory locations on Linux (`XDG_CONFIG_HOME`) |
| One-liner install | `curl \| python3 -` command that bootstraps a full ADOS global installation |

**Related documents**

- Change spec: `doc/changes/2026-04/2026-04-30--GH-1--portable-python-install-uninstall-scripts/chg-GH-1-spec.md`
- Test spec: `doc/quality/test-specs/test-spec-cross-platform-install.md`
- System dependencies guide: `doc/guides/system-dependencies.md`
- README: `README.md`
