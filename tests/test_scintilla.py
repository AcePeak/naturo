"""Tests for the Scintilla text provider (Notepad++/SciTE/IDE editors).

The cross-process ctypes reads (SCI_GETLENGTH/SCI_GETTEXT via VirtualAllocEx)
require a live Scintilla control, so these tests mock the two Win32-touching
seams — ``_find_scintilla_windows`` and ``_read_scintilla_text`` — and exercise
the pure node-building / cascade-graft logic (Linux-collectable in CI).
"""
from __future__ import annotations

from naturo.backends.base import ElementInfo
from naturo.cascade import _scintilla


def test_fetch_builds_document_node(monkeypatch):
    monkeypatch.setattr(
        _scintilla, "_find_scintilla_windows", lambda h: [(123, (10, 20, 800, 600))]
    )
    monkeypatch.setattr(_scintilla, "_read_scintilla_text", lambda h: "hello\nworld")

    nodes = _scintilla.fetch_scintilla_content(999)

    assert len(nodes) == 1
    node = nodes[0]
    assert node.role == "Document"
    assert node.name == "Scintilla editor"
    assert node.value == "hello\nworld"
    assert (node.x, node.y, node.width, node.height) == (10, 20, 800, 600)
    assert node.properties["source"] == "scintilla"
    assert node.properties["readable"] is True
    assert node.properties["editable"] is True


def test_fetch_names_multiple_editors(monkeypatch):
    monkeypatch.setattr(
        _scintilla,
        "_find_scintilla_windows",
        lambda h: [(1, (0, 0, 800, 600)), (2, (0, 0, 400, 300))],
    )
    monkeypatch.setattr(_scintilla, "_read_scintilla_text", lambda h: f"text-{h}")

    nodes = _scintilla.fetch_scintilla_content(999)

    assert [n.name for n in nodes] == ["Scintilla editor", "Scintilla editor 2"]
    assert [n.value for n in nodes] == ["text-1", "text-2"]


def test_fetch_empty_when_no_scintilla(monkeypatch):
    monkeypatch.setattr(_scintilla, "_find_scintilla_windows", lambda h: [])
    assert _scintilla.fetch_scintilla_content(999) == []


def test_fetch_skips_empty_and_unreadable_text(monkeypatch):
    monkeypatch.setattr(
        _scintilla,
        "_find_scintilla_windows",
        lambda h: [(1, (0, 0, 10, 10)), (2, (0, 0, 10, 10))],
    )
    # First editor is empty (""), second unreadable (None) — both dropped.
    reads = {1: "", 2: None}
    monkeypatch.setattr(_scintilla, "_read_scintilla_text", lambda h: reads[h])
    assert _scintilla.fetch_scintilla_content(999) == []


def test_fetch_swallows_read_exceptions(monkeypatch):
    def _boom(_h):
        raise OSError("cross-process read failed")

    monkeypatch.setattr(
        _scintilla, "_find_scintilla_windows", lambda h: [(1, (0, 0, 10, 10))]
    )
    monkeypatch.setattr(_scintilla, "_read_scintilla_text", _boom)
    assert _scintilla.fetch_scintilla_content(999) == []


def test_is_scintilla_window(monkeypatch):
    monkeypatch.setattr(
        _scintilla, "_find_scintilla_windows", lambda h: [(1, (0, 0, 5, 5))]
    )
    assert _scintilla.is_scintilla_window(1) is True

    monkeypatch.setattr(_scintilla, "_find_scintilla_windows", lambda h: [])
    assert _scintilla.is_scintilla_window(1) is False


# ── Cascade graft ──────────────────────────────────────────────────────────


def _win(role, name, source=None, x=0, y=0, w=10, h=10, children=None):
    props = {"source": source} if source else {}
    return ElementInfo(
        id=f"{role}-{name}", role=role, name=name, value=None,
        x=x, y=y, width=w, height=h, children=children or [], properties=props,
    )


class _FakeBackend:
    def __init__(self, tree):
        self._tree = tree

    def get_element_tree(self, backend="uia", **kwargs):
        return self._tree if backend == "uia" else None


