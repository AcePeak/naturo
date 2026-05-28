# QA Status
Last updated: 2026-05-28 10:00
Current round: 130
Current milestone: v0.3.2 (21 open, ship-gated by #863)

## This Round
- CI Desktop Tests: 138 desktop/integration + 13 e2e tests SKIPPED at HEAD `eee1ad5` (no interactive desktop). 0 failures, 0 passes. `.last-ci-sha` updated.
- Persona: Enterprise RPA Dev (hour 10 mod 8 = 2)
- Session: NO_DESKTOP_SESSION (services session; console session 2 not bindable from agent shell)
- Issues verified: none (all 5 status:done still blocked by #863; partial verifications on record from R117)
- E2E tests: skipped (no desktop)
- Regression: 21 contract-level test cases re-run — 3 pass (TC-0046, TC-0042-exploratory, TC-0049 bumped), 18 fail (bugs still reproduce, `consecutive_passes` reset to 0). Desktop test cases skipped.
- MCP end-to-end probe: 9 tool calls (initialize, tools/list, capture_screen×2, see_ui_tree, type_text×3 incl. Pydantic-type-error, click, press_key, list_windows); surfaced 1 new silent-failure bug (#883)
- Enterprise RPA 10-step workflow scripted with `-j`: every step exited 1, every envelope parseable, `set -e` viable
- New test cases created: TC-0070 (mcp-list-windows-silent-success, #883)
- Test cases cleaned up: none
- New issues created: #883 (P1, v0.3.4, silent-failure)
- Data points added: #863 (12th+ consecutive round)
- Total active test cases: 49 (was 48 + TC-0070)
- Tests run: 151 CI tests (all skipped due to no desktop) + 21 contract regressions + 9 MCP JSON-RPC probes + 10 scripted RPA-workflow probes

## Top 3 Risks
1. **Contract-drift surface still widening.** 19 open envelope/error-code/exit-code bugs now (#844, #864–883). +1 this round. A single contract-test harness over CLI + MCP would catch most of these pre-merge.
2. **#863 ship-gate unmoved for 21+ days.** Workaround (launch QA from console session) identified but not enacted. Five status:done items frozen behind it. Owner/decision still needed.
3. **NO_DESKTOP_SESSION silent-failure cluster keeps growing.** #868 (MCP capture_screen), #875 (dialog detect), #878 (CLI app windows), #883 (MCP list_windows). All same class — guard missing at resolver layer. One `require_interactive_desktop()` precondition would close the cluster.
