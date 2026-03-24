# QA Round 15 Report — 2026-03-23 16:06 CST

**QA-Mariana** | L0 Smoke + Test Suite + Environment Verification | Compile Machine (SSH)

## Environment

- **Machine**: Compile (100.113.29.45) via SSH
- **naturo version**: 0.2.1 (latest from main, commit `ce2d894`)
- **Git pull**: ✅ Successful — pulled 3 new commits since Round 14 (the git access issue is resolved)
- **Desktop session**: Console session 1 exists (disconnected) — headless-safe tests only
- **Screen**: 1024×768 @ 96 DPI, 1.0x scale

## Dev Completions Check

**No `status:done` issues pending QA verification.** All recent PRs were auto-closed via merge.

Recent fixes pulled this round:
- `ce2d894` — scroll --on / --id coordinate resolution (#161 via #171)
- `1bb0a30` — app switch excludes calling terminal (#151 via #167)
- `5101012` — help text formatting fix (#153 via #162)

## Test Suite Results

### Core CLI tests (test_cli.py)
- **16 passed, 18 skipped** (skips are desktop-dependent, expected)
- 1 known failure: #145 (`see` in SSH without desktop)

### Full test suite (excluding desktop-dependent test files)
- **1,353 passed, 224 skipped, 21 desktop-only failures**
- All 21 failures are mouse/keyboard/UI tests requiring active desktop session — **expected via SSH**
- **No regressions detected** in headless-safe tests

## Open Bug Status

| Issue | Status | Notes |
|-------|--------|-------|
| #165 type --paste without TEXT | **Still open** | Confirmed: returns `INVALID_INPUT` instead of pasting clipboard |
| #164 tray/taskbar identical results | **Cannot verify** | Both return empty in SSH — needs desktop |
| #158 menu-inspect system menu only | **Cannot verify** | Needs desktop |
| #156 find --app ignored in non-AI | **Partially confirmed** | Returns WINDOW_NOT_FOUND — can't fully test without desktop |
| #154 drag --from eN --to eN | **Cannot verify** | Needs desktop |
| #150 comtypes dependency missing | **Cannot verify** | Needs desktop |
| #145 see fails in SSH | **Confirmed** | Known, P2 |
| #137/#135 TitleBar bounds (0,0 0x0) | **Cannot verify** | Needs desktop |

## Proactive Tests

### scroll --on/--id fix (#161)
- `naturo scroll down --coords 500 300 --json` → Returns `NO_DESKTOP_SESSION` (expected in SSH)
- The scroll help text correctly shows `--on` and `--id` flags
- Code review of commit `ce2d894` confirms the fix resolves target element coordinates

### capture live
- `naturo capture live --json` → ✅ Success, produced `naturo-screen-20260323-160800.png` (1024×768)

### list screens
- `naturo list screens --json` → ✅ Correct: 1 monitor, 1024×768, 96 DPI, primary

### Error messages
- `naturo see --json` → Clear error: `WINDOW_NOT_FOUND` with helpful suggestion
- `naturo type --paste --json` → Clear error: `INVALID_INPUT`

## Quality Assessment

**Current state: Stable but SSH-limited for deep verification.**

The codebase is healthy — 1,353 tests passing, no regressions. The git access issue from Round 14 is resolved. Recent Dev work (scroll fix, app switch fix, help text fix) all merged cleanly.

### Limitation
7 of 9 open bugs require active desktop session to verify. SSH-only testing has reached its ceiling for bug verification. All remaining open bugs (P1-P2) involve UI interaction that can't be tested headlessly.

### Top 3 Priorities
1. **Desktop session testing needed** — bulk of open bugs (#137, #135, #158, #164, #154, #150) are blocked on desktop access
2. **#165 type --paste** — confirmed broken, simple fix, would improve UX
3. **#145 see in SSH** — low priority but affects CI/test reliability

### Risk
No new bugs found this round. The product is stable at the CLI/API level. The risk area is UI interaction correctness (DPI, bounds, element targeting) which requires RDP/desktop testing to validate.

## Self-Check
1. L2 (UX) test? — Partial (CLI help text, error messages)
2. L3 (real machine)? — Yes, compile machine via SSH
3. "装傻" test? — N/A this round (all recent changes are internal fixes)
4. Design-level追问? — #165 is a design gap (--paste should work without TEXT)
5. Correctness vs "runs"? — Validated output values (screen resolution, capture dimensions)
6. New user satisfaction? — CLI basics solid, but UI interaction bugs would frustrate desktop users
