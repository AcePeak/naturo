# QA Status
Last updated: 2026-04-02 03:17 UTC
Current round: 86
Current milestone: v0.3.2

## This Round
- CI Desktop Tests: 115 passed, 1 failed (known #777), 18 skipped (commit b2e21f4)
- CI E2E Tests: 9 passed, 2 xfailed, 2 xpassed
- Issues verified: none (no status:done issues)
- E2E tests: Notepad (pass), Calculator (env issue — can't launch)
- Regression: 11/11 passed, 0 retired
- New test cases created: none
- Test cases cleaned up: none
- New issues created: none
- Total active test cases: 22
- Tests run: 11 regression + E2E + exploratory + CI suite

## Top 3 Risks
1. **Calculator UWP launch broken in environment** — Calculator process starts but window never appears. Can't test Calculator E2E flows.
2. **CI Unicode DLL failure (#777)** — naturo_core.dll capture_screen still fails with Unicode paths. CLI workaround works via Python PIL fallback.
3. **Open P1 bugs (#781, #783, #784)** — JSON exit codes, duplicate stderr, type -E newline dropping — all affect scripting use cases.
