---
id: chg-GH-1-test-plan
status: Proposed
created: 2026-04-30
last_updated: 2026-04-30
owners: [ados-core]
service: scripts
labels: [python, cross-platform, install, uninstall, tooling]
version_impact: minor
summary: "Test plan for porting install.sh and uninstall.sh to Python 3 (stdlib only), covering cross-platform parity on Windows, Linux, and macOS with Python 3.8 and 3.12."
links:
  change_spec: ./chg-GH-1-spec.md
  implementation_plan: doc/planning/portable-install-scripts-plan.md
  testing_strategy: .ai/rules/testing-strategy.md
---

# Test Plan - Portable Python Install/Uninstall Scripts (GH-1)

## 1. Scope and Objectives

This test plan covers the Python 3 port of `scripts/install.sh` and `scripts/uninstall.sh`, targeting full functional parity across Windows, Linux, and macOS with Python 3.8 and 3.12. The primary risk is behavioral divergence from the Bash originals — wrong file paths, missing idempotency, unsafe deletions, or broken CLI flags. A secondary risk is platform-specific path handling bugs on Windows (UNC paths, spaces, long paths) and Linux (XDG overrides). The plan traces directly to the seven acceptance criteria (AC1–AC7) and maps to the T1–T30 scenario table in `doc/planning/portable-install-scripts-plan.md`.

### 1.1 In Scope

- `scripts/ados_lib/` shared library modules: `platform_paths`, `logger`, `manifest`, `file_ops`, `gitignore`, `safety`, `git_ops`, `cli`, `types`
- `scripts/install.py` — global and local installation flows, all CLI flags, environment variable overrides
- `scripts/uninstall.py` — global and local uninstallation flows, confirmation prompts, `safe_rmdir`
- `scripts/bootstrap.py` — one-liner bootstrap for Linux and macOS
- Cross-platform correctness: Windows path handling, XDG overrides on Linux, macOS case-insensitive filesystem
- Python version compatibility: 3.8 and 3.12
- Idempotency: re-running install produces zero changes when state is already current
- Dry-run mode: no filesystem mutations when `--dry-run` is passed
- Safety guards: `safe_rmdir` must block root, home, and shallow paths on all platforms

### 1.2 Out of Scope & Known Gaps

- GitHub Actions CI pipeline (tracked as a separate change)
- Removal of the legacy Bash scripts (deferred until Python version is fully validated)
- GUI/TUI or binary distribution
- PyPI packaging (`setup.py` / `pyproject.toml`)
- Windows one-liner bootstrap (PowerShell path documented but not automatically tested)
- Interactive mode diff prompt (manual verification only — `input()` is hard to automate reliably)

---

## 2. References

| Document | Path |
|----------|------|
| Change spec | `doc/changes/2026-04/2026-04-30--GH-1--portable-python-install-uninstall-scripts/chg-GH-1-spec.md` |
| Implementation plan | `doc/planning/portable-install-scripts-plan.md` |
| Concept doc | `doc/planning/portable-install-scripts-concept.md` |
| Bash original — install | `scripts/install.sh` |
| Bash original — uninstall | `scripts/uninstall.sh` |

---

## 3. Coverage Overview

### 3.1 Functional Coverage (F-#, AC-#)

| AC ID | Description | TC ID(s) | Status |
|-------|-------------|----------|--------|
| AC1 | `--help` output equivalent to Bash version | TC-INST-001 | Covered |
| AC2 | `--global` performs identical operations to Bash | TC-INST-010, TC-INST-011, TC-INST-012 | Covered |
| AC3 | `--local --dry-run` shows same file operations as Bash | TC-INST-020, TC-INST-021 | Covered |
| AC4 | `--global --dry-run` (uninstall) lists same files as Bash | TC-UNINST-010, TC-UNINST-011 | Covered |
| AC5 | `safe_rmdir` blocks dangerous paths on all platforms | TC-SAFETY-001, TC-SAFETY-002, TC-SAFETY-003, TC-SAFETY-004 | Covered |
| AC6 | All tests pass on Python 3.8 and 3.12, Windows/Linux/macOS | TC-XPLAT-001, TC-XPLAT-002, TC-XPLAT-003 | Covered |
| AC7 | One-liner bootstrap works on Linux and macOS | TC-BOOT-001 | Covered |

### 3.2 Interface Coverage (API-#, EVT-#, DM-#)

The change exposes a CLI interface (not an HTTP API or event bus). The following CLI surface is covered:

| CLI Surface | Description | TC ID(s) |
|-------------|-------------|----------|
| `install.py --help` | Help text completeness | TC-INST-001 |
| `install.py --global` | Global install flow | TC-INST-010 |
| `install.py --local` | Local install flow | TC-INST-011 |
| `install.py --local --dry-run` | Dry-run no mutation | TC-INST-020 |
| `install.py --local --force` | Force overwrite | TC-FOPS-003 |
| `uninstall.py --global --dry-run` | Global dry-run list | TC-UNINST-010 |
| `uninstall.py --local` | Local uninstall flow | TC-UNINST-020 |
| `uninstall.py --force` | Skip confirmation | TC-UNINST-030 |
| `bootstrap.py` (one-liner) | Clone + global install | TC-BOOT-001 |
| Environment variable overrides | `ADOS_SOURCE_DIR`, `ADOS_HOME`, etc. | TC-GIT-003, TC-INST-012 |

### 3.3 Non-Functional Coverage (NFR-#)

| NFR | Description | TC ID(s) | Notes |
|-----|-------------|----------|-------|
| NFR-1: No external dependencies | stdlib-only import check | TC-LIB-001 | Verified by import audit |
| NFR-2: Python 3.8 compatibility | All tests run on 3.8 | TC-XPLAT-001 | Syntax check + test run |
| NFR-3: Python 3.12 compatibility | All tests run on 3.12 | TC-XPLAT-001 | Test run |
| NFR-4: Cross-platform paths | Windows / Linux / macOS path correctness | TC-PATHS-001, TC-XPLAT-002, TC-XPLAT-003 | Platform mocks + manual |
| NFR-5: Idempotency | Second install run produces zero changes | TC-INST-021 | Integration test |

