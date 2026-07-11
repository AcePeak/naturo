"""Tests for naturo.mcp._inspect — MCP UI inspection tools.

Tests cover see_ui_tree, find_element, get_element_value, set_element_value,
toggle_element, select_element, expand_collapse_element with mocked backend.
All tests run on Linux CI (no Windows dependencies).
"""
from __future__ import annotations

import asyncio
import json
from unittest.mock import MagicMock, patch

import pytest

mcp_available = True
try:
    from naturo.mcp_server import create_server
except ImportError:
    mcp_available = False

pytestmark = pytest.mark.skipif(not mcp_available, reason="mcp package not installed")


def _call_tool(server, tool_name: str, arguments: dict):
    """Helper to call an MCP tool function by name."""
    async def _run():
        return await server.call_tool(tool_name, arguments)

    loop = asyncio.new_event_loop()
    try:
        return loop.run_until_complete(_run())
    finally:
        loop.close()


def _make_element(**overrides):
    """Create a mock element with standard attributes."""
    el = MagicMock()
    el.id = overrides.get("id", "btn_ok")
    el.role = overrides.get("role", "Button")
    el.name = overrides.get("name", "OK")
    el.value = overrides.get("value", None)
    el.x = overrides.get("x", 100)
    el.y = overrides.get("y", 200)
    el.width = overrides.get("width", 80)
    el.height = overrides.get("height", 30)
    el.properties = overrides.get("properties", {})
    el.children = overrides.get("children", [])
    el.is_actionable = overrides.get("is_actionable", False)
    return el


@pytest.fixture
def mock_backend():
    backend = MagicMock()
    backend.get_element_tree.return_value = _make_element()
    backend.find_element.return_value = _make_element()
    backend.get_element_value.return_value = {
        "value": "hello",
        "pattern": "ValuePattern",
        "role": "Edit",
        "name": "Input",
        "automation_id": "txt_input",
        "x": 10,
        "y": 20,
        "width": 200,
        "height": 25,
    }
    backend.set_element_value.return_value = True
    backend.toggle_element.return_value = "On"
    backend.select_element.return_value = True
    backend.expand_collapse_element.return_value = True
    backend._resolve_hwnd.return_value = 12345
    return backend


@pytest.fixture
def snapshot_mgr(tmp_path):
    """Real SnapshotManager using a temp directory."""
    from naturo.snapshot import SnapshotManager
    return SnapshotManager(storage_root=tmp_path, session="test")


@pytest.fixture
def server(mock_backend, snapshot_mgr):
    with patch("naturo.mcp_server.get_backend", return_value=mock_backend), \
         patch("naturo.snapshot.get_snapshot_manager", return_value=snapshot_mgr):
        yield create_server()


# ── see_ui_tree ──────────────────────────────────────────────────────


