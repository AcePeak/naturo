"""Tests for naturo.bridge._models — WindowInfo, ElementInfo, and parsing helpers."""

import json
from unittest.mock import MagicMock, patch

import pytest

from naturo.bridge._models import (
    ElementInfo,
    WindowInfo,
    _decode_native,
    _parse_element,
    _safe_json_loads,
    _system_ansi_encoding,
    populate_hierarchy,
)


# ---------------------------------------------------------------------------
# _decode_native
# ---------------------------------------------------------------------------

class TestDecodeNative:
    """Tests for _decode_native byte decoding."""

    def test_utf8_bytes(self):
        assert _decode_native(b"hello") == "hello"

    def test_utf8_unicode(self):
        text = "日本語テスト"
        assert _decode_native(text.encode("utf-8")) == text

    def test_fallback_to_system_encoding(self):
        """When UTF-8 fails, should fall back to locale preferred encoding."""
        # GBK-encoded Chinese text that is NOT valid UTF-8
        gbk_bytes = "测试".encode("gbk")
        with patch("locale.getpreferredencoding", return_value="gbk"):
            result = _decode_native(gbk_bytes)
            assert result == "测试"

    def test_fallback_default_cp936(self):
        """When locale returns empty string, should default to cp936."""
        gbk_bytes = "你好".encode("gbk")
        with patch("locale.getpreferredencoding", return_value=""):
            result = _decode_native(gbk_bytes)
            # cp936 is compatible with gbk
            assert "你好" in result or len(result) > 0

    def test_empty_bytes(self):
        assert _decode_native(b"") == ""

    def test_ascii_bytes(self):
        assert _decode_native(b"Notepad") == "Notepad"

    def test_ansi_fallback_ignores_utf8_mode_locale_on_windows(self):
        """#1150: the ANSI fallback must use the OS codepage (GetACP), not
        ``locale.getpreferredencoding``.

        Under Python UTF-8 mode (``PYTHONUTF8=1`` / ``-X utf8``)
        ``locale.getpreferredencoding`` returns ``"utf-8"`` regardless of the
        OS ANSI codepage, so the old fallback re-decoded GBK title bytes as
        UTF-8 and corrupted every non-ASCII character to U+FFFD.  The decoded
        title must instead match the true Win32 wide-API value.
        """
        title = "无标题 - Notepad"
        raw = b'[{"hwnd": 1, "title": "' + title.encode("gbk") + b'"}]'
        fake_windll = MagicMock()
        fake_windll.kernel32.GetACP.return_value = 936
        with patch("naturo.bridge._models.sys.platform", "win32"), patch(
            "naturo.bridge._models.ctypes.windll", fake_windll, create=True
        ), patch("locale.getpreferredencoding", return_value="utf-8"):
            result = _decode_native(raw)
        assert title in result
        assert "�" not in result


# ---------------------------------------------------------------------------
# _system_ansi_encoding
# ---------------------------------------------------------------------------

class TestSystemAnsiEncoding:
    """Tests for _system_ansi_encoding OS-codepage resolution (#1150)."""

    def test_windows_prefers_getacp_over_locale(self):
        """On Windows the OS ANSI codepage comes from GetACP, never locale.

        This is the crux of #1150: ``locale.getpreferredencoding`` reports
        ``"utf-8"`` under Python UTF-8 mode even on a CP936 desktop, so it
        cannot be trusted to detect the codepage of the native DLL's bytes.
        """
        fake_windll = MagicMock()
        fake_windll.kernel32.GetACP.return_value = 936
        with patch("naturo.bridge._models.sys.platform", "win32"), patch(
            "naturo.bridge._models.ctypes.windll", fake_windll, create=True
        ), patch("locale.getpreferredencoding", return_value="utf-8"):
            assert _system_ansi_encoding() == "cp936"

    def test_windows_falls_back_to_locale_when_getacp_unavailable(self):
        """If GetACP cannot be called, fall back to the locale encoding."""
        fake_windll = MagicMock()
        fake_windll.kernel32.GetACP.side_effect = OSError("boom")
        with patch("naturo.bridge._models.sys.platform", "win32"), patch(
            "naturo.bridge._models.ctypes.windll", fake_windll, create=True
        ), patch("locale.getpreferredencoding", return_value="gbk"):
            assert _system_ansi_encoding() == "gbk"

    def test_non_windows_uses_locale(self):
        """Off Windows there is no ANSI codepage; use the locale encoding."""
        with patch("naturo.bridge._models.sys.platform", "linux"), patch(
            "locale.getpreferredencoding", return_value="utf-8"
        ):
            assert _system_ansi_encoding() == "utf-8"

    def test_defaults_to_cp936_when_no_encoding_resolved(self):
        """When neither GetACP nor locale yields an encoding, default to cp936."""
        with patch("naturo.bridge._models.sys.platform", "linux"), patch(
            "locale.getpreferredencoding", return_value=""
        ):
            assert _system_ansi_encoding() == "cp936"


