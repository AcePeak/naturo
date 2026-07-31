"""COM/Excel additive recognition provider (M2).

Excel renders its grid as a single opaque UIA node — a UIA-only tool sees the
window chrome but none of the cells. This provider binds the *running* Excel
instance for a target window via COM and emits each non-empty cell of the used
range as a ``com``-tagged (deterministic) :class:`ElementInfo`, with screen
coordinates from Excel's ``Window.PointsToScreenPixelsX/Y`` conversion. This is
naturo's moat on spreadsheets, mirroring the CDP (web) and JAB (Java) additive
providers.

``pywin32`` is an optional dependency; if it is unavailable, or no Excel is
running, the provider degrades to an empty result (like CDP without a debug
port) — it never raises into the cascade.
"""
from __future__ import annotations

import logging
from typing import List, Optional

from naturo.backends.base import ElementInfo

logger = logging.getLogger(__name__)

# Defaults bound the tree size and COM round-trips on a huge sheet. They are not
# silent (truncation is logged) and, crucially, not global mutable state: a
# caller that needs a bigger slice passes larger values PER CALL — threaded from
# `see --excel-max-cells` / see_ui_tree(excel_max_cells=…) through run_cascade —
# which is safe under multi-process/concurrent use, unlike a process-wide env var.
_DEFAULT_MAX_EXCEL_CELLS = 500  #: max non-empty cells emitted
_DEFAULT_MAX_SCAN_ROWS = 400    #: max rows scanned of the used range
_DEFAULT_MAX_SCAN_COLS = 100    #: max cols scanned of the used range


def _win32_class_name(hwnd: int) -> Optional[str]:
    try:
        import win32gui

        return win32gui.GetClassName(hwnd)
    except Exception as exc:  # pragma: no cover - platform/dep guard
        logger.debug("COM/Excel: GetClassName(%s) failed: %s", hwnd, exc)
        return None


def _iter_descendant_hwnds(hwnd: int) -> List[int]:
    """All descendant window handles of ``hwnd`` (empty on any failure)."""
    try:
        import win32gui

        found: List[int] = []

        def _collect(child_hwnd: int, _lparam: int) -> bool:
            found.append(child_hwnd)
            return True  # keep enumerating

        win32gui.EnumChildWindows(hwnd, _collect, None)
        return found
    except Exception as exc:  # pragma: no cover - platform/dep guard
        logger.debug("COM/Excel: EnumChildWindows(%s) failed: %s", hwnd, exc)
        return []


def _find_excel_grid_hwnd(hwnd: int) -> Optional[int]:
    """Return the ``EXCEL7`` spreadsheet-grid window (``hwnd`` itself or a
    descendant), else ``None``.

    Covers MS Excel (top-level ``XLMAIN`` → ``EXCEL7`` child) *and*
    Excel-compatible suites such as WPS 表格, whose top-level window is
    ``OpusApp`` but which wrap the very same ``XLMAIN``/``EXCEL7`` grid hierarchy.
    """
    if _win32_class_name(hwnd) == "EXCEL7":
        return hwnd
    for child in _iter_descendant_hwnds(hwnd):
        if _win32_class_name(child) == "EXCEL7":
            return child
    return None


def is_excel_window(hwnd: int) -> bool:
    """True if ``hwnd`` is (or contains) an Excel spreadsheet grid.

    Matches MS Excel (top-level class ``XLMAIN``) and Excel-compatible suites
    such as WPS 表格 (top-level ``OpusApp`` wrapping an ``EXCEL7`` grid), so the
    COM cell provider fires for both without the caller passing any extra flags.
    """
    if _win32_class_name(hwnd) == "XLMAIN":
        return True
    return _find_excel_grid_hwnd(hwnd) is not None


#: Workbook file extensions whose ROT document monikers identify an open Excel.
_EXCEL_DOC_SUFFIXES = (".xlsx", ".xlsm", ".xlsb", ".xls", ".csv")


def _get_excel_via_class_moniker():
    """Fast path: bind the ``Excel.Application`` class moniker (may be slow or
    absent on licensing-degraded hosts, raising MK_E_UNAVAILABLE)."""
    try:
        import win32com.client

        return win32com.client.GetActiveObject("Excel.Application")
    except Exception as exc:
        logger.debug("COM/Excel: GetActiveObject(Excel.Application) failed: %s", exc)
        return None


def _get_excel_from_rot():
    """Fallback: find a running Excel ``Application`` by enumerating the Running
    Object Table for an open workbook.

    Document monikers register reliably even when the ``Excel.Application``
    class moniker is slow/absent (observed on an "unauthorized product" Excel:
    GetActiveObject transiently raised MK_E_UNAVAILABLE while a workbook was
    open and only the document moniker was in the ROT).
    """
    try:
        import pythoncom
    except Exception:  # pragma: no cover - dep guard
        return None
    try:
        rot = pythoncom.GetRunningObjectTable()
        ctx = pythoncom.CreateBindCtx(0)
        for moniker in rot.EnumRunning():
            try:
                name = moniker.GetDisplayName(ctx, None)
            except Exception:
                continue
            if name and name.lower().endswith(_EXCEL_DOC_SUFFIXES):
                try:
                    workbook = rot.GetObject(moniker)
                    app = getattr(workbook, "Application", None)
                    if app is not None:
                        return app
                except Exception as exc:
                    logger.debug("COM/Excel: ROT bind '%s' failed: %s", name, exc)
    except Exception as exc:
        logger.debug("COM/Excel: ROT enumeration failed: %s", exc)
    return None


