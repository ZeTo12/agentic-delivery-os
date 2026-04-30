---
change:
  ref: GH-1
  type: feat
  status: Proposed
  slug: portable-python-install-uninstall-scripts
  title: "Portable Python install and uninstall scripts for cross-platform support"
  owners: [juliusz-cwiakalski]
  service: scripts
  labels: [cross-platform, python, install, tooling]
  version_impact: minor
  audience: mixed
  security_impact: low
  risk_level: medium
  dependencies:
    internal: [scripts/install.sh, scripts/uninstall.sh, doc/guides/system-dependencies.md, README.md]
    external: [Python 3.8+, git CLI]
---

# CHANGE SPECIFICATION

> **PURPOSE**: Port `scripts/install.sh` and `scripts/uninstall.sh` from Bash to Python 3 (stdlib only) so that Windows, Linux, and macOS users can install and uninstall ADOS without a Bash emulator or WSL.

## 1. SUMMARY

The existing ADOS install and uninstall scripts are implemented in Bash (~760 and ~429 lines respectively), making them unavailable to Windows users without WSL or a Bash emulator. This change delivers functional Python 3 equivalents — `scripts/install.py` and `scripts/uninstall.py` — backed by a shared library `scripts/ados_lib/`, a minimal one-liner bootstrap entry point, and an updated test suite. The Bash scripts remain in place in parallel, ensuring no regression for existing Unix users.

## 2. CONTEXT

### 2.1 Current State Snapshot

ADOS installation and uninstall are performed via `scripts/install.sh` and `scripts/uninstall.sh`. Both scripts:

- Depend on GNU Bash ≥ 4 and POSIX utilities (`cp`, `mkdir`, `diff`, `git`).
- Support `--global` (repo clone to `~/.ados/` + opencode config install) and `--local` (project-level copy) modes.
- Respect a set of environment variable overrides (`ADOS_REPO_URL`, `ADOS_HOME`, `ADOS_SOURCE_DIR`, `DRY_RUN`, etc.).
- Emit structured log output with tag-prefixed lines (e.g., `[INFO]  (ados-install) message`).
- Exit with documented codes: `0` success, `2` usage, `3` config, `4` runtime, `5` external failure.
- Are tested manually; no automated cross-platform CI exists yet.

### 2.2 Pain Points / Gaps

- **Windows incompatibility**: Native Windows users (PowerShell / CMD) cannot run the Bash scripts without WSL or Git Bash — a significant friction point for ADOS adoption.
- **Single-platform tooling**: Contributors and consumers on Windows cannot participate in install/update workflows without environment setup that is outside the ADOS scope.
- **Shared code duplication**: Both Bash scripts contain overlapping logic (path resolution, file copy-with-diff, git operations, `.gitignore` management) with no shared library, leading to maintenance risk if behaviors diverge.
- **No stdlib-level portability layer**: There is no abstraction over platform-specific config directories (`%APPDATA%` vs XDG vs `~/.config`).

## 3. PROBLEM STATEMENT

Because `install.sh` and `uninstall.sh` are Bash-only scripts, Windows users cannot install or update ADOS natively, resulting in a blocked adoption path for a significant portion of potential contributors and consumers, and placing unnecessary dependency on WSL or third-party Bash emulators.

## 4. GOALS

- **G-1**: Provide a Python 3 (stdlib only) install entry point with functional parity to `install.sh` on Windows, Linux, and macOS.
- **G-2**: Provide a Python 3 (stdlib only) uninstall entry point with functional parity to `uninstall.sh` on Windows, Linux, and macOS.
- **G-3**: Extract shared logic into a versioned library (`ados_lib/`) to eliminate duplication between install and uninstall and reduce future maintenance cost.
- **G-4**: Provide a minimal one-liner bootstrap entry point (`bootstrap.py`) that works on Linux and macOS via `curl | python3 -` and on Windows via PowerShell.
- **G-5**: Provide a unit and integration test suite runnable with Python stdlib `unittest` on all three platforms.
- **G-6**: Update `README.md` and `doc/guides/system-dependencies.md` to document Python-based installation paths for all platforms.

### 4.1 Success Metrics / KPIs

