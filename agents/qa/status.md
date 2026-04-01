# QA Status
Last updated: 2026-04-02 05:00 UTC
Current round: 88
Current milestone: v0.3.2

## This Round
- CI Desktop Tests: 1 failed, 5 passed, 18 skipped (commit 672d998); E2E: 9 passed, 2 xfailed, 2 xpassed
- Issues verified: none pending
- E2E tests: Notepad (pass), Calculator (fail — invisible #785)
- Regression: 6/7 passed, 1 failed (TC-0031 menu click), 0 retired
- New test cases created: TC-0044 (click coords out-of-bounds)
- Test cases cleaned up: none
- New issues created: #787 (P2 click coords out-of-bounds)
- Total active test cases: 27
- Tests run: 7 regression + CI suite + exploratory

## Top 3 Risks
1. UWP Calculator completely invisible to naturo after launch — PID mismatch with UWP launcher (#785)
2. Menu click regression on UWP Notepad — broken for both click eN and keyboard Alt+F (#786)
3. No status:done issues for 72+ hours — QA verification pipeline idle, no Dev fixes to verify