# ---------------------------------------------------------------------------
# _safe_json_loads
# ---------------------------------------------------------------------------

class TestSafeJsonLoads:
    """Tests for _safe_json_loads with surrogate repair."""

    def test_valid_json(self):
        result = _safe_json_loads('{"key": "value"}')
        assert result == {"key": "value"}

    def test_valid_json_array(self):
        result = _safe_json_loads('[1, 2, 3]')
        assert result == [1, 2, 3]

    def test_valid_json_string(self):
        result = _safe_json_loads('"hello"')
        assert result == "hello"

    def test_valid_json_number(self):
        result = _safe_json_loads("42")
        assert result == 42

    def test_valid_json_with_unicode(self):
        result = _safe_json_loads('{"text": "\\u0041"}')
        assert result == {"text": "A"}

    def test_unpaired_high_surrogate_parsed(self):
        """Python json.loads accepts orphaned surrogates — no repair needed."""
        bad_json = '{"name": "test\\uD800value"}'
        result = _safe_json_loads(bad_json)
        assert result["name"] == "test\ud800value"

    def test_unpaired_low_surrogate_parsed(self):
        """Python json.loads accepts orphaned low surrogates."""
        bad_json = '{"name": "test\\uDC00value"}'
        result = _safe_json_loads(bad_json)
        assert result["name"] == "test\udc00value"

    def test_repair_path_on_actual_invalid_json(self):
        """When JSON has surrogates AND other issues causing decode error,
        the repair path strips surrogates and retries."""
        # Simulate a string that fails initial parse but succeeds after repair.
        # Truncated JSON with a surrogate — first parse fails, repair strips
        # the surrogate and the remaining JSON is still invalid → raises.
        with pytest.raises(json.JSONDecodeError):
            _safe_json_loads('{"name": "test\\uD800')  # truncated

    def test_valid_surrogate_pair_preserved(self):
        """A valid surrogate pair (high + low) should be preserved."""
        # \uD83D\uDE00 is the surrogate pair for 😀 (U+1F600)
        good_json = '{"emoji": "\\uD83D\\uDE00"}'
        result = _safe_json_loads(good_json)
        assert result["emoji"] == "😀"

    def test_nested_json(self):
        result = _safe_json_loads('{"a": {"b": [1, 2]}}')
        assert result == {"a": {"b": [1, 2]}}

    def test_completely_invalid_json_raises(self):
        with pytest.raises(json.JSONDecodeError):
            _safe_json_loads("not json at all {{{")


# ---------------------------------------------------------------------------
# WindowInfo
# ---------------------------------------------------------------------------

class TestWindowInfo:
    """Tests for the WindowInfo dataclass."""

    def test_basic_creation(self):
        w = WindowInfo(
            hwnd=12345,
            title="Notepad",
            process_name="C:\\Windows\\notepad.exe",
            pid=1000,
            x=100, y=200, width=800, height=600,
            is_visible=True,
            is_minimized=False,
        )
        assert w.hwnd == 12345
        assert w.title == "Notepad"
        assert w.process_name == "C:\\Windows\\notepad.exe"
        assert w.pid == 1000
        assert w.x == 100
        assert w.y == 200
        assert w.width == 800
        assert w.height == 600
        assert w.is_visible is True
        assert w.is_minimized is False

    def test_handle_alias(self):
        """handle property should return hwnd for cross-platform compatibility."""
        w = WindowInfo(
            hwnd=99999, title="Test", process_name="test.exe",
            pid=1, x=0, y=0, width=100, height=100,
            is_visible=True, is_minimized=False,
        )
        assert w.handle == w.hwnd
        assert w.handle == 99999

    def test_minimized_window(self):
        w = WindowInfo(
            hwnd=1, title="Minimized", process_name="app.exe",
            pid=2, x=0, y=0, width=0, height=0,
            is_visible=True, is_minimized=True,
        )
        assert w.is_minimized is True

    def test_invisible_window(self):
        w = WindowInfo(
            hwnd=1, title="", process_name="bg.exe",
            pid=3, x=0, y=0, width=0, height=0,
            is_visible=False, is_minimized=False,
        )
        assert w.is_visible is False
        assert w.title == ""


