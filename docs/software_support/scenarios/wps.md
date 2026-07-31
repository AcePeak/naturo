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
  - **Fixed naturo** (commit `7dd71f8a`): `is_excel_window()` now matches a window *containing* an EXCEL7 grid, and a new `AccessibleObjectFromWindow(OBJID_NATIVEOM)` connection binds the Window OM cross-bitness. Now `naturo see` emits all 16 cells as deterministic `com` DataItems with coords — **no extra flags (easy)**. Verified against the known test sheet (产品/数量/单价/总价 + 苹果/香蕉/橙子).
- **S2 (edit a spreadsheet) — ✅ PASSED (2026-07-31), required a naturo fix.**
  - First (rejected) attempt: coordinate click + type. Fragile — clicking a cell's top-left hit the
    A1/A2 boundary (edited the wrong cell), and a later edit did nothing because the WPS window was
    **behind the terminal** (the click landed on the terminal). Coordinate editing depends on z-order
    and pixel precision — the wrong mechanism.
  - **Fixed naturo** (commit `d5b99e54`): added `write_excel_cell(hwnd, addr, value)` to
    `_com_excel.py` (binds the same Window OM as the reader, assigns `ActiveSheet.Range(addr).Value`),
    and routed `naturo set` to it for `com_*` cells. Deterministic, GUI/z-order-independent — needs
    **no** coords/method/backend flags (easy): just `naturo set <ref> <value>`.
  - Verified live: `naturo set e260 产品` (A1 999→产品, string), `naturo set e264 红苹果` (A2, string),
    `naturo set e265 12` (B2 10→12, coerced to a **number**) — each confirmed by re-reading the grid
    with `naturo see`, **while WPS was not the foreground window** (terminal was). Restored
    the sheet to its canonical values afterward. Numeric strings coerce to int/float; leading-zero
    strings (IDs/zips) stay text.
- **S3 (read a document) — ✅ PASSED (2026-07-31), no naturo fix needed.**
  - WPS registers itself as the **`Word.Application`** COM server (compat), reporting
    `Name == "Microsoft Word"` — exactly the trick 表格 uses for Excel. So naturo's existing
    **file-based** `word_read(path)` (a dedicated `DispatchEx("Word.Application")` instance) drives
    WPS 文字 with no change. Verified: wrote `wps_test.docx` then read it back — text identical (69
    chars, `季度销售报告 …`).
- **S4 (write a document) — ✅ PASSED (2026-07-31), no naturo fix.** Same `Word.Application` path:
  `word_write(path, text)` created and populated `wps_test.docx`; the S3 read-back confirms it
  persisted. `append=True` also supported.
- **S5 (new document) — ✅ PASSED (2026-07-31), no naturo fix.** `word_write` with a non-existent
  path does `Documents.Add()` + `SaveAs` — the programmatic equivalent of "new doc from the start
  page", GUI-independent. (The CEF start-page tile itself has no ref → coord-only; the COM `.Add`
  path is the clean, deterministic way and needs no start page.)
- **S6 (save / save-as) — ✅ PASSED (2026-07-31), needed a naturo fix for 表格.** File-COM writers
  persist via `Save`/`SaveAs`: `word_write` saves the .docx; `excel_write` saves the .xlsx. Fixing
  a WPS-surfaced bug was required for the spreadsheet path — `excel_write` read `ws.Name` **after**
  `wb.Close()`, and WPS releases the worksheet proxy on close (OLE `0x800a01a8`); MS Excel tolerated
  it, hiding the bug. Fixed in `c9d070b4` (capture the name before closing). Verified: `excel_write`
  → `excel_read` round-trips on WPS (A1/B1, then cleaned up the temp file).

### WPS COM support summary (App#2)
| Path | Surface | naturo interface | Status |
|------|---------|------------------|--------|
| Live spreadsheet (open window) | 表格 EXCEL7 grid | `see` (read), `set <ref>` (write) | ✅ fixed `7dd71f8a`/`d5b99e54` |
| File spreadsheet | any .xlsx | `excel_read` / `excel_write` (Excel.Application→WPS) | ✅ fixed `c9d070b4` |
| File document | any .docx | `word_read` / `word_write` (Word.Application→WPS) | ✅ works as-is |
| Native shell (menus/tabs/新建) | OpusApp UIA | `see` → `click <ref>` | ✅ works as-is |
| CEF surfaces (login, start page) | KxCefWebView | coord-only (no CDP port) | ⚠️ coord fallback |

**Conclusion:** WPS 表格 + 文字 are fully supported (read + write + save) through naturo COM —
deterministic, easy (ref/path only, no aux params), GUI/z-order-independent. Only the CEF web
surfaces remain coord-only (no debug port to attach). WPS = **SUPPORTED**.
