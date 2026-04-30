---
id: chg-GH-1-portable-python-install-uninstall-scripts
status: Proposed
created: 2026-04-30T00:00:00Z
last_updated: 2026-04-30T00:00:00Z
owners: []
service: ados-scripts
labels: [feat, cross-platform, python, scripting]
links:
  change_spec: ./chg-GH-1-spec.md
  planning_doc: ../../../../doc/planning/portable-install-scripts-plan.md
summary: >
  Port scripts/install.sh and scripts/uninstall.sh to Python 3 (stdlib only) so they run
  natively on Windows, Linux, and macOS. Shared logic lives in scripts/ados_lib/;
  the existing Bash scripts are retained with a deprecation notice until the Python
  versions are fully validated.
version_impact: minor
---

# IMPLEMENTATION PLAN — GH-1: Portable Python Install / Uninstall Scripts

## Context and Goals

The existing `scripts/install.sh` (~760 lines) and `scripts/uninstall.sh` (~429 lines) are
Bash-only and therefore cannot run natively on Windows. This plan delivers Python 3 ports of
both scripts that are **functionally identical** to the Bash originals — same CLI flags, same
environment variables, same exit codes, same file manifest — while adding first-class Windows
support.

Primary source: `doc/planning/portable-install-scripts-plan.md` (detailed 7-phase plan,
concept analysis, Bash → Python mapping table).

Key design decisions already resolved:

- **Stdlib only** — no `pip install`, no external packages.
- **Python ≥ 3.8** — minimum required for walrus operator and `shutil.copytree(dirs_exist_ok=True)`.
- **Shared library** — common code in `scripts/ados_lib/`; both entry-point scripts import it.
- **Parallel existence** — Bash scripts remain with a deprecation comment; removal is a separate ticket.
- **No CI introduced here** — GitHub Actions is out of scope; tests are run manually on each platform.

## Scope

### In Scope

- `scripts/ados_lib/` shared library (types, logger, platform_paths, manifest, file_ops, gitignore, safety, git_ops, cli)
- `scripts/install.py` — Python entry point with full CLI parity to `install.sh`
- `scripts/uninstall.py` — Python entry point with full CLI parity to `uninstall.sh`
- `scripts/bootstrap.py` — minimal one-liner bootstrapper (clones repo, calls `install.py --global`)
- Unit and integration tests under `scripts/tests/` using `unittest` (stdlib only)
- Cross-platform edge-case handling: Windows spaces in paths, XDG override on Linux, case-insensitive macOS FS
- Documentation updates: `README.md`, `doc/guides/system-dependencies.md`
- Deprecation comments added to `install.sh` and `uninstall.sh`

### Out of Scope

- Removal of existing Bash scripts (separate ticket after validation)
- GUI / TUI interface
- PyInstaller or binary distribution
- Python packaging (`setup.py` / `pyproject.toml`)
- GitHub Actions CI workflow (separate ticket)

### Constraints

- No external Python packages permitted
- `git` CLI must remain a system dependency
- Python ≥ 3.8 (macOS Monterey+, Ubuntu 20.04+, Windows via python.org or Store)
- Colourised diff output gated on `os.isatty()` — not assumed available

### Risks

- **RSK-1**: `python` vs `python3` alias divergence across platforms. Mitigated by: shebang `#!/usr/bin/env python3`; Windows documentation recommends `py -3` or `python`.
- **RSK-2**: Windows paths with spaces or Unicode. Mitigated by: exclusive use of `pathlib.Path`; never string concatenation for paths.
- **RSK-3**: `subprocess` shell-string behaviour differs on Windows. Mitigated by: always pass git commands as lists (`["git", "clone", ...]`), never `shell=True`.

### Success Metrics

- `python3 scripts/install.py --local` produces identical file tree to `bash scripts/install.sh --local` on Linux/macOS.
- `python scripts/install.py --local` completes successfully on Windows with no Bash dependency.
- All 30 test scenarios in the test matrix pass on Python 3.8 and 3.12 across Windows, Linux, macOS.
- One-liner bootstrap works on Linux and macOS; Windows curl-equivalent documented.

## Phases

### Phase 1: Shared Library — Foundations