class TestSeeUiTreeCascade:
    """The unified see --cascade tree must be reachable via MCP (M3 criterion 1)."""

    def test_cascade_returns_fused_correctness_tagged_tree(self, server):
        from naturo.backends.base import ElementInfo
        from naturo.cascade._types import CascadeResult, CascadeStats

        root = ElementInfo(
            id="w", role="Window", name="App", value=None,
            x=0, y=0, width=200, height=200,
            properties={"source": "uia"},
            children=[
                ElementInfo(id="b", role="Button", name="Save", value=None,
                            x=0, y=0, width=100, height=50, children=[],
                            properties={"source": "uia"}),
                ElementInfo(id="c", role="Link", name="Open", value=None,
                            x=100, y=0, width=40, height=40, children=[],
                            properties={"source": "cdp"}),
            ],
        )
        result = CascadeResult(tree=root, stats=CascadeStats(), primary_provider="uia")

        with patch("naturo.cascade.run_cascade", return_value=result) as mock_cascade:
            out = _call_tool(server, "see_ui_tree", {"cascade": True, "hwnd": 123, "format": "json"})

        mock_cascade.assert_called_once()
        data = json.loads(out[0].text)
        assert data["success"] is True
        tree = data["tree"]
        # every fused node carries techniques[] + correctness + confidence
        assert tree["techniques"] == ["uia"]
        assert tree["correctness"] == "deterministic"
        assert tree["confidence"] == 1.0
        child_techs = {tuple(ch["techniques"]) for ch in tree["children"]}
        assert ("uia",) in child_techs and ("cdp",) in child_techs
        # deterministic preferred, no false uncertain
        assert all(ch["correctness"] == "deterministic" for ch in tree["children"])
        # structured recognition summary is exposed to the agent
        assert "recognition_summary" in data
        assert data["recognition_summary"]["by_technique"].get("cdp") == 1
        assert data["recognition_summary"]["has_uncertain"] is False

    def test_cascade_with_app_routes_through_app_content_tree(self, server, mock_backend):
        # (calc-zombie) cascade + --app + no hwnd must gather ALL of the app's
        # windows via app_content_tree (dropping empty UWP ghost frames), mirroring
        # `see --app --cascade`, instead of a single run_cascade that can land on a
        # chrome-only ghost.
        from naturo.backends.base import ElementInfo

        root = ElementInfo(
            id="w", role="Window", name="Live", value=None,
            x=0, y=0, width=200, height=200, children=[],
            properties={"source": "uia"},
        )
        with (
            patch("naturo.cascade._appwindows.app_content_tree",
                  return_value=(root, None)) as mock_act,
            patch("naturo.cascade.run_cascade") as mock_cascade,
        ):
            out = _call_tool(server, "see_ui_tree",
                             {"cascade": True, "app": "calc", "format": "json"})

        mock_act.assert_called_once()
        mock_cascade.assert_not_called()
        data = json.loads(out[0].text)
        assert data["success"] is True
        assert data["tree"]["name"] == "Live"

    def test_non_cascade_tree_has_no_fusion_tags(self, server, mock_backend):
        # plain (single-backend) path stays unchanged — no techniques/correctness.
        out = _call_tool(server, "see_ui_tree", {"format": "json"})
        data = json.loads(out[0].text)
        assert "techniques" not in data["tree"]
        assert "recognition_summary" not in data