| Metric | Target |
|--------|--------|
| CLI flag parity between Python and Bash versions | 100% of flags supported |
| Environment variable parity | 100% of env vars respected |
| Exit code parity | All 5 exit codes match Bash behavior |
| Platform coverage | Windows 10+, Ubuntu 20.04+, macOS Monterey+ |
| Python version coverage | Python 3.8 and 3.12 |
| External package dependencies | 0 (stdlib only) |
| Unit + integration tests passing (per platform) | All tests green on all 3 platforms |
| `safe_rmdir` dangerous path blocks | 100% of dangerous paths blocked on all platforms |

### 4.2 Non-Goals

- **NG-1**: Removal of `scripts/install.sh` and `scripts/uninstall.sh` — Bash scripts remain in parallel.
- **NG-2**: Introduction of GitHub Actions CI — treated as a separate work item.
- **NG-3**: PyInstaller or binary distribution of the scripts.
- **NG-4**: Python packaging (`setup.py` / `pyproject.toml`).
- **NG-5**: GUI or TUI for installation.
- **NG-6**: Support for Python versions below 3.8.

## 5. FUNCTIONAL CAPABILITIES

| ID | Capability | Rationale |
|----|------------|-----------|
| F-1 | Python install entry point with `--global` mode | Enables native Windows global installation without WSL |
| F-2 | Python install entry point with `--local` mode | Enables native Windows project-level installation |
| F-3 | Python uninstall entry point with `--global` mode | Enables native Windows global removal without WSL |
| F-4 | Python uninstall entry point with `--local` mode | Enables native Windows project-level removal |
| F-5 | Shared library `ados_lib/` with platform-agnostic primitives | Eliminates code duplication; single source of truth for path resolution, file ops, git ops |
| F-6 | Platform-aware config directory resolution | Correctly maps opencode global dir to `%APPDATA%` (Windows), XDG (Linux), `~/.config` (macOS) |
| F-7 | Copy-with-diff capability in file operations | Preserves interactive and force update modes from Bash version |
| F-8 | Safe directory removal with depth guard | Prevents accidental deletion of root, home, or shallow paths on all platforms |
| F-9 | `.gitignore` entry management | Adds required ADOS ignore entries idempotently |
| F-10 | Git operations over subprocess (no shell=True) | Enables git interactions on Windows without shell emulation |
| F-11 | Minimal one-liner bootstrap script | Enables `curl | python3 -` installation pattern for Linux/macOS; PowerShell equivalent for Windows |
| F-12 | Dry-run mode across all operations | Allows users to preview install/uninstall operations without making changes |
| F-13 | Full environment variable override support | Preserves power-user and CI-level configurability from Bash version |
| F-14 | Structured log output matching Bash format | Ensures operational familiarity; eases transition for existing users |

### 5.1 Capability Details

**F-1 / F-2 — Install entry points**: `scripts/install.py` accepts the same CLI flags as `install.sh` (`-g/--global`, `-l/--local`, `-b/--branch`, `-n/--dry-run`, `-v/--verbose`, `-f/--force`, `-i/--interactive`, `--no-fetch`, `--allow-non-root`, `-h/--help`, `-V/--version`). Default mode is `--local` when neither `--global` nor `--local` is specified. All environment variable overrides from the Bash version must be honoured.

**F-3 / F-4 — Uninstall entry points**: `scripts/uninstall.py` accepts equivalent flags and performs the same removal operations as `uninstall.sh`. Global uninstall removes agent/command files and the ADOS home directory; local uninstall removes project-specific and updatable files and cleans empty directories.

**F-5 — Shared library**: `scripts/ados_lib/` is a Python package importable from both entry points. Its modules cover: `types` (config dataclasses), `logger` (structured output), `platform_paths` (OS-aware directory resolution), `manifest` (file lists), `file_ops` (copy/diff/remove), `gitignore` (idempotent entry management), `safety` (path validation, safe removal), `git_ops` (subprocess-based git interactions), and `cli` (argparse-based argument parsing).