def test_run_cascade_grafts_scintilla_onto_tree():
    from unittest.mock import patch

    from naturo import cascade as cascade_pkg
    from naturo.cascade import _flatten, run_cascade

    root = _win("Window", "new 1 - Notepad++", w=800, h=600,
                children=[_win("Pane", "editor pane", w=800, h=560)])
    backend = _FakeBackend(root)
    doc = _win("Document", "Scintilla editor", source="scintilla",
               x=0, y=0, w=800, h=560)
    doc.value = "int main() {}"
    doc.properties.update({"readable": True, "editable": True})

    with patch.object(cascade_pkg, "_is_scintilla_window", lambda h: True), \
         patch.object(cascade_pkg, "_fetch_scintilla_content", lambda h: [doc]), \
         patch.object(cascade_pkg, "_is_excel_window", lambda h: False), \
         patch.object(cascade_pkg, "_is_java_window", lambda h: False), \
         patch.object(cascade_pkg, "find_cdp_port", lambda pid: None), \
         patch.object(cascade_pkg, "_fetch_cdp_elements", lambda *a, **k: []):
        result = run_cascade(backend, backend_name="auto", hwnd=999)

    grafted = [
        e for e in _flatten(result.tree)
        if e.properties.get("source") == "scintilla"
    ]
    assert len(grafted) == 1, "Scintilla content was not grafted onto the fused tree"
    assert grafted[0].value == "int main() {}"
    assert any(
        p.name == "scintilla" and p.status == "ok" for p in result.stats.providers
    )


# ── Live re-read on `get eN` (snapshot staleness fix) ────────────────────────


def _element_tree_mixin():
    """Import ElementTreeMixin, skipping if the Windows backend can't load here."""
    import pytest

    try:
        from naturo.backends.windows._element._tree import ElementTreeMixin
    except Exception:  # pragma: no cover - non-Windows CI without the DLL
        pytest.skip("Windows element backend unavailable on this platform")
    return ElementTreeMixin


class _Elem:
    """Minimal stand-in for a resolved snapshot UIElement."""

    def __init__(self, identifier, role="Document", name="Scintilla editor",
                 frame=(1, 2, 3, 4)):
        self.identifier = identifier
        self.role = role
        self.title = name
        self.label = name
        self.frame = frame


def test_get_ref_live_reads_scintilla_control(monkeypatch):
    mixin = _element_tree_mixin()
    from naturo.cascade import _scintilla

    # A Scintilla ref must be read LIVE (not from the snapshot value), so an edit
    # after `see` is reflected. CRLF is normalised to LF like other doc reads.
    monkeypatch.setattr(_scintilla, "_read_scintilla_text", lambda h: "line1\r\nline2")

    out = mixin._read_scintilla_ref_live(_Elem("scintilla_4242"))

    assert out is not None
    assert out["value"] == "line1\nline2"
    assert out["pattern"] == "Scintilla"
    assert out["source"] == "scintilla"
    assert (out["x"], out["y"], out["width"], out["height"]) == (1, 2, 3, 4)


def test_get_ref_live_reads_hwnd_from_identifier(monkeypatch):
    mixin = _element_tree_mixin()
    from naturo.cascade import _scintilla

    seen = {}

    def _read(h):
        seen["hwnd"] = h
        return "text"

    monkeypatch.setattr(_scintilla, "_read_scintilla_text", _read)
    mixin._read_scintilla_ref_live(_Elem("scintilla_8066078"))
    assert seen["hwnd"] == 8066078


def test_get_ref_live_ignores_non_scintilla():
    mixin = _element_tree_mixin()
    assert mixin._read_scintilla_ref_live(_Elem("txtSearch", role="Edit")) is None
    assert mixin._read_scintilla_ref_live(_Elem(None)) is None


def test_get_ref_live_empty_document_is_still_read(monkeypatch):
    mixin = _element_tree_mixin()
    from naturo.cascade import _scintilla

    # "" is a valid (empty) document — distinct from None (unreadable control).
    monkeypatch.setattr(_scintilla, "_read_scintilla_text", lambda h: "")
    out = mixin._read_scintilla_ref_live(_Elem("scintilla_9"))
    assert out is not None
    assert out["value"] == ""


def test_get_ref_live_none_when_control_gone(monkeypatch):
    mixin = _element_tree_mixin()
    from naturo.cascade import _scintilla

    # None → control can't be read → fall through to the normal path.
    monkeypatch.setattr(_scintilla, "_read_scintilla_text", lambda h: None)
    assert mixin._read_scintilla_ref_live(_Elem("scintilla_9")) is None