**Goal**: Implement the platform-independent building blocks that both scripts require: package init, data types, logger, platform path resolution, and the file manifest.

**Tasks**:

- [x] **1.1** Create `scripts/ados_lib/__init__.py` — package init with `__version__ = "2.0.0"`
- [x] **1.2** Create `scripts/ados_lib/types.py` — dataclasses for runtime configuration:
  - `InstallConfig(mode, branch, dry_run, verbose, force, interactive, no_fetch, allow_non_root)`
  - `UninstallConfig(mode, dry_run, verbose, force)`
  - `Counters(added, updated, unchanged)` / `Counters(removed, skipped)`
- [x] **1.3** Create `scripts/ados_lib/logger.py` — logging primitives:
  - `log_info(tag, msg)`, `log_warn(tag, msg)`, `log_err(tag, msg)`, `log_debug(tag, msg, verbose)`
  - Coloured output when `sys.stderr.isatty()` / `sys.stdout.isatty()` — `\033[...m` sequences
  - Format identical to Bash: `[INFO]  (ados-install) message`
- [x] **1.4** Create `scripts/ados_lib/platform_paths.py` — OS-specific path resolution:
  - `get_ados_home() -> Path` — `ADOS_HOME` env var or `~/.ados`
  - `get_ados_repo_dir() -> Path` — `ADOS_REPO_DIR` env var or `~/.ados/repo`
  - `get_opencode_global_dir() -> Path` — Windows: `%APPDATA%/opencode`; Linux: XDG; macOS: `~/.config/opencode`
  - `get_ados_repo_url() -> str`, `get_ados_raw_url() -> str`
- [x] **1.5** Create `scripts/ados_lib/manifest.py` — file lists (1:1 copy from Bash):
  - `UPDATABLE_FILES`, `TEMPLATE_DIR`, `PROJECT_FILES`, `LOCAL_DIRS`
  - `AGENT_FILES`, `COMMAND_FILES`, `LOCAL_UPDATABLE_FILES`, `LOCAL_TEMPLATE_FILES`
- [x] **1.6** Create `scripts/tests/__init__.py` — test package stub (includes `make_mock_ados_source` helper)

**Acceptance Criteria**:

- Must: All modules import cleanly with no external dependencies (`import ados_lib` succeeds from repo root)
- Must: `platform_paths` returns correct paths on Windows, Linux, and macOS (verified via mocked `sys.platform` and `os.environ`)
- Must: Logger output format matches the Bash format string exactly (`[INFO]  (ados-install) ...`)
- Should: `Counters` dataclass supports `+` accumulation or simple attribute access

**Files and modules**:

- `scripts/ados_lib/__init__.py` (new)
- `scripts/ados_lib/types.py` (new)
- `scripts/ados_lib/logger.py` (new)
- `scripts/ados_lib/platform_paths.py` (new)
- `scripts/ados_lib/manifest.py` (new)
- `scripts/tests/__init__.py` (new)

**Tests**:

- `scripts/tests/test_platform_paths.py` — mock `sys.platform` and `os.environ`; assert correct path per OS
- Manual: `python3 -c "from ados_lib import logger; logger.log_info('test','hello')"` — verify format and colour

**Completion signal**: `feat(GH-1): add ados_lib shared library (types, logger, platform_paths, manifest)`

---

### Phase 2: Shared Library — File Operations & Safety

**Goal**: Implement file copy-with-diff, directory helpers, `.gitignore` manipulation, and safety guards that prevent accidental deletion of critical paths.

**Tasks**:

- [x] **2.1** Create `scripts/ados_lib/file_ops.py`:
  - `copy_file_with_diff(src, dest, label, config, counters, updatable=False) -> None`
    - Detect symlinks (`Path.is_symlink()`) and replace with real copy
    - Content comparison via `filecmp.cmp(shallow=False)`
    - Implement all 6 copy modes: new file, identical (skip), force-update, interactive (unified diff + prompt), updatable auto-update, project-file preserve
    - `prompt_diff_overwrite(src, dest, label) -> bool` using `difflib.unified_diff()`
  - `copy_updatable_file(src, dest, label, config, counters)` — thin wrapper
  - `ensure_dir(dir_path, label, config) -> None` — `mkdir(parents=True, exist_ok=True)` with dry-run gate
  - `remove_file(path, label, config, counters) -> None` — `unlink(missing_ok=True)` with dry-run gate
