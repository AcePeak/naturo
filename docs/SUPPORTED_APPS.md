# Supported & Tested Apps

Naturo is tested against real applications on real Windows machines. This document tracks which apps have been verified to work with naturo's see/click/type/capture capabilities.

## Compatibility Matrix

| App | Category | See (UI Tree) | Click | Type | Capture | Full E2E | Last Tested | Version | Notes |

| Notepad | Text Editor | ✅ | ✅ | ✅ | ✅ | ✅ | 2026-03 | Windows 11 | Smooth end-to-end workflow including Save As |

| Calculator | Utility | ✅ | ✅ | ⚠️ | ✅ | ✅ | 2026-03 | Windows 11 | Typing limited to button input (no keyboard in some modes) |

| File Explorer | System Tool | ✅ | ✅ | ⚠️ | ✅ | ⚠️ | 2026-03 | Windows 11 | Some rename/navigation inconsistencies |

| Paint | Graphics | ✅ | ✅ | ⚠️ | ✅ | ✅ | 2026-03 | Windows 11 | Text tool works, but formatting limited |

| Excel | Productivity | ⚠️ | ✅ | ⚠️ | ✅ | ⚠️ | 2026-03 | Microsoft 365 | Complex formulas and large sheets may fail |

| Browser (Edge/Chrome) | Web | ⚠️ | ✅ | ✅ | ✅ | ⚠️ | 2026-03 | Latest | Dynamic elements sometimes not detected |

| Settings | System Tool | ⚠️ | ⚠️ | ❌ | ✅ | ❌ | 2026-03 | Windows 11 | Some panels fail to load or interact |

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

*This document is auto-updated by QA testing. Last update:2026-03
