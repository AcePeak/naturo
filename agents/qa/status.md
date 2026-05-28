# QA Status
Last updated: 2026-05-29 00:00
Current round: 144
Current milestone: v0.3.2 (27 open, ship-gated by epic #885 + 5 SendInput-blocked status:done from console session)

## This Round
- CI Desktop Tests: skipped (HEAD `893209e` differs from `.last-ci-sha` `426477d`, but `git diff --stat 426477d..HEAD` shows only `agents/qa/**` + `tests/qa-reports/**` paths — single `[skip ci]` R143 report commit, zero source changes). Sentinel will advance to `893209e`.
- Persona: First-time User (hour 00 mod 8 = 0)
- Session: NO_DESKTOP_SESSION (Naturobot user, non-interactive — same constraint as R134–R143)
- Issues verified: none new (5 status:done all SendInput-blocked from this session; comment threads already comprehensive — no piling-on)
- E2E tests: skipped (no desktop)
- Regression: **12/12 testable-from-NO_DESKTOP TCs re-confirmed FAIL on HEAD `893209e`** (TC-0054 #866, TC-0055 #867, TC-0057 #869, TC-0061 #874, TC-0062 #875, TC-0063 #876, TC-0065 #878, TC-0067 #880, TC-0079 #893, TC-0080 #894, TC-0081 #895, TC-0083 #897)
- Phase 4 (First-time User): walked the "freshly `pip install naturo`-d user" path on NATUROBOT. Major papercut: **`-h` short flag rejected everywhere** — every Click-based CLI a first-time user has touched (git/curl/pip/python/man/ls/...) accepts `-h`, but `naturo -h`, `naturo see -h`, `naturo app launch -h` all emit `Error: No such option: -h` exit 2. Filed as **#899** (P2 v0.3.4 enhancement). One-line fix at root: `context_settings={'help_option_names': ['-h', '--help']}` propagates to every subcommand. Adjacent finding: the FuzzyGroup typo suggester also leaks `help` as a third hidden command (R136 found `snapshot`, `hotkey`; R144 adds `help`), so `naturo helo` → "Did you mean 'help'?" but `naturo help see` exits 2 — dead-end suggestion. Commented on #867 extending the leaked-hidden-command class to {snapshot, hotkey, help}.
- New issues created: **#899** (P2 v0.3.4 enhancement — accept `-h` as `--help` alias, POSIX convention, First-time User papercut).
- Comments added: **#867** (extension — `help` is a third leaked hidden command; same one-line fix covers all three).
- New test cases created: **TC-0084** (`-h` short flag not accepted, #899).
- Test cases updated: R144 last_run/notes set on TC-0054, TC-0055, TC-0057, TC-0061, TC-0062, TC-0063, TC-0065, TC-0067, TC-0079, TC-0080, TC-0081, TC-0083. **Restored TC-0080 YAML body** (`exploratory/json-ensure-ascii-escapes-chinese.yaml`) — file was inadvertently emptied during R143 testcase folder edits while CATALOG.md still referenced it; recovered from commit `2e7761a` (R139 last-good).
- Test cases cleaned up: none.
- Total active test cases: **63** (62 → 63 with TC-0084).
- Tests run: 12 regression re-verifications + ~25 envelope/exit-code probes across 20+ commands + first-time-user shell session walk-through (pip show / --help / -h / typos / config show / common subcommand sampling) + 1 new issue filed + 1 issue scope-extended + 1 TC restored.

## Top 3 Risks
1. **Exit-code + envelope contract is still un-script-able, ship-gated.** Nothing moved on the open cluster (#864–#884, #886, #889–#891, #893–#899) between R143 and R144. The First-time User angle adds a new edge: a user who learned `-h` from any POSIX CLI hits "No such option: -h" exit 2 as their first interaction (#899). That sits on top of the FuzzyGroup leaking 3 hidden commands (#867), the `naturo doctor` discoverability gap (#898), and the 12-callsite envelope drift cluster. None of these alone are fatal, but together they make naturo feel un-polished at first touch — exactly when retention is decided.
2. **`naturo doctor` gap (#898) is still the highest-leverage single fix for first-time UX.** R144 reinforces R143's finding: a fresh user has to run 6+ probes to answer "is my environment OK?" and one of those probes (`desktop list -j`, #869) actively misleads them by leaking an install prompt before the JSON envelope. #898 + #869 fix + #899 fix together close the first-30-seconds friction surface with one PR each, none touching production hot paths.
3. **Same risk as R142–R143: 5 SendInput-blocked `status:done` unverified ~32h** after restructured ship gate; only Ace's console-session run or a #863 workaround moves this. R144 made no progress (same NO_DESKTOP session); same as R134–R143.

## Environment
- Windows 11 Pro 10.0.26200.8457
- naturo 0.3.1 (HEAD `893209e`)
- Runner: NATUROBOT (Naturobot user), NO_DESKTOP_SESSION
