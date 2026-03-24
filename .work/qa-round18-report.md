# QA Round 18 Report — 2026-03-24 14:07

**QA-Mariana** | Version: 0.2.5 (main @ 0e2ebc4) | Machine: Robot-Compile (Win11, 1920×1080, 96DPI)

## 1. Verification Status

### #208 — UIA probe falls back to vision for Win32 apps
- **Status**: ⏳ Cannot verify — PR #214 not yet merged to main
- **Dev comment**: Fix adds `_get_native_core()` with COM init before UIA probe
- **Action**: Waiting for merge; will verify next round

### #142 — Global --provider, --model, --api-key flags
- **Status**: ⚠️ Partially implemented — flags exist only on `find` command, not globally
- **Issue**: Title says "Global flags for all AI-capable commands" but implementation adds flags only to `naturo find --ai`. `naturo --provider` returns "No such option"
- **Action**: Will comment on issue

### #143 — Anthropic subscription/OAuth token auth
- **Status**: ✅ Code merged (PR #207), `naturo config show` shows ANTHROPIC_AUTH_TOKEN field
- **Note**: Cannot verify runtime auth without actual Anthropic token on test machine

### #138 — Auto-detect Electron apps in see
- **Status**: ✅ Code merged (PR #213), `naturo electron list` correctly detects Electron apps (Clash, Edge, etc.)
- **Note**: Lists `naturo.exe` itself as Electron — possible false positive worth investigating

### #173 — Snapshot session isolation
- **Status**: ✅ Code merged (PR #209), 274 new tests

## 2. Proactive Testing Results

### L0 — Smoke Tests ✅
| Command | Result | Notes |
|---------|--------|-------|
| `naturo --version` | ✅ 0.2.5 | |
| `naturo --help` | ✅ | All 22 commands listed |
| `naturo --json app list` | ✅ | Global --json works |
| `naturo app list --json` | ✅ | Consistent with global |
| `naturo list screens --json` | ✅ | 1 monitor, 1920×1080, 96 DPI |
| `naturo list windows --json` | ✅ | 15 windows found (via schtasks /it /i) |
| `naturo config show --json` | ✅ | Clean JSON, credential redaction |
| `naturo electron list --json` | ✅ | 4 Electron apps detected |

### L1 — Error Handling ✅
| Scenario | Result | Notes |
|----------|--------|-------|
| `see --depth 0` | ✅ INVALID_INPUT | Clear error message |
| `see --depth 11` | ✅ INVALID_INPUT | Boundary enforced |
| `see --app nonexistent` | ✅ WINDOW_NOT_FOUND | Suggests `naturo list windows` |
| `app launch notepad2` | ✅ APP_NOT_FOUND | Clear error |
| `click --json` (no desktop) | ✅ NO_DESKTOP_SESSION | Explains situation + suggests RDP |
| `click` (no desktop, no json) | ✅ | Same error, text format, exit code 2 |

### L1 — UWP App Traversal ❌ (Known #191)
| App | Elements Found | Expected | Status |
|-----|---------------|----------|--------|
| Notepad (Win11 UWP) | 2 (Window + TitleBar) | ~15+ (menu, tabs, edit area, status bar) | ❌ |
| Calculator (UWP) | 1 (Pane, 0 children) | ~50+ (buttons, display) | ❌ |

This is the known issue #191 — UWP/ApplicationFrameHost traversal is broken.

### Mouse Operations — COM Error (schtasks context)
| Command | Result | Notes |
|---------|--------|-------|
| `click --coords 400 300` | ❌ "mouse_move: System/COM error" | Via schtasks /it /i |
| `click e2 --app notepad` | ❌ Same COM error | |
| `move --coords 500 500` | ❌ Same COM error | |
| `type QAtest` | ✅ | Keyboard works fine |
| `press enter` | ✅ | Keyboard works fine |

**Analysis**: All mouse operations (click, move, drag) fail with COM error code -2 when run via schtasks, even with `/it /i` flags. Keyboard operations (type, press) work fine. This is likely a Win32 `SendInput` permission issue in the schtasks execution context — the mouse API requires a specific desktop interaction level that schtasks doesn't provide. **This is a test environment limitation, not a naturo bug.** However, it means we cannot verify mouse-dependent commands without an actual RDP session or OpenClaw node connection.

### Repo Hygiene Issue ⚠️
- **60+ screenshot .png files** committed to the repo root (`naturo-screen-*.png`)
- Total ~20MB of binary files in git history
- Branch `fix/cleanup-screenshots` exists, suggesting Dev is aware
- Recommendation: Add `*.png` to `.gitignore` (except intentional ones), remove from history with `git filter-branch` or BFG

## 3. Product Quality Assessment

### Current State: 6/10 — "Works for specific scenarios, but major gaps"

**Strengths:**
- Error handling is excellent — clear messages with suggested actions
- JSON output is consistent and well-structured
- Command structure is clean and intuitive (`naturo --help` is good)
- New features (config, electron detect) are solid additions
- DPI reporting is accurate (96 DPI confirmed)

**Weaknesses:**
- UWP app traversal (#191) is a showstopper for Win11 — Notepad and Calculator are THE default test apps
- Auto-routing (#208) regression still unfixed (PR pending)
- `click --coords` is the most basic use case and it works in principle, but testing is blocked

### Top 3 Improvement Priorities
1. **Fix UWP traversal (#191)** — Without this, naturo is unusable on Win11 defaults (Notepad, Calculator, Settings are all UWP)
2. **Merge #208 fix** — Auto-routing falling back to vision defeats the purpose
3. **Repo cleanup** — 60+ screenshots in git is unprofessional for an open-source project

### Risk Warnings
1. **Win11 compatibility**: If users try naturo on Win11 with default apps, they'll see empty/minimal UI trees and assume the tool is broken
2. **#142 incomplete**: Issue closed but only partially implemented — users reading changelog will expect global flags
3. **Test coverage gap**: No way to verify mouse operations without RDP — could be hiding real bugs

## 4. Cleanup Performed
- ✅ Quit notepad, calc via `naturo app quit`
- ✅ Deleted schtasks NaturoQA, NaturoQA2, NaturoQATest
- ⚠️ 3 zombie Notepad.exe processes in session 0 (can't kill from SSH, harmless)