---

## 4. Test Types and Layers

| Layer | Framework | Root Directory | Pattern | Notes |
|-------|-----------|----------------|---------|-------|
| **Unit** | `unittest` (stdlib) | `scripts/tests/` | `test_*.py` | Modules tested in isolation with mocked deps |
| **Integration** | `unittest` (stdlib) | `scripts/tests/` | `test_*_integration.py` | Full install/uninstall roundtrip in `tempfile.mkdtemp()` |
| **Manual / Smoke** | Human verification | N/A | — | One-liner bootstrap, interactive mode, cross-platform runs |

**Run command**: `python -m unittest discover -s scripts/tests`

No pytest, no external packages. All test helpers (tempdir fixture, mock ADOS source creator) live in `scripts/tests/__init__.py`.

---

## 5. Test Scenarios

### 5.1 Scenario Index

| TC ID | Title | Type | Impact Level | Priority | AC Coverage |
|-------|-------|------|--------------|----------|-------------|
| TC-LIB-001 | No external package imports | Edge Case | Critical | High | NFR-1 |
| TC-PATHS-001 | Platform paths resolve correctly per OS | Happy Path | Critical | High | AC6 |
| TC-PATHS-002 | Logger output matches Bash format | Happy Path | Important | Medium | AC2 |
| TC-FOPS-001 | copy_file_with_diff — new file | Happy Path | Critical | High | AC2, AC3 |
| TC-FOPS-002 | copy_file_with_diff — identical file skipped | Happy Path | Important | High | AC2, AC3 |
| TC-FOPS-003 | copy_file_with_diff — force overwrite on diff | Happy Path | Important | High | AC2 |
| TC-FOPS-004 | copy_file_with_diff — interactive mode prompt | Edge Case | Minor | Low | AC2 |
| TC-FOPS-005 | copy_file_with_diff — updatable auto-update | Happy Path | Important | Medium | AC2 |
| TC-FOPS-006 | copy_file_with_diff — project-specific preserve | Happy Path | Important | High | AC2 |
| TC-FOPS-007 | copy_file_with_diff — symlink replaced by copy | Edge Case | Minor | Medium | AC2 |
| TC-SAFETY-001 | safe_rmdir blocks root path | Negative | Critical | High | AC5 |
| TC-SAFETY-002 | safe_rmdir blocks home directory | Negative | Critical | High | AC5 |
| TC-SAFETY-003 | safe_rmdir blocks shallow path (< 3 parts) | Negative | Critical | High | AC5 |
| TC-SAFETY-004 | safe_rmdir succeeds for deep-enough safe path | Happy Path | Critical | High | AC5 |
| TC-GIT-001 | gitignore entry added when missing | Happy Path | Important | Medium | AC2 |
| TC-GIT-002 | gitignore entry skipped when already present | Edge Case | Important | Medium | AC2 |
| TC-GIT-003 | git clone for new repo | Happy Path | Important | High | AC2 |
| TC-GIT-004 | git pull for existing repo | Happy Path | Important | High | AC2 |
| TC-GIT-005 | git branch switch | Happy Path | Important | Medium | AC2 |
| TC-GIT-006 | resolve_source_dir — ADOS_SOURCE_DIR override | Happy Path | Important | High | AC2, AC3 |
| TC-GIT-007 | resolve_source_dir — script's own repo fallback | Happy Path | Important | Medium | AC2 |
| TC-INST-001 | install.py --help output | Happy Path | Important | High | AC1 |
| TC-INST-010 | install --global full roundtrip | Happy Path | Critical | High | AC2 |
| TC-INST-011 | install --local full roundtrip | Happy Path | Critical | High | AC2, AC3 |
| TC-INST-012 | install respects all env vars | Happy Path | Important | High | AC2 |
| TC-INST-020 | install --local --dry-run no mutations | Happy Path | Critical | High | AC3 |
| TC-INST-021 | install --local idempotency (second run) | Corner Case | Critical | High | AC2, AC6 |
| TC-UNINST-010 | uninstall --global --dry-run lists correct files | Happy Path | Critical | High | AC4 |
| TC-UNINST-011 | uninstall --global full roundtrip | Happy Path | Critical | High | AC4 |
| TC-UNINST-020 | uninstall --local full roundtrip | Happy Path | Critical | High | AC4 |
| TC-UNINST-030 | uninstall --force skips confirmation | Edge Case | Important | Medium | AC4 |
| TC-XPLAT-001 | All unit tests pass on Python 3.8 and 3.12 | Regression | Critical | High | AC6 |
| TC-XPLAT-002 | Windows paths with spaces handled correctly | Edge Case | Critical | High | AC6 |
| TC-XPLAT-003 | XDG_CONFIG_HOME override respected on Linux | Edge Case | Important | Medium | AC6 |
| TC-BOOT-001 | One-liner bootstrap.py clone + global install | Happy Path | Important | High | AC7 |

### 5.2 Scenario Details

---

#### TC-LIB-001 - No External Package Imports

**Scenario Type**: Edge Case
**Impact Level**: Critical
**Priority**: High
**Related IDs**: AC6, NFR-1
**Test Type(s)**: Unit
**Automation Level**: Automated
**Target Layer / Location**: `scripts/tests/test_lib_imports.py`
**Tags**: @backend

**Preconditions**:
- Python 3.8+ environment with only stdlib available

**Steps**:
1. Import each `ados_lib` module (`platform_paths`, `logger`, `manifest`, `file_ops`, `gitignore`, `safety`, `git_ops`, `cli`, `types`)
2. Import `install` and `uninstall` entry-point modules

**Expected Outcome**:
- All imports succeed without `ModuleNotFoundError`
- No `pip`-installed package is required

---

#### TC-PATHS-001 - Platform Paths Resolve Correctly per OS

