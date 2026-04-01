# QA Status
Last updated: 2026-04-01 20:33
Current round: 80
Current milestone: v0.3.2

## This Round
- CI Desktop Tests: 5 passed, 1 failed (known #777), 18 skipped (commit 1850476)
- CI E2E Tests: 9 passed, 3 xfailed, 1 xpassed
- Issues verified: none pending
- E2E tests: Calculator (pass), Notepad (pass)
- Regression: 19/19 passed, 3 skipped (no Electron app), 0 retired
- New test cases created: none
- Test cases cleaned up: none
- New issues created: none
- Total active test cases: 22
- Tests run: 19

## Top 3 Risks
1. **CI Unicode DLL failure (#777)** — naturo_core.dll capture_screen still fails with Unicode paths in CI. CLI path works via Python PIL fallback, but C++ bridge is broken.
2. **AI Vision tests untestable** — TC-0026/0027/0029 consistently skipped because no Electron app is installed on the test machine. Vision fill-gaps and hybrid mode remain unverified.
3. **Explorer performance** — `naturo see --app explorer` takes ~50 seconds due to massive element tree. Power users with many Explorer windows will experience significant latency.