- [x] **2.2** Create `scripts/ados_lib/gitignore.py`:
  - `file_contains_line(file_path, pattern) -> bool`
  - `ensure_gitignore_entry(gitignore_path, entry, config) -> None` — append only if not already present
- [x] **2.3** Create `scripts/ados_lib/safety.py`:
  - `validate_paths(config) -> None` — warn if `ADOS_HOME` or `OPENCODE_GLOBAL_DIR` is outside `$HOME`
  - `safe_rmdir(dir_path, label, config) -> None`:
    - Reject empty path
    - Reject root path or home directory
    - Reject path with fewer than 3 resolved components (`len(Path(p).resolve().parts) < 3`)
    - Respect dry-run gate

**Acceptance Criteria**:

- Must: `copy_file_with_diff` behaves identically to the Bash version for all 6 copy scenarios
- Must: `safe_rmdir` blocks dangerous paths on all three platforms (root, home, shallow path)
- Must: Interactive mode renders a unified diff and awaits `y/n` confirmation before writing
- Must: All file operations respect `config.dry_run` and log what *would* happen without modifying the filesystem

**Files and modules**:

- `scripts/ados_lib/file_ops.py` (new)
- `scripts/ados_lib/gitignore.py` (new)
- `scripts/ados_lib/safety.py` (new)

**Tests**:

- `scripts/tests/test_file_ops.py` — `tempfile`-based tests for all 6 copy scenarios (T3–T9)
- `scripts/tests/test_safety.py` — `safe_rmdir` with root, home, shallow, and valid paths (T10–T13)
- `scripts/tests/test_gitignore.py` — add entry, detect duplicate (T14–T15)

**Completion signal**: `feat(GH-1): add file_ops, gitignore, safety modules to ados_lib`

---

### Phase 3: Shared Library — Git Operations

**Goal**: Implement all git interactions (clone, pull, branch switch, source resolution) as platform-safe Python functions using `subprocess` list invocation.

**Tasks**:

- [x] **3.1** Create `scripts/ados_lib/git_ops.py`:
  - `require_git() -> None` — `shutil.which("git")` or `sys.exit(5)`
  - `git_run(args, cwd=None, check=True, capture=True) -> subprocess.CompletedProcess`
    - Always `["git"] + args` — never `shell=True`
    - `encoding="utf-8"`, `errors="replace"`
  - `clone_or_update_repo(config) -> None`
    - If `.git` absent in `ADOS_REPO_DIR` → clone
    - Else → fetch, checkout branch, `git pull --ff-only`
    - Log before/after SHA
  - `auto_fetch_source(source_dir, config) -> None`
    - Skip when: `config.no_fetch`, `ADOS_SOURCE_DIR` set, or `source_dir` is not a git repo
    - Switch branch if needed; `git pull --ff-only` with fallback warning on failure
  - `resolve_source_dir(config) -> Path`
    - Priority: (1) `ADOS_SOURCE_DIR` env, (2) script's own repo (`Path(__file__).resolve().parent.parent`), (3) `ADOS_REPO_DIR`
  - `require_project_root(allow_non_root, config) -> None`
    - Check for `.git` directory; use `git rev-parse --show-toplevel` for monorepo support
  - `get_short_sha(repo_dir) -> str | None`
  - `get_current_branch(repo_dir) -> str | None`

**Acceptance Criteria**:

- Must: All git subprocesses use list form — `grep` or code review must find zero `shell=True` in `git_ops.py`
- Must: `resolve_source_dir` priority order matches the Bash `resolve_source_dir()` function exactly
- Must: Git errors are caught, logged via `log_err`, and result in a clean `sys.exit` — no raw tracebacks to end users (except in `--verbose` mode)

**Files and modules**:

- `scripts/ados_lib/git_ops.py` (new)

**Tests**:

- `scripts/tests/test_git_ops.py` — `unittest.mock.patch("subprocess.run", ...)` for clone, pull, branch-switch (T16–T18)
- `scripts/tests/test_git_ops.py` — mock `os.environ` for `resolve_source_dir` priority (T19–T20)

