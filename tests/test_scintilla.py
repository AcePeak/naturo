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
