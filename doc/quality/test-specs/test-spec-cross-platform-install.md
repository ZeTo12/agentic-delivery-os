---
# Copyright (c) 2025-2026 Juliusz Ćwiąkalski (https://www.cwiakalski.com | https://www.linkedin.com/in/juliusz-cwiakalski/ | https://x.com/cwiakalski)
# MIT License - see LICENSE file for full terms
source: https://github.com/juliusz-cwiakalski/agentic-delivery-os/blob/main/doc/quality/test-specs/test-spec-cross-platform-install.md

id: TEST-SPEC-CROSS-PLATFORM-INSTALL
status: Current
created: 2026-04-30
last_updated: 2026-04-30
owners: [ados-core]
service: scripts
links:
  related_changes: ["GH-1"]
  feature_spec: doc/spec/features/feature-cross-platform-install.md
---

# Test Specification: Cross-Platform Install / Uninstall Scripts

## Overview

This test specification covers the Python 3 install/uninstall scripts (`scripts/install.py`, `scripts/uninstall.py`), the shared library (`scripts/ados_lib/`), and the one-liner bootstrap (`scripts/bootstrap.py`). The primary testing concern is behavioural parity with the Bash originals on Windows, Linux, and macOS. Secondary concerns are safety (path guards), idempotency, and dry-run correctness.

All automated tests use Python's stdlib `unittest` framework with no external dependencies. The complete test suite is run with:

```
python -m unittest discover -s scripts/tests
```

## Test Scope

**In scope:**
- `scripts/ados_lib/` — all 9 modules: `platform_paths`, `logger`, `manifest`, `file_ops`, `gitignore`, `safety`, `git_ops`, `cli`, `types`
- `scripts/install.py` — global and local flows, all CLI flags, environment variable overrides
- `scripts/uninstall.py` — global and local flows, confirmation prompts, `safe_rmdir`
- `scripts/bootstrap.py` — one-liner clone + global install
- Cross-platform path correctness (Windows `%APPDATA%`, Linux XDG, macOS `~/.config`)
- Python version compatibility: CPython 3.8 and 3.12
- Idempotency: second install run produces zero changes
- Dry-run atomicity: no filesystem mutations with `--dry-run`
- Safety guards: `safe_rmdir` blocking root, home, and shallow paths

**Out of scope / known gaps:**
- GitHub Actions CI pipeline (separate work item)
- Interactive mode diff prompt — covered by semi-automated mock only (`input()` hard to automate end-to-end)
- Windows PowerShell one-liner bootstrap — documented but not automatically tested
- Removal of Bash scripts (deferred)

## Test Levels

### Unit Tests

- **Purpose:** Validate each `ados_lib` module in isolation.
- **Tools:** `unittest`, `unittest.mock` — stdlib only.
- **Coverage:** All 9 library modules have dedicated test files.
- **Location:** `scripts/tests/test_platform_paths.py`, `test_logger.py`, `test_file_ops.py`, `test_gitignore.py`, `test_safety.py`, `test_git_ops.py`, `test_cli.py`, `test_lib_imports.py`

### Integration Tests

- **Purpose:** Validate full install and uninstall roundtrips against a mock ADOS source tree.
- **Tools:** `unittest`, `tempfile.mkdtemp()`, `unittest.mock.patch("subprocess.run")`.
- **Location:** `scripts/tests/test_install_global.py`, `test_install_local.py`, `test_uninstall_global.py`, `test_uninstall_local.py`
- **Key scenarios:** global install roundtrip, local install roundtrip, dry-run no-mutation, idempotency, global uninstall roundtrip, local uninstall roundtrip.

### Manual / Smoke Tests

- **Purpose:** Validate one-liner bootstrap on a live system; cross-platform Python 3.8 / 3.12 matrix.
- **Tools:** Human verification on Linux, macOS, and Windows machines.
- **Required before merge:** TC-BOOT-001 (Linux/macOS one-liner) and TC-XPLAT-001 (multi-version run).

## Test Data

