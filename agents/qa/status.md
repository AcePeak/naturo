# QA Status
Last updated: 2026-05-28 20:09
Current round: 140
Current milestone: v0.3.2 (27 open, ship-gated by epic #885 + 5 SendInput-blocked status:done from console session)

## This Round
- CI Desktop Tests: skipped (no source changes since `ceecfd5` — only QA-report `[skip ci]` commits R138 `16adca7` and R139 `2e7761a` in interval). Reconciling `.last-ci-sha` to `2e7761a` on commit.
- Persona: Power User (hour 20 mod 8 = 4)
- Session: NO_DESKTOP_SESSION (ROBOT-COMPILE / Naturobot user, SSH session — no interactive desktop bind)
- Issues verified: none (5 status:done all SendInput-blocked from this session — no state change since R139, no fresh comments per Orc-Mycelium "piling on has diminishing value" escalation)
- E2E tests: skipped (no desktop)
- Regression: **8/8 testable-from-NO_DESKTOP TCs re-confirmed FAIL on HEAD `2e7761a`** (TC-0054, 0062, 0065, 0067, 0071, 0076, 0079, 0080)
- Phase 4 (Power User): probed every Power-User concern reachable from NO_DESKTOP_SESSION. Read-only enumeration (`app windows -j` bypass per #878) confirms 14 real windows on the host with 1 Chrome / 1 Clash / 2 Windows Terminal tabs / 5+ File Explorer windows / 0 Notepad / 0 Calculator / 2 Chinese-titled windows (escaped as `\uXXXX` per #894). NEW envelope drift inside `naturo wait` itself: duration mode emits `{success, mode, wait_time}` (3 keys), predicate modes `--gone`/`--window`/`--element` emit `{success, found, wait_time, warnings}` (4 keys, no `mode` discriminator). Consumers must branch on input args to parse output.
- New issues created: **#895** (P2 v0.3.4 — naturo wait JSON success envelope drifts across sub-modes).
- Comments added: none (per Orc-Mycelium escalation: no fresh pile-on comments on #863 / status:done; new finding goes straight to a fresh issue).
- New test cases created: **TC-0081** (exploratory/wait-success-envelope-drift, source #895).
- Test cases updated: none (R139 already updated TC-0054/0062/0079; same-day re-run does not change `last_run` or `consecutive_passes`).
- Test cases cleaned up: none.
- Total active test cases: **60** (+1).
- Tests run: ~40 CLI probes (exit-code matrix, conflict flags, boundary args, sub-mode envelopes) + 8 regression re-verifications + 1 new TC drafted.

## Top 3 Risks
1. **#885 epic still entirely on Dev-Sirius's queue (idle 53+ days).** R140 adds yet another contract-drift finding (#895) on top of #864–#884. Cluster now spans 13 filed P2/P1 bugs against the `-j` JSON output surface. None ship-blocking individually; collectively they undermine README's ✅ "AI Agent Ready: JSON output" claim (#887). Until #885 closes and a centralized envelope contract lands with a CI schema-validator gate, every new desktop-required command will compound this matrix.
2. **5 SendInput-blocked status:done unverified ~28h** after restructured ship gate. R140 made no progress here — only Ace's console-session run or a #863 wrapper can move this. v0.3.2 ship gate cannot close.
3. **Silent-failure cluster (#885) still has ≥7 entrypoints in the wild** (`dialog detect`, `taskbar list`, `tray list`, `app windows`, `wait --gone`, MCP `list_windows`, MCP `capture_screen`). Agents querying any of these from NO_DESKTOP contexts hallucinate from empty/black/stale data. Restructured ship gate makes #885 the gating Dev work, but no Dev movement in R136–R140.

## Environment
- Windows 11 Pro 10.0.26200
- naturo 0.3.1 (HEAD `2e7761a`)
- Runner: ROBOT-COMPILE (Naturobot user), NO_DESKTOP_SESSION