**Completion signal**: `feat(GH-1): add git_ops module to ados_lib`

---

### Phase 4: Install Script (`install.py`)

**Goal**: Implement the complete Python install entry-point with CLI parity to `install.sh`, covering both `--local` and `--global` modes, all environment variables, and correct exit codes.

**Tasks**:

- [ ] **4.1** Create `scripts/ados_lib/cli.py` — argparse-based argument parsing:
  - `parse_install_args(argv=None) -> InstallConfig`
  - `parse_uninstall_args(argv=None) -> UninstallConfig`
  - Flags (must match Bash): `-g/--global`, `-l/--local`, `-b/--branch <branch>`, `-n/--dry-run`, `-v/--verbose`, `-f/--force`, `-i/--interactive`, `--no-fetch`, `--allow-non-root`, `-h/--help`, `-V/--version`
  - Default mode: `--local` when neither `-g` nor `-l` supplied
- [ ] **4.2** Create `scripts/install.py` — main entry-point:
  - Shebang: `#!/usr/bin/env python3`
  - `signal.signal(signal.SIGINT, ...)` interrupt handler
  - `do_global_install(config)`:
    - `require_git()` → `validate_paths()` → `clone_or_update_repo()` → `install_global_files()` → summary
  - `do_local_install(config)`:
    - `require_project_root()` → `validate_paths()` → `resolve_source_dir()` → `auto_fetch_source()` → `install_local_files()` → summary with next-steps hint
  - `install_local_files(source_dir, config, counters)`:
    - Project-specific files, updatable files, template globs (`*.md` from template dir), directory stubs, `.gitignore` entries
  - `main(argv=None)` — testable entry-point (allows `main(["--dry-run", "--local"])` in tests)
- [ ] **4.3** Environment variable support — all vars read and honoured:
  - `ADOS_REPO_URL`, `ADOS_RAW_URL`, `ADOS_HOME`, `ADOS_REPO_DIR`, `OPENCODE_GLOBAL_DIR`, `ADOS_SOURCE_DIR`
  - `DRY_RUN`, `VERBOSE`, `FORCE`, `INTERACTIVE`, `NO_FETCH`, `ADOS_BRANCH`, `ALLOW_NON_ROOT`
- [ ] **4.4** Exit codes (must match Bash):
  - `0` = success, `2` = usage error, `3` = configuration error, `4` = runtime error, `5` = external dependency missing

**Acceptance Criteria**:

- Must: `python3 scripts/install.py --help` renders all flags (content-equivalent to `bash scripts/install.sh --help`)
- Must: `python3 scripts/install.py --local --dry-run` (with `ADOS_SOURCE_DIR` set) logs same file operations as the Bash equivalent
- Must: `python3 scripts/install.py --global` clones/updates the repo and copies agent/command files (verified in integration test with mocked git)
- Must: All environment variables listed in 4.3 override their corresponding defaults

**Files and modules**:

- `scripts/ados_lib/cli.py` (new)
- `scripts/install.py` (new)

**Tests**:

- `scripts/tests/test_install_local.py` — local install into `tempfile.mkdtemp()` with mock source dir; verify file tree (T21, T23, T24)
- `scripts/tests/test_install_global.py` — global install with mocked `subprocess.run` (git) and mock filesystem (T22)

**Completion signal**: `feat(GH-1): add portable install.py with full CLI parity`

---

### Phase 5: Uninstall Script (`uninstall.py`)

**Goal**: Implement the complete Python uninstall entry-point with CLI parity to `uninstall.sh`, covering both `--local` and `--global` modes, confirmation prompts, and safe directory removal.

**Tasks**:

- [ ] **5.1** Create `scripts/uninstall.py` — main entry-point:
  - Shebang: `#!/usr/bin/env python3`
  - `confirm_action(message, config) -> bool` — returns `True` immediately when `config.force` or `config.dry_run`
  - `do_global_uninstall(config)`:
    - Confirmation prompt (skipped with `--force` / `--dry-run`)
    - `remove_global_agents(config, counters)` — remove `.md` files from `OPENCODE_GLOBAL_DIR/agent/`
    - `remove_global_commands(config, counters)` — remove `.md` files from `OPENCODE_GLOBAL_DIR/command/`
    - `safe_rmdir(ADOS_HOME, ...)` — remove ADOS home directory
    - Summary output
  - `do_local_uninstall(config)`:
    - `require_project_root(allow_non_root=False, config)` — strict; must be at project root
    - Confirmation prompt
    - `remove_local_files(config, counters)`:
      - Project-specific files, updatable files, template files
      - Remove empty directories (`not any(Path(d).iterdir())` check — cross-platform)
    - Summary output
  - `main(argv=None)` — testable entry-point

**Acceptance Criteria**:

- Must: `python3 scripts/uninstall.py --help` shows all supported flags
- Must: `python3 scripts/uninstall.py --global --dry-run` lists the same files that `bash scripts/uninstall.sh --global --dry-run` would remove
- Must: `safe_rmdir` blocks dangerous paths identically on all platforms (covered by Phase 2 tests; integration-confirmed here)
- Must: Empty-directory check works on Windows (no `ls -A` dependency)
- Must: `--force` bypasses confirmation prompt without stdin interaction

**Files and modules**:

- `scripts/uninstall.py` (new)

**Tests**:

- `scripts/tests/test_uninstall_local.py` — install-then-uninstall round-trip in `tempfile.mkdtemp()`; assert files removed (T25)
- `scripts/tests/test_uninstall_global.py` — mock directory structure; assert removal calls with mocked `safe_rmdir` (T26)
- `scripts/tests/test_uninstall_local.py` — mock `input()` to verify `--force` skips prompt (T27)

**Completion signal**: `feat(GH-1): add portable uninstall.py with full CLI parity`

---

### Phase 6: Cross-Platform Tests

**Goal**: Validate all modules on Windows, Linux, and macOS with Python 3.8 and 3.12; add integration tests for full install/uninstall round-trips.

**Tasks**:

- [ ] **6.1** Add test helpers in `scripts/tests/__init__.py`:
  - `make_mock_ados_source(tmp_dir) -> Path` — creates a fake ADOS repo tree with stub `.opencode/agent/*.md`, `.opencode/command/*.md`, templates, etc.
  - `run_tests()` helper or confirm `python -m unittest discover -s scripts/tests` works from repo root
- [ ] **6.2** Create `scripts/tests/test_install_integration.py` — full install round-trip:
  - [ ] Step A: Create mock ADOS source via `make_mock_ados_source()`
  - [ ] Step B: Run `install.main(["--local", "--no-fetch"])` with `ADOS_SOURCE_DIR` pointing to mock source
  - [ ] Step C: Assert all expected files and directories exist in tmp target
  - [ ] Step D: Run again — assert idempotency (counters: `added=0`, `updated=0`, `unchanged=N`)
  - [ ] Step E: Modify one file in mock source → run again → assert `updated=1`
- [ ] **6.3** Create `scripts/tests/test_uninstall_integration.py` — full uninstall round-trip:
  - Install first (reuse helper), then run `uninstall.main(["--local", "--force"])`, assert files removed
- [ ] **6.4** Document manual cross-platform verification steps in a test run checklist comment in `test_install_integration.py`
- [ ] **6.5** Handle platform-specific edge cases in tests:
  - Windows: path with spaces — `Path(tmp) / "John Doe" / "project"`
  - Linux: `XDG_CONFIG_HOME` env override
  - macOS: case-insensitive FS (document limitation; do not add special code)

**Acceptance Criteria**:

- Must: `python -m unittest discover -s scripts/tests` exits 0 on Linux and macOS with Python 3.8 and 3.12
- Must: The same command exits 0 on Windows with Python 3.8 and 3.12
- Must: No test imports anything outside Python stdlib
- Should: Integration tests are fast (<10 s total) — no real network calls

**Files and modules**:

- `scripts/tests/__init__.py` (updated — add helpers)
- `scripts/tests/test_install_integration.py` (new)
- `scripts/tests/test_uninstall_integration.py` (new)

**Tests**:

- Manual verification: run `python -m unittest discover -s scripts/tests` on each of: Ubuntu, macOS, Windows — Python 3.8 and 3.12
- Record results in Execution Log below

