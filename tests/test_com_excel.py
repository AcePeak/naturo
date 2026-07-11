"""COM/Excel additive provider + cascade graft (M2).

Linux-collectable: uses a fake Excel COM object graph and a fake backend — no
real Excel, no pywin32, no desktop. See docs/design/software-adaptation-degree.md.
"""
from __future__ import annotations

from unittest.mock import patch

from naturo.backends.base import ElementInfo
import naturo.cascade as cascade_pkg
from naturo.cascade import _flatten, recognition_summary, run_cascade
from naturo.cascade._com_excel import fetch_excel_cells


# ── fake Excel COM object graph ───────────────────────────────────────────

class _FakeCell:
    def __init__(self, value, left, top, width=48, height=16, addr="A1"):
        self.Value = value
        self.Left = left
        self.Top = top
        self.Width = width
        self.Height = height
        self._addr = addr

    @property
    def Address(self):
        # Model late-bound COM dispatch: Address is a PROPERTY returning the
        # absolute "$A$1" string, NOT a callable method. (The real provider bug
        # was calling cell.Address(False, False) on this property.)
        return f"${self._addr[0]}${self._addr[1:]}"


class _Count:
    def __init__(self, n):
        self.Count = n


class _FakeUsedRange:
    def __init__(self, grid):  # grid: {(row, col): _FakeCell}, 1-based
        self._grid = grid
        self._rows = max((r for r, _ in grid), default=0)
        self._cols = max((c for _, c in grid), default=0)

    @property
    def Rows(self):
        return _Count(self._rows)

    @property
    def Columns(self):
        return _Count(self._cols)

    def Cells(self, r, c):
        return self._grid.get((r, c), _FakeCell("", 0, 0, addr=f"r{r}c{c}"))


class _FakeSheet:
    def __init__(self, used):
        self.UsedRange = used


class _FakeWindow:
    def __init__(self, sheet, hwnd=123):
        self.ActiveSheet = sheet
        self.Hwnd = hwnd

    # identity projection so asserted coords equal the document points
    def PointsToScreenPixelsX(self, pts):
        return int(pts)

    def PointsToScreenPixelsY(self, pts):
        return int(pts)


class _FakeExcel:
    def __init__(self, win):
        self.Windows = [win]
        self.ActiveWindow = win


def _excel_with(grid, hwnd=123):
    return _FakeExcel(_FakeWindow(_FakeSheet(_FakeUsedRange(grid)), hwnd=hwnd))


# ── fetch_excel_cells mapping ─────────────────────────────────────────────

def test_fetch_maps_nonempty_cells_and_skips_empty():
    grid = {
        (1, 1): _FakeCell("Name", 100, 50, addr="A1"),
        (1, 2): _FakeCell("", 148, 50, addr="B1"),          # empty -> skipped
        (2, 1): _FakeCell("Widget", 100, 66, addr="A2"),
        (2, 2): _FakeCell(42, 148, 66, addr="B2"),
    }
    with patch("naturo.cascade._com_excel._get_running_excel",
               return_value=_excel_with(grid)):
        cells = fetch_excel_cells(123)

    by_addr = {c.properties["cell"]: c for c in cells}
    assert set(by_addr) == {"A1", "A2", "B2"}          # B1 skipped (empty)
    a1 = by_addr["A1"]
    assert a1.properties["source"] == "com"
    assert a1.name == "Name" and a1.value == "Name"
    assert (a1.x, a1.y, a1.width, a1.height) == (100, 50, 48, 16)
    assert by_addr["B2"].value == "42"                  # coerced to str


def test_get_running_excel_prefers_class_moniker():
    import naturo.cascade._com_excel as ce
    with patch.object(ce, "_get_excel_via_class_moniker", return_value="FAST"), \
         patch.object(ce, "_get_excel_from_rot", return_value="ROT"):
        assert ce._get_running_excel() == "FAST"


def test_get_running_excel_falls_back_to_rot_when_class_moniker_absent():
    # The licensing-degraded-host case: GetActiveObject fails, but an open
    # workbook is bindable via the ROT document moniker.
    import naturo.cascade._com_excel as ce
    with patch.object(ce, "_get_excel_via_class_moniker", return_value=None), \
         patch.object(ce, "_get_excel_from_rot", return_value="ROT_APP"):
        assert ce._get_running_excel() == "ROT_APP"


