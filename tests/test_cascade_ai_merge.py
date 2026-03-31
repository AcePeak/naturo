"""Tests for AI vision merge into UIA tree (#694)."""
from __future__ import annotations

from naturo.backends.base import ElementInfo
from naturo.cascade import _iou, _merge_ai_into_tree, _find_containing_node


def _el(role="Button", name="", x=0, y=0, w=50, h=30, children=None, source=None):
    """Helper to create ElementInfo."""
    props = {}
    if source:
        props["source"] = source
    return ElementInfo(
        id="", role=role, name=name, value=None,
        x=x, y=y, width=w, height=h,
        children=children or [],
        properties=props,
    )


class TestIoU:
    def test_no_overlap(self):
        a = _el(x=0, y=0, w=10, h=10)
        b = _el(x=100, y=100, w=10, h=10)
        assert _iou(a, b) == 0.0

    def test_full_overlap(self):
        a = _el(x=0, y=0, w=10, h=10)
        b = _el(x=0, y=0, w=10, h=10)
        assert _iou(a, b) == 1.0

    def test_partial_overlap(self):
        a = _el(x=0, y=0, w=10, h=10)
        b = _el(x=5, y=5, w=10, h=10)
        result = _iou(a, b)
        assert 0.1 < result < 0.2  # 25/175

    def test_zero_area(self):
        a = _el(x=0, y=0, w=0, h=0)
        b = _el(x=0, y=0, w=10, h=10)
        assert _iou(a, b) == 0.0


class TestFindContainingNode:
    def test_finds_smallest_encloser(self):
        """Should pick the Pane, not the root Window."""
        pane = _el(role="Pane", x=0, y=0, w=200, h=800)
        root = _el(role="Window", x=0, y=0, w=1920, h=1080, children=[pane])
        node = _find_containing_node(root, 100, 400)
        assert node is pane

    def test_falls_back_to_root(self):
        """Point outside any child should find root."""
        pane = _el(role="Pane", x=500, y=0, w=200, h=800)
        root = _el(role="Window", x=0, y=0, w=1920, h=1080, children=[pane])
        node = _find_containing_node(root, 50, 50)
        assert node is root


class TestMergeAiIntoTree:
    def test_feishu_scenario(self):
        """Simulate Feishu: UIA has right panel, AI finds left nav icons."""
        btn1 = _el(role="Button", name="Send", x=1200, y=720, w=40, h=40)
        right_panel = _el(role="Document", name="messenger-chat",
                          x=480, y=50, w=800, h=750, children=[btn1])
        left_pane = _el(role="Pane", name="SideEdgeView",
                        x=0, y=0, w=130, h=800)
        root = _el(role="Pane", name="飞书", x=0, y=0, w=1480, h=800,
                    children=[left_pane, right_panel])

        ai_elements = [
            _el(role="TreeItem", name="消息", x=18, y=84, w=100, h=25, source="vision"),
            _el(role="TreeItem", name="视频会议", x=18, y=110, w=100, h=25, source="vision"),
            _el(role="TreeItem", name="日历", x=18, y=136, w=100, h=25, source="vision"),
            _el(role="TreeItem", name="云文档", x=18, y=162, w=100, h=25, source="vision"),
            # Overlaps with UIA's Send button — should be skipped
            _el(role="Button", name="Send message", x=1200, y=720, w=40, h=40, source="vision"),
        ]

        novel, added, skipped = _merge_ai_into_tree(root, ai_elements)

        assert added == 4
        assert skipped == 1

        # Nav items should be grafted into left_pane (deepest container)
        assert len(left_pane.children) == 4
        assert left_pane.children[0].name == "消息"
        assert left_pane.children[3].name == "云文档"

        # Right panel unchanged
        assert len(right_panel.children) == 1
        assert right_panel.children[0].name == "Send"

    def test_empty_ai(self):
        root = _el(role="Window", x=0, y=0, w=1920, h=1080)
        novel, added, skipped = _merge_ai_into_tree(root, [])
        assert added == 0
        assert skipped == 0

    def test_all_duplicates(self):
        """All AI elements overlap with UIA — nothing added."""
        btn = _el(role="Button", name="OK", x=100, y=200, w=80, h=30)
        root = _el(role="Window", x=0, y=0, w=1920, h=1080, children=[btn])
        ai = [_el(role="Button", name="OK btn", x=100, y=200, w=80, h=30)]
        novel, added, skipped = _merge_ai_into_tree(root, ai)
        assert added == 0
        assert skipped == 1

    def test_zero_bounds_skipped(self):
        root = _el(role="Window", x=0, y=0, w=1920, h=1080)
        ai = [_el(role="Button", name="ghost", x=0, y=0, w=0, h=0)]
        novel, added, skipped = _merge_ai_into_tree(root, ai)
        assert added == 0
        assert skipped == 1