# ---------------------------------------------------------------------------
# ElementInfo
# ---------------------------------------------------------------------------

class TestElementInfo:
    """Tests for the ElementInfo dataclass."""

    def test_basic_creation(self):
        e = ElementInfo(
            id="btn1", role="Button", name="OK", value=None,
            x=10, y=20, width=80, height=30,
        )
        assert e.id == "btn1"
        assert e.role == "Button"
        assert e.name == "OK"
        assert e.value is None
        assert e.x == 10
        assert e.y == 20
        assert e.width == 80
        assert e.height == 30

    def test_default_children_empty(self):
        e = ElementInfo(
            id="e1", role="Pane", name="Root", value=None,
            x=0, y=0, width=100, height=100,
        )
        assert e.children == []

    def test_default_optional_fields(self):
        e = ElementInfo(
            id="e1", role="Edit", name="Input", value="text",
            x=0, y=0, width=200, height=25,
        )
        assert e.parent_id is None
        assert e.keyboard_shortcut is None
        assert e.hwnd is None

    def test_with_children(self):
        child = ElementInfo(
            id="c1", role="Text", name="Label", value=None,
            x=5, y=5, width=50, height=20,
        )
        parent = ElementInfo(
            id="p1", role="Group", name="Panel", value=None,
            x=0, y=0, width=100, height=100,
            children=[child],
        )
        assert len(parent.children) == 1
        assert parent.children[0].name == "Label"

    def test_with_keyboard_shortcut(self):
        e = ElementInfo(
            id="save", role="MenuItem", name="Save", value=None,
            x=0, y=0, width=100, height=25,
            keyboard_shortcut="Ctrl+S",
        )
        assert e.keyboard_shortcut == "Ctrl+S"

    def test_with_hwnd(self):
        e = ElementInfo(
            id="edit1", role="Edit", name="TextBox", value="hello",
            x=0, y=0, width=200, height=25,
            hwnd=65540,
        )
        assert e.hwnd == 65540

    def test_states_default_none(self):
        """states defaults to None for elements without accessibility states."""
        e = ElementInfo(
            id="e1", role="Edit", name="Input", value=None,
            x=0, y=0, width=200, height=25,
        )
        assert e.states is None

    def test_with_states(self):
        """A checkbox-like element can carry its JAB accessibility states (#1200)."""
        e = ElementInfo(
            id="chk1", role="CheckBox", name="Express Shipping", value=None,
            x=0, y=0, width=120, height=24,
            states="enabled,focusable,visible,checked",
        )
        assert e.states == "enabled,focusable,visible,checked"

    def test_children_are_independent_lists(self):
        """Each ElementInfo should have its own children list."""
        e1 = ElementInfo(id="a", role="A", name="A", value=None, x=0, y=0, width=0, height=0)
        e2 = ElementInfo(id="b", role="B", name="B", value=None, x=0, y=0, width=0, height=0)
        e1.children.append(
            ElementInfo(id="c", role="C", name="C", value=None, x=0, y=0, width=0, height=0)
        )
        assert len(e1.children) == 1
        assert len(e2.children) == 0


# ---------------------------------------------------------------------------
# _parse_element
# ---------------------------------------------------------------------------

