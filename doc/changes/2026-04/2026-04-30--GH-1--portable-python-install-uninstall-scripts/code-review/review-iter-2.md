# Code Review — Iteration 2

**Change**: GH-1 — Portable Python install/uninstall scripts
**Date**: 2026-04-30
**Reviewer**: reviewer agent (re-review after remediation iteration 1)
**Status**: FAIL

## Finding Count

| Severity | Count |
|----------|-------|
| Critical | 0 |
| Major    | 0 |
| Minor    | 4 |
| Nit      | 1 |
| **Total**| **5** |

## Remediation Verification

All 4 major and 5 minor findings from iteration 1 were correctly addressed:

| Finding | Status |
|---------|--------|
| #1 — `validate_paths` startswith false-positive | ✅ Fixed — parts-based check applied |
| #2 — Dead code `before_sha_val` in `git_ops.py` | ✅ Fixed — dead lines removed |
| #3 — Type mismatch `require_project_root` | ✅ Fixed — signature changed to `verbose: bool` |
| #4 — Double-log in `safe_rmdir` dry-run | ✅ Fixed — `log_info` moved inside `else` branch |
| #5 — `log_info` stream parameter asymmetry | ✅ Acknowledged (no action required) |
| #6 — `PROJECT_FILES` empty list undocumented | ✅ Fixed — explanatory comment added |
| #7 — `file_contains_line` substring match | ✅ Fixed — exact line match implemented |
| #8 — Redundant `.gitignore` entries | ✅ Fixed — `.ai/local` entry removed, only `.ai/local/` kept |
| #9 — `require_project_root` implicit CWD | ✅ Fixed — `cwd=Path.cwd()` passed explicitly |
| #10 — Stale comment / dead code | ✅ Fixed as part of #2 |
| #11 — Docstring scenario count mismatch | ✅ Fixed — updated to "8-scenario logic" |
| #12 — Unused `field` import in `types.py` | ✅ Fixed — import removed |

## New Findings (Iteration 2)

### Key Themes

1. **Dry-run double-log pattern** — The `safe_rmdir` double-log was fixed (iter-1 finding #4), but the same pattern was not applied consistently to `copy_file_with_diff` (new-file branch), `ensure_dir`, `remove_file`, and `remove_local_files`. All four emit both a `[DRY-RUN] Would …` line AND an action line (`add`, `create`, `remove`) on every dry-run operation.

2. **Non-ASCII arrow character in log strings** — Two `→` characters in `git_ops.py` cause `UnicodeEncodeError` on Windows cp1252 consoles. This is confirmed by a test failure (`test_switches_branch_when_needed` errors on the Windows runner).

## Plan Task Audit

- All Phase 1–8 tasks are marked `[x]` done.
- One task remains open: **7.5** (manual one-liner verification on Linux/macOS) — correctly deferred to PR validation; not a blocker.
- No DONE_BUT_UNCHECKED or CHECKED_BUT_MISSING gaps.

## Test Suite

- 63 tests run; **62 pass, 1 error, 1 skip**.
- The error (`test_switches_branch_when_needed`) is caused by finding #1 (non-ASCII arrow in log string on Windows cp1252).
- The skip is the pre-existing symlink test on Windows — expected and documented.

## Next Step

**CALL_CODER** — remediate the 4 minor double-log findings and 1 nit (non-ASCII arrow). These are straightforward one-line fixes. Re-review after remediation.
