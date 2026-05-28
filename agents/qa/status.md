# QA Status
Last updated: 2026-05-28 11:09
Current round: 131
Current milestone: v0.3.2 (21 open, ship-gated by #863)

## This Round
- CI Desktop Tests: skipped (only commit since `eee1ad5` is R130 `[skip ci]` report; advanced `.last-ci-sha` to `2d15274`)
- Persona: Chinese User (hour 11 mod 8 = 3)
- Session: NO_DESKTOP_SESSION (services session 0; console session 2 active but not bindable from agent shell)
- Issues verified: none (5 status:done still blocked by #863; partial verifications on record from R117; no new #863 data point this round — 13+ already on file)
- E2E tests: skipped (no desktop)
- Regression: 3 contract-level test cases re-run — 2 pass (TC-0046 bumped to 28, TC-0042-exploratory bumped to 3), 1 fail (TC-0054 #866, stays at 0). Desktop test cases skipped.
- Phase 4 (Chinese User): CLI handles `--app 记事本`, `type "你好世界"`, `-o /tmp/中文路径/...` correctly; JSON uses `\uXXXX` escaping; MCP returns raw UTF-8 (initial mojibake was Python-on-Windows GBK stdout artifact, not server bug). No new Chinese-specific bugs.
- Envelope-shape probe: 13 commands across NO_DESKTOP_SESSION + stale-snapshot-ref paths → three distinct shapes (6/3/2 fields). Root cause: `json_error()` helper strips `category`/`context`/`recoverable` vs `NaturoError.to_json_response()`.
- New test cases created: TC-0071 (envelope-shape-drift, #884)
- Test cases cleaned up: none
- New issues created: #884 (P2, v0.3.4)
- Data points added: none (intentional — #863 has 13+; piling on without ownership decision adds noise)
- Total active test cases: 50 (was 49 + TC-0071)
- Tests run: 13 CLI envelope probes + 9 MCP JSON-RPC probes (initialize + see_ui_tree + launch_app + type_text variants) + 3 regression cases

## Top 3 Risks
1. **Contract-drift surface still widening.** 20 open envelope/error-code/exit-code bugs (#844, #864–884). +1 this round. Two parallel error-serialization paths (`NaturoError.to_json_response()` vs `cli/error_helpers.py json_error()`) — collapse into one helper would fix #884, partially close #877, prevent the next 3 of this class.
2. **#863 ship-gate unmoved for 21+ days.** Workaround identified, not enacted. Five status:done frozen. QA blocker-comments at diminishing returns — ownership/decision needed.
3. **NO_DESKTOP_SESSION silent-failure cluster (#868, #875, #878, #883) + envelope-drift cluster (#876, #877, #884) suggest JSON contract is highest-leverage to harden pre-v0.3.2.** A pytest contract-test harness over CLI + MCP would catch most pre-merge.
