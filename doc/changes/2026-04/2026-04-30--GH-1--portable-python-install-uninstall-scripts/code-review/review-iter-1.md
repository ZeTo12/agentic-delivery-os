# Code Review — GH-1: Portable Python Install/Uninstall Scripts
## Iteration 1

**Date**: 2026-04-30
**Reviewer**: reviewer agent
**Status**: FAIL
**Findings**: 12 (0 critical / 4 major / 5 minor / 3 nit)

---

## Severity Breakdown

| Severity | Count |
|----------|-------|
| Critical | 0 |
| Major    | 4 |
| Minor    | 5 |
| Nit      | 3 |
| **Total**| **12** |

---

## Key Themes

1. **Dead / incorrect code in git_ops.py** — a string-literal condition creates unreachable code and a never-used variable (`before_sha_val`).
2. **Type safety suppressed with `# type: ignore`** — `uninstall.py` passes `UninstallConfig` where `InstallConfig` is expected; the mismatch is masked rather than fixed.
3. **Dry-run log double-emission** — `safe_rmdir` emits both a `[DRY-RUN]` line and a `remove` line on dry-run runs.
4. **Path-prefix false-positive** — `validate_paths` uses `str.startswith` for path containment, which is incorrect for sibling directories with similar names.
5. **Gitignore duplicate-detection uses substring match** — causes `.ai/local` to suppress `.ai/local/` (or vice versa), meaning only one of the two intended entries is ever written.

---

## Spec / Plan Compliance

- All 7 phases are marked DONE in the execution log. ✅
- One open task remains: **7.5** (manual one-liner verification on Linux/macOS) — deferred to PR validation, acceptable per plan notes. ✅
- All acceptance criteria are addressed in the implementation. ✅
- `shell=True` is absent from all subprocess calls. ✅
- `pathlib.Path` used throughout; no string path concatenation found. ✅
- stdlib-only; no external imports detected. ✅

---

## Next Step

**CALL_CODER** — remediate the 4 major findings before re-review.
