# QA Status
Last updated: 2026-05-27 22:17
Current round: 118
Current milestone: v0.3.2

## This Round
- CI Desktop Tests: skipped (pytest run hangs in browser/launch_chrome trying CDP port; same blocker class as #842)
- Persona: Scripter/Automator (hour 22 % 8 = 6)
- Issues verified + closed: **none** — session-1 (Naturobot) disconnected mid-round; all desktop ops returned NO_DESKTOP_SESSION
- Issues NOT attempted: #786, #788, #807, #840, #843 (all 5 still blocked on #863)
- New issues created: **#864** (P2, bug, from:qa) `--id eN` rejected by 8 of 9 element-targeting commands; **#865** (P2, bug, from:qa) `see -j` bare tree on success vs envelope on error
- Updated #863 with broader-scope evidence (entire desktop binding can drop after RDP reconnect, not just SendInput)
- Phase 5 regression: skipped (input/desktop-dependent; would falsely claim coverage)
- Phase 6 test cases: **TC-0052** (get/type/press/find/etc reject --id), **TC-0053** (see -j envelope inconsistency)
- Cleanup: re-killed 14 stale Notepad processes via `taskkill /F /IM Notepad.exe`; UWP Notepad still resurrected the same tabs on next launch (suspended-state restore)
- Tests run: 49 distinct exploratory checks (scripter-focused: help parse 12, --id matrix 9, JSON envelope matrix 12, source inspection 2, smoke 3, subprocess exit-code matrix 11)

## Status:done queue
- Started: 5
- Verified + closed: 0
- Rejected: 0
- Partial-verify, retained: 5 (no movement from round 117)
- **End of round**: 5 (#786, #788, #807, #840, #843) — all blocked on #863

## Top 3 Risks
1. **#863 broader than originally framed.** Round 118 confirmed the SendInput block is the leading edge of a full interactive-desktop-binding loss. After RDP disconnect/reconnect, the QA process is pinned to session 1 (now disconnected), while console session 2 holds the active desktop. ALL naturo desktop commands fail, not just input. Workaround: launch QA from console session, not RDP.
2. **UWP Notepad tab leak persists across rounds.** `taskkill` clears the process but UWP Application Frame Host restores the multi-tab session on next launch from suspended state. 14 stale tabs from rounds 100-116 keep reappearing. Need a UWP-aware close (`naturo app quit notepad --force --no-restore`) or shell-level UWP package suspension.
3. **JSON contract drift across CLI surface.** Three patterns coexist: (a) `list <x> -j` envelopes both ways, (b) `see -j` bare-tree on success + envelope on error (#865), (c) Click-level validation errors emit Usage text + exit=2 regardless of `-j`. AI agents and scripters cannot rely on a uniform discriminator. Sweep PR recommended before v0.3.4 marketing push.
