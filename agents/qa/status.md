# QA Status
Last updated: 2026-04-01 22:22
Current round: 82
Current milestone: v0.3.2

## This Round
- CI Desktop Tests: 5 passed, 1 failed (known #777), 18 skipped, 2 xpassed; E2E: 9 passed (commit b7b83c2)
- Issues verified: none pending
- E2E tests: Calculator (pass), Notepad (pass)
- Regression: 12/12 passed, 2 retired (TC-0036, TC-0039)
- New test cases created: TC-0042 (JSON stderr duplicate error)
- Test cases retired: TC-0036 (#743 closed, 5 passes), TC-0039 (#752 closed, 5 passes)
- New issues created: #783 (P2, JSON stderr duplication)
- Total active test cases: 25
- Tests run: 20+

## Top 3 Risks
1. **CI Unicode DLL failure (#777)** — naturo_core.dll capture_screen still fails with Unicode paths in CI. CLI path works via Python PIL fallback, but C++ bridge is broken.
2. **AI Vision / Hybrid mode tests untestable** — 6 test cases always skipped due to missing API keys and Electron apps. Coverage gap growing.
3. **v0.3.2 scope tripled** — 31+ open issues including browser automation pivot. Risk of shipping with insufficient QA on new browser features.