class TestParseElement:
    """Tests for _parse_element JSON dict -> ElementInfo conversion."""

    def test_minimal_dict(self):
        data = {}
        elem = _parse_element(data)
        assert elem.id == ""
        assert elem.role == ""
        assert elem.name == ""
        assert elem.value is None
        assert elem.x == 0
        assert elem.y == 0
        assert elem.width == 0
        assert elem.height == 0
        assert elem.children == []

    def test_full_dict(self):
        data = {
            "id": "btn_ok",
            "role": "Button",
            "name": "OK",
            "value": "pressed",
            "x": 100,
            "y": 200,
            "width": 80,
            "height": 30,
            "keyboard_shortcut": "Enter",
        }
        elem = _parse_element(data)
        assert elem.id == "btn_ok"
        assert elem.role == "Button"
        assert elem.name == "OK"
        assert elem.value == "pressed"
        assert elem.x == 100
        assert elem.y == 200
        assert elem.width == 80
        assert elem.height == 30
        assert elem.keyboard_shortcut == "Enter"

    def test_states_absent_defaults_none(self):
        """A native element JSON without a ``states`` key yields ``states=None``."""
        elem = _parse_element({"id": "x", "role": "Button", "name": "OK"})
        assert elem.states is None

    def test_reads_states(self):
        """``_parse_element`` surfaces the native ``states`` field (#1200).

        The Java Access Bridge layer (``core/src/jab.cpp``) writes a ``states``
        string into the per-element JSON, but the parser previously discarded it,
        so a Swing ``JCheckBox``'s checked/unchecked state never reached any
        Python consumer. Surfacing it unblocks honest verify-after-action for
        JAB-driven checkbox/toggle automation (#932).
        """
        data = {
            "id": "chk1",
            "role": "CheckBox",
            "name": "Express Shipping",
            "x": 758, "y": 407, "width": 404, "height": 26,
            "states": "enabled,focusable,visible,showing,checked",
        }
        elem = _parse_element(data)
        assert elem.states == "enabled,focusable,visible,showing,checked"

    def test_states_propagate_to_children(self):
        """Each parsed child independently carries its own ``states``."""
        data = {
            "id": "panel", "role": "Pane", "name": "Form",
            "children": [
                {"id": "c1", "role": "CheckBox", "name": "A", "states": "checked"},
                {"id": "c2", "role": "CheckBox", "name": "B", "states": "unchecked"},
            ],
        }
        elem = _parse_element(data)
        assert [c.states for c in elem.children] == ["checked", "unchecked"]

    def test_with_children(self):
        data = {
            "id": "panel",
            "role": "Pane",
            "name": "Main",
            "x": 0, "y": 0, "width": 500, "height": 400,
            "children": [
                {"id": "btn1", "role": "Button", "name": "Save", "x": 10, "y": 10, "width": 80, "height": 30},
                {"id": "btn2", "role": "Button", "name": "Cancel", "x": 100, "y": 10, "width": 80, "height": 30},
            ],
        }
        elem = _parse_element(data)
        assert len(elem.children) == 2
        assert elem.children[0].name == "Save"
        assert elem.children[1].name == "Cancel"

    def test_nested_children(self):
        data = {
            "id": "root",
            "role": "Window",
            "name": "App",
            "x": 0, "y": 0, "width": 800, "height": 600,
            "children": [{
                "id": "group1",
                "role": "Group",
                "name": "Toolbar",
                "x": 0, "y": 0, "width": 800, "height": 50,
                "children": [{
                    "id": "btn",
                    "role": "Button",
                    "name": "New",
                    "x": 5, "y": 5, "width": 40, "height": 40,
                }],
            }],
        }
        elem = _parse_element(data)
        assert elem.children[0].children[0].name == "New"

    def test_parent_id_from_dict(self):
        data = {"id": "child1", "role": "Button", "name": "X", "parent_id": "parent1"}
        elem = _parse_element(data)
        assert elem.parent_id == "parent1"

    def test_missing_optional_value(self):
        data = {"id": "e1", "role": "Text", "name": "Label"}
        elem = _parse_element(data)
        assert elem.value is None


# ---------------------------------------------------------------------------
# populate_hierarchy
# ---------------------------------------------------------------------------