def test_fetch_empty_when_no_excel_running():
    with patch("naturo.cascade._com_excel._get_running_excel", return_value=None):
        assert fetch_excel_cells(123) == []


def test_fetch_respects_max_cells_cap():
    grid = {(r, 1): _FakeCell(f"v{r}", 10, 10 * r, addr=f"A{r}") for r in range(1, 21)}
    with patch("naturo.cascade._com_excel._get_running_excel",
               return_value=_excel_with(grid)):
        cells = fetch_excel_cells(123, max_cells=5)
    assert len(cells) == 5


def test_is_excel_window_uses_class_name():
    from naturo.cascade._com_excel import is_excel_window
    with patch("naturo.cascade._com_excel._win32_class_name", return_value="XLMAIN"):
        assert is_excel_window(123) is True
    with patch("naturo.cascade._com_excel._win32_class_name", return_value="Chrome_WidgetWin_1"):
        assert is_excel_window(123) is False


# ── cascade graft: com cells reach the fused tree, tagged deterministic ────

class _FakeBackend:
    def __init__(self, tree):
        self._tree = tree

    def get_element_tree(self, backend="uia", **kwargs):
        return self._tree if backend == "uia" else None


def _win(role, name, source=None, x=0, y=0, w=10, h=10, children=None):
    props = {"source": source} if source else {}
    return ElementInfo(id=f"{role}-{name}", role=role, name=name, value=None,
                       x=x, y=y, width=w, height=h,
                       children=children or [], properties=props)


def test_run_cascade_grafts_com_cells_onto_tree():
    root = _win("Window", "Book1 - Excel", w=800, h=600,
                children=[_win("Pane", "Ribbon", w=800, h=100)])
    backend = _FakeBackend(root)
    com_cell = _win("DataItem", "Widget", source="com", x=100, y=120, w=48, h=16)

    with patch.object(cascade_pkg, "_is_excel_window", lambda h: True), \
         patch.object(cascade_pkg, "_fetch_excel_cells", lambda h: [com_cell]), \
         patch.object(cascade_pkg, "_is_java_window", lambda h: False), \
         patch.object(cascade_pkg, "find_cdp_port", lambda pid: None), \
         patch.object(cascade_pkg, "_fetch_cdp_elements", lambda *a, **k: []):
        result = run_cascade(backend, backend_name="auto", hwnd=999)

    ids = [e.id for e in _flatten(result.tree)]
    assert "DataItem-Widget" in ids, "COM cell was not grafted onto the fused tree"
    summary = recognition_summary(result.tree)
    assert summary["by_technique"].get("com") == 1
    # com is deterministic — the fused cell node is correctness-preferred.
    from naturo.cascade import annotate
    node = next(e for e in _flatten(result.tree) if e.id == "DataItem-Widget")
    fusion = annotate(node.properties)
    assert fusion["correctness"] == "deterministic"
    assert fusion["techniques"] == ["com"]
    # provider stat recorded
    assert any(p.name == "com" and p.status == "ok" for p in result.stats.providers)


# ── configurable scan/emit caps (env override) ───────────────────────────────


class TestExcelLimitsConfigurable:
    """The Excel scan/emit caps default sensibly but are env-overridable."""

    def test_env_int_parsing(self):
        from naturo.cascade._com_excel import _env_int

        with patch.dict("os.environ", {"X": "1500"}):
            assert _env_int("X", 500) == 1500
        # missing / non-integer / non-positive all fall back to the default
        with patch.dict("os.environ", {}, clear=True):
            assert _env_int("X", 500) == 500
        with patch.dict("os.environ", {"X": "nope"}):
            assert _env_int("X", 500) == 500
        with patch.dict("os.environ", {"X": "0"}):
            assert _env_int("X", 500) == 500
        with patch.dict("os.environ", {"X": "-10"}):
            assert _env_int("X", 500) == 500

    def test_caps_read_from_env(self):
        from naturo.cascade import _com_excel as m

        with patch.dict("os.environ", {}, clear=True):
            assert m._max_excel_cells() == 500
            assert m._max_scan_rows() == 400
            assert m._max_scan_cols() == 100
        with patch.dict("os.environ", {
            "NATURO_EXCEL_MAX_CELLS": "5000",
            "NATURO_EXCEL_MAX_ROWS": "2000",
            "NATURO_EXCEL_MAX_COLS": "256",
        }):
            assert m._max_excel_cells() == 5000
            assert m._max_scan_rows() == 2000
            assert m._max_scan_cols() == 256