**Scenario Type**: Happy Path
**Impact Level**: Critical
**Priority**: High
**Related IDs**: AC6, NFR-4
**Test Type(s)**: Unit
**Automation Level**: Automated
**Target Layer / Location**: `scripts/tests/test_platform_paths.py`
**Tags**: @backend

**Preconditions**:
- `unittest.mock.patch` available to mock `sys.platform` and `os.environ`

**Steps**:
1. Mock `sys.platform = "win32"` and `os.environ["APPDATA"] = "C:\\Users\\testuser\\AppData\\Roaming"` → call `get_opencode_global_dir()`
2. Mock `sys.platform = "linux"` and `os.environ["XDG_CONFIG_HOME"] = "/custom/config"` → call `get_opencode_global_dir()`
3. Mock `sys.platform = "darwin"` → call `get_opencode_global_dir()`
4. Verify `get_ados_home()` returns `ADOS_HOME` env var when set; falls back to `~/.ados` when unset

**Expected Outcome**:
- Windows: returns `C:\Users\testuser\AppData\Roaming\opencode`
- Linux (XDG set): returns `/custom/config/opencode`
- macOS: returns `~/.config/opencode` (expanded)
- `ADOS_HOME` override is respected

---

#### TC-PATHS-002 - Logger Output Matches Bash Format

**Scenario Type**: Happy Path
**Impact Level**: Important
**Priority**: Medium
**Related IDs**: AC2
**Test Type(s)**: Unit
**Automation Level**: Automated
**Target Layer / Location**: `scripts/tests/test_logger.py`
**Tags**: @backend

**Preconditions**:
- Logger module imported; stderr redirected to `io.StringIO`

**Steps**:
1. Call `log_info("ados-install", "some message")`
2. Call `log_warn("ados-install", "a warning")`
3. Call `log_err("ados-install", "an error")`
4. Capture output and compare format

**Expected Outcome**:
- Output matches format: `[INFO]  (ados-install) some message`
- Warn uses `[WARN] `, error uses `[ERR]  `
- Format is identical to Bash output (field widths, tag in parentheses)

---

#### TC-FOPS-001 - copy_file_with_diff — New File

**Scenario Type**: Happy Path
**Impact Level**: Critical
**Priority**: High
**Related IDs**: AC2, AC3
**Test Type(s)**: Unit
**Automation Level**: Automated
**Target Layer / Location**: `scripts/tests/test_file_ops.py`
**Tags**: @backend

**Preconditions**:
- Temporary directory created via `tempfile.mkdtemp()`
- Source file exists; destination does not

**Steps**:
1. Call `copy_file_with_diff(src, dest, label, config, counters)` where dest does not exist

**Expected Outcome**:
- Destination file is created with identical content to source
- `counters.added` is incremented by 1

---

#### TC-FOPS-002 - copy_file_with_diff — Identical File Skipped

**Scenario Type**: Happy Path
**Impact Level**: Important
**Priority**: High
**Related IDs**: AC2, AC3
**Test Type(s)**: Unit
**Automation Level**: Automated
**Target Layer / Location**: `scripts/tests/test_file_ops.py`
**Tags**: @backend

**Preconditions**:
- Source and destination files exist with identical content

**Steps**:
1. Call `copy_file_with_diff(src, dest, label, config, counters)`

**Expected Outcome**:
- Destination file is not modified (mtime unchanged or content identical)
- `counters.unchanged` is incremented; `counters.updated` is not

---

#### TC-FOPS-003 - copy_file_with_diff — Force Overwrite on Diff

**Scenario Type**: Happy Path
**Impact Level**: Important
**Priority**: High
**Related IDs**: AC2
**Test Type(s)**: Unit
**Automation Level**: Automated
**Target Layer / Location**: `scripts/tests/test_file_ops.py`
**Tags**: @backend

**Preconditions**:
- Source and destination differ; `config.force = True`

**Steps**:
1. Call `copy_file_with_diff(src, dest, label, config, counters)` with force mode

**Expected Outcome**:
- Destination is overwritten with source content
- `counters.updated` incremented

---

#### TC-FOPS-004 - copy_file_with_diff — Interactive Mode Prompt

**Scenario Type**: Edge Case
**Impact Level**: Minor
**Priority**: Low
**Related IDs**: AC2
**Test Type(s)**: Unit
**Automation Level**: Semi-automated
**Target Layer / Location**: `scripts/tests/test_file_ops.py`
**Tags**: @backend

**Preconditions**:
- Source and destination differ; `config.interactive = True`
- `builtins.input` mocked to return `"y"` then `"n"`

**Steps**:
1. Mock `input()` to return `"y"` → call `copy_file_with_diff(...)`; verify file is updated
2. Mock `input()` to return `"n"` → call `copy_file_with_diff(...)`; verify file is NOT updated

**Expected Outcome**:
- With `"y"`: destination overwritten; `counters.updated` incremented
- With `"n"`: destination preserved; `counters.unchanged` incremented

---

#### TC-FOPS-005 - copy_file_with_diff — Updatable Auto-Update

**Scenario Type**: Happy Path
**Impact Level**: Important
**Priority**: Medium
**Related IDs**: AC2
**Test Type(s)**: Unit
**Automation Level**: Automated
**Target Layer / Location**: `scripts/tests/test_file_ops.py`
**Tags**: @backend

**Preconditions**:
- Source and destination differ; file is in updatable list; `config.force = False`, `config.interactive = False`

**Steps**:
1. Call `copy_updatable_file(src, dest, label, config, counters)`

**Expected Outcome**:
- Destination automatically updated without prompt
- `counters.updated` incremented

---

#### TC-FOPS-006 - copy_file_with_diff — Project-Specific Preserve

**Scenario Type**: Happy Path
**Impact Level**: Important
**Priority**: High
**Related IDs**: AC2
**Test Type(s)**: Unit
**Automation Level**: Automated
**Target Layer / Location**: `scripts/tests/test_file_ops.py`
**Tags**: @backend

**Preconditions**:
- Source and destination differ; file is a project-specific file (not in updatable list); no `--force`