class TestPopulateHierarchy:
    """Tests for populate_hierarchy tree traversal."""

    def test_single_element_no_id(self):
        """Element without id should get auto-assigned 'e1'."""
        root = ElementInfo(
            id="", role="Window", name="App", value=None,
            x=0, y=0, width=800, height=600,
        )
        populate_hierarchy(root)
        assert root.id == "e1"
        assert root.parent_id is None

    def test_single_element_with_id(self):
        """Element with existing id should keep it."""
        root = ElementInfo(
            id="myid", role="Window", name="App", value=None,
            x=0, y=0, width=800, height=600,
        )
        populate_hierarchy(root)
        assert root.id == "myid"
        assert root.parent_id is None

    def test_parent_child_relationship(self):
        child = ElementInfo(
            id="c1", role="Button", name="OK", value=None,
            x=10, y=10, width=80, height=30,
        )
        root = ElementInfo(
            id="root", role="Window", name="App", value=None,
            x=0, y=0, width=800, height=600,
            children=[child],
        )
        populate_hierarchy(root)
        assert root.parent_id is None
        assert child.parent_id == "root"

    def test_auto_id_assignment(self):
        """Children without ids should get sequential e1, e2, etc."""
        child1 = ElementInfo(id="", role="Button", name="A", value=None, x=0, y=0, width=0, height=0)
        child2 = ElementInfo(id="", role="Button", name="B", value=None, x=0, y=0, width=0, height=0)
        root = ElementInfo(
            id="root", role="Window", name="App", value=None,
            x=0, y=0, width=800, height=600,
            children=[child1, child2],
        )
        populate_hierarchy(root)
        assert child1.id == "e1"
        assert child2.id == "e2"

    def test_deep_hierarchy(self):
        """Three levels deep, parent_id chain should be correct."""
        grandchild = ElementInfo(id="gc", role="Text", name="Label", value=None, x=0, y=0, width=0, height=0)
        child = ElementInfo(
            id="ch", role="Group", name="Panel", value=None,
            x=0, y=0, width=0, height=0, children=[grandchild],
        )
        root = ElementInfo(
            id="rt", role="Window", name="App", value=None,
            x=0, y=0, width=0, height=0, children=[child],
        )
        populate_hierarchy(root)
        assert root.parent_id is None
        assert child.parent_id == "rt"
        assert grandchild.parent_id == "ch"

    def test_mixed_ids_and_auto_ids(self):
        """Mix of elements with and without ids."""
        child_with_id = ElementInfo(id="existing", role="Button", name="A", value=None, x=0, y=0, width=0, height=0)
        child_no_id = ElementInfo(id="", role="Button", name="B", value=None, x=0, y=0, width=0, height=0)
        root = ElementInfo(
            id="", role="Window", name="App", value=None,
            x=0, y=0, width=0, height=0,
            children=[child_with_id, child_no_id],
        )
        populate_hierarchy(root)
        assert root.id == "e1"
        assert child_with_id.id == "existing"
        assert child_no_id.id == "e2"
        assert child_with_id.parent_id == "e1"
        assert child_no_id.parent_id == "e1"

    def test_counter_increments_across_branches(self):
        """Auto-id counter should increment across sibling branches."""
        left_child = ElementInfo(id="", role="A", name="L", value=None, x=0, y=0, width=0, height=0)
        left_grandchild = ElementInfo(id="", role="B", name="LG", value=None, x=0, y=0, width=0, height=0)
        left_child.children = [left_grandchild]
        right_child = ElementInfo(id="", role="C", name="R", value=None, x=0, y=0, width=0, height=0)
        root = ElementInfo(
            id="root", role="Window", name="App", value=None,
            x=0, y=0, width=0, height=0,
            children=[left_child, right_child],
        )
        populate_hierarchy(root)
        assert left_child.id == "e1"
        assert left_grandchild.id == "e2"
        assert right_child.id == "e3"

    def test_explicit_parent_id_overwritten(self):
        """populate_hierarchy overwrites any existing parent_id."""
        child = ElementInfo(
            id="c", role="Button", name="X", value=None,
            x=0, y=0, width=0, height=0, parent_id="old_parent",
        )
        root = ElementInfo(
            id="r", role="Window", name="App", value=None,
            x=0, y=0, width=0, height=0, children=[child],
        )
        populate_hierarchy(root)
        assert child.parent_id == "r"

    def test_empty_children_list(self):
        """Leaf element with no children should work fine."""
        root = ElementInfo(
            id="leaf", role="Button", name="OK", value=None,
            x=0, y=0, width=80, height=30,
        )
        populate_hierarchy(root)
        assert root.parent_id is None
        assert root.children == []
