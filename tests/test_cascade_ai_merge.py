"""Tests for AI vision merge into UIA tree (#694, #702)."""
from __future__ import annotations

from naturo.backends.base import ElementInfo
from naturo.cascade import _iou, _merge_ai_into_tree, _find_containing_node, _text_proximity_match


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

    def test_text_proximity_dedup_catches_shifted_duplicates(self):
        """#702: AI '消息 13' near UIA '消息' should be deduped by text+proximity."""
        uia_label = _el(role="Text", name="消息", x=413, y=159, w=53, h=32)
        root = _el(role="Window", x=0, y=0, w=1920, h=1080, children=[uia_label])
        # Vision element: same text (contains UIA name), shifted coords, bigger box
        ai = [_el(role="Text", name="消息 13", x=249, y=109, w=240, h=48, source="vision")]
        novel, added, skipped = _merge_ai_into_tree(root, ai)
        assert added == 0
        assert skipped == 1

    def test_text_proximity_dedup_exact_name_nearby(self):
        """#702: Same exact name within proximity → skip."""
        uia_label = _el(role="Text", name="标签", x=413, y=428, w=53, h=32)
        root = _el(role="Window", x=0, y=0, w=1920, h=1080, children=[uia_label])
        ai = [_el(role="Text", name="标签", x=249, y=305, w=240, h=48, source="vision")]
        novel, added, skipped = _merge_ai_into_tree(root, ai)
        assert added == 0
        assert skipped == 1

    def test_text_proximity_dedup_too_far(self):
        """Same text but too far apart → NOT a duplicate."""
        uia_label = _el(role="Text", name="Save", x=100, y=100, w=50, h=30)
        root = _el(role="Window", x=0, y=0, w=1920, h=1080, children=[uia_label])
        ai = [_el(role="Text", name="Save", x=1500, y=900, w=60, h=30, source="vision")]
        novel, added, skipped = _merge_ai_into_tree(root, ai)
        assert added == 1
        assert skipped == 0

    def test_text_proximity_dedup_no_name(self):
        """Elements without names should not be text-matched."""
        uia_el = _el(role="Button", name="", x=100, y=100, w=50, h=30)
        root = _el(role="Window", x=0, y=0, w=1920, h=1080, children=[uia_el])
        ai = [_el(role="Button", name="", x=120, y=110, w=50, h=30, source="vision")]
        # IoU is low (different sizes), no text to match → should be added
        novel, added, skipped = _merge_ai_into_tree(root, ai)
        assert added == 1


class TestTextProximityMatch:
    def test_match_contains(self):
        """AI name contains UIA name → match."""
        uia = [_el(name="消息", x=413, y=159, w=53, h=32)]
        ai = _el(name="消息 13", x=350, y=150, w=100, h=40)
        assert _text_proximity_match(ai, uia) is uia[0]

    def test_match_contained_by(self):
        """UIA name contains AI name → match."""
        uia = [_el(name="Save Document", x=100, y=100, w=80, h=30)]
        ai = _el(name="Save", x=120, y=110, w=60, h=25)
        assert _text_proximity_match(ai, uia) is uia[0]

    def test_no_match_different_text(self):
        """Different text → no match even if close."""
        uia = [_el(name="Open", x=100, y=100, w=50, h=30)]
        ai = _el(name="Save", x=110, y=105, w=50, h=30)
        assert _text_proximity_match(ai, uia) is None

    def test_no_match_too_far(self):
        """Same text but beyond proximity → no match."""
        uia = [_el(name="OK", x=100, y=100, w=50, h=30)]
        ai = _el(name="OK", x=1000, y=1000, w=50, h=30)
        assert _text_proximity_match(ai, uia) is None

    def test_no_match_empty_name(self):
        """Empty AI name → no match."""
        uia = [_el(name="OK", x=100, y=100, w=50, h=30)]
        ai = _el(name="", x=110, y=105, w=50, h=30)
        assert _text_proximity_match(ai, uia) is None

    def test_case_insensitive(self):
        """Text matching is case-insensitive."""
        uia = [_el(name="Save", x=100, y=100, w=50, h=30)]
        ai = _el(name="SAVE", x=120, y=110, w=60, h=25)
        assert _text_proximity_match(ai, uia) is uia[0]

    def test_custom_proximity(self):
        """Custom proximity radius."""
        uia = [_el(name="OK", x=100, y=100, w=50, h=30)]
        ai = _el(name="OK", x=250, y=100, w=50, h=30)
        # Distance ~150px — within 200 default but beyond 100 custom
        assert _text_proximity_match(ai, uia, proximity_px=200) is uia[0]
        assert _text_proximity_match(ai, uia, proximity_px=100) is None