**Completion signal**: `test(GH-1): add cross-platform integration test suite for Python install scripts`

---

### Phase 7: Documentation & One-Liner Bootstrap

**Goal**: Provide a self-contained one-liner bootstrapper, update README and system-dependencies guide, and mark the Bash scripts as deprecated.

**Tasks**:

- [ ] **7.1** Create `scripts/bootstrap.py` — standalone one-liner entry-point (~30 lines, no `import ados_lib`):
  - Clone repo to `~/.ados/repo` using `subprocess.run(["git", "clone", ...])` directly
  - `sys.exit` with clear message if git not found (`shutil.which("git")`)
  - Exec `install.py --global` from the cloned repo via `subprocess.run`
- [ ] **7.2** Update `README.md` — installation section:
  - Linux/macOS one-liner: `curl -fsSL https://raw.githubusercontent.com/juliusz-cwiakalski/agentic-delivery-os/main/scripts/bootstrap.py | python3 -`
  - Windows PowerShell: `irm https://raw.githubusercontent.com/juliusz-cwiakalski/agentic-delivery-os/main/scripts/bootstrap.py | python -`
  - Note: Python ≥ 3.8 required
  - Note: Bash variants remain available as fallback
- [ ] **7.3** Update `doc/guides/system-dependencies.md`:
  - Add Python 3.8+ as a system dependency
  - Add install instructions for each platform (Windows: python.org or Store; Linux: distro package manager; macOS: Homebrew or python.org)
- [ ] **7.4** Add deprecation comments to `scripts/install.sh` and `scripts/uninstall.sh`:
  - Line 1 comment: `# DEPRECATED: Use scripts/install.py for cross-platform support. This Bash version will be removed in a future release.`
- [ ] **7.5** Verify one-liner manually on Linux and macOS; document result in Execution Log

**Acceptance Criteria**:

- Must: `bootstrap.py` is a single self-contained file with no `import ados_lib`
- Must: One-liner install completes successfully on Linux and macOS (manual test)
- Must: README shows both Python (recommended) and Bash (fallback) install paths
- Must: `doc/guides/system-dependencies.md` lists Python ≥ 3.8 with per-platform install notes
- Should: Windows PowerShell one-liner documented even if not manually tested in this change

**Files and modules**:

- `scripts/bootstrap.py` (new)
- `README.md` (updated)
- `doc/guides/system-dependencies.md` (updated)
- `scripts/install.sh` (updated — deprecation comment)
- `scripts/uninstall.sh` (updated — deprecation comment)

**Tests**:

- Manual: run bootstrap one-liner on Linux and macOS; confirm global install completes
- Manual: `python3 scripts/bootstrap.py` from a clean temp dir with `ADOS_HOME` overridden

**Completion signal**: `docs(GH-1): add cross-platform install documentation and one-liner bootstrap`

---

## Test Scenarios