**F-6 — Platform path resolution**: `platform_paths.py` resolves config directories without third-party libraries. On Windows: `%APPDATA%\opencode`; on Linux: `$XDG_CONFIG_HOME/opencode` or `~/.config/opencode`; on macOS: `~/.config/opencode`. `ADOS_HOME` and `OPENCODE_GLOBAL_DIR` environment variables override defaults.

**F-7 — Copy-with-diff**: When a destination file already exists and differs from source, behaviour depends on mode: `--force` overwrites silently; `--interactive` shows a unified diff and prompts; updatable files auto-update; project-specific files are preserved. Symlinks at the destination are replaced by a regular copy.

**F-8 — Safe directory removal**: `safe_rmdir` checks that a path is not empty, not root, not the user's home directory, and has a minimum resolved depth (≥ 3 path components on both Unix and Windows). Violations raise a hard error before any deletion occurs.

**F-9 — `.gitignore` management**: Before adding an entry, `gitignore.py` checks whether an identical line already exists, preventing duplicate entries.

**F-10 — Git operations**: All git commands are invoked via `subprocess.run` with argument lists (never shell strings), UTF-8 encoding, and `errors="replace"` to handle non-ASCII output on Windows. `require_git()` uses `shutil.which("git")` to verify availability.

**F-11 — Bootstrap script**: `scripts/bootstrap.py` is a self-contained (~30-line) script with no `ados_lib` dependency. It clones the ADOS repo to `~/.ados/repo` and then invokes `install.py --global`. This enables the one-liner pattern without requiring a pre-downloaded library.

**F-12 — Dry-run mode**: When active, no files are written, removed, or git operations executed. All planned operations are logged with a `[DRY-RUN]` marker, producing output equivalent to the Bash version's dry-run behavior.

**F-13 — Environment variable support**: The full set of Bash-version environment overrides is supported: `ADOS_REPO_URL`, `ADOS_RAW_URL`, `ADOS_HOME`, `ADOS_REPO_DIR`, `OPENCODE_GLOBAL_DIR`, `ADOS_SOURCE_DIR`, `DRY_RUN`, `VERBOSE`, `FORCE`, `INTERACTIVE`, `NO_FETCH`, `ADOS_BRANCH`, `ALLOW_NON_ROOT`.

**F-14 — Log format**: Output lines follow the pattern `[LEVEL]  (ados-install) message` matching the Bash version. Colour is applied only when the output is a TTY (`os.isatty()`).

## 6. USER & SYSTEM FLOWS

```
Flow 1: Global install (new machine)
  User runs: python3 scripts/install.py --global
  → System validates git is available
  → System validates target paths (warns if outside $HOME)
  → System clones ADOS repo to ~/.ados/repo (or pulls if exists)
  → System copies agent + command .md files to opencode global dir
  → System prints summary (added/updated/unchanged counts)
  → Exit 0

Flow 2: Local install (project onboarding)
  User runs: python3 scripts/install.py --local
  → System verifies current directory is a git project root
  → System validates paths
  → System resolves source dir (ADOS_SOURCE_DIR → local repo → ~/.ados/repo)
  → System auto-fetches latest source (unless --no-fetch)
  → System copies project files, updatable files, templates, creates dir stubs
  → System ensures .gitignore entries
  → System prints summary + next-steps
  → Exit 0

Flow 3: One-liner global install (Linux/macOS)
  User runs: curl -fsSL <raw-url>/scripts/bootstrap.py | python3 - --global
  → bootstrap.py clones ADOS repo to ~/.ados/repo
  → bootstrap.py invokes install.py --global
  → Flow 1 continues

Flow 4: Dry-run preview
  User runs: python3 scripts/install.py --local --dry-run
  → System executes Flow 2 logic without writing any files
  → All planned operations logged with [DRY-RUN] marker
  → Exit 0

Flow 5: Global uninstall
  User runs: python3 scripts/uninstall.py --global
  → System prompts for confirmation (skipped with --force or --dry-run)
  → System removes agent files from opencode global dir
  → System removes command files from opencode global dir
  → System calls safe_rmdir on ADOS home
  → System prints removal summary
  → Exit 0

Flow 6: Local uninstall
  User runs: python3 scripts/uninstall.py --local
  → System verifies current directory is git project root (strict)
  → System prompts for confirmation
  → System removes project-specific, updatable, and template files
  → System removes empty ADOS directories
  → System prints removal summary
  → Exit 0
```

