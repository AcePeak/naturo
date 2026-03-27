# Dev Status
Last updated: 2026-03-27T16:45:00Z
Session: P1 bug fixes + P2 help command

## This Session
- Issue #442 (P1) — click --on fails for short text: PR #458 created
- Issue #457 (P2) — naturo help returns error: PR #459 created
- Issue #455 (P1) — test_detect_notepad_has_uia: investigated, commented analysis (cannot fix from Linux)
- Issue #456 (P1) — element IDs shift: analyzed, commented suggested approach
- Tests: 1627 passed, 334 skipped, 0 failed
- PRs: #458 created (click fallback), #459 created (help command)

## Open PRs by Me
- #458 — fix: click --on fallback for localized text (fixes #442) — CI blocked (pending #454 merge)
- #459 — fix: naturo help command alias (fixes #457) — CI blocked (pending #454 merge)

## Current State
- Earliest open milestone: v0.3.1 (multiple P1 bugs remaining)
- CI: broken on main (actions/checkout@v5 doesn't exist) — PR #454 by Orc-Mycelium fixes this
- Open P1 bugs: #455 (Windows-only, needs runner), #456 (eN stability design), #449 (--app non-deterministic), #446 (flaky test)

## Next Session Should
- Check if PR #454 (CI fix) merged — then #458 and #459 should auto-merge or re-enable auto-merge
- Address any review feedback on #458 or #459
- Fix #456 (element ID stability) — implement hash-based stable eN IDs
- Fix #449 (--app non-deterministic) — investigate window resolution logic
- #455 and #446 require Windows runner testing