**Steps**:
1. Call `copy_file_with_diff(src, dest, label, config, counters)` in default (non-force, non-interactive) mode

**Expected Outcome**:
- Destination is NOT overwritten; local modifications preserved
- A warning or skip message is logged

---

#### TC-FOPS-007 - copy_file_with_diff — Symlink Replaced by Copy

**Scenario Type**: Edge Case
**Impact Level**: Minor
**Priority**: Medium
**Related IDs**: AC2
**Test Type(s)**: Unit
**Automation Level**: Automated
**Target Layer / Location**: `scripts/tests/test_file_ops.py`
**Tags**: @backend

**Preconditions**:
- Unix-like platform (test is skipped on Windows)
- Destination is a symlink pointing to another file

**Steps**:
1. Create a symlink at the destination path
2. Call `copy_file_with_diff(src, dest, label, config, counters)`

**Expected Outcome**:
- Symlink is replaced with a regular file copy
- `Path(dest).is_symlink()` returns `False` after operation

---

#### TC-SAFETY-001 - safe_rmdir Blocks Root Path

**Scenario Type**: Negative
**Impact Level**: Critical
**Priority**: High
**Related IDs**: AC5
**Test Type(s)**: Unit
**Automation Level**: Automated
**Target Layer / Location**: `scripts/tests/test_safety.py`
**Tags**: @backend

**Preconditions**:
- `safe_rmdir` imported from `ados_lib.safety`

**Steps**:
1. Call `safe_rmdir("/", label, config)` (Unix) or `safe_rmdir("C:\\", label, config)` (Windows)

**Expected Outcome**:
- Raises `RuntimeError` or `SystemExit` with a clear error message
- No filesystem mutation occurs

---

#### TC-SAFETY-002 - safe_rmdir Blocks Home Directory

**Scenario Type**: Negative
**Impact Level**: Critical
**Priority**: High
**Related IDs**: AC5
**Test Type(s)**: Unit
**Automation Level**: Automated
**Target Layer / Location**: `scripts/tests/test_safety.py`
**Tags**: @backend

**Preconditions**:
- `Path.home()` is mockable or a real home path is used

**Steps**:
1. Call `safe_rmdir(str(Path.home()), label, config)`

**Expected Outcome**:
- Raises `RuntimeError` or `SystemExit`
- Home directory is not deleted

---

#### TC-SAFETY-003 - safe_rmdir Blocks Shallow Path

**Scenario Type**: Negative
**Impact Level**: Critical
**Priority**: High
**Related IDs**: AC5
**Test Type(s)**: Unit
**Automation Level**: Automated
**Target Layer / Location**: `scripts/tests/test_safety.py`
**Tags**: @backend

**Preconditions**:
- A path with fewer than 3 resolved parts (e.g., `/tmp` on Linux, `C:\foo` on Windows)

**Steps**:
1. Call `safe_rmdir("/tmp", label, config)` (2 parts on Linux)
2. Call `safe_rmdir("C:\\foo", label, config)` (2 parts on Windows)

**Expected Outcome**:
- Both calls raise `RuntimeError` or `SystemExit`

---

#### TC-SAFETY-004 - safe_rmdir Succeeds for Safe Deep Path

**Scenario Type**: Happy Path
**Impact Level**: Critical
**Priority**: High
**Related IDs**: AC5
**Test Type(s)**: Unit
**Automation Level**: Automated
**Target Layer / Location**: `scripts/tests/test_safety.py`
**Tags**: @backend

**Preconditions**:
- Temporary directory with depth ≥ 3 (e.g., `/tmp/ados-test/subdir/`)

**Steps**:
1. Create the directory via `tempfile.mkdtemp()` nested two levels deep
2. Call `safe_rmdir(path, label, config)` in non-dry-run mode

**Expected Outcome**:
- Directory is removed without error
- `Path(path).exists()` returns `False`

---

#### TC-GIT-001 - gitignore Entry Added When Missing

**Scenario Type**: Happy Path
**Impact Level**: Important
**Priority**: Medium
**Related IDs**: AC2
**Test Type(s)**: Unit
**Automation Level**: Automated
**Target Layer / Location**: `scripts/tests/test_gitignore.py`
**Tags**: @backend

**Preconditions**:
- Temporary `.gitignore` file that does not contain the target entry

**Steps**:
1. Call `ensure_gitignore_entry(gitignore_path, ".ai/local/", config)`

**Expected Outcome**:
- `.ai/local/` is appended to the `.gitignore` file
- File is not otherwise modified

---

#### TC-GIT-002 - gitignore Entry Skipped When Already Present

**Scenario Type**: Edge Case
**Impact Level**: Important
**Priority**: Medium
**Related IDs**: AC2
**Test Type(s)**: Unit
**Automation Level**: Automated
**Target Layer / Location**: `scripts/tests/test_gitignore.py`
**Tags**: @backend

**Preconditions**:
- `.gitignore` already contains the target entry

**Steps**:
1. Call `ensure_gitignore_entry(gitignore_path, ".ai/local/", config)` again

**Expected Outcome**:
- No duplicate entry is added
- File content is identical before and after

---

#### TC-GIT-003 - Git Clone for New Repo

**Scenario Type**: Happy Path
**Impact Level**: Important
**Priority**: High
**Related IDs**: AC2
**Test Type(s)**: Unit
**Automation Level**: Automated
**Target Layer / Location**: `scripts/tests/test_git_ops.py`
**Tags**: @backend

**Preconditions**:
- `subprocess.run` mocked to simulate successful `git clone`
- Target directory does not contain a `.git` folder

**Steps**:
1. Call `clone_or_update_repo(config)` where `ADOS_REPO_DIR` does not have `.git`

**Expected Outcome**:
- `subprocess.run` called with `["git", "clone", ...]` — no `shell=True`
- Clone command includes correct URL and destination path

---

#### TC-GIT-004 - Git Pull for Existing Repo