class TestSeeUiTree:

    def test_returns_tree_structure(self, server, mock_backend):
        result = _call_tool(server, "see_ui_tree", {"format": "json"})
        data = json.loads(result[0].text)
        assert data["success"] is True
        assert "tree" in data
        assert "snapshot_id" in data
        tree = data["tree"]
        # IDs are now stable hash-based refs (e.g. "e1234")
        assert tree["id"].startswith("e")
        assert tree["role"] == "Button"
        assert tree["name"] == "OK"
        assert tree["bounds"] == {"x": 100, "y": 200, "width": 80, "height": 30}

    def test_compact_is_default_and_token_lean(self, server, mock_backend):
        # Default = compact text: one line per actionable/named node, no bounds/
        # nulls/raw properties → far fewer tokens, and the LLM reads it directly.
        result = _call_tool(server, "see_ui_tree", {})
        data = json.loads(result[0].text)
        assert data["success"] is True
        assert data["format"] == "compact"
        assert "tree_text" in data and "tree" not in data
        assert "snapshot_id" in data
        # the OK button shows up as `eN Button "OK"`, and no bounds/properties leak
        assert 'Button "OK"' in data["tree_text"]
        assert "bounds" not in data["tree_text"]
        assert "properties" not in data["tree_text"]
        # compact must be much smaller than the JSON tree for the same window
        js = json.loads(_call_tool(server, "see_ui_tree", {"format": "json"})[0].text)
        assert len(data["tree_text"]) < len(json.dumps(js["tree"]))

    def test_compact_refs_stay_resolvable_for_click(self, server, mock_backend):
        # eN refs in compact output must be stored so click/type still resolve.
        result = _call_tool(server, "see_ui_tree", {})
        data = json.loads(result[0].text)
        import re
        refs = re.findall(r"\be\d+\b", data["tree_text"])
        assert refs, "compact output must expose eN refs"
        from naturo.snapshot import get_snapshot_manager
        mgr = get_snapshot_manager()
        assert mgr.resolve_ref_element(refs[0], None) is not None

    def test_match_filters_to_intent(self, server, mock_backend):
        # match="<intent>" returns only matching elements, with resolvable refs.
        result = _call_tool(server, "see_ui_tree", {"match": "OK"})
        data = json.loads(result[0].text)
        assert data["success"] is True
        assert data["match"] == "OK"
        assert data["matched"] >= 1
        assert 'Button "OK"' in data["tree_text"]
        import re
        refs = re.findall(r"\be\d+\b", data["tree_text"])
        from naturo.snapshot import get_snapshot_manager
        assert get_snapshot_manager().resolve_ref_element(refs[0], None) is not None

    def test_match_no_hits_is_empty_but_ok(self, server, mock_backend):
        result = _call_tool(server, "see_ui_tree", {"match": "zzznotpresent"})
        data = json.loads(result[0].text)
        assert data["success"] is True
        assert data["matched"] == 0
        assert data["tree_text"] == ""

    def test_auto_jab_fallback_when_uia_is_opaque(self, server, mock_backend):
        # UIA renders Java/Swing as an opaque frame (sparse); see_ui_tree must
        # transparently re-read via JAB so the agent gets the real controls
        # instead of screenshotting.
        uia_frame = _make_element(id="frame", role="Window", name="Java App", children=[])
        swing = _make_element(id="root", role="Window", name="Java App", children=[
            _make_element(id="b", role="Button", name="Local Process"),
            _make_element(id="c", role="RadioButton", name="Remote Process"),
        ])

        def _by_backend(**kw):
            return swing if kw.get("backend") == "jab" else uia_frame

        mock_backend.get_element_tree.side_effect = _by_backend
        result = _call_tool(server, "see_ui_tree", {"hwnd": 1})
        data = json.loads(result[0].text)
        # the compact output now carries the JAB-recovered Swing controls
        assert 'Button "Local Process"' in data["tree_text"]
        assert 'RadioButton "Remote Process"' in data["tree_text"]

    def test_no_jab_fallback_when_uia_already_rich(self, server, mock_backend):
        # A normal window with a rich UIA tree must NOT trigger a JAB re-read.
        rich = _make_element(id="w", role="Window", name="App", children=[
            _make_element(id=f"n{i}", role="Button", name=f"Btn{i}") for i in range(15)
        ])
        calls = []

        def _track(**kw):
            calls.append(kw.get("backend"))
            return rich

        mock_backend.get_element_tree.side_effect = _track
        _call_tool(server, "see_ui_tree", {"hwnd": 1})
        assert "jab" not in calls  # rich UIA tree → no JAB fallback

    def test_with_window_title(self, server, mock_backend):
        _call_tool(server, "see_ui_tree", {"window_title": "Notepad"})
        mock_backend.get_element_tree.assert_any_call(
            app=None, window_title="Notepad", hwnd=None, pid=None,
            depth=0, backend="uia",
        )

    def test_custom_depth_and_backend(self, server, mock_backend):
        _call_tool(server, "see_ui_tree", {"depth": 3, "accessibility_backend": "msaa"})
        mock_backend.get_element_tree.assert_any_call(
            app=None, window_title=None, hwnd=None, pid=None,
            depth=3, backend="msaa",
        )

    def test_with_hwnd(self, server, mock_backend):
        _call_tool(server, "see_ui_tree", {"hwnd": 12345})
        mock_backend.get_element_tree.assert_any_call(
            app=None, window_title=None, hwnd=12345, pid=None,
            depth=0, backend="uia",
        )

    def test_with_pid(self, server, mock_backend):
        _call_tool(server, "see_ui_tree", {"pid": 9999})
        mock_backend.get_element_tree.assert_any_call(
            app=None, window_title=None, hwnd=None, pid=9999,
            depth=0, backend="uia",
        )

    def test_long_value_bounded_by_default(self, server, mock_backend):
        # A big Document value must NOT be dumped in full (token-lean); it is
        # truncated to a preview with a marker for how much was elided.
        long_text = "".join(f"line{i} " for i in range(200))  # ~1.7k chars
        doc = _make_element(id="doc", role="Document", name="Editor", value=long_text)
        mock_backend.get_element_tree.return_value = doc
        result = _call_tool(server, "see_ui_tree", {})
        text = json.loads(result[0].text)["tree_text"]
        assert "chars)" in text          # "…(+N chars)" elision marker
        assert long_text not in text     # full body not inlined
        assert len(text) < len(long_text)

    def test_full_text_inlines_complete_value(self, server, mock_backend):
        long_text = "".join(f"line{i} " for i in range(200))
        doc = _make_element(id="doc", role="Document", name="Editor", value=long_text)
        mock_backend.get_element_tree.return_value = doc
        result = _call_tool(server, "see_ui_tree", {"full_text": True})
        text = json.loads(result[0].text)["tree_text"]
        assert long_text in text         # complete value present
        assert "chars)" not in text      # no truncation marker

    def test_short_value_shown_in_full_by_default(self, server, mock_backend):
        doc = _make_element(id="e", role="Edit", name="Search", value="hello world")
        mock_backend.get_element_tree.return_value = doc
        result = _call_tool(server, "see_ui_tree", {})
        text = json.loads(result[0].text)["tree_text"]
        assert "hello world" in text
        assert "chars)" not in text

    def test_capability_flags_rendered(self, server, mock_backend):
        # readable/actionable/editable from the backend surface as [rae] so the
        # agent targets the real interactive node, not a role guess.
        edit = _make_element(id="in", role="Edit", name="用户名",
                             properties={"readable": True, "actionable": True,
                                         "editable": True})
        btn = _make_element(id="ok", role="Button", name="连接",
                            properties={"actionable": True})
        root = _make_element(id="w", role="Window", name="Dlg", children=[edit, btn])
        mock_backend.get_element_tree.return_value = root
        text = json.loads(_call_tool(server, "see_ui_tree", {})[0].text)["tree_text"]
        # the input carries all three; the button only actionable
        assert any('"用户名"' in ln and ln.rstrip().endswith("[rae]")
                   for ln in text.splitlines())
        assert any('"连接"' in ln and ln.rstrip().endswith("[a]")
                   for ln in text.splitlines())

    def test_app_param_triggers_multi_window_enumeration(self, server, mock_backend):
        """When app is provided without hwnd, _resolve_hwnds is used (#737)."""
        child = _make_element(id="btn1", role="Button", name="Click Me")
        window_tree = _make_element(id="win1", role="Window", name="App Window", children=[child])
        mock_backend._resolve_hwnds.return_value = [100]
        mock_backend.get_element_tree.return_value = window_tree
        result = _call_tool(server, "see_ui_tree", {"app": "MyApp"})
        data = json.loads(result[0].text)
        assert data["success"] is True
        mock_backend._resolve_hwnds.assert_called_once_with(app="MyApp")
        mock_backend.get_element_tree.assert_any_call(
            hwnd=100, depth=0, backend="uia",
        )

    def test_app_with_multiple_windows_merges_trees(self, server, mock_backend):
        """Multiple windows for same app are merged under a virtual root (#737)."""
        tree1 = _make_element(id="w1", role="Window", name="Win 1")
        tree2 = _make_element(id="w2", role="Window", name="Win 2")
        mock_backend._resolve_hwnds.return_value = [100, 200]
        mock_backend.get_element_tree.side_effect = [tree1, tree2]
        result = _call_tool(server, "see_ui_tree", {"app": "MultiWin", "format": "json"})
        data = json.loads(result[0].text)
        assert data["success"] is True
        tree = data["tree"]
        assert tree["role"] == "Application"
        assert tree["name"] == "MultiWin"
        assert len(tree["children"]) == 2
        assert tree["children"][0]["role"] == "WindowGroup"
        assert tree["children"][1]["role"] == "WindowGroup"

    def test_app_no_windows_returns_error(self, server, mock_backend):
        """No windows found for app returns NO_WINDOW error (#737)."""
        mock_backend._resolve_hwnds.return_value = []
        result = _call_tool(server, "see_ui_tree", {"app": "Nonexistent"})
        data = json.loads(result[0].text)
        assert data["success"] is False
        assert data["error"]["code"] == "WINDOW_NOT_FOUND"

    def test_app_with_hwnd_bypasses_multi_window(self, server, mock_backend):
        """When both app and hwnd are provided, hwnd takes priority (#737)."""
        _call_tool(server, "see_ui_tree", {"app": "MyApp", "hwnd": 12345})
        # Should NOT call _resolve_hwnds — hwnd takes priority
        mock_backend._resolve_hwnds.assert_not_called()
        mock_backend.get_element_tree.assert_any_call(
            app="MyApp", window_title=None, hwnd=12345, pid=None,
            depth=0, backend="uia",
        )

    def test_negative_depth_returns_error(self, server):
        # Only a negative depth is invalid now — 0 = unlimited, positive = honored.
        result = _call_tool(server, "see_ui_tree", {"depth": -1})
        data = json.loads(result[0].text)
        assert data["success"] is False
        assert data["error"]["code"] == "INVALID_INPUT"

    def test_zero_depth_is_valid_unlimited(self, server):
        # 0 (unlimited, the default) must NOT be rejected as invalid input.
        result = _call_tool(server, "see_ui_tree", {"depth": 0})
        data = json.loads(result[0].text)
        assert not (
            data.get("success") is False
            and data.get("error", {}).get("code") == "INVALID_INPUT"
        )

    def test_large_depth_is_valid(self, server):
        # A depth beyond the old 10 ceiling is accepted (native-bounded), so
        # setting the parameter is never silently useless.
        result = _call_tool(server, "see_ui_tree", {"depth": 40})
        data = json.loads(result[0].text)
        assert not (
            data.get("success") is False
            and data.get("error", {}).get("code") == "INVALID_INPUT"
        )

    def test_invalid_backend_returns_error(self, server):
        result = _call_tool(server, "see_ui_tree", {"accessibility_backend": "invalid"})
        data = json.loads(result[0].text)
        assert data["success"] is False
        assert data["error"]["code"] == "INVALID_INPUT"

    def test_no_window_returns_error(self, server, mock_backend):
        mock_backend.get_element_tree.return_value = None
        result = _call_tool(server, "see_ui_tree", {})
        data = json.loads(result[0].text)
        assert data["success"] is False
        assert data["error"]["code"] == "WINDOW_NOT_FOUND"

    def test_nested_children_serialized(self, server, mock_backend):
        child = _make_element(id="child1", role="Text", name="Hello", children=[])
        parent = _make_element(id="root", role="Window", name="Main", children=[child])
        mock_backend.get_element_tree.return_value = parent
        result = _call_tool(server, "see_ui_tree", {"format": "json"})
        data = json.loads(result[0].text)
        tree = data["tree"]
        assert len(tree["children"]) == 1
        # IDs are now stable hash-based refs
        assert tree["children"][0]["id"].startswith("e")
        assert tree["children"][0]["role"] == "Text"

    def test_valid_backend_values_accepted(self, server, mock_backend):
        for backend_name in ("uia", "msaa", "ia2", "jab", "auto"):
            result = _call_tool(server, "see_ui_tree", {"accessibility_backend": backend_name})
            data = json.loads(result[0].text)
            assert data["success"] is True


