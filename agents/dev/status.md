# Dev Status
Last updated: 2026-03-27T19:20:00Z
Session: PR merges, click performance optimization (#448)

## This Session
- PR #468 (fixes #465) — --app rejects title-only matches: **merged** (8383d49)
- PR #466 (fixes #456) — stable hash-based element refs: branch updated, CI re-running (previously cancelled Windows DLL test)
- Issue #448 (P2) — click via eN refs 13x slower: PR #470 created (skip auto-routing for cached refs, use snapshot HWND for focus)
- Tests: 1836 passed, 547 skipped, 0 failed
- PRs merged: #468 | PRs pending CI: #466, #470

## Open PRs by Me
- #466 — fix: stable hash-based element refs (fixes #456) — CI re-running after branch update, 5/6 checks green, Windows DLL test in progress
- #470 — fix: skip auto-routing for eN ref clicks (fixes #448) — CI just started

## Current State
- Earliest open milestone: v0.3.1 (2 issues: #312 P1 hybrid mode, #448 P2 click perf)
- CI: green on main
- Issues addressed this session: #465 (merged), #448 (PR created)
- #448 is partially fixed — routing skip saves ~0.7s/click, but full parity with pywinauto requires batch/daemon mode

## Next Session Should
- Check CI on PRs #466 and #470 — merge if green, fix if failing
- Enable auto-merge on #466 and #470 once CI passes
- Address any review feedback on open PRs
- Investigate #312 (Win32+UIA hybrid mode) — P1 in v0.3.1, requires Windows C++ DLL work
- If #312 is too large for one session, break into sub-issues