**Scenario Type**: Happy Path
**Impact Level**: Important
**Priority**: High
**Related IDs**: AC2
**Test Type(s)**: Unit
**Automation Level**: Automated
**Target Layer / Location**: `scripts/tests/test_git_ops.py`
**Tags**: @backend

**Preconditions**:
- `subprocess.run` mocked; `.git` folder exists in `ADOS_REPO_DIR`

**Steps**:
1. Call `clone_or_update_repo(config)` where `.git` is present

**Expected Outcome**:
- `git pull --ff-only` is invoked (not `git clone`)
- No `shell=True` in any subprocess call

---

#### TC-GIT-005 - Git Branch Switch

**Scenario Type**: Happy Path
**Impact Level**: Important
**Priority**: Medium
**Related IDs**: AC2
**Test Type(s)**: Unit
**Automation Level**: Automated
**Target Layer / Location**: `scripts/tests/test_git_ops.py`
**Tags**: @backend

**Preconditions**:
- `subprocess.run` mocked; `config.branch` set to a non-default branch name

**Steps**:
1. Call `clone_or_update_repo(config)` with `config.branch = "my-feature"`

**Expected Outcome**:
- `git fetch` followed by `git checkout my-feature` are invoked in order

---

#### TC-GIT-006 - resolve_source_dir ADOS_SOURCE_DIR Override

**Scenario Type**: Happy Path
**Impact Level**: Important
**Priority**: High
**Related IDs**: AC2, AC3
**Test Type(s)**: Unit
**Automation Level**: Automated
**Target Layer / Location**: `scripts/tests/test_git_ops.py`
**Tags**: @backend

**Preconditions**:
- `os.environ["ADOS_SOURCE_DIR"]` set to a valid temp directory

**Steps**:
1. Call `resolve_source_dir(config)`

**Expected Outcome**:
- Returns the path from `ADOS_SOURCE_DIR` (priority 1)
- Does not fall back to script repo or global repo

---

#### TC-GIT-007 - resolve_source_dir Script's Own Repo Fallback

**Scenario Type**: Happy Path
**Impact Level**: Important
**Priority**: Medium
**Related IDs**: AC2
**Test Type(s)**: Unit
**Automation Level**: Automated
**Target Layer / Location**: `scripts/tests/test_git_ops.py`
**Tags**: @backend

**Preconditions**:
- `ADOS_SOURCE_DIR` not set; script runs from within its own git repo (`.git` present two levels up)

**Steps**:
1. Call `resolve_source_dir(config)` without `ADOS_SOURCE_DIR` env var

