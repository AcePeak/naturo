# Dev Status
Last updated: 2026-03-28T03:20:00Z
Session: Win32+UIA hybrid enumeration (#312) + PR triage

## This Session
- **Issue #312 (v0.3.1, P1):** PR #493 created. Implemented Win32+UIA hybrid enumeration for VB6/ActiveX apps — Win32 HWND tree as base with UIA drill-down for complex controls (VSFlexGrid, SysListView32, SysTreeView32, AfxOleControl42u). Auto mode now uses hybrid instead of pure Win32 for shallow trees. 15 new tests.
- **PR #492** (selector CLI flag): Windows DLL tests cancelled (timeout ~55min). Updated branch to trigger fresh CI.
- **PR #489** (Orc-Mycelium CI diagnosis): Same Windows timeout pattern. Updated branch.
- Tests: 1921 passed, 548 skipped, 0 failed (Ubuntu)
- PRs: #493 created (CI running), #492 and #489 branches updated

## Open PRs
- #493 — feat: Win32+UIA hybrid enumeration (fixes #312) — CI running
- #492 — feat: add --selector flag to click/type/press (fixes #103) — CI re-running after branch update
- #489 — (Orc-Mycelium) dev-prompt CI diagnosis protocol — CI re-running after branch update

## Current State
- Earliest open milestone: v0.3.1 (#312 — PR created, pending merge)
- Next milestone: v0.3.2 (#361, #102)
- CI: GREEN on main; Windows DLL tests flaky on PR branches (timeout/cancel)
- Known CI issue: Windows DLL test job hangs at ~55 min, gets cancelled. Affects all PRs.

## Next Session Should
1. **Check CI on PR #493** — merge if green, fix if red. Enable auto-merge.
2. **Check CI on PR #492** — merge if green after branch update
3. **Investigate Windows DLL test timeout** — all 3 open PRs have the same cancellation pattern. May need a CI timeout fix or test isolation.
4. **Issue #361 (v0.3.2, P1)** — Stable app/window ID system for scripting
5. **Issue #102 (v0.3.2)** — Wire SelectorBuilder into `see` command output