def _get_running_excel():
    """Return a running Excel ``Application`` COM object, or ``None``.

    Tries the class moniker first (fast), then the ROT document-moniker
    fallback so binding is reliable even when the class moniker is slow/absent
    on a licensing-degraded host.
    """
    return _get_excel_via_class_moniker() or _get_excel_from_rot()


#: OBJID_NATIVEOM — asks a window to hand back its native automation (OM) object.
_OBJID_NATIVEOM = 0xFFFFFFF0


def _get_window_via_native_om(hwnd: int):
    """Bind the Excel ``Window`` OM straight from the ``EXCEL7`` grid window via
    ``AccessibleObjectFromWindow(OBJID_NATIVEOM)``.

    This is the connection path for Excel-compatible suites (e.g. **WPS 表格**)
    whose ``Application`` neither registers in the Running Object Table nor is
    reachable through the ``Excel.Application`` class moniker (different ProgID +
    bitness) — yet which expose the standard Excel object model on their grid
    window (WPS even reports ``Application.Name == 'Microsoft Excel'``). It is
    also a robust last resort for real Excel when the moniker/ROT are transiently
    unavailable. Returns a ``Window`` (with ``.ActiveSheet`` and
    ``.PointsToScreenPixelsX/Y``), or ``None``.
    """
    grid = _find_excel_grid_hwnd(hwnd)
    if grid is None:
        return None
    try:
        import ctypes

        import pythoncom
        import win32com.client

        # IID_IDispatch = {00020400-0000-0000-C000-000000000046}
        class _GUID(ctypes.Structure):
            _fields_ = [
                ("D1", ctypes.c_uint32), ("D2", ctypes.c_uint16),
                ("D3", ctypes.c_uint16), ("D4", ctypes.c_uint8 * 8),
            ]

        iid = _GUID(0x00020400, 0, 0, (ctypes.c_uint8 * 8)(0xC0, 0, 0, 0, 0, 0, 0, 0x46))
        ptr = ctypes.c_void_p()
        hr = ctypes.windll.oleacc.AccessibleObjectFromWindow(
            grid, _OBJID_NATIVEOM, ctypes.byref(iid), ctypes.byref(ptr))
        if hr != 0 or not ptr.value:
            return None
        disp = pythoncom.ObjectFromAddress(ptr.value, pythoncom.IID_IDispatch)
        return win32com.client.Dispatch(disp)
    except Exception as exc:
        logger.debug("COM/Excel: native-OM bind for hwnd %s failed: %s", hwnd, exc)
        return None


def _resolve_excel_window(hwnd: int):
    """Return the Excel ``Window`` OM for ``hwnd`` (real Excel or an
    Excel-compatible suite like WPS 表格), or ``None``.

    Tries the running ``Excel.Application`` (class moniker / ROT) first, then
    binds the ``Window`` straight off the ``EXCEL7`` grid via ``OBJID_NATIVEOM``
    — the path that works for WPS, whose ``Application`` registers in neither.
    Shared by the cell reader (:func:`fetch_excel_cells`) and writer
    (:func:`write_excel_cell`) so both resolve the target window identically.
    """
    xl = _get_running_excel()
    win = _window_for_hwnd(xl, hwnd) if xl is not None else None
    if win is None:
        # Excel-compatible suites (e.g. WPS 表格) don't register in the ROT and
        # aren't the Excel.Application class moniker — bind the Window OM directly
        # from the EXCEL7 grid window. (Also a last resort for real Excel when the
        # moniker/ROT are transiently unavailable.)
        win = _get_window_via_native_om(hwnd)
    return win


def _window_for_hwnd(xl, hwnd: int):
    """Find the Excel ``Window`` whose ``.Hwnd`` matches ``hwnd`` (else active)."""
    try:
        for win in xl.Windows:
            try:
                if int(win.Hwnd) == int(hwnd):
                    return win
            except Exception:
                continue
    except Exception as exc:
        logger.debug("COM/Excel: enumerating windows failed: %s", exc)
    try:
        return xl.ActiveWindow
    except Exception:
        return None