# ── find_element ─────────────────────────────────────────────────────


class TestFindElement:

    def test_found_element_returned(self, server, mock_backend):
        result = _call_tool(server, "find_element", {"selector": "Button:OK"})
        data = json.loads(result[0].text)
        assert data["success"] is True
        assert data["element"]["role"] == "Button"
        assert data["element"]["name"] == "OK"
        mock_backend.find_element.assert_called_once_with(
            selector="Button:OK", window_title=None,
        )

    def test_with_window_title(self, server, mock_backend):
        _call_tool(server, "find_element", {"selector": "Edit:*search*", "window_title": "Firefox"})
        mock_backend.find_element.assert_called_once_with(
            selector="Edit:*search*", window_title="Firefox",
        )

    def test_element_not_found(self, server, mock_backend):
        mock_backend.find_element.return_value = None
        result = _call_tool(server, "find_element", {"selector": "Button:Nonexistent"})
        data = json.loads(result[0].text)
        assert data["success"] is False
        assert data["error"]["code"] == "ELEMENT_NOT_FOUND"
        assert "Nonexistent" in data["error"]["message"]


# ── get_element_value ────────────────────────────────────────────────


class TestGetElementValue:

    def test_returns_value_and_metadata(self, server, mock_backend):
        result = _call_tool(server, "get_element_value", {"ref": "e47"})
        data = json.loads(result[0].text)
        assert data["success"] is True
        assert data["value"] == "hello"
        assert data["pattern"] == "ValuePattern"
        assert data["ref"] == "e47"
        assert data["bounds"]["x"] == 10

    def test_element_not_found(self, server, mock_backend):
        mock_backend.get_element_value.return_value = None
        result = _call_tool(server, "get_element_value", {"ref": "e999"})
        data = json.loads(result[0].text)
        assert data["success"] is False
        assert data["error"]["code"] == "ELEMENT_NOT_FOUND"

    def test_by_automation_id(self, server, mock_backend):
        _call_tool(server, "get_element_value", {"automation_id": "txt_input"})
        mock_backend.get_element_value.assert_called_once_with(
            ref=None, automation_id="txt_input", role=None,
            name=None, window_title=None, hwnd=None,
        )

    def test_by_role_and_name(self, server, mock_backend):
        _call_tool(server, "get_element_value", {"role": "Edit", "name": "Username"})
        mock_backend.get_element_value.assert_called_once_with(
            ref=None, automation_id=None, role="Edit",
            name="Username", window_title=None, hwnd=None,
        )


