# QA Status
Last updated: 2026-05-29 07:06
Current round: 151
Current milestone: v0.3.2 (30 open / 89 closed)

## This Round (Skeptical Evaluator persona, no-desktop session, HEAD ec07c24)
- CI Desktop Tests: skipped (no source changes since 17aefe6 — diff is only qa-reports/testcases/docs)
- Issues verified: none — 5 status:done (#786/788/807/840/843) all need runtime input/desktop; blocked by #863 (ship-gate, needs console session). Not closed, not rejected.
- E2E tests: blocked (no interactive desktop this session)
- Guard cluster on ec07c24: positive-lock (TC-0088) PASS; #878/#875/#893 silent-failure cluster STILL PRESENT (identical to R150); MCP list_apps also leaks real apps (success:true)
- CLI-contract spot-confirms unchanged: #873 (serverInfo=1.26.0), #874 (-j --version bypass), #876 (selector list {}), #899 (-h rejected)
- Regression: 1/8 pass (positive-lock 3→4), 7/8 bug-repro cases correctly still failing, desktop cases blocked; 0 retired
- New test cases created: none (library saturated for no-desktop surface)
- Test cases cleaned up: none
- New issues created: none (all findings map to open issues — no duplicates filed)
- Total active test cases: ~50
- Tests run: ~20 commands + MCP initialize/tools-list/list_apps end-to-end

## Skeptical Evaluator verdict
Would prototype on naturo (CLI+MCP+element-tree beats pyautogui coords / pywinauto library-only),
but would NOT ship an unattended agent until #885 guard cluster + JSON-envelope drift
(#874/#876/#882/#884) close. Small, high-leverage gate — not a feature backlog. Aligns with #887.

## Top 3 Risks
1. Dev-Sirius idle 54 days; #885 (P0 adoption-blocker) unfixed across releases — process risk, not discovery risk.
2. Agent-readiness claims contradicted (#887): MCP success:true on context-invalid calls is the worst failure mode for the "built for AI agents" pitch.
3. Ship gate environmentally stuck: 5 status:done input fixes unverifiable without console/RDP (#863) — no agent-session round can clear them.
