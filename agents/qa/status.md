# QA Status
Last updated: 2026-04-02 19:15
Current round: 99
Current milestone: v0.3.2

## This Round
- CI Desktop Tests: 5 passed, 1 failed (#777 unicode path), 18 skipped (commit 028fd50). E2E: 9 passed, 3 xfail, 1 xpass
- Issues verified: none pending
- E2E tests: Calculator (pass), Notepad (pass)
- Regression: 7/11 passed, 4 failed (all known: #777, #783, #784, #787)
- New test cases created: none
- Test cases cleaned up: none
- New issues created: none (all failures match existing issues)
- Total active test cases: 25
- Tests run: 11 regression + E2E + exploratory + Chinese user simulation

## Top 3 Risks
1. **type -E newline drop (#784)** — P1: Multiline text automation broken in keystroke mode; workaround: use --paste
2. **JSON stderr duplication (#783)** — P2: click -j still emits duplicate error to stderr, breaks 2>&1 pipe
3. **Unicode path in C++ DLL (#777)** — P1: Chinese users get file I/O errors on capture_screen with Chinese paths
