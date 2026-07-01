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

#: Max non-empty cells emitted (a huge sheet must not explode the tree).
_MAX_EXCEL_CELLS = 500
#: Max cells *scanned* (bounds COM round-trips on a large used range).
_MAX_SCAN_ROWS = 400
_MAX_SCAN_COLS = 100


def _win32_class_name(hwnd: int) -> Optional[str]:
    try:
        import win32gui

        return win32gui.GetClassName(hwnd)
    except Exception as exc:  # pragma: no cover - platform/dep guard
        logger.debug("COM/Excel: GetClassName(%s) failed: %s", hwnd, exc)
        return None


def is_excel_window(hwnd: int) -> bool:
    """True if ``hwnd`` is an Excel top-level workbook window (class ``XLMAIN``)."""
    return _win32_class_name(hwnd) == "XLMAIN"


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
    hwnd: int, *, max_cells: int = _MAX_EXCEL_CELLS
) -> List[ElementInfo]:
    """Fetch non-empty cells of the active sheet's used range as ``com`` nodes.

    Returns an empty list on any failure (no Excel running, pywin32 missing,
    COM error) — the cascade treats it like an unavailable provider.
    Truncation (sheet larger than the scan/emit caps) is logged, never silent.
    """
    xl = _get_running_excel()
    if xl is None:
        return []
    win = _window_for_hwnd(xl, hwnd)
    if win is None:
        return []
    try:
        used = win.ActiveSheet.UsedRange
        nrows = min(int(used.Rows.Count), _MAX_SCAN_ROWS)
        ncols = min(int(used.Columns.Count), _MAX_SCAN_COLS)
    except Exception as exc:
        logger.debug("COM/Excel: cannot read used range: %s", exc)
        return []

    elements: List[ElementInfo] = []
    truncated = int(used.Rows.Count) > _MAX_SCAN_ROWS or int(used.Columns.Count) > _MAX_SCAN_COLS
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
            "COM/Excel: output bounded to %d cells / %dx%d scan; sheet is larger.",
            max_cells, _MAX_SCAN_ROWS, _MAX_SCAN_COLS,
        )
    return elements
