# QA Status
Last updated: 2026-04-01 21:31
Current round: 79
Current milestone: v0.3.2

## This Round
- CI Desktop Tests: 14 passed, 1 failed (known #777), 18 skipped, 3 xfailed, 1 xpassed (commit 780642e)
- Issues verified: none pending
- E2E tests: Calculator (pass), Notepad (pass)
- Regression: 16/16 passed, 6 skipped (infrastructure)
- Test cases retired: TC-0034 (capture Chinese filepath, #693 closed, 6 passes)
- New test cases created: none
- New issues created: none
- Total active test cases: 26
- Tests run: 22+

## Top 3 Risks
1. **CI Unicode DLL failure (#777)** — naturo_core.dll capture_screen still fails with Unicode paths in CI. CLI path works via Python PIL fallback, but C++ bridge is broken.
2. **AI Vision / Hybrid mode tests untestable** — 6 test cases always skipped due to missing API keys and Electron apps. Coverage gap growing.
3. **v0.3.2 scope tripled** — 31 open issues including browser automation pivot. Risk of shipping with insufficient QA on new browser features.