def _cell_to_element(win, cell) -> Optional[ElementInfo]:
    """Map one Excel cell COM object to a screen-positioned ElementInfo."""
    value = cell.Value
    if value is None or str(value).strip() == "":
        return None
    # Excel gives cell geometry in document points; convert to screen pixels
    # via the window's own projection so the coords line up with UIA/CDP.
    left = int(win.PointsToScreenPixelsX(cell.Left))
    top = int(win.PointsToScreenPixelsY(cell.Top))
    right = int(win.PointsToScreenPixelsX(cell.Left + cell.Width))
    bottom = int(win.PointsToScreenPixelsY(cell.Top + cell.Height))
    # Under late-bound COM dispatch (GetActiveObject, no makepy/EnsureDispatch)
    # ``Address`` resolves as a PROPERTY returning the absolute "$A$1" string —
    # calling it with args raises ``'str' object is not callable``.  Read it as
    # a property and normalize to the plain "A1" label.
    addr = str(cell.Address).replace("$", "")  # e.g. "B3"
    return ElementInfo(
        id=f"com_{addr}",
        role="DataItem",
        name=str(value),
        value=str(value),
        x=left,
        y=top,
        width=max(0, right - left),
        height=max(0, bottom - top),
        children=[],
        properties={"source": "com", "cell": addr},
    )


def fetch_excel_cells(
    hwnd: int,
    *,
    max_cells: Optional[int] = None,
    max_rows: Optional[int] = None,
    max_cols: Optional[int] = None,
) -> List[ElementInfo]:
    """Fetch non-empty cells of the active sheet's used range as ``com`` nodes.

    Returns an empty list on any failure (no Excel running, pywin32 missing,
    COM error) — the cascade treats it like an unavailable provider.
    Truncation (sheet larger than the scan/emit caps) is logged, never silent.

    ``max_cells`` / ``max_rows`` / ``max_cols`` override the emit and scan caps
    for THIS call (``None`` = the module defaults). They are per-call, not global
    state, so concurrent callers can each choose their own bound safely.
    """
    if max_cells is None:
        max_cells = _DEFAULT_MAX_EXCEL_CELLS
    if max_rows is None:
        max_rows = _DEFAULT_MAX_SCAN_ROWS
    if max_cols is None:
        max_cols = _DEFAULT_MAX_SCAN_COLS

    win = _resolve_excel_window(hwnd)
    if win is None:
        return []
    try:
        used = win.ActiveSheet.UsedRange
        nrows = min(int(used.Rows.Count), max_rows)
        ncols = min(int(used.Columns.Count), max_cols)
    except Exception as exc:
        logger.debug("COM/Excel: cannot read used range: %s", exc)
        return []

    elements: List[ElementInfo] = []
    truncated = int(used.Rows.Count) > max_rows or int(used.Columns.Count) > max_cols
    for r in range(1, nrows + 1):
        for c in range(1, ncols + 1):
            if len(elements) >= max_cells:
                truncated = True
                break
            try:
                element = _cell_to_element(win, used.Cells(r, c))
            except Exception as exc:
                logger.debug("COM/Excel: cell (%d,%d) failed: %s", r, c, exc)
                continue
            if element is not None:
                elements.append(element)
        if len(elements) >= max_cells:
            break

    if truncated:
        logger.info(
            "COM/Excel: output bounded to %d cells / %dx%d scan; sheet is larger. "
            "Raise it with `see --excel-max-cells/--excel-max-rows/--excel-max-cols` "
            "(or the see_ui_tree excel_max_* args) to read more.",
            max_cells, max_rows, max_cols,
        )
    return elements


def _coerce_cell_value(value):
    """Coerce a text value to the natural Excel cell type.

    ``naturo set`` hands us a string; writing ``"888"`` verbatim would store
    text (left-aligned) where the user means the number 888. Parse ints and
    floats so they land as numbers; leave everything else (including
    number-like strings with leading zeros / plus signs that ``int`` rejects)
    as text — matching what a user typing into the cell would get.
    """
    if not isinstance(value, str):
        return value
    s = value.strip()
    if s.lstrip("-").isdigit():
        # Coerce to int only when it round-trips — keeps leading-zero / plus
        # strings (IDs, zip codes, "007") as text, like typing into the cell.
        try:
            n = int(s)
            if str(n) == s:
                return n
        except ValueError:
            pass
        return value  # all-digit but not int-round-trippable (leading zero) → text
    if any(ch in s for ch in ".eE"):
        try:
            return float(s)
        except (ValueError, TypeError):
            pass
    return value


def write_excel_cell(hwnd: int, address: str, value) -> bool:
    """Write ``value`` into cell ``address`` (e.g. ``"A2"``) of the active sheet.

    Deterministic COM write — the counterpart to :func:`fetch_excel_cells`'s
    read. Resolves the same ``Window`` OM (real Excel *or* an Excel-compatible
    suite such as WPS 表格 via ``OBJID_NATIVEOM``) and assigns
    ``ActiveSheet.Range(address).Value``. GUI/z-order-independent, so it does not
    depend on the window being foreground or on a coordinate hit-test. Returns
    ``True`` on success, ``False`` on any failure (no Excel bound, bad address,
    COM error) — the caller reports the failure.
    """
    win = _resolve_excel_window(hwnd)
    if win is None:
        return False
    try:
        win.ActiveSheet.Range(address).Value = _coerce_cell_value(value)
        return True
    except Exception as exc:
        logger.debug("COM/Excel: write %s = %r failed: %s", address, value, exc)
        return False
