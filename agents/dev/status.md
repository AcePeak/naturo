# Dev Status
Last updated: 2026-03-28T10:15:00Z
Session: CI gate fix + security/infra improvements

## This Session
- **PR #516 created**: CI Gate job to unblock auto-merge (fixes #510, P1)
- **PR #517 created**: Enable Dependabot for pip + GitHub Actions (fixes #416)
- **PR #518 created**: README badges — downloads, platform, pyversions (fixes #49)
- **PR #519 created**: CodeQL security scanning for Python and C++ (fixes #417)
- Tests: 2001 passed, 373 skipped, 0 failures
- PRs: 4 created this session, 2 from previous session (#513, #515) still open

## Current State
- Earliest open milestone: v0.3.4 (issues #416, #417, #49 now have PRs)
- CI: GREEN on main (Windows DLL failure is expected/non-blocking)
- Open PRs: #513 (README docs), #515 (agent tests), #516 (CI gate), #517 (Dependabot), #518 (badges), #519 (CodeQL)
- Blocker: PR #516 needs manual merge by admin (chicken-and-egg — the CI gate fix itself is blocked by the problem it fixes). After merge, update branch protection to require only "CI Gate".

## Next Session Should
1. **Check if PR #516 (CI gate) was merged** — if yes, verify auto-merge works on remaining PRs
2. **Check remaining PRs** (#513, #515, #517, #518, #519) — merge if CI green, address any review feedback
3. **Code health**: `backends/windows.py` is 4005 lines (#411) — consider splitting into submodules
4. **Backlog**: Pick highest-impact P2 issues (e.g., #411 refactor, #412 input strategy, #419 release notes automation)
5. **Self-driven**: test first-user experience, find friction in CLI output and error messages