**Expected Outcome**:
- Returns `Path(__file__).resolve().parent.parent` (the script's own repo root)

---

#### TC-INST-001 - install.py --help Output

**Scenario Type**: Happy Path
**Impact Level**: Important
**Priority**: High
**Related IDs**: AC1
**Test Type(s)**: Unit
**Automation Level**: Automated
**Target Layer / Location**: `scripts/tests/test_cli.py`
**Tags**: @backend

**Preconditions**:
- `scripts/install.py` is importable; `argparse` parser accessible

**Steps**:
1. Call `parse_install_args(["--help"])` inside a `try/except SystemExit` block (argparse exits on `--help`)
2. Capture the help text printed to stdout

**Expected Outcome**:
- Help text includes all flags: `--global`, `--local`, `--branch`, `--dry-run`, `--verbose`, `--force`, `--interactive`, `--no-fetch`, `--allow-non-root`, `--version`
- Flag descriptions are equivalent in meaning to the Bash `--help` output

---

#### TC-INST-010 - install --global Full Roundtrip

**Scenario Type**: Happy Path
**Impact Level**: Critical
**Priority**: High
**Related IDs**: AC2
**Test Type(s)**: Integration
**Automation Level**: Automated
**Target Layer / Location**: `scripts/tests/test_install_global.py`
**Tags**: @backend

**Preconditions**:
- `subprocess.run` mocked to simulate successful git clone
- Temporary directory used as `ADOS_HOME` and `OPENCODE_GLOBAL_DIR`
- Mock ADOS source with `.opencode/agent/*.md` and `.opencode/command/*.md` files

**Steps**:
1. Set `ADOS_SOURCE_DIR` to the mock source directory
2. Call `main(["--global", "--no-fetch"])` from `install`

**Expected Outcome**:
- All agent and command `.md` files are copied to the mock `OPENCODE_GLOBAL_DIR`
- Summary line reports correct `added` count
- Exit code is `0`

---

#### TC-INST-011 - install --local Full Roundtrip

**Scenario Type**: Happy Path
**Impact Level**: Critical
**Priority**: High
**Related IDs**: AC2, AC3
**Test Type(s)**: Integration
**Automation Level**: Automated
**Target Layer / Location**: `scripts/tests/test_install_local.py`
**Tags**: @backend

**Preconditions**:
- Temporary project directory initialised as a git repo (`git init`)
- Mock ADOS source with all expected file categories (project files, updatable files, templates, dir stubs)
- `ADOS_SOURCE_DIR` pointing at mock source

**Steps**:
1. Call `main(["--local", "--no-fetch"])` from `install` with CWD set to temp project dir

**Expected Outcome**:
- All expected files are present in temp project dir after install
- `.gitignore` contains the expected entries
- Directory stubs created
- Summary reports correct `added`/`unchanged`/`updated` counts
- Exit code is `0`

---

#### TC-INST-012 - install Respects All Environment Variables

**Scenario Type**: Happy Path
**Impact Level**: Important
**Priority**: High
**Related IDs**: AC2
**Test Type(s)**: Unit
**Automation Level**: Automated
**Target Layer / Location**: `scripts/tests/test_install_local.py`
**Tags**: @backend

**Preconditions**:
- Env vars set: `ADOS_HOME`, `ADOS_REPO_DIR`, `OPENCODE_GLOBAL_DIR`, `ADOS_SOURCE_DIR`, `DRY_RUN=1`, `VERBOSE=1`

**Steps**:
1. Parse config with those env vars set
2. Verify each config field reflects the env var value

**Expected Outcome**:
- `config.dry_run = True`, `config.verbose = True`
- `get_ados_home()` returns the value of `ADOS_HOME`
- `get_ados_repo_dir()` returns the value of `ADOS_REPO_DIR`

---

#### TC-INST-020 - install --local --dry-run No Mutations

**Scenario Type**: Happy Path
**Impact Level**: Critical
**Priority**: High
**Related IDs**: AC3
**Test Type(s)**: Integration
**Automation Level**: Automated
**Target Layer / Location**: `scripts/tests/test_install_local.py`
**Tags**: @backend

**Preconditions**:
- Clean temporary project directory (no ADOS files yet)
- `ADOS_SOURCE_DIR` pointing at mock source

**Steps**:
1. Call `main(["--local", "--dry-run", "--no-fetch"])`
2. Check filesystem state after call

**Expected Outcome**:
- No files are created or modified in the project directory
- Log output lists the files that **would** be installed
- Exit code is `0`

---

#### TC-INST-021 - install --local Idempotency (Second Run)

**Scenario Type**: Corner Case
**Impact Level**: Critical
**Priority**: High
**Related IDs**: AC2, AC6
**Test Type(s)**: Integration
**Automation Level**: Automated
**Target Layer / Location**: `scripts/tests/test_install_local.py`
**Tags**: @backend

**Preconditions**:
- First `install --local --no-fetch` has already completed successfully

**Steps**:
1. Run `main(["--local", "--no-fetch"])` a second time (no changes to source)
2. Capture counters

**Expected Outcome**:
- `counters.added = 0`, `counters.updated = 0`
- `counters.unchanged` equals the total number of managed files
- No files are modified; exit code is `0`

---

#### TC-UNINST-010 - uninstall --global --dry-run Lists Correct Files

**Scenario Type**: Happy Path
**Impact Level**: Critical
**Priority**: High
**Related IDs**: AC4
**Test Type(s)**: Integration
**Automation Level**: Automated
**Target Layer / Location**: `scripts/tests/test_uninstall_global.py`
**Tags**: @backend

**Preconditions**:
- Mock `OPENCODE_GLOBAL_DIR` populated with agent and command `.md` files
- Mock `ADOS_HOME` directory exists

**Steps**:
1. Call `main(["--global", "--dry-run"])` from `uninstall`
2. Capture log output

**Expected Outcome**:
- Log lists every agent and command file under `OPENCODE_GLOBAL_DIR`
- Log lists `ADOS_HOME` as target for removal
- No files are actually deleted; exit code is `0`

---

#### TC-UNINST-011 - uninstall --global Full Roundtrip

**Scenario Type**: Happy Path
**Impact Level**: Critical
**Priority**: High
**Related IDs**: AC4, AC5
**Test Type(s)**: Integration
**Automation Level**: Automated
**Target Layer / Location**: `scripts/tests/test_uninstall_global.py`
**Tags**: @backend

**Preconditions**:
- Mock `OPENCODE_GLOBAL_DIR` with agent/command files; mock `ADOS_HOME`
- `config.force = True` (skip confirmation prompt in test)

**Steps**:
1. Call `main(["--global", "--force"])` from `uninstall`

**Expected Outcome**:
- All agent/command files removed from `OPENCODE_GLOBAL_DIR`
- `ADOS_HOME` directory removed
- `counters.removed` reflects correct file count
- Exit code is `0`

---

#### TC-UNINST-020 - uninstall --local Full Roundtrip

**Scenario Type**: Happy Path
**Impact Level**: Critical
**Priority**: High
**Related IDs**: AC4
**Test Type(s)**: Integration
**Automation Level**: Automated
**Target Layer / Location**: `scripts/tests/test_uninstall_local.py`
**Tags**: @backend

**Preconditions**:
- Temporary project directory with a full local ADOS installation (produced by TC-INST-011)
- `config.force = True`

**Steps**:
1. Call `main(["--local", "--force"])` from `uninstall`

**Expected Outcome**:
- All ADOS-managed files removed from project directory
- Empty ADOS directories removed
- Non-ADOS project files remain untouched
- Exit code is `0`

---

#### TC-UNINST-030 - uninstall --force Skips Confirmation

**Scenario Type**: Edge Case
**Impact Level**: Important
**Priority**: Medium
**Related IDs**: AC4
**Test Type(s)**: Unit
**Automation Level**: Automated
**Target Layer / Location**: `scripts/tests/test_uninstall_global.py`
**Tags**: @backend

**Preconditions**:
- `builtins.input` NOT mocked (any call to it would raise an error in test context)

**Steps**:
1. Call `confirm_action("Are you sure?", config)` with `config.force = True`

**Expected Outcome**:
- Returns `True` immediately without calling `input()`

---

#### TC-XPLAT-001 - All Unit Tests Pass on Python 3.8 and 3.12

**Scenario Type**: Regression
**Impact Level**: Critical
**Priority**: High
**Related IDs**: AC6
**Test Type(s)**: Unit, Integration
**Automation Level**: Manual
**Target Layer / Location**: `scripts/tests/`
**Tags**: @backend

**Preconditions**:
- Python 3.8 and Python 3.12 installed locally or in tox/pyenv

**Steps**:
1. Run `python3.8 -m unittest discover -s scripts/tests`
2. Run `python3.12 -m unittest discover -s scripts/tests`
3. Repeat on Linux, macOS, and Windows

**Expected Outcome**:
- All tests pass (`OK`) on both Python versions on all three platforms
- No `SyntaxError` or `AttributeError` related to version differences

---

#### TC-XPLAT-002 - Windows Paths with Spaces Handled Correctly

**Scenario Type**: Edge Case
**Impact Level**: Critical
**Priority**: High
**Related IDs**: AC6
**Test Type(s)**: Unit
**Automation Level**: Automated
**Target Layer / Location**: `scripts/tests/test_platform_paths.py`
**Tags**: @backend

**Preconditions**:
- `os.environ["APPDATA"]` mocked to `C:\Users\John Doe\AppData\Roaming` (path contains space)

**Steps**:
1. Call `get_opencode_global_dir()` with the mocked env var
2. Call `copy_file_with_diff(src, dest, ...)` where dest is under the path-with-space directory

**Expected Outcome**:
- Path resolved correctly using `pathlib.Path` — no string splitting or shell interpolation errors
- File copy succeeds without `FileNotFoundError`

---

#### TC-XPLAT-003 - XDG_CONFIG_HOME Override Respected on Linux

**Scenario Type**: Edge Case
**Impact Level**: Important
**Priority**: Medium
**Related IDs**: AC6
**Test Type(s)**: Unit
**Automation Level**: Automated
**Target Layer / Location**: `scripts/tests/test_platform_paths.py`
**Tags**: @backend

**Preconditions**:
- `sys.platform` mocked to `"linux"`
- `os.environ["XDG_CONFIG_HOME"]` set to a custom temp path

**Steps**:
1. Call `get_opencode_global_dir()`

**Expected Outcome**:
- Returns `XDG_CONFIG_HOME/opencode` (uses override, not `~/.config`)

---

#### TC-BOOT-001 - One-Liner bootstrap.py Clone and Global Install

**Scenario Type**: Happy Path
**Impact Level**: Important
**Priority**: High
**Related IDs**: AC7
**Test Type(s)**: Manual
**Automation Level**: Manual
**Target Layer / Location**: `scripts/bootstrap.py`
**Tags**: @backend

**Preconditions**:
- Linux or macOS system with Python 3.8+ and `git` installed
- No existing `~/.ados` directory

**Steps**:
1. Run: `curl -fsSL https://raw.githubusercontent.com/.../scripts/bootstrap.py | python3 -`
2. Observe output and check filesystem

**Expected Outcome**:
- `~/.ados/repo` is cloned from the ADOS GitHub repo
- Global agent and command files installed to `~/.config/opencode/` (or XDG path)
- Exit code is `0`; no error messages

**Notes / Clarifications**:
- Windows one-liner is documented but not automatically tested (PowerShell `irm | python`)
- This scenario must be verified manually before the change is merged

---

## 6. Environments and Test Data

### Environments

| Environment | Purpose | How to Obtain |
|-------------|---------|---------------|
| Local dev (Linux/macOS) | Primary development and unit test execution | Developer machine |
| Local dev (Windows) | Windows-specific path testing | Windows VM or native machine |
| Python 3.8 | Minimum version compatibility | `pyenv install 3.8.x` or system package |
| Python 3.12 | Latest stable compatibility | `pyenv install 3.12.x` or system package |

### Test Data Strategy

- All integration tests use `tempfile.mkdtemp()` for isolated directories — no global filesystem state shared between tests
- A helper function in `scripts/tests/__init__.py` creates a mock ADOS source tree (`make_mock_ados_source(root)`) with the expected directory structure and placeholder `.md` files
- Git operations are mocked via `unittest.mock.patch("subprocess.run")` — no network access required for unit/integration tests
- Tests clean up temp directories in `tearDown()` via `shutil.rmtree(self.tmpdir, ignore_errors=True)`

### Isolation Strategy

- Each test class creates and destroys its own temp directory
- Environment variables modified in tests are patched with `unittest.mock.patch.dict(os.environ, {...}, clear=False)` to prevent leakage between tests

---

## 7. Automation Plan and Implementation Mapping

| TC ID | Test File | Execution Command | Mocking Requirements | Status |
|-------|-----------|-------------------|----------------------|--------|
| TC-LIB-001 | `scripts/tests/test_lib_imports.py` | `python -m unittest scripts.tests.test_lib_imports` | None | To Implement |
| TC-PATHS-001 | `scripts/tests/test_platform_paths.py` | `python -m unittest discover -s scripts/tests` | `sys.platform`, `os.environ` | To Implement |
| TC-PATHS-002 | `scripts/tests/test_logger.py` | `python -m unittest discover -s scripts/tests` | `sys.stderr` redirect | To Implement |
| TC-FOPS-001 | `scripts/tests/test_file_ops.py` | `python -m unittest discover -s scripts/tests` | `tempfile` | To Implement |
| TC-FOPS-002 | `scripts/tests/test_file_ops.py` | `python -m unittest discover -s scripts/tests` | `tempfile` | To Implement |
| TC-FOPS-003 | `scripts/tests/test_file_ops.py` | `python -m unittest discover -s scripts/tests` | `tempfile` | To Implement |
| TC-FOPS-004 | `scripts/tests/test_file_ops.py` | `python -m unittest discover -s scripts/tests` | `builtins.input` | To Implement |
| TC-FOPS-005 | `scripts/tests/test_file_ops.py` | `python -m unittest discover -s scripts/tests` | `tempfile` | To Implement |
| TC-FOPS-006 | `scripts/tests/test_file_ops.py` | `python -m unittest discover -s scripts/tests` | `tempfile` | To Implement |
| TC-FOPS-007 | `scripts/tests/test_file_ops.py` | `python -m unittest discover -s scripts/tests` | `tempfile` (Unix skip on Windows) | To Implement |
| TC-SAFETY-001 | `scripts/tests/test_safety.py` | `python -m unittest discover -s scripts/tests` | None | To Implement |
| TC-SAFETY-002 | `scripts/tests/test_safety.py` | `python -m unittest discover -s scripts/tests` | `Path.home` (optional mock) | To Implement |
| TC-SAFETY-003 | `scripts/tests/test_safety.py` | `python -m unittest discover -s scripts/tests` | None | To Implement |
| TC-SAFETY-004 | `scripts/tests/test_safety.py` | `python -m unittest discover -s scripts/tests` | `tempfile` | To Implement |
| TC-GIT-001 | `scripts/tests/test_gitignore.py` | `python -m unittest discover -s scripts/tests` | `tempfile` | To Implement |
| TC-GIT-002 | `scripts/tests/test_gitignore.py` | `python -m unittest discover -s scripts/tests` | `tempfile` | To Implement |
| TC-GIT-003 | `scripts/tests/test_git_ops.py` | `python -m unittest discover -s scripts/tests` | `subprocess.run` | To Implement |
| TC-GIT-004 | `scripts/tests/test_git_ops.py` | `python -m unittest discover -s scripts/tests` | `subprocess.run` | To Implement |
| TC-GIT-005 | `scripts/tests/test_git_ops.py` | `python -m unittest discover -s scripts/tests` | `subprocess.run` | To Implement |
| TC-GIT-006 | `scripts/tests/test_git_ops.py` | `python -m unittest discover -s scripts/tests` | `os.environ` | To Implement |
| TC-GIT-007 | `scripts/tests/test_git_ops.py` | `python -m unittest discover -s scripts/tests` | `tempfile`, `Path.__file__` | To Implement |
| TC-INST-001 | `scripts/tests/test_cli.py` | `python -m unittest discover -s scripts/tests` | `sys.stdout` capture | To Implement |
| TC-INST-010 | `scripts/tests/test_install_global.py` | `python -m unittest discover -s scripts/tests` | `subprocess.run`, `tempfile`, `os.environ` | To Implement |
| TC-INST-011 | `scripts/tests/test_install_local.py` | `python -m unittest discover -s scripts/tests` | `tempfile`, `os.environ`, `git init` | To Implement |
| TC-INST-012 | `scripts/tests/test_install_local.py` | `python -m unittest discover -s scripts/tests` | `os.environ` | To Implement |
| TC-INST-020 | `scripts/tests/test_install_local.py` | `python -m unittest discover -s scripts/tests` | `tempfile`, `os.environ` | To Implement |
| TC-INST-021 | `scripts/tests/test_install_local.py` | `python -m unittest discover -s scripts/tests` | `tempfile`, `os.environ` | To Implement |
| TC-UNINST-010 | `scripts/tests/test_uninstall_global.py` | `python -m unittest discover -s scripts/tests` | `tempfile`, `os.environ` | To Implement |
| TC-UNINST-011 | `scripts/tests/test_uninstall_global.py` | `python -m unittest discover -s scripts/tests` | `tempfile`, `os.environ` | To Implement |
| TC-UNINST-020 | `scripts/tests/test_uninstall_local.py` | `python -m unittest discover -s scripts/tests` | `tempfile`, `os.environ` | To Implement |
| TC-UNINST-030 | `scripts/tests/test_uninstall_global.py` | `python -m unittest discover -s scripts/tests` | `builtins.input` guarded | To Implement |
| TC-XPLAT-001 | All test files | `python3.8 -m unittest discover -s scripts/tests` + `python3.12 ...` | None additional | Manual Only |
| TC-XPLAT-002 | `scripts/tests/test_platform_paths.py` | `python -m unittest discover -s scripts/tests` | `os.environ["APPDATA"]`, `sys.platform` | To Implement |
| TC-XPLAT-003 | `scripts/tests/test_platform_paths.py` | `python -m unittest discover -s scripts/tests` | `os.environ["XDG_CONFIG_HOME"]`, `sys.platform` | To Implement |
| TC-BOOT-001 | N/A | Manual execution on Linux/macOS terminal | None — live network + git | Manual Only |

---

## 8. Risks, Assumptions, and Open Questions

### 8.1 Risks

| Risk | Likelihood | Impact | Mitigation |
|------|------------|--------|-----------|
| `python` vs `python3` alias differences on Windows | Medium | High | Document `py -3` for Windows; shebang `#!/usr/bin/env python3` for Unix |
| Windows paths with spaces or Unicode chars break file ops | Medium | High | Use `pathlib.Path` exclusively; test TC-XPLAT-002 |
| Behavioral divergence from Bash discovered late | Medium | High | Run Bash + Python scripts side-by-side on same input in integration tests |
| `subprocess.run` encoding issues on Windows (non-UTF8 console) | Low | Medium | Pass `encoding="utf-8", errors="replace"` always |
| `symlink` tests fail on Windows (restricted by default) | Medium | Low | Skip TC-FOPS-007 on Windows via `@unittest.skipIf(sys.platform == "win32", ...)` |
| No CI yet — cross-platform tests rely on manual execution | High | Medium | Enforce manual sign-off checklist before merge (TC-XPLAT-001, TC-BOOT-001) |

### 8.2 Assumptions

- Python 3.8+ is available on all target machines (documented as a prerequisite)
- `git` CLI is installed and on `PATH`
- The Bash originals (`install.sh`, `uninstall.sh`) serve as the reference implementation; any divergence found during testing is a bug in the Python version
- Tests run in isolation — no test mutates global filesystem or env vars permanently
- Interactive mode (`--interactive`) is considered low-risk and covered only by semi-automated mock tests; full end-to-end interactive testing is manual

### 8.3 Open Questions

| # | Question | Blocking? | Owner |
|---|----------|-----------|-------|
| 1 | What is the exact list of files in `UPDATABLE_FILES`, `PROJECT_FILES`, `AGENT_FILES`, `COMMAND_FILES` in the manifest? Integration tests need this to assert correct file counts. | Yes | `@coder` — derive from `install.sh` manifest section |
| 2 | Should TC-XPLAT-001 (multi-version/multi-platform) be gated as a DoD requirement before PR merge, or is it best-effort for the initial PR? | Yes | `@pm` to decide |
| 3 | `testing-strategy.md` was not found at `.ai/rules/testing-strategy.md`. If a strategy file is created later, this test plan should be reconciled against it. | No | `@toolsmith` |

---

## 9. Plan Revision Log

| Version | Date | Author | Changes |
|---------|------|--------|---------|
| 1.0 | 2026-04-30 | test-plan-writer | Initial test plan; 35 scenarios mapped to AC1–AC7; derived from planning doc T1–T30 and change summary |

---

## 10. Test Execution Log

| TC ID | Run Date | Result | Notes |
|-------|----------|--------|-------|
| — | — | — | Not yet executed |
