# QA Round 14 Report — 2026-03-23 15:36 CST

**QA-Mariana** | L0 Smoke + Bug Confirmation + Environment Check | Compile Machine (SSH)

## 🚨 Environment Issue: Compile Machine Cannot Git Pull

**Critical blocker for verification workflow.**

```
fatal: unable to access 'https://github.com/AcePeak/naturo.git/': Recv failure: Connection was reset
```

- Compile machine (100.113.29.45) is **2 commits behind** main
- Missing: #151 (app switch terminal exclusion) and #153 (help text formatting)
- Remote URL uses `x-access-token:gho_...` — token may be expired or network blocked
- **Cannot verify recent fixes until this is resolved**

## Dev Completions Check

No `status:done` issues pending QA verification. Recent closes (#151, #153) were auto-closed via merged PRs.

- CI: **All green** — latest 5 runs all `success`
- Version on compile machine: `naturo 0.2.1` (latest commit: `34a1c01`)
- Version on main: `1bb0a30` (2 commits ahead)

## Open Bug Confirmation

Tested on compile machine with current version (0.2.1):

### #165 — `type --paste` without TEXT → Still broken ❌
```
naturo type --paste --json
→ {"success": false, "error": {"code": "INVALID_INPUT", "message": "TEXT argument is required"}}
```
Expected: should paste from clipboard without requiring TEXT argument.

### #154 — `drag --from eN --to eN` → Still broken ❌
```
naturo drag --from e1 --to e2 --json
→ {"success": false, "error": {"code": "INVALID_INPUT", "message": "Specify --from-coords X Y (element-based drag coming in Phase 3)"}}
```
Still deferred to "Phase 3" despite issue saying it should work now.

### #161 — `scroll --on` → Cannot test (needs desktop session)
### #156 — `find --app` ignored → Cannot test (needs desktop session)
### #158 — `menu-inspect` only system menu → Cannot test (needs desktop session)

## L0 Smoke Results

| Command | Status | Notes |
|---------|--------|-------|
| `--help` | ✅ | 21 commands listed |
| `--version` | ✅ | `naturo, version 0.2.1` |
| `list screens --json` | ✅ | Valid JSON, 1024x768, 96 DPI |
| `list apps --json` | ✅ | Valid JSON (empty via SSH) |
| `list windows --json` | ✅ | Valid JSON + SSH warning |
| `capture live --json` | ✅ | Screenshot captured, correct dimensions |
| `tray list --json` | ✅ | Valid JSON (empty via SSH) |
| `taskbar list --json` | ✅ | Valid JSON (empty via SSH) |
| `snapshot list` | ✅ | Subcommands visible |

## Input Validation Testing

| Test | Result | Notes |
|------|--------|-------|
| `click --coords abc def` | ✅ | "not a valid integer" |
| `click --coords -1 -1` | ✅ | Proper NO_DESKTOP_SESSION (reaches execution) |
| `click --coords 99999 99999` | ✅ | Proper NO_DESKTOP_SESSION |
| `scroll down --amount 0` | ✅ | "--amount must be >= 1" |
| `scroll down --amount -5` | ✅ | "--amount must be >= 1" |
| `type --paste --file nonexistent.txt` | ✅ | "File not found" |
| `naturo notacommand` | ⚠️ | "No such command" but no suggestion |
| `naturo clck` | ⚠️ | "No such command" but no suggestion (relates to #149) |

Input validation is solid. Edge cases handled correctly.

## Fuzzy Command Matching (#149) — Still Not Implemented

`naturo clck` returns generic "No such command" with no "did you mean 'click'?" suggestion. Issue #149 is open and unassigned.

## Quality Assessment

**Current level: CLI framework solid, GUI testing severely limited.**

- Error handling and JSON output are consistent across all commands
- Input validation catches edge cases well
- But **10 open bugs** remain, mostly GUI-dependent (P1 level)
- Compile machine git connectivity blocks verification of new fixes

**Biggest risks:**
1. **Compile machine can't sync** — Dev is shipping fixes we can't verify
2. **No desktop session** — 6 of 10 open bugs require GUI to test/verify
3. **#165 and #154** are UX-impacting bugs that break user expectations

## Top 3 Actions Needed

1. **Fix compile machine GitHub access** — expired token or network issue, blocking all verification
2. **RDP session reconnection** — needed for GUI bug testing (#161, #156, #158, #137, #135, #150)
3. **Dev prioritize #165** (type --paste) — this is a user-expectation violation (Principle of Least Astonishment)
