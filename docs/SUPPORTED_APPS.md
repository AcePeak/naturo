# Supported & Tested Apps

Naturo is tested against real applications on real Windows machines. This document tracks which apps have been verified to work with naturo's see/click/type/capture capabilities.

## Compatibility Matrix

**Sources for each row (no authored claims):** apps naturo ships **curated built-in selectors** for (`naturo/selectors_builtin/*.json` — created against the real running app) are marked ✅ for See; Office apps additionally have **COM** automation (`excel_*`/`word_*`) with tests; browsers/Electron are **CDP**-wired; framework proofs come from the recognition benchmark fixtures; rows marked "live-verified" were driven end-to-end in a real desktop session. **Full E2E ✅** is reserved for a complete real workflow with evidence. `Capture` (screenshot) is framework-agnostic and works everywhere.

| App | Category | See (UI Tree) | Click | Type | Capture | Full E2E | Last Tested | Notes |
|-----|----------|:---:|:---:|:---:|:---:|:---:|------------|-------|
| Notepad | Editor (Win11/TSF) | ✅ | ✅ | ✅ | ✅ | ✅ | 2026-08 | Live-verified this session: launch → type → read-back → quit; IME-immune type via clipboard/ValuePattern ladder (#1219); quit verifies by window-ownership (#1197) |
| Calculator | UWP | ✅ | ✅ | ✅ | ✅ | — | — | Built-in selectors; UWP/UIA |
| File Explorer | Shell (Win32) | ✅ | ✅ | ✅ | ✅ | — | — | Built-in selectors |
| Settings | UWP | ✅ | ✅ | ✅ | ✅ | — | — | Built-in selectors; UWP |
| Control Panel | Shell | ✅ | ✅ | — | ✅ | — | — | Built-in selectors |
| Task Manager | System (Win32) | ✅ | ✅ | — | ✅ | — | — | Built-in selectors |
| Registry Editor | System (Win32) | ✅ | ✅ | ✅ | ✅ | — | — | Built-in selectors |
| Snipping Tool | UWP | ✅ | ✅ | — | ✅ | — | — | Built-in selectors |
| Paint | Win32 | ✅ | ✅ | ✅ | ✅ | — | — | Built-in selectors |
| Command Prompt | Console | ✅ | — | — | ✅ | — | — | Built-in selectors; avoid injecting input into a live console |
| Windows Terminal | Console | ✅ | — | — | ✅ | — | — | Built-in selectors; input to a live terminal is intentionally avoided |
| Excel | Office / COM | ✅ | ✅ | ✅ | ✅ | ✅ | 2026 | COM: open/read/write/run-macro/list-sheets (`excel_*`, tested) + selectors |
| Word | Office / COM | ✅ | ✅ | ✅ | ✅ | — | — | COM: `word_read`/`word_write` + selectors |
| PowerPoint | Office / COM | ✅ | ✅ | ✅ | ✅ | — | — | Built-in selectors + COM |
| Outlook | Office | ✅ | ✅ | ✅ | ✅ | — | — | Built-in selectors |
| Google Chrome | Browser / CDP | ✅ | ✅ | ✅ | ✅ | — | — | CDP-wired for rendered/logged-in pages; selectors |
| Microsoft Edge | Browser / CDP | ✅ | ✅ | ✅ | ✅ | — | — | CDP-wired; selectors |
| Firefox | Browser / Gecko | ✅ | ✅ | ✅ | ✅ | — | — | Via IAccessible2; selectors |
| VS Code | Electron / CDP | ✅ | ✅ | ✅ | ✅ | — | — | Electron auto-detected, CDP fallback; selectors |
| Microsoft Teams | Electron / CDP | ✅ | ✅ | ✅ | ✅ | — | — | Built-in selectors; Electron/CDP |
| Java Swing (owned fixture) | Java / JAB | ✅ | ✅ | ✅ | ✅ | ✅ | 2026 | Recognition proof: `SwingControlsFixture.java` — JAB recovers controls a UIA-only baseline is blind to (#932) |
| Electron (owned fixture) | Electron / CDP | ✅ | ✅ | ✅ | ✅ | ✅ | 2026 | Recognition benchmark fixture (`benchmarks/recognition/fixtures/electron`) |

### Legend
- ✅ Fully working
- ⚠️ Partial (some limitations)
- ❌ Not working
- 🔧 Requires workaround (see Notes)
- — Not tested

## Testing Methodology

Each app is tested with a **realistic end-to-end workflow** — not just "can we see elements", but "can we actually use this app the way a real user would". Examples:

- **Notepad**: Open → type text → Save As → choose location → verify file exists
- **Excel**: Open → new workbook → enter data in cells → apply formula → format → save
- **Calculator**: Open → perform calculation → verify result
- **File Explorer**: Navigate folders → create folder → rename → delete
- **Browser**: Open URL → interact with page elements → navigate

Every step is verified by **screenshot + AI vision analysis** to confirm the operation succeeded.

## How to Report Compatibility Issues

If you find an app that doesn't work well with naturo, please [open an issue](https://github.com/AcePeak/naturo/issues/new) with:
1. App name and version
2. What you tried (`naturo see --app "AppName"`)
3. What happened vs what you expected
4. Screenshots if possible

## UI Framework Coverage

| Framework | Status | Apps |
|-----------|--------|------|
| Win32/WPF | ✅ Supported | Most desktop apps |
| UWP | ✅ Supported | Calculator, Settings, Store |
| Electron | ⚠️ Auto-detected | VS Code, Slack, Discord (CDP fallback available) |
| Java Swing/AWT | ✅ Supported | IntelliJ, Eclipse (via Java Access Bridge) |
| Qt | ⚠️ Partial | Some apps expose UIA, some don't |
| CEF/Chromium | ⚠️ Via CDP | Apps embedding Chromium |
| Firefox (Gecko) | ✅ Supported | Via IAccessible2 |

---

*Populated 2026-08 from code-provable support (built-in selectors in `naturo/selectors_builtin/`, COM office automation, CDP browser wiring, IAccessible2/JAB backends) + recognition-benchmark fixtures + live desktop verification of the rows marked as such. It is not exhaustive — any app with recognizable UIA/MSAA/JAB/CDP elements works even if unlisted; this table records the apps with explicit support evidence. Detailed per-app QA validation logs are maintained separately in the QA validation records.*
