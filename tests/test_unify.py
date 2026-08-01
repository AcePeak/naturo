"""Unit tests for the unified-element-tree merge (naturo/cascade/_unify.py)."""
from naturo.backends.base import ElementInfo
from naturo.cascade._unify import merge_a11y_trees, _same_element, _norm_name


def E(role, name, x, y, w, h, source="uia", children=None, **props):
    p = {"source": source}
    p.update(props)
    return ElementInfo(id="", role=role, name=name, value=None,
                       x=x, y=y, width=w, height=h,
                       children=children or [], properties=p)


def _flat(root):
    out = []
    def v(n):
        out.append(n)
        for c in n.children:
            v(c)
    v(root)
    return out


def test_norm_name_strips_accelerator_and_case():
    assert _norm_name("&File") == "file"
    assert _norm_name("文件(&F)") == _norm_name("文件(F)")
    assert _norm_name("  OK  ") == "ok"


def test_full_overlap_stays_same_size_and_unions_source():
    # UIA and MSAA both see the same window + one button at the same rect.
    uia = E("Window", "App", 0, 0, 100, 100, source="uia",
            children=[E("Button", "OK", 10, 10, 40, 20, source="uia")])
    msaa = E("Window", "App", 0, 0, 100, 100, source="msaa",
             children=[E("Button", "OK", 10, 10, 40, 20, source="msaa")])
    merged = merge_a11y_trees(uia, msaa)
    flat = _flat(merged)
    assert len(flat) == 2  # no duplicate button
    btn = next(n for n in flat if n.role == "Button")
    # primary source intact + secondary recorded as a corroborating source
    assert btn.properties["source"] == "uia"
    assert "msaa" in btn.properties.get("corroborated_by", [])


def test_secondary_unique_control_is_grafted():
    # MSAA sees a character-grid cell the UIA tree lacks -> graft under container.
    uia = E("Window", "CharMap", 0, 0, 200, 200, source="uia",
            children=[E("Pane", "", 0, 30, 200, 170, source="uia")])
    msaa = E("Window", "CharMap", 0, 0, 200, 200, source="msaa",
             children=[E("ListItem", "U+0041", 20, 40, 16, 16, source="msaa")])
    merged = merge_a11y_trees(uia, msaa)
    names = [n.name for n in _flat(merged)]
    assert "U+0041" in names  # grafted
    cell = next(n for n in _flat(merged) if n.name == "U+0041")
    assert cell.properties["source"] == "msaa"


def test_empty_offscreen_secondary_adds_nothing():
    # The Naturobot case: rich UIA primary, junk MSAA (all 0x0/offscreen).
    uia = E("Window", "自然机器人", 0, 0, 1920, 1032, source="uia",
            children=[E("RadioButton", "应用商店", 12, 46, 176, 36, source="uia"),
                      E("RadioButton", "我的应用", 12, 94, 176, 36, source="uia")])
    msaa = E("Window", "自然机器人", 0, 0, 0, 0, source="msaa",
             children=[E("Button", "最小化", 0, 0, 0, 0, source="msaa"),
                       E("ScrollBar", "垂直滚动条", 0, 0, 0, 0, source="msaa")])
    merged = merge_a11y_trees(uia, msaa)
    flat = _flat(merged)
    # nothing junky grafted; the real UIA controls survive
    assert len(flat) == 3
    assert {n.name for n in flat if n.role == "RadioButton"} == {"应用商店", "我的应用"}


def test_accelerator_and_container_guard():
    # "&File" (uia) == "File" (msaa) -> match; a small button is NOT matched to
    # its big containing pane (size-ratio guard).
    assert _same_element(E("MenuItem", "&File", 0, 0, 40, 20),
                         E("MenuItem", "File", 1, 1, 40, 20))
    assert not _same_element(E("Button", "X", 0, 0, 20, 20),
                             E("Pane", "", 0, 0, 400, 400))