# ── Write side: set_scintilla_text routing + `set eN` short-circuit ───────────


def test_set_scintilla_text_writes_to_scintilla_child(monkeypatch):
    # hwnd is already a Scintilla control → write to it directly (no child search).
    class _U:
        def GetClassNameW(self, hwnd, buf, n):
            buf.value = "Scintilla"
            return 9

    monkeypatch.setattr(_scintilla, "_win32", lambda: (_U(), object()))
    calls = {}
    monkeypatch.setattr(
        _scintilla, "_write_scintilla_text",
        lambda h, t: (calls.__setitem__("args", (h, t)), True)[1],
    )
    assert _scintilla.set_scintilla_text(4242, "new text") is True
    assert calls["args"] == (4242, "new text")


def test_set_scintilla_text_finds_child_when_given_parent(monkeypatch):
    # hwnd is NOT a Scintilla control → find the biggest Scintilla child first.
    class _U:
        def GetClassNameW(self, hwnd, buf, n):
            buf.value = "Notepad++"
            return 9

    monkeypatch.setattr(_scintilla, "_win32", lambda: (_U(), object()))
    monkeypatch.setattr(
        _scintilla, "_find_scintilla_windows", lambda h: [(777, (0, 0, 800, 600))]
    )
    seen = {}
    monkeypatch.setattr(
        _scintilla, "_write_scintilla_text",
        lambda h, t: (seen.__setitem__("hwnd", h), True)[1],
    )
    assert _scintilla.set_scintilla_text(100, "x") is True
    assert seen["hwnd"] == 777


def test_set_scintilla_text_false_when_no_scintilla(monkeypatch):
    class _U:
        def GetClassNameW(self, hwnd, buf, n):
            buf.value = "Notepad++"
            return 9

    monkeypatch.setattr(_scintilla, "_win32", lambda: (_U(), object()))
    monkeypatch.setattr(_scintilla, "_find_scintilla_windows", lambda h: [])
    assert _scintilla.set_scintilla_text(100, "x") is False


def test_set_scintilla_text_false_for_zero_hwnd():
    assert _scintilla.set_scintilla_text(0, "x") is False


def test_write_refuses_readonly_control(monkeypatch):
    # SCI_GETREADONLY -> 1 must abort the write (never a phantom success), and
    # must NOT reach OpenProcess/WriteProcessMemory.
    reached = {"open": False}

    class _U:
        def SendMessageW(self, hwnd, msg, w, l):
            if msg == _scintilla._SCI_GETREADONLY:
                return 1  # read-only
            return 0

    class _K:
        def OpenProcess(self, *a):
            reached["open"] = True
            return 0

    monkeypatch.setattr(_scintilla, "_win32", lambda: (_U(), _K()))
    assert _scintilla._write_scintilla_text(555, "nope") is False
    assert reached["open"] is False


def test_set_element_value_routes_scintilla_identifier(monkeypatch):
    # `set eN` on a Scintilla node passes automation_id="scintilla_<hwnd>" into
    # set_element_value, which must short-circuit to the cross-process writer
    # (parsing the child hwnd) instead of the doomed UIA path.
    import pytest

    try:
        from naturo.backends.windows._input._uia_interact import UIAInteractMixin
    except Exception:  # pragma: no cover - non-Windows CI without the DLL
        pytest.skip("Windows interaction backend unavailable on this platform")

    seen = {}
    monkeypatch.setattr(
        _scintilla, "set_scintilla_text",
        lambda h, t: (seen.__setitem__("args", (h, t)), True)[1],
    )
    mixin = UIAInteractMixin.__new__(UIAInteractMixin)
    ok = mixin.set_element_value(text="payload", automation_id="scintilla_8066078")
    assert ok is True
    assert seen["args"] == (8066078, "payload")


def test_set_element_value_scintilla_bad_identifier(monkeypatch):
    import pytest

    try:
        from naturo.backends.windows._input._uia_interact import UIAInteractMixin
    except Exception:  # pragma: no cover
        pytest.skip("Windows interaction backend unavailable on this platform")

    # Malformed "scintilla_" id (no parseable hwnd) → False, no crash.
    mixin = UIAInteractMixin.__new__(UIAInteractMixin)
    assert mixin.set_element_value(text="x", automation_id="scintilla_notanint") is False