- Integration tests use `tempfile.mkdtemp()` — isolated per test, no shared global state.
- `scripts/tests/__init__.py` provides `make_mock_ados_source(root)` to create a minimal ADOS source tree with placeholder `.md` files for all expected file categories.
- Git operations are mocked via `unittest.mock.patch("subprocess.run")` — no network access required for automated tests.
- Environment variables modified in tests use `unittest.mock.patch.dict(os.environ, {...}, clear=False)` to prevent leakage.
- `tearDown()` removes temp directories via `shutil.rmtree(self.tmpdir, ignore_errors=True)`.

## Test Scenarios

### Scenario: No external package imports (TC-LIB-001)

- **Given:** Python 3.8+ environment with only stdlib available.
- **When:** Each `ados_lib` module is imported, along with `install` and `uninstall`.
- **Then:** All imports succeed without `ModuleNotFoundError`; no `pip`-installed package is required.

---

### Scenario: Platform paths resolve correctly per OS (TC-PATHS-001)

- **Given:** `sys.platform` and relevant env vars are mocked for Windows, Linux (with XDG), and macOS.
- **When:** `get_opencode_global_dir()` and `get_ados_home()` are called.
- **Then:**
  - Windows: `%APPDATA%\opencode`
  - Linux (XDG set): `$XDG_CONFIG_HOME/opencode`
  - macOS: `~/.config/opencode`
  - `ADOS_HOME` env override is respected over the default.

---

### Scenario: Logger output matches Bash format (TC-PATHS-002)

- **Given:** stderr redirected to `io.StringIO`.
- **When:** `log_info`, `log_warn`, `log_err` are called with tag `"ados-install"`.
- **Then:** Output matches `[INFO]  (ados-install) message` format with correct field widths.

---

### Scenario: copy_file_with_diff — new file (TC-FOPS-001)

- **Given:** Source exists; destination does not.
- **When:** `copy_file_with_diff(src, dest, ...)` is called.
- **Then:** Destination created with identical content; `counters.added` incremented by 1.

---

### Scenario: copy_file_with_diff — identical file skipped (TC-FOPS-002)

- **Given:** Source and destination have identical content.
- **When:** `copy_file_with_diff(src, dest, ...)` is called.
- **Then:** Destination unmodified; `counters.unchanged` incremented; `counters.updated` not incremented.

---

### Scenario: copy_file_with_diff — force overwrite on diff (TC-FOPS-003)

- **Given:** Source and destination differ; `config.force = True`.
- **When:** `copy_file_with_diff(src, dest, ...)` is called.
- **Then:** Destination overwritten with source content; `counters.updated` incremented.

---

### Scenario: copy_file_with_diff — project-specific preserve (TC-FOPS-006)

- **Given:** Source and destination differ; file is project-specific (not in updatable list); no `--force`.
- **When:** `copy_file_with_diff(src, dest, ...)` is called.
- **Then:** Destination not overwritten; local modifications preserved; skip/warning logged.

---

### Scenario: safe_rmdir blocks root path (TC-SAFETY-001)

