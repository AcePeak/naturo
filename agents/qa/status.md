# QA Status
Last updated: 2026-05-27 21:29
Current round: 117
Current milestone: v0.3.2

## This Round
- CI Desktop Tests: skipped (no code changes since cf3e1fd Apr 5; only docs/reviews/workflow files touched)
- Persona: Accessibility User (hour 21 % 8 = 5)
- Issues verified + closed: #832 (refactor app_cmd), #833 (refactor _shell), #810 (MCP stdout JSON-RPC), #834 (browser -j flag), #841 (Calculator UIA detection)
- Issues REJECTED back to Dev: #844 — PR #853 fix is dead code due to FastMCP setup ordering (`server.call_tool` reassigned AFTER `_setup_handlers` already bound the original method); reproduced verbatim Pydantic-laden error. Detailed root cause posted; status:done removed.
- Issues partially verified (code + unit tests pass, runtime blocked by #863): #840 (type newlines), #843 (capture popup menu) — status:done retained, partial-verify comments posted.
- Issues NOT attempted (need input): #786, #788, #807
- New issues created: **#863** (P1, bug, from:qa) — SendInput blocked in QA session, runtime verification of input commands impossible. Root: ERROR_ACCESS_DENIED (5) from SendInput, likely UIPI / RDP-reconnect desktop binding.
- Phase 5 regression: skipped (input-dependent, blocked on #863)
- Phase 6 test cases: none created (no product-level new behavior to capture)
- E2E read-only checks: app launch/quit/find/inspect/list/see all OK; Notepad UWP 1 PID owns 14 tabs.
- Tests run: 13 verification scenarios + 28 unit test cases across the 5 verified fixes
- Cleanup: force-quit 14 stale Notepad windows left from rounds 100-116.

## Status:done queue
- Started: 11
- Verified + closed: 5
- Rejected: 1 (#844)
- Partial-verify, retained: 2 (#840, #843)
- Not attempted: 3 (#786, #788, #807)
- **End of round**: 5 (#786, #788, #807, #840, #843) — all blocked on #863

## Top 3 Risks
1. **#863 SendInput block** gates 5 of 5 remaining status:done verifications. v0.3.2 release blocked on either resolving the session UIPI issue OR explicit Ace authorization to accept code+unit-test as sufficient verification (would violate SOUL.md Iron Rule about screenshot evidence).
2. **#844 fix was dead code, undetected for 7 weeks** (PR #853 merged Apr 5). Unit tests passed; runtime path never exercised end-to-end. Suggests other FastMCP overrides done post-init may also be silently broken — audit recommended.
3. **UWP Notepad window leak across rounds** — rounds 100, 115, 116 each left unsaved test content as orphan tabs. Force-quit cleared them this round. App-lifecycle hygiene is in the QA prompt; need to actually follow it every round.
