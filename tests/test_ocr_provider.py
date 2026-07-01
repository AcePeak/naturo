"""Local OCR provider + cascade merge (M2).

Linux-collectable: rapidocr is mocked, the backend is fake — no engine, no
desktop. See docs/RECOGNITION_TREE.md (uncertain techniques) and
docs/design/software-adaptation-degree.md.
"""
from __future__ import annotations

from unittest.mock import patch

from naturo.backends.base import ElementInfo
import naturo.cascade as cascade_pkg
from naturo.cascade import _flatten, recognition_summary, run_cascade
from naturo.cascade._ocr import fetch_ocr_elements


def _raw(text, x, y, w, h, score):
    """rapidocr raw item: [box(4 pts), text, score]."""
    box = [[x, y], [x + w, y], [x + w, y + h], [x, y + h]]
    return [box, text, score]


# ── fetch_ocr_elements mapping ────────────────────────────────────────────

def test_fetch_ocr_maps_text_and_offsets_by_window_origin():
    raw = [
        _raw("Hello", 10, 20, 100, 30, 0.97),
        _raw("lowconf", 5, 5, 40, 10, 0.2),   # below min_score -> skipped
        _raw("", 0, 0, 50, 10, 0.9),           # empty text -> skipped
    ]
    with patch("naturo.cascade._ocr._get_ocr_engine", return_value=object()), \
         patch("naturo.cascade._ocr._run_ocr", return_value=raw):
        els = fetch_ocr_elements("shot.png", (200, 300, 800, 600))

    assert len(els) == 1
    e = els[0]
    assert e.properties["source"] == "ocr"
    assert e.name == "Hello" and e.value == "Hello"
    assert abs(e.properties["confidence"] - 0.97) < 1e-9
    # box (10,20) offset by window origin (200,300) -> (210,320); size preserved
    assert (e.x, e.y, e.width, e.height) == (210, 320, 100, 30)


def test_fetch_ocr_empty_when_engine_unavailable():
    with patch("naturo.cascade._ocr._get_ocr_engine", return_value=None):
        assert fetch_ocr_elements("shot.png", (0, 0, 10, 10)) == []


def test_fetch_ocr_respects_min_score():
    raw = [_raw("keep", 0, 0, 50, 20, 0.6), _raw("drop", 0, 30, 50, 20, 0.4)]
    with patch("naturo.cascade._ocr._get_ocr_engine", return_value=object()), \
         patch("naturo.cascade._ocr._run_ocr", return_value=raw):
        els = fetch_ocr_elements("shot.png", (0, 0, 100, 100), min_score=0.5)
    assert [e.name for e in els] == ["keep"]


# ── cascade merge: OCR text is fused as an uncertain, warned node ──────────

class _FakeBackend:
    def __init__(self, tree):
        self._tree = tree

    def get_element_tree(self, backend="uia", **kwargs):
        return self._tree if backend == "uia" else None


def _el(role, name, source=None, x=0, y=0, w=10, h=10, children=None):
    props = {}
    if source:
        props["source"] = source
    if source == "ocr":
        props["confidence"] = 0.8
    return ElementInfo(id=f"{role}-{name}", role=role, name=name, value=None,
                       x=x, y=y, width=w, height=h,
                       children=children or [], properties=props)


def test_run_cascade_merges_ocr_as_uncertain_warned_node():
    root = _el("Window", "App", w=400, h=400,
               children=[_el("Pane", "body", w=400, h=400)])
    backend = _FakeBackend(root)
    ocr_el = _el("Text", "BakedText", source="ocr", x=50, y=300, w=80, h=20)

    with patch.object(cascade_pkg, "_fetch_ocr_elements", lambda *a, **k: [ocr_el]), \
         patch.object(cascade_pkg, "_is_excel_window", lambda h: False), \
         patch.object(cascade_pkg, "_is_java_window", lambda h: False), \
         patch.object(cascade_pkg, "find_cdp_port", lambda pid: None), \
         patch.object(cascade_pkg, "_fetch_cdp_elements", lambda *a, **k: []):
        result = run_cascade(
            backend, backend_name="auto", hwnd=1,
            screenshot_path="shot.png", run_ocr=True,
        )

    ids = [e.id for e in _flatten(result.tree)]
    assert "Text-BakedText" in ids, "OCR text was not fused into the tree"
    summary = recognition_summary(result.tree)
    assert summary["by_technique"].get("ocr") == 1
    assert summary["uncertain_nodes"] >= 1 and summary["has_uncertain"] is True

    from naturo.cascade import annotate, uncertain_warning
    node = next(e for e in _flatten(result.tree) if e.id == "Text-BakedText")
    fusion = annotate(node.properties)
    assert fusion["correctness"] == "uncertain"      # image/OCR -> uncertain
    assert fusion["techniques"] == ["ocr"]
    assert uncertain_warning(summary) is not None     # CLI would warn
    assert any(p.name == "ocr" and p.status == "ok" for p in result.stats.providers)


def test_run_cascade_no_ocr_when_flag_off():
    root = _el("Window", "App", w=400, h=400,
               children=[_el("Pane", "body", w=400, h=400)])
    backend = _FakeBackend(root)
    with patch.object(cascade_pkg, "_fetch_ocr_elements", lambda *a, **k: [1 / 0]), \
         patch.object(cascade_pkg, "_is_excel_window", lambda h: False), \
         patch.object(cascade_pkg, "_is_java_window", lambda h: False), \
         patch.object(cascade_pkg, "find_cdp_port", lambda pid: None), \
         patch.object(cascade_pkg, "_fetch_cdp_elements", lambda *a, **k: []):
        # run_ocr defaults False -> the OCR fetch must never be called.
        result = run_cascade(backend, backend_name="auto", hwnd=1,
                             screenshot_path="shot.png")
    assert not any(p.name == "ocr" for p in result.stats.providers)