## 7. SCOPE & BOUNDARIES

### 7.1 In Scope

- `scripts/install.py` — Python install entry point with full CLI and env var parity to `install.sh`
- `scripts/uninstall.py` — Python uninstall entry point with full CLI and env var parity to `uninstall.sh`
- `scripts/ados_lib/` — shared library package (`__init__`, `types`, `logger`, `platform_paths`, `manifest`, `file_ops`, `gitignore`, `safety`, `git_ops`, `cli`)
- `scripts/bootstrap.py` — minimal one-liner bootstrap entry point
- Unit tests for all `ados_lib` modules via stdlib `unittest`
- Integration tests for full install/uninstall roundtrip (local and global modes)
- `README.md` update — Windows/Linux/macOS install instructions including Python variant
- `doc/guides/system-dependencies.md` update — Python 3.8+ documented as dependency

### 7.2 Out of Scope

- [OUT] Removal of `scripts/install.sh` and `scripts/uninstall.sh`
- [OUT] GitHub Actions CI workflow for automated cross-platform testing
- [OUT] PyInstaller or binary distribution
- [OUT] Python packaging (`setup.py` / `pyproject.toml`)
- [OUT] GUI or TUI
- [OUT] Support for Python < 3.8

### 7.3 Deferred / Maybe-Later

- GitHub Actions CI for automated matrix testing (Windows × Linux × macOS × Python 3.8 × 3.12) — separate work item
- Retirement of Bash scripts after Python version has been validated in production
- `argcomplete` shell completion for Python scripts — requires external dependency
- Windows PowerShell one-liner via `irm | python` — documented in README but not tested in automated suite

## 8. INTERFACES & INTEGRATION CONTRACTS

### 8.1 REST / HTTP Endpoints

N/A — this change delivers CLI tooling, not HTTP services.

### 8.2 Events / Messages

N/A

### 8.3 Data Model Impact

| ID | Element | Description |
|----|---------|-------------|
| DM-1 | `InstallConfig` | Dataclass capturing resolved install configuration: mode, branch, dry_run, verbose, force, interactive, no_fetch, allow_non_root |
| DM-2 | `UninstallConfig` | Dataclass capturing resolved uninstall configuration: mode, dry_run, verbose, force |
| DM-3 | `Counters` (install) | Dataclass tracking install operation outcomes: added, updated, unchanged |
| DM-4 | `Counters` (uninstall) | Dataclass tracking uninstall operation outcomes: removed, skipped |
| DM-5 | File manifest lists | Named constants in `manifest.py` (`UPDATABLE_FILES`, `PROJECT_FILES`, `LOCAL_DIRS`, `AGENT_FILES`, `COMMAND_FILES`, etc.) — 1:1 parity with Bash variable arrays |

### 8.4 External Integrations

| Integration | Notes |
|-------------|-------|
| `git` CLI | Required on all platforms; invoked via `subprocess.run` with argument list; version ≥ 2.x assumed |
| GitHub raw content URL | Used by bootstrap and global install to fetch/clone ADOS repo; overridable via `ADOS_REPO_URL` / `ADOS_RAW_URL` |

### 8.5 Backward Compatibility

- Bash scripts (`install.sh`, `uninstall.sh`) are unchanged and continue to work for existing Unix users.
- The Python scripts do not alter any file formats, manifest structures, or directory layouts produced by the Bash scripts. A project installed with the Bash version can be updated or uninstalled with the Python version and vice versa.
- Environment variables accepted by the Python version are a strict superset of those accepted by the Bash version.

## 9. NON-FUNCTIONAL REQUIREMENTS (NFRs)

