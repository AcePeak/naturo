# QA Round 17 Report — 2026-03-24 03:12 CST

**QA-Mariana** | L1 Functional — UX Merge Verification + Regression | Compile Machine (SSH)

## Environment

- **Machine**: Compile (100.113.29.45) via SSH
- **naturo version**: 0.2.1 (latest — git pull + pip install -e . successful)
- **Git**: Updated from `941c9c9` to `975c15d` (5 new commits)
- **Desktop session**: Disconnected console — headless-safe tests only
- **Screen**: 1024×768 @ 96 DPI, 1.0x scale
- **CI (Mac)**: 1505 passed, 480 skipped — **all green**

## GitHub HTTPS Access: Restored ✅

Round 16 reported git pull failing (port 443 timeout). Resolved now — git proxy config (`http.proxy http://127.0.0.1:7890`) in place and working. Pull + install completed cleanly.

## Verification Focus: Recent Merges (#163, #170, #172)

### #163 — Hide snapshot commands from top-level help ✅
- `naturo --help` no longer shows `snapshot` — **verified**
- `naturo snapshot list --help` still works (hidden but accessible) — **good backward compat**

### #170 — Merge window commands into app ✅
- `naturo --help` shows `app`, not `window` — **verified**
- `naturo app --help` shows all subcommands (close, find, focus, inspect, launch, list, maximize, minimize, move, quit, relaunch, restore, windows) — **verified**
- `naturo window --help` still works with deprecation notice: "use 'naturo app' instead" — **good backward compat**
- `naturo --json app list` returns valid JSON `{"success": true, "apps": [], "count": 0}` — **verified**
- `naturo --json app windows` returns valid JSON — **verified**
- `naturo --json app find notepad` correctly finds running process — **verified**
- `naturo --json app inspect notepad` returns method probe info — **verified**
- `naturo app move` without args gives clear error: "Specify an app name, --window, or --hwnd" — **verified**

### #172 — Merge hotkey into press ✅
- `naturo --help` shows `press`, not `hotkey` — **verified**
- `naturo press --help` shows combined usage with examples for both single keys and combos — **verified**
- Help text includes migration hint: "ctrl+c (was: hotkey)" — **good UX**
- `naturo hotkey --help` still works with deprecation notice — **good backward compat**

## Additional Tests

### Fuzzy command matching (#149) ✅
- `naturo clik` → "Did you mean 'click'?" — **verified**
- `naturo caputre` → "Did you mean 'capture'?" — **verified**

### Wait command simple duration (#169) ✅
- `naturo wait 2` → "Waited 2.0s" — **verified**
- `naturo --json wait 1` → `{"success": true, "mode": "duration", "wait_time": 1.0}` — **verified**
- `naturo wait 0` → succeeds (zero wait) — **verified**
- `naturo wait -- -5` → "Duration must be >= 0, got -5.0" — **boundary check OK**

### Edge case: `naturo wait 2s` → ❌ UX issue (P3)
- Error: "Invalid value: '2s' is not a valid float"
- User expectation: `2s` should be a natural way to express "2 seconds"
- Not a bug per se, but a "least astonishment" violation — users will try `2s`, `500ms`, etc.
- **Recommendation**: Accept human-friendly duration strings (low priority, P3)

### Capture ✅
- `naturo --json capture live` → screenshot saved, valid JSON with width/height/dpi — **verified**

### Error messages ✅
- `naturo see` (no desktop) → clear JSON error with suggested_action — **good**
- `naturo app move` (no target) → clear error with guidance — **good**
- `naturo press nonexistentkey` (SSH) → NO_DESKTOP_SESSION (correct, can't test key validation without desktop)

## Status:Done Issues Pending Verification

**None.** All previously tagged `status:done` issues have been verified.

## Open Bugs

**None.** Zero open bugs in the tracker.

## CI Regression Check

1505 tests passed, 480 skipped — **no regressions** from the 5 recent commits.

## Quality Assessment

### Current State: **Solid** 🟢

v0.2.1 is in good shape. The UX merges (hotkey→press, window→app) are clean with proper backward compatibility via deprecated aliases. Fuzzy matching and improved error messages continue to raise the bar.

### Top 3 Observations

1. **Backward compat done right** — deprecated commands (hotkey, window, snapshot at top-level) still work with clear migration messages. No breakage for existing scripts. This is how it should be done.

2. **CLI polish is accumulating** — fuzzy matching, better errors, `--see` flag on interaction commands, wait simple duration. Each small, but together they make a noticeably better UX.

3. **Desktop-dependent testing gap** — SSH session can't test actual UI interaction (press, click, see). RDP console session is disconnected. Full L2/L3 testing requires an active desktop session.

### Risk

- **No desktop session** limits verification depth. Core UI commands (see→click pipeline, press actual keys) are tested by CI mocks but not on real desktop this round. Need an RDP session for thorough L2 testing next time.

---

*Round 17 complete. Next round should prioritize L2 user experience testing with an active desktop session.*