# ── set_element_value ────────────────────────────────────────────────


class TestSetElementValue:

    def test_success(self, server, mock_backend):
        result = _call_tool(server, "set_element_value", {
            "value": "new text", "automation_id": "txt_input",
        })
        data = json.loads(result[0].text)
        assert data["success"] is True
        assert data["action"] == "set_value"
        assert data["value"] == "new text"

    def test_failure(self, server, mock_backend):
        mock_backend.set_element_value.return_value = False
        result = _call_tool(server, "set_element_value", {
            "value": "x", "automation_id": "txt_readonly",
        })
        data = json.loads(result[0].text)
        assert data["success"] is False
        assert data["error"]["code"] == "SET_VALUE_FAILED"

    def test_with_window_title_resolves_hwnd(self, server, mock_backend):
        _call_tool(server, "set_element_value", {
            "value": "test", "window_title": "Notepad",
        })
        mock_backend._resolve_hwnd.assert_called_once_with(window_title="Notepad")

    def test_unresolvable_window_title_fails_loudly(self, server, mock_backend):
        """(#957) An unmatched window_title must fail loudly, never silently
        target the foreground window."""
        from naturo.errors import WindowNotFoundError
        mock_backend._resolve_hwnd.side_effect = WindowNotFoundError("Gone")
        result = _call_tool(server, "set_element_value", {
            "value": "test", "window_title": "Gone",
        })
        data = json.loads(result[0].text)
        assert data["success"] is False
        assert data["error"]["code"] == "WINDOW_NOT_FOUND"
        # The element write must NOT run against the foreground window.
        mock_backend.set_element_value.assert_not_called()

    def test_ref_resolves_via_snapshot(self, server, mock_backend):
        mock_elem = MagicMock()
        mock_elem.identifier = "resolved_aid"
        mock_elem.role = "Edit"
        mock_elem.title = "Name"
        mock_elem.label = None

        with patch("naturo.snapshot.get_snapshot_manager") as mock_mgr_fn:
            mock_mgr = MagicMock()
            mock_mgr.resolve_ref_element.return_value = (mock_elem, "snap1")
            mock_mgr_fn.return_value = mock_mgr

            _call_tool(server, "set_element_value", {"value": "test", "ref": "e5"})
            mock_mgr.resolve_ref_element.assert_called_once_with("e5")