| ID | Requirement | Threshold |
|----|-------------|-----------|
| NFR-1 | Platform portability | All capabilities must function on Windows 10+, Ubuntu 20.04+, macOS 12+ without platform-specific pre-requisites beyond Python ≥ 3.8 and git |
| NFR-2 | Python version compatibility | All code must run without modification on CPython 3.8 and CPython 3.12 |
| NFR-3 | Zero external dependencies | No `pip install` required; only Python stdlib modules permitted |
| NFR-4 | Startup time | `python3 scripts/install.py --help` must return within 2 seconds on any supported platform |
| NFR-5 | Idempotency | Re-running `install.py --local` on an already-installed project must produce 0 added, 0 updated, N unchanged — no side effects |
| NFR-6 | Atomic dry-run | `--dry-run` must produce zero file system changes; assertion verifiable by comparing directory snapshots before and after |
| NFR-7 | Safe removal guard | `safe_rmdir` must reject paths with fewer than 3 resolved path components and must reject root and home directory paths on all platforms |
| NFR-8 | Test suite self-containment | All tests must run with `python -m unittest discover` from the repo root; no pytest, tox, or external test runner required |
| NFR-9 | Log format fidelity | Python log output format must match Bash format: `[LEVEL]  (ados-install) message` |
| NFR-10 | Windows path safety | All path operations must use `pathlib.Path` — string concatenation for paths is prohibited |

## 10. TELEMETRY & OBSERVABILITY REQUIREMENTS

The scripts are CLI tools running in user environments where centralised telemetry is not applicable. Observable signals are:

- Structured stdout/stderr log lines at `[INFO]`, `[WARN]`, `[ERR]`, and `[DEBUG]` levels — consumable by shell pipelines and CI log parsers.
- Exit codes (`0`, `2`, `3`, `4`, `5`) enabling automated success/failure detection in shell scripts and CI steps.
- Summary counters printed at completion (added/updated/unchanged for install; removed/skipped for uninstall) — enabling diff-based change detection in automated runs.

## 11. RISKS & MITIGATIONS

| ID | Risk | Impact | Probability | Mitigation | Residual Risk |
|----|------|--------|-------------|------------|---------------|
| RSK-1 | `python` vs `python3` command alias differs across platforms (Windows uses `python`, Linux/macOS `python3`; some systems have neither on PATH) | M | H | Use shebang `#!/usr/bin/env python3`; document `py -3` for Windows in README and `system-dependencies.md`; bootstrap.py detects available alias | L |
| RSK-2 | Windows paths with spaces or Unicode characters causing path resolution failures | H | M | Use `pathlib.Path` throughout; never concatenate path strings; test explicitly with paths containing spaces | L |
| RSK-3 | `subprocess.run` behaves differently on Windows (no implicit `/bin/sh`; quoting rules differ) | H | M | Pass all git commands as argument lists (`["git", "clone", ...]`); never use `shell=True`; include Windows subprocess mock tests | L |
| RSK-4 | Behavioural divergence between Python and Bash versions discovered post-delivery | M | M | Maintain 1:1 Bash→Python mapping table in planning doc; acceptance criteria explicitly compare outputs; keep Bash scripts in parallel as reference | M |
| RSK-5 | macOS case-insensitive filesystem causing incorrect file comparison results | L | L | Use `filecmp.cmp(shallow=False)` for content comparison; document as known platform edge case | L |

## 12. ASSUMPTIONS

