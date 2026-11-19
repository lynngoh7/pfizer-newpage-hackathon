## What and why

<!-- 1 to 3 lines: what this changes and why. -->

## How to test

1.
2.

## Checklist

- [ ] Title uses conventional commit style (feat / fix / docs / chore / ci …)
- [ ] Backend tests pass (`cd backend && .venv/bin/pytest`)
- [ ] Frontend builds (`npm run build`)
- [ ] Non-obvious code has a short comment saying why; safety checks name the rule they enforce
- [ ] `docs/STATUS.md` updated; new files added to `docs/FILES.md`
- [ ] Privacy: no outbound network calls, no note text written to disk or logs, every file read goes through `resolve_and_check`
- [ ] Only fictional sample notes used (`sample_notes/`), never real ones
- [ ] Screenshot attached for UI changes
