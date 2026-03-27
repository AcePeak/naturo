# Dev Status
Last updated: 2026-03-27T15:20:00Z
Session: Hybrid tree + get --all

## This Session
- Issue #367 (P0) — Hybrid tree with per-node backend selection: PR #450 created
- Issue #382 (P2) — get: add --all flag: PR #451 created
- Tests: 1796 passed, 393 skipped, 0 failed
- PRs: #450 created (hybrid tree), #451 created (get --all), both auto-merge enabled

## Open PRs by Me
- #450 — feat: hybrid tree (fixes #367) — CI pending, auto-merge enabled
- #451 — feat: get --all (fixes #382) — CI pending, auto-merge enabled
- #444 — fix: HWND resolution (fixes #440) — CI green, blocked (needs review)
- #443 — fix: focus after menu (fixes #441) — CI green, blocked (needs review)
- #439 — feat: Codecov (fixes #409) — CI failing (Windows hang, needs #445 merge + rebase)
- #433 — fix: IME type (fixes #425) — CI failing (same, needs rebase)

## Current State
- Earliest open milestone: v0.3.1 (3 issues remaining: #312 P1, #313 P2, #411 P2)
- CI: green on main
- #445 (Orc-Mycelium CI fix) is green, blocked — once merged, #439 and #433 need rebase

## Next Session Should
- Check if #450 and #451 merged — if CI failed, fix
- Rebase #439 and #433 after #445 merges
- Pick #312 (P1, Win32+UIA hybrid) or #313 (P2, highlight all) from v0.3.1
- #312 is closely related to #367 — may be partially addressed, assess overlap