| ID  | Scenario                                                         | Phase | Verification Method    |
|-----|------------------------------------------------------------------|-------|------------------------|
| T1  | `platform_paths` returns correct paths on Win / Linux / macOS   | 1     | Mocked `sys.platform` + `os.environ` |
| T2  | Logger format matches Bash `[INFO]  (ados-install) ...`          | 1     | String comparison      |
| T3  | `copy_file_with_diff` — new file created                         | 2     | `tempfile`             |
| T4  | `copy_file_with_diff` — identical file skipped                   | 2     | `tempfile`             |
| T5  | `copy_file_with_diff` — force-update on diff                     | 2     | `tempfile`             |
| T6  | `copy_file_with_diff` — interactive mode prompts and applies     | 2     | Mock `input()`         |
| T7  | `copy_file_with_diff` — updatable file auto-updated              | 2     | `tempfile`             |
| T8  | `copy_file_with_diff` — project-specific file preserved          | 2     | `tempfile`             |
| T9  | `copy_file_with_diff` — symlink replaced with real copy          | 2     | `tempfile` (Unix only) |
| T10 | `safe_rmdir` — root path rejected                                | 2     | Assert `RuntimeError`  |
| T11 | `safe_rmdir` — home directory rejected                           | 2     | Assert `RuntimeError`  |
| T12 | `safe_rmdir` — path with < 3 components rejected                 | 2     | Assert `RuntimeError`  |
| T13 | `safe_rmdir` — valid deep path removed                           | 2     | `tempfile`             |
| T14 | `ensure_gitignore_entry` — entry appended                        | 2     | `tempfile`             |
| T15 | `ensure_gitignore_entry` — duplicate skipped                     | 2     | `tempfile`             |
| T16 | `clone_or_update_repo` — clones when repo absent                 | 3     | Mock `subprocess.run`  |
| T17 | `clone_or_update_repo` — pulls when repo present                 | 3     | Mock `subprocess.run`  |
| T18 | `clone_or_update_repo` — switches branch when needed             | 3     | Mock `subprocess.run`  |
| T19 | `resolve_source_dir` — `ADOS_SOURCE_DIR` env takes priority      | 3     | Mock `os.environ`      |
| T20 | `resolve_source_dir` — falls back to script's own repo           | 3     | `tempfile`             |
| T21 | `install.py --local` full round-trip                             | 4     | Integration            |
| T22 | `install.py --global` full round-trip                            | 4     | Integration            |
| T23 | `install.py --local` second run — idempotent                     | 4     | Integration            |
| T24 | `install.py --local --dry-run` — no filesystem changes           | 4     | Integration            |
| T25 | `uninstall.py --local --force` removes all installed files       | 5     | Integration            |
| T26 | `uninstall.py --global --force` removes agent/command files      | 5     | Integration            |
| T27 | `uninstall.py --force` bypasses confirmation prompt              | 5     | Mock `input()`         |
| T28 | Windows path with spaces handled without error                   | 6     | Platform test          |
| T29 | `XDG_CONFIG_HOME` override respected on Linux                    | 6     | Env mock               |
| T30 | `bootstrap.py` one-liner completes on Linux and macOS            | 7     | Manual                 |

## Artifacts and Links

| Artifact                        | Location                                                                                    | Type     |
|---------------------------------|---------------------------------------------------------------------------------------------|----------|
| Change spec                     | `doc/changes/2026-04/2026-04-30--GH-1--portable-python-install-uninstall-scripts/chg-GH-1-spec.md` | Spec |
| This plan                       | `doc/changes/2026-04/2026-04-30--GH-1--portable-python-install-uninstall-scripts/chg-GH-1-plan.md` | Plan |
| Primary planning document       | `doc/planning/portable-install-scripts-plan.md`                                             | Planning |
| Concept document                | `doc/planning/portable-install-scripts-concept.md`                                          | Planning |
| Shared library                  | `scripts/ados_lib/`                                                                         | Code     |
| Install entry-point             | `scripts/install.py`                                                                        | Code     |
| Uninstall entry-point           | `scripts/uninstall.py`                                                                      | Code     |
| One-liner bootstrapper          | `scripts/bootstrap.py`                                                                      | Code     |
| Unit & integration tests        | `scripts/tests/`                                                                            | Tests    |
| README (install section)        | `README.md`                                                                                 | Docs     |
| System dependencies guide       | `doc/guides/system-dependencies.md`                                                         | Docs     |

## Plan Revision Log

| Version | Date       | Author      | Changes                       |
|---------|------------|-------------|-------------------------------|
| 1.0     | 2026-04-30 | plan-writer | Initial plan derived from `doc/planning/portable-install-scripts-plan.md` |

## Execution Log

| Phase | Status | Started | Completed | Commit | Notes |
|-------|--------|---------|-----------|--------|-------|
| 1     | DONE   | 2026-04-30 | 2026-04-30 | feat(GH-1): add ados_lib shared library (types, logger, platform_paths, manifest) | 11 tests PASS |
| 2     | DONE   | 2026-04-30 | 2026-04-30 | feat(GH-1): add file_ops, gitignore, safety modules to ados_lib | 24 pass, 1 skip (symlink/Win) |
| 3     | DONE   | 2026-04-30 | 2026-04-30 | feat(GH-1): add git_ops module to ados_lib | 11 tests PASS; zero shell=True |
| 4     | —      |         |           |        |       |
| 5     | —      |         |           |        |       |
| 6     | —      |         |           |        |       |
| 7     | —      |         |           |        |       |
