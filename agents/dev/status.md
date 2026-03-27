# Dev Status
Last updated: 2026-03-27T14:30Z
Session: Merge 6 PRs, fix 2 new P1 bugs (#441, #440), enable auto-merge on remaining PRs

## This Session
- Merged 6 PRs: #429 (exit code 2), #434 (Chinese titles), #435 (CI markers), #436 (duplicate PyPI), #437 (HWND test), #438 (lifecycle test)
- Issue #441 (P1, bug) — PR #443 created: Restore internal focus to editor after menu close. `focus_element_uia` now falls back to finding first Edit/Document control when called with only hwnd. Added UIA focus to `type_cmd` (was missing).
- Issue #440 (P1, bug) — PR #444 created: Prefer larger window over popup menu in HWND resolution. Changed tie-breaking from "shorter title" to "larger window area".
- Enabled auto-merge (squash) on PRs #433, #439, #443, #444
- Tests: 1829 passed, 0 failed (non-Windows suite)
- PRs: 6 merged, 4 open (#433, #439, #443, #444)

## Current State
- Earliest open milestone: v0.3.1
- CI: PRs #433 and #439 have Windows DLL tests cancelled (timeout) — auto-merge enabled, awaiting re-run
- Open PRs by me: #433 (IME fix), #439 (Codecov), #443 (focus after menu), #444 (popup HWND)
- Remaining backlog P1 issues without PRs: #420 (README docs), #413 (comparison table), #361 (stable ID), #312 (hybrid mode)

## Next Session Should
- Check if PRs #443 and #444 merged via auto-merge
- Investigate PRs #433 and #439 Windows test timeout — may need to re-trigger or split the changes
- Work on remaining P1 issues: #420 (README clarification) is a good-first-issue/docs task
- If all v0.3.1 milestone issues are done, advance to next milestone