# ── toggle_element ───────────────────────────────────────────────────


class TestToggleElement:

    def test_success_returns_new_state(self, server, mock_backend):
        result = _call_tool(server, "toggle_element", {"automation_id": "chk_agree"})
        data = json.loads(result[0].text)
        assert data["success"] is True
        assert data["action"] == "toggle"
        assert data["new_state"] == "On"

    def test_failure(self, server, mock_backend):
        mock_backend.toggle_element.return_value = None
        result = _call_tool(server, "toggle_element", {"name": "Missing"})
        data = json.loads(result[0].text)
        assert data["success"] is False
        assert data["error"]["code"] == "TOGGLE_FAILED"

    def test_with_window_title(self, server, mock_backend):
        _call_tool(server, "toggle_element", {
            "automation_id": "chk", "window_title": "Settings",
        })
        mock_backend._resolve_hwnd.assert_called_once_with(window_title="Settings")


# ── select_element ───────────────────────────────────────────────────


class TestSelectElement:

    def test_success(self, server, mock_backend):
        result = _call_tool(server, "select_element", {"name": "Option A"})
        data = json.loads(result[0].text)
        assert data["success"] is True
        assert data["action"] == "select"

    def test_failure(self, server, mock_backend):
        mock_backend.select_element.return_value = False
        result = _call_tool(server, "select_element", {"name": "Missing"})
        data = json.loads(result[0].text)
        assert data["success"] is False
        assert data["error"]["code"] == "SELECT_FAILED"


# ── expand_collapse_element ──────────────────────────────────────────


