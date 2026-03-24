# QA Round 16 Report — 2026-03-23 18:06 CST

**QA-Mariana** | L1 Functional + Parameter Standardization Review | Compile Machine (SSH)

## Environment

- **Machine**: Compile (100.113.29.45) via SSH
- **naturo version**: 0.2.1 (stale — cannot update)
- **Git pull**: ❌ **FAILED** — `github.com:443` connection timeout. Ping works (84ms), HTTPS blocked.
- **Desktop session**: Console session exists (disconnected) — headless-safe tests only
- **Screen**: 1024×768 @ 96 DPI, 1.0x scale

## ⚠️ Blocker: Compile Machine Lost GitHub HTTPS Access

**Symptom**: `git pull` and `curl -I https://github.com` both timeout on port 443. Ping to `20.205.243.166` works fine (82-84ms, 0% loss). No proxy configured.

**Impact**: Cannot pull latest code, cannot verify PR #176 (#166 fix), compile machine stuck on `ce2d894`.

**Note**: Round 15 (2h ago) reported git access was working. Something changed — possibly ISP/firewall/GFW-related.

## Dev Completions Check

**No `status:done` issues pending QA verification.**

## Open PR Review

### PR #176 — Standardize CLI parameter names (#166)
- **CI**: ✅ Passed (3m50s)
- **Code review** (from local repo):
  - New `naturo/cli/options.py` — clean, well-documented shared decorators
  - `--window` replaces `--window-title` as primary (old kept as hidden alias) ✅
  - `--hwnd` replaces `--window-id` (old kept hidden) ✅
  - `--app` absorbs `--process-name` (old kept hidden) ✅
  - Backward compatibility preserved via hidden aliases ✅
  - **Cannot verify on test machine** due to git connectivity blocker

## Tests Performed (on v0.2.1)

### Boundary Validation (L1)
| Test | Result | Notes |
|------|--------|-------|
| `see --depth 0` | ✅ Rejected | "must be between 1 and 10, got 0" |
| `see --depth 99` | ✅ Rejected | "must be between 1 and 10, got 99" |
| `press --count 0 enter` | ✅ Rejected | "must be >= 1, got 0" |
| `press --count -1 enter` | ✅ Rejected | "must be >= 1, got -1" |
| `naturo nonexistent` | ✅ Rejected | "No such command 'nonexistent'" |

All boundary errors return structured JSON with `INVALID_INPUT` code and helpful `suggested_action`. Good UX.

### Core Commands Smoke (L0)
| Command | Result | Notes |
|---------|--------|-------|
| `naturo --version` | ✅ | 0.2.1 |
| `naturo --help` | ✅ | 24 commands listed |
| `naturo list screens --json` | ✅ | Correct: 1024×768, 96 DPI, primary |
| `naturo list apps --json` | ✅ | Returns empty (no desktop apps in SSH session) |
| `naturo capture live --json` | ✅ | Captured 1024×768 screenshot |
| `naturo see --json` | ✅ | `WINDOW_NOT_FOUND` — appropriate error |
| `naturo click --coords 500 300` | ✅ | `NO_DESKTOP_SESSION` — correct detection |
| `naturo press enter --json` | ✅ | `NO_DESKTOP_SESSION` — correct detection |

### Help Text Consistency (L1)
Reviewed all interaction commands (`click`, `type`, `press`, `hotkey`, `scroll`, `drag`, `move`):
- All show `--app`, `--window-title` (old name, pre-#166), `--hwnd`
- All show `-m, --method` with same choices `[auto|cdp|uia|msaa|ia2|jab|vision]`
- All show `-j, --json`
- ✅ Consistent within v0.2.1

### Command Substructure
- `capture` is now a command group (subcommand: `live`) — `naturo capture --json` fails with "No such option" instead of routing to `capture live`. Noted but not a regression — this is by design.
- `app` subcommands all present: find, hide, inspect, launch, list, quit, relaunch, switch, unhide ✅
- `window` subcommands all present: close, focus, list, maximize, minimize, move, resize, restore, set-bounds ✅

## Quality Assessment

**Current state: CLI stable, test machine degraded.**

### GitHub Connectivity Issue
The compile machine losing GitHub HTTPS access is the **top operational blocker**. It prevents:
- Code updates (can't test latest commits)
- PR #176 verification on real Windows
- Any new fix testing

This is likely a GFW/ISP issue (HTTPS blocked while ICMP works). May resolve on its own or need proxy configuration.

### Product Quality (v0.2.1 baseline)
- **Boundary validation**: Solid — all tested edge cases properly rejected with clear messages
- **Error handling**: Excellent — `NO_DESKTOP_SESSION`, `WINDOW_NOT_FOUND` all have actionable `suggested_action`
- **Command structure**: Clean and consistent
- **JSON output**: Consistent across commands

### Top 3 Priorities
1. **Fix compile machine GitHub access** — either configure git proxy or wait for connectivity to restore. This blocks all QA progress.
2. **Merge PR #176** — CI passed, code review looks clean. Once merged + machine connectivity restored, verify param standardization on real Windows.
3. **Desktop session testing** — 7 open bugs still blocked on RDP access (#137, #135, #158, #164, #154, #150, #165)

### Risk
- **Compile machine isolation**: If GitHub blockage persists, we lose our only Windows test environment for code updates. Consider setting up a git proxy or mirror.
- **Stale test environment**: Machine is running code from 2+ hours ago, can't verify any new merges.

## Self-Check
1. L2 (UX) test? — Yes, tested boundary inputs and error messages from user perspective
2. L3 (real machine)? — Yes, all tests on compile machine via SSH
3. "装傻" test? — Partially: tested `naturo nonexistent`, bad params
4. Design-level追问? — PR #176 code review done, architecture is clean
5. Correctness vs "runs"? — Validated actual output values (resolution, DPI, error codes)
6. New user satisfaction? — CLI basics work well; UI bugs and connectivity are the gaps