- Python 3.8 or later is available on the target machine (documented as a new prerequisite).
- The `git` CLI is available on `PATH` on all target platforms (existing prerequisite, unchanged).
- The repository URL and raw content URL remain stable or are overridden via environment variables.
- Windows long-path support (`\\?\` prefix) is not required for the initial delivery; standard `pathlib.Path` resolution is sufficient.
- The Bash scripts will not be modified as part of this change (they receive only an optional deprecation comment).
- No changes to the file manifests (lists of files installed/uninstalled) are required — Python version mirrors the Bash lists exactly.

## 13. DEPENDENCIES

| Direction | Item | Notes |
|-----------|------|-------|
| Depends on | Python ≥ 3.8 (CPython) | New runtime prerequisite; must be documented |
| Depends on | `git` CLI on PATH | Existing prerequisite; unchanged |
| Depends on | `scripts/install.sh` behavioral specification | Python version must match Bash behavior; Bash script is the reference |
| Depends on | `scripts/uninstall.sh` behavioral specification | Same as above |
| Blocks | GitHub Actions CI work item | CI will target the Python test suite delivered by this change |
| Blocks | Bash script retirement | Retirement can only proceed after this change is validated in production |

## 14. OPEN QUESTIONS

| ID | Question | Context | Status |
|----|----------|---------|--------|
| OQ-1 | Should `bootstrap.py` also support Windows PowerShell one-liner (`irm \| python`)? | Phase 7 planning recommends documenting it but not automating tests. Unclear whether automated test is required. | Open |
| OQ-2 | Should the Python scripts emit machine-readable JSON output on request (e.g., `--output json`)? | Would benefit CI consumers. Not in Bash version. | Open — out of scope for this change unless owners decide otherwise |
| OQ-3 | Should `install.py` add a deprecation comment to `install.sh` automatically, or should that be a manual editorial change? | Planning doc suggests adding a comment to Bash scripts; unclear whether this is scripted or manual. | Open |

## 15. DECISION LOG

| ID | Decision | Rationale | Date |
|----|----------|-----------|------|
| DEC-1 | Python stdlib only; no external packages | Eliminates `pip install` as a prerequisite; keeps bootstrap simple and auditable | 2026-04-30 |
| DEC-2 | Minimum Python version: 3.8 | Walrus operator (`:=`) and `shutil.copytree(dirs_exist_ok=True)` require 3.8; widely available on Ubuntu 20.04+, macOS Monterey+, Windows Store | 2026-04-30 |
| DEC-3 | Bash scripts remain in parallel (not removed) | Avoids regression for existing Unix users; allows side-by-side validation before retirement | 2026-04-30 |
| DEC-4 | Shared library extracted to `scripts/ados_lib/` | Eliminates code duplication between install and uninstall; enables independent unit testing of primitives | 2026-04-30 |
| DEC-5 | `bootstrap.py` as separate minimal file (Option A) | Avoids single-file mode complexity in `install.py`; ~30 lines, no `ados_lib` import, easy to audit | 2026-04-30 |
| DEC-6 | Git commands invoked as argument lists, never shell strings | Ensures correct quoting and behavior on Windows where no `/bin/sh` is available | 2026-04-30 |
| DEC-7 | GitHub Actions CI deferred to separate work item | Project has no existing CI infrastructure; introducing it in scope of this change would expand risk surface | 2026-04-30 |

## 16. AFFECTED COMPONENTS (HIGH-LEVEL)

| Component | Impact |
|-----------|--------|
| `scripts/install.sh` | Existing — receives optional deprecation comment only; no logic changes |
| `scripts/uninstall.sh` | Existing — receives optional deprecation comment only; no logic changes |
| `scripts/install.py` | New — Python install entry point |
| `scripts/uninstall.py` | New — Python uninstall entry point |
| `scripts/bootstrap.py` | New — minimal one-liner bootstrap |
| `scripts/ados_lib/` | New — shared Python library package |
| `scripts/tests/` | New — stdlib unittest suite |
| `README.md` | Updated — cross-platform install instructions |
| `doc/guides/system-dependencies.md` | Updated — Python 3.8+ documented as dependency |

## 17. ACCEPTANCE CRITERIA

| ID | Criterion | Linked |
|----|-----------|--------|
| AC-F1-1 | **Given** a terminal on any supported platform with Python ≥ 3.8 available, **when** the user runs `python3 scripts/install.py --help`, **then** the output lists all flags equivalent to `bash scripts/install.sh --help` (--global, --local, --branch, --dry-run, --verbose, --force, --interactive, --no-fetch, --allow-non-root) | F-1, F-2 |
| AC-F1-2 | **Given** a machine with git available and no prior ADOS installation, **when** the user runs `python3 scripts/install.py --global`, **then** ADOS agent and command files are installed to the platform-appropriate opencode global directory and the operation summary matches the Bash version's output structure | F-1, F-6, F-14 |
| AC-F2-1 | **Given** a git project root directory with ADOS source available, **when** the user runs `python3 scripts/install.py --local --dry-run`, **then** all planned file operations are logged with a `[DRY-RUN]` marker and no files are written or modified | F-2, F-12 |
| AC-F2-2 | **Given** an already-installed local project, **when** the user runs `python3 scripts/install.py --local` a second time without any source changes, **then** the summary reports 0 added, 0 updated, and N unchanged — no files are overwritten | F-2, NFR-5 |
| AC-F3-1 | **Given** a globally-installed ADOS environment, **when** the user runs `python3 scripts/uninstall.py --global --dry-run`, **then** the output lists the same set of files that `bash scripts/uninstall.sh --global --dry-run` would list | F-3, F-12 |
| AC-F4-1 | **Given** a locally-installed ADOS project, **when** the user runs `python3 scripts/uninstall.py --local --force`, **then** all project-level ADOS files are removed and any empty ADOS directories are cleaned up | F-4 |
| AC-F8-1 | **Given** any supported platform, **when** `safe_rmdir` is called with a path resolving to fewer than 3 components (e.g., `/`, `C:\`, `~`), **then** the function raises a hard error and performs no deletion | F-8, NFR-7 |
| AC-F8-2 | **Given** any supported platform, **when** `safe_rmdir` is called with the user's home directory, **then** the function raises a hard error and performs no deletion | F-8, NFR-7 |
| AC-F10-1 | **Given** a Windows environment without `/bin/sh`, **when** any git operation is performed by the Python scripts, **then** `subprocess.run` is called with a list argument and `shell=False` — verified by unit tests using mocked subprocess | F-10 |
| AC-F11-1 | **Given** a Linux or macOS machine, **when** the user runs `curl -fsSL <bootstrap-url> \| python3 - --global`, **then** the ADOS repo is cloned and global install completes successfully | F-11 |
| AC-NFR-1 | **Given** Python 3.8 and Python 3.12 on each of Windows, Linux, and macOS, **when** the full unittest suite is run with `python -m unittest discover`, **then** all tests pass with zero failures or errors | NFR-2, NFR-8 |
| AC-NFR-2 | **Given** the `ados_lib` package, **when** it is imported in a Python 3.8 environment, **then** no `ImportError` is raised and no packages outside the Python stdlib are required | NFR-3 |

## 18. ROLLOUT & CHANGE MANAGEMENT (HIGH-LEVEL)

- The Python scripts are additive — no existing Bash scripts or installed artifacts are altered during rollout.
- Delivery is sequenced across 7 phases (shared library foundations → file ops & safety → git ops → install script → uninstall script → cross-platform tests → documentation & bootstrap), with each phase committed independently.
- Existing Unix users continue using `install.sh` / `uninstall.sh` without any required action.
- Windows users are directed to the new Python scripts via updated `README.md` documentation.
- After the PR is merged and validated on all three platforms, a follow-up work item can be opened to retire the Bash scripts.

## 19. DATA MIGRATION / SEEDING (IF APPLICABLE)

N/A — no data migration required. Files installed by the Bash version are compatible with the Python version; no format changes are introduced.

## 20. PRIVACY / COMPLIANCE REVIEW

- The scripts do not collect, transmit, or store any user data.
- Network access is limited to cloning/pulling the public ADOS GitHub repository, which is already performed by the existing Bash scripts.
- No privacy or compliance concerns identified.

## 21. SECURITY REVIEW HIGHLIGHTS

- **Path traversal protection**: `safe_rmdir` enforces minimum path depth and blocks home/root removal, mitigating the risk of accidental or malicious recursive deletion.
- **No `shell=True`**: All subprocess invocations use argument lists, preventing shell injection via crafted environment variable values or branch names.
- **No external package installation**: stdlib-only approach eliminates supply-chain risk from third-party Python packages.
- **Low security impact overall**: The scripts operate on local filesystems with user-level permissions; no privileged escalation is performed.

## 22. MAINTENANCE & OPERATIONS IMPACT

- The shared `ados_lib/` library becomes the single maintenance point for path resolution, file operations, and git interactions — any future behavioral change needs to be made once, not in both Bash and Python scripts.
- Once Bash scripts are retired (future work item), the Bash-specific knowledge requirement for contributors is eliminated.
- The `unittest` test suite provides regression protection for future changes to library modules.
- Python 3.8 end-of-life (October 2024) means the minimum version constraint may need revisiting; upgrading to 3.9+ unlocks additional typing improvements but requires explicit decision.

## 23. GLOSSARY

| Term | Definition |
|------|------------|
| ADOS | Agentic Delivery OS — the spec-driven software delivery system this repo implements |
| ados_lib | The shared Python library package (`scripts/ados_lib/`) containing platform-agnostic primitives |
| Global install | Installing ADOS agent and command definitions to the system-level opencode config directory, making them available in all projects |
| Local install | Copying ADOS artifacts into the current project directory |
| Dry-run | Execution mode where all operations are planned and logged but no filesystem changes are made |
| Updatable file | A file that ADOS manages and auto-updates on re-run (e.g., documentation handbook, guides) |
| Project-specific file | A file installed by ADOS that is preserved and never overwritten on re-run (e.g., `pm-instructions.md`) |
| safe_rmdir | A library function that removes a directory only after verifying it is not a dangerous path (root, home, or shallow) |
| XDG | X Desktop Group — the standard defining config directory locations on Linux (`XDG_CONFIG_HOME`) |
| One-liner install | A single shell command (e.g., `curl \| python3 -`) that bootstraps a full ADOS global installation |
| bootstrap.py | A minimal, self-contained Python script (~30 lines) that enables the one-liner install pattern without depending on `ados_lib` |

## 24. APPENDICES

### Appendix A: Bash → Python Standard Library Mapping

| Bash Construct | Python Equivalent |
|----------------|-------------------|
| `cp file1 file2` | `shutil.copy2(src, dest)` |
| `mkdir -p dir` | `Path(dir).mkdir(parents=True, exist_ok=True)` |
| `rm -f file` | `Path(file).unlink(missing_ok=True)` |
| `rm -rf dir` | `shutil.rmtree(dir)` |
| `diff -q file1 file2` | `filecmp.cmp(file1, file2, shallow=False)` |
| `diff -u file1 file2` | `difflib.unified_diff(...)` |
| `ls -A dir` (empty check) | `any(Path(dir).iterdir())` |
| `realpath -m path` | `Path(path).resolve()` |
| `command -v git` | `shutil.which("git")` |
| `git clone …` | `subprocess.run(["git", "clone", …])` |
| `read -r answer` | `input("prompt")` |
| `grep -qF pattern file` | `pattern in Path(file).read_text()` |
| `BASH_SOURCE[0]` | `Path(__file__).resolve().parent` |
| `$HOME` | `Path.home()` |
| `set -e` (exit on error) | Exceptions + try/except |
| `trap INT` | `signal.signal(signal.SIGINT, handler)` |
| `case` (argument parsing) | `argparse.ArgumentParser` |
| Exit codes | `sys.exit(code)` |
| Coloured output | `\033[…m` with `os.isatty()` check |

### Appendix B: Exit Code Reference

| Code | Meaning |
|------|---------|
| 0 | Success |
| 2 | Usage error |
| 3 | Configuration error |
| 4 | Runtime error |
| 5 | External command failure |

## 25. DOCUMENT HISTORY

| Version | Date | Author | Changes |
|---------|------|--------|---------|
| 1.0 | 2026-04-30 | spec-writer | Initial specification |

---

## AUTHORING GUIDELINES

This spec was authored from:
- Planning session summary provided by the user
- `doc/planning/portable-install-scripts-plan.md` (primary reference for module detail, mapping table, and phase structure)
- `scripts/install.sh` header (lines 1–80) for CLI flags, environment variables, exit codes, and behavioral description
- `doc/templates/change-spec-template.md` for structural guidance

Missing information (e.g., confirmed owner identity, CI timeline) is captured in OPEN QUESTIONS rather than invented.

## VALIDATION CHECKLIST

- [x] `change.ref` matches provided `workItemRef` (GH-1)
- [x] `owners` has at least one entry
- [x] `status` is "Proposed"
- [x] All sections present in order (1-25 + guidelines + checklist)
- [x] ID prefixes consistent and unique (F-, AC-, NFR-, RSK-, DEC-, DM-, OQ-)
- [x] Acceptance criteria reference at least one F-/NFR- ID and use Given/When/Then
- [x] NFRs include measurable values
- [x] Risks include Impact & Probability
- [x] No implementation details (no file-level code paths, no step-by-step tasks)
- [x] No content duplicated from linked docs
- [x] Front matter validates per front_matter_rules