class TestExpandCollapseElement:

    def test_expand_success(self, server, mock_backend):
        result = _call_tool(server, "expand_collapse_element", {
            "expand": True, "name": "Dropdown",
        })
        data = json.loads(result[0].text)
        assert data["success"] is True
        assert data["action"] == "expand"

    def test_collapse_success(self, server, mock_backend):
        result = _call_tool(server, "expand_collapse_element", {
            "expand": False, "name": "Dropdown",
        })
        data = json.loads(result[0].text)
        assert data["success"] is True
        assert data["action"] == "collapse"

    def test_expand_failure(self, server, mock_backend):
        mock_backend.expand_collapse_element.return_value = False
        result = _call_tool(server, "expand_collapse_element", {
            "expand": True, "name": "Static",
        })
        data = json.loads(result[0].text)
        assert data["success"] is False
        assert data["error"]["code"] == "EXPAND_FAILED"

    def test_collapse_failure(self, server, mock_backend):
        mock_backend.expand_collapse_element.return_value = False
        result = _call_tool(server, "expand_collapse_element", {
            "expand": False, "name": "Static",
        })
        data = json.loads(result[0].text)
        assert data["success"] is False
        assert data["error"]["code"] == "COLLAPSE_FAILED"

    def test_with_window_title(self, server, mock_backend):
        _call_tool(server, "expand_collapse_element", {
            "expand": True, "name": "Tree", "window_title": "Explorer",
        })
        mock_backend._resolve_hwnd.assert_called_once_with(window_title="Explorer")


# ── read_web_text ────────────────────────────────────────────────────


class TestReadWebText:

    def test_reads_rendered_text_via_cdp(self, server, mock_backend):
        fake_client = MagicMock()
        fake_client.evaluate.return_value = (
            "Artificial intelligence is transforming the world"
        )
        with patch("naturo.cascade.find_cdp_port", return_value=9222), \
             patch("naturo.cdp.CDPClient", return_value=fake_client):
            result = _call_tool(server, "read_web_text", {"hwnd": 4332842})
        data = json.loads(result[0].text)
        assert data["success"] is True
        assert "Artificial intelligence" in data["text"]
        assert data["char_count"] == len(fake_client.evaluate.return_value)
        fake_client.connect.assert_called_once()

    def test_selector_targets_element(self, server, mock_backend):
        fake_client = MagicMock()
        fake_client.evaluate.return_value = "42"
        with patch("naturo.cascade.find_cdp_port", return_value=9222), \
             patch("naturo.cdp.CDPClient", return_value=fake_client):
            result = _call_tool(
                server, "read_web_text", {"hwnd": 1, "selector": ".result"}
            )
        data = json.loads(result[0].text)
        assert data["text"] == "42"
        assert data["selector"] == ".result"
        expr = fake_client.evaluate.call_args[0][0]
        assert "querySelector" in expr and ".result" in expr

    def test_no_cdp_endpoint_returns_actionable_error(self, server, mock_backend):
        with patch("naturo.cascade.find_cdp_port", return_value=None):
            result = _call_tool(server, "read_web_text", {"hwnd": 1})
        data = json.loads(result[0].text)
        assert data["success"] is False
        assert data["error"]["code"] == "CDP_NOT_AVAILABLE"

    def test_requires_a_target_window(self, server, mock_backend):
        result = _call_tool(server, "read_web_text", {})
        data = json.loads(result[0].text)
        assert data["success"] is False
        assert data["error"]["code"] == "INVALID_INPUT"

    def test_uses_recorded_port_not_probe(self, server, mock_backend):
        # launch_browser records hwnd -> port; read_web_text must use that exact
        # port and NOT blind-probe (which cross-talks when several debuggable
        # browsers are alive).
        from naturo.browser import _registry
        _registry.record(777, 9250)
        fake_client = MagicMock()
        fake_client.evaluate.return_value = "this-window's-own-text"
        try:
            with patch("naturo.cascade.find_cdp_port", return_value=None) as fcp, \
                 patch("naturo.cdp.CDPClient", return_value=fake_client) as cc:
                result = _call_tool(server, "read_web_text", {"hwnd": 777})
            data = json.loads(result[0].text)
            assert data["success"] is True
            assert data["text"] == "this-window's-own-text"
            fcp.assert_not_called()
            cc.assert_called_once_with(port=9250)
        finally:
            _registry.forget(777)
