# Dev Status
Last updated: 2026-03-28T04:15:00Z
Session: Highlight improvements (#313) + PR monitoring

## This Session
- **Issue #313 (v0.3.1, P2):** PR #494 created. Replaced 3-flash GDI cycle with simultaneous persistent display. Added depth-based coloring, label collision avoidance, actionable-only default (`--all` flag), `--annotate` PIL mode, `--filter` by role. 19 new tests.
- **PR #492** (selector CLI): Windows DLL test still in_progress (~55 min). 5/6 checks green.
- **PR #493** (Win32+UIA hybrid): Same — Windows DLL test still running. 5/6 checks green.
- **PR #489** (Orc-Mycelium): Same pattern.
- Tests: 30 passed, 1 skipped, 0 failed (local Ubuntu — annotate + highlight + CLI consistency)
- PRs: #494 created (CI running), #492/#493 still awaiting Windows DLL test

## Open PRs
- #494 — feat: highlight simultaneous display, label avoidance, annotate mode (fixes #313) — CI running
- #493 — feat: Win32+UIA hybrid enumeration (fixes #312) — Windows DLL test in_progress
- #492 — feat: add --selector flag to click/type/press (fixes #103) — Windows DLL test in_progress
- #489 — (Orc-Mycelium) dev-prompt CI diagnosis protocol — Windows DLL test in_progress

## Current State
- Earliest open milestone: v0.3.1 (#312 PR #493 pending, #313 PR #494 pending)
- Next milestone: v0.3.2 (#361, #103 PR #492 pending)
- CI: GREEN on main; Windows DLL test job runs very long on PR branches
- Auto-merge: could not enable yet (checks still in_progress)

## Next Session Should
1. **Check CI on all PRs** — enable auto-merge on any that passed. Fix if red.
2. **Investigate Windows DLL test duration** — all 4 open PRs have the same slow pattern. May need test timeout or isolation fix.
3. **Issue #361 (v0.3.2, P1)** — Stable app/window ID system for scripting (next after v0.3.1 clears)
4. **Issue #102 (v0.3.2)** — Wire SelectorBuilder into `see` command output