- **Given:** `safe_rmdir` called with `/` (Unix) or `C:\` (Windows).
- **When:** Function is invoked.
- **Then:** Raises `RuntimeError` or `SystemExit`; no filesystem mutation.

---

### Scenario: safe_rmdir blocks home directory (TC-SAFETY-002)

- **Given:** `safe_rmdir` called with `str(Path.home())`.
- **When:** Function is invoked.
- **Then:** Raises `RuntimeError` or `SystemExit`; home directory not deleted.

---

### Scenario: safe_rmdir blocks shallow path — fewer than 3 parts (TC-SAFETY-003)

- **Given:** Path with fewer than 3 resolved components (e.g., `/tmp` on Linux, `C:\foo` on Windows).
- **When:** `safe_rmdir` is called.
- **Then:** Raises `RuntimeError` or `SystemExit` on both platforms.

---

### Scenario: safe_rmdir succeeds for deep safe path (TC-SAFETY-004)

- **Given:** Temporary directory with depth ≥ 3.
- **When:** `safe_rmdir(path, ...)` is called in non-dry-run mode.
- **Then:** Directory removed without error; `Path(path).exists()` is `False`.

---

### Scenario: gitignore entry added when missing (TC-GIT-001)

- **Given:** Temporary `.gitignore` not containing the target entry.
- **When:** `ensure_gitignore_entry(path, ".ai/local/", config)` is called.
- **Then:** Entry appended; file otherwise unmodified.

---

### Scenario: gitignore entry skipped when already present (TC-GIT-002)

- **Given:** `.gitignore` already contains the target entry.
- **When:** `ensure_gitignore_entry` is called again.
- **Then:** No duplicate added; file content unchanged.

---

### Scenario: git clone for new repo (TC-GIT-003)

- **Given:** `subprocess.run` mocked; no `.git` folder in target directory.
- **When:** `clone_or_update_repo(config)` is called.
- **Then:** `subprocess.run` called with `["git", "clone", ...]`; `shell=False`.

---

### Scenario: install.py --help output (TC-INST-001)

- **Given:** `scripts/install.py` is importable.
- **When:** `parse_install_args(["--help"])` is called (catching `SystemExit`).
- **Then:** Help text lists all flags: `--global`, `--local`, `--branch`, `--dry-run`, `--verbose`, `--force`, `--interactive`, `--no-fetch`, `--allow-non-root`, `--version`.

---

### Scenario: install --global full roundtrip (TC-INST-010)

- **Given:** Mock ADOS source; `subprocess.run` mocked; temp dirs for `ADOS_HOME` and `OPENCODE_GLOBAL_DIR`.
- **When:** `main(["--global", "--no-fetch"])` called from `install`.
- **Then:** All agent and command `.md` files copied to mock global dir; summary reports correct `added` count; exit code 0.

---

### Scenario: install --local full roundtrip (TC-INST-011)

- **Given:** Temp project dir initialised with `git init`; mock ADOS source.
- **When:** `main(["--local", "--no-fetch"])` called.
- **Then:** All expected files present; `.gitignore` has required entries; directory stubs created; exit code 0.

---

### Scenario: install --local --dry-run no mutations (TC-INST-020)

- **Given:** Clean temporary project directory.
- **When:** `main(["--local", "--dry-run", "--no-fetch"])` called.
- **Then:** No files created or modified; log lists files that would be installed; exit code 0.

---

### Scenario: install --local idempotency (TC-INST-021)

- **Given:** First `install --local --no-fetch` has completed successfully.
- **When:** `main(["--local", "--no-fetch"])` run a second time without source changes.
- **Then:** `counters.added = 0`, `counters.updated = 0`; `counters.unchanged` equals total managed file count; no files modified; exit code 0.

---

### Scenario: uninstall --global --dry-run lists correct files (TC-UNINST-010)

- **Given:** Mock `OPENCODE_GLOBAL_DIR` with agent/command `.md` files; mock `ADOS_HOME`.
- **When:** `main(["--global", "--dry-run"])` called from `uninstall`.
- **Then:** Log lists every agent and command file and `ADOS_HOME`; no files deleted; exit code 0.

---

### Scenario: uninstall --global full roundtrip (TC-UNINST-011)

- **Given:** Same mock dirs; `config.force = True`.
- **When:** `main(["--global", "--force"])` called from `uninstall`.
- **Then:** All agent/command files removed; `ADOS_HOME` removed; `counters.removed` correct; exit code 0.

---

### Scenario: uninstall --local full roundtrip (TC-UNINST-020)

- **Given:** Temp project with full local ADOS install (produced by TC-INST-011); `config.force = True`.
- **When:** `main(["--local", "--force"])` called from `uninstall`.
- **Then:** All ADOS-managed files removed; empty dirs removed; non-ADOS files untouched; exit code 0.

---

### Scenario: Windows paths with spaces handled correctly (TC-XPLAT-002)

- **Given:** `os.environ["APPDATA"]` mocked to a path containing a space (e.g., `C:\Users\John Doe\AppData\Roaming`).
- **When:** `get_opencode_global_dir()` called and a file is copied under that path.
- **Then:** Path resolved correctly via `pathlib.Path`; no `FileNotFoundError`; no shell interpolation error.

---

### Scenario: XDG_CONFIG_HOME override respected on Linux (TC-XPLAT-003)

- **Given:** `sys.platform = "linux"`; `XDG_CONFIG_HOME` set to a custom temp path.
- **When:** `get_opencode_global_dir()` called.
- **Then:** Returns `XDG_CONFIG_HOME/opencode` (not `~/.config/opencode`).

---

### Scenario: One-liner bootstrap clone and global install (TC-BOOT-001) — Manual

- **Given:** Linux or macOS with Python 3.8+ and `git`; no existing `~/.ados` directory.
- **When:** `curl -fsSL <bootstrap-url> | python3 -` is run.
- **Then:** `~/.ados/repo` cloned; global agent/command files installed to `~/.config/opencode/`; exit code 0.
- **Note:** Must be verified manually before PR merge.

## Performance & Load Tests

No load testing applicable. Startup time requirement: `python3 scripts/install.py --help` must return within 2 seconds on any supported platform (verified manually).

## Security Tests

| Concern | Test |
|---------|------|
| Root path deletion | TC-SAFETY-001 |
| Home directory deletion | TC-SAFETY-002 |
| Shallow path deletion | TC-SAFETY-003 |
| Shell injection via subprocess | TC-GIT-003 (verifies `shell=False` and argument-list call) |
| No external packages | TC-LIB-001 |

## Negative Testing

| Condition | Scenario |
|-----------|---------|
| `safe_rmdir` on root | TC-SAFETY-001 |
| `safe_rmdir` on home | TC-SAFETY-002 |
| `safe_rmdir` on shallow path | TC-SAFETY-003 |
| `--dry-run` produces no filesystem mutations | TC-INST-020 |
| Second install run with no source changes | TC-INST-021 (no overwrites) |

## Automation Strategy

- **CI/CD:** No CI pipeline yet (deferred to a separate work item). All automated tests run locally.
- **Execution trigger:** Manual — run `python -m unittest discover -s scripts/tests` before every PR.
- **Multi-version:** Run on Python 3.8 and 3.12 manually (TC-XPLAT-001) as a DoD gate.
- **Cross-platform:** Windows path tests use mocked `os.environ` and `sys.platform`; live Windows execution is manual.

## Test Environment

| Environment | Purpose |
|-------------|---------|
| Local dev (Linux / macOS) | Primary unit and integration test execution |
| Local dev (Windows) | Windows-specific path mocking verification; live path smoke tests |
| Python 3.8 | Minimum version compatibility gate |
| Python 3.12 | Latest stable compatibility |

**Mocking strategies:**
- `subprocess.run` — mocked for all git operations in automated tests
- `sys.platform` — mocked for platform-path tests
- `os.environ` — patched with `patch.dict` (no permanent leakage)
- `builtins.input` — mocked for interactive-mode and force-confirmation tests
- Filesystem — isolated via `tempfile.mkdtemp()` per test class

## Test Coverage Metrics

| Category | Target | Notes |
|----------|--------|-------|
| `ados_lib` module coverage | Each module has a dedicated test file | 9 modules × 1 test file |
| AC coverage | AC1–AC7 (all acceptance criteria) | Mapped in test plan §3.1 |
| Safety guard coverage | 100% of dangerous-path cases | TC-SAFETY-001 – 004 |
| Idempotency | 100% for local install | TC-INST-021 |
| Dry-run atomicity | 100% — zero mutations verified | TC-INST-020 |

## Maintenance

- When a new file is added to any manifest list (`UPDATABLE_FILES`, `PROJECT_FILES`, etc.), integration tests asserting file counts must be updated.
- If Bash scripts are retired in a future change, the cross-reference tests (TC-INST-010, TC-INST-011) that assert parity with Bash output can be updated to use the Python version as the sole reference.
- When Python minimum version is raised above 3.8, TC-XPLAT-001 must be updated accordingly.

## References

- Feature specification: `doc/spec/features/feature-cross-platform-install.md`
- Change spec: `doc/changes/2026-04/2026-04-30--GH-1--portable-python-install-uninstall-scripts/chg-GH-1-spec.md`
- Change test plan: `doc/changes/2026-04/2026-04-30--GH-1--portable-python-install-uninstall-scripts/chg-GH-1-test-plan.md`
- System dependencies guide: `doc/guides/system-dependencies.md`
