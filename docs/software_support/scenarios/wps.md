# WPS Office — common-user scenarios (App#2)

Method (per the mission goal): imagine what a **normal user** does, then drive each step with
**naturo** and judge if it works. Do **not** assume WPS is one UI technology — try naturo's full
stack (UIA / MSAA / **COM** / CDP / OCR). The user experience must be **easy** — `naturo see` / a
naturo read should just work on WPS without the user hand-feeding hwnd/method/backend. When a step
fails, **stop and fix naturo**, then re-run. Record supportable vs non-supportable windows in
[`../VALIDATION_LOG.md`](../VALIDATION_LOG.md).

WPS = `OpusApp` (Word-compat) native shell + embedded **CEF** (login/start page). Spreadsheet =
「表格」(Excel-like, COM `Ket.Application`/`KWPS`), Writer =「文字」(Word-like COM), Presentation =「演示」.

## Scenarios (in priority order)

| # | Scenario | Steps | Valuable data / success | Likely naturo path |
|---|----------|-------|-------------------------|--------------------|
| S1 | **Read a spreadsheet** | open an .xlsx/.csv in WPS 表格 → read cell values | the cell grid (rows×cols) matches the file | COM (WPS spreadsheet), like `excel_read` |
| S2 | **Edit a spreadsheet** | set a cell's value → read it back | the new value persists | COM `set`/`read` |
| S3 | **Read a document** | open a .docx in WPS 文字 → read the body text | text matches the file | COM (WPS writer), like `word_read` |
| S4 | **Write a document** | type text into a doc → read it back | typed text present | COM / UIA type |
| S5 | **New blank doc from start page** | click 表格/文字 on the start page → blank editor | a new editor window opens | start-page tile (CEF → coord fallback) or COM `.Add` |
| S6 | **Save / Save As** | save the current file to a path | file exists on disk | COM `.SaveAs` or UIA dialog |

## Status log (updated as executed)
- **S1 (read a spreadsheet) — ✅ PASSED (2026-07-31), required a naturo fix.**
  - First attempt: `naturo see --hwnd <wps> --cascade` returned only 259 UIA chrome nodes, **0 cells** — the COM provider never fired (it gated on top-level class `XLMAIN`; WPS is `OpusApp`), and WPS's Application isn't reachable via `Excel.Application` moniker or the ROT.
  - Root cause found: WPS mirrors Excel's window tree — an **`EXCEL7`** grid nested under `OpusApp` — and exposes the standard Excel OM there (`Application.Name == "Microsoft Excel"`).
  - **Fixed naturo** (commit `7dd71f8a`): `is_excel_window()` now matches a window *containing* an EXCEL7 grid, and a new `AccessibleObjectFromWindow(OBJID_NATIVEOM)` connection binds the Window OM cross-bitness. Now `naturo see --cascade` emits all 16 cells as deterministic `com` DataItems with coords — **no extra flags (easy)**. Verified against the known test sheet (产品/数量/单价/总价 + 苹果/香蕉/橙子).
- S2–S6: pending.
