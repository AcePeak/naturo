"""Tests for naturo.cli.interaction._common — shared interaction helpers.

Covers element search fallback, app ID resolution, selector resolution,
output formatting, desktop session checks, auto-routing, and post-action
UI snapshot. All mock-based, CI-safe.
"""
from __future__ import annotations

import json
import os
import sys
from dataclasses import dataclass, field
from typing import Optional
from unittest.mock import MagicMock, patch, PropertyMock

import pytest


# ── Fake element for tree search tests ────────────────────────────────────


@dataclass
class FakeElement:
    """Minimal element stub matching ElementInfo interface."""
    name: str = ""
    role: str = "Text"
    value: str = ""
    x: int = 100
    y: int = 100
    width: int = 50
    height: int = 30
    id: str = ""
    children: list = field(default_factory=list)
    properties: dict = field(default_factory=dict)
    is_actionable: bool = False


@dataclass
class FakeMatch:
    """Stub for search_elements result."""
    element: FakeElement
    score: float = 1.0


# ── _find_element_by_text_fallback tests ──────────────────────────────────


class TestFindElementByTextFallback:
    """Test the fallback element search with priority matching."""

    def _call(self, backend, text, **kwargs):
        from naturo.cli.interaction._common import _find_element_by_text_fallback
        return _find_element_by_text_fallback(backend, text, **kwargs)

    def test_returns_none_when_backend_has_no_tree(self):
        backend = MagicMock(spec=[])  # no get_element_tree
        assert self._call(backend, "OK") is None

    def test_returns_none_when_tree_is_none(self):
        backend = MagicMock()
        backend.get_element_tree.return_value = None
        assert self._call(backend, "OK") is None

    def test_returns_none_when_tree_raises(self):
        backend = MagicMock()
        backend.get_element_tree.side_effect = RuntimeError("fail")
        assert self._call(backend, "OK") is None

    def test_returns_none_when_no_matches(self):
        backend = MagicMock()
        backend.get_element_tree.return_value = FakeElement()
        with patch("naturo.search.search_elements", return_value=[]):
            assert self._call(backend, "OK") is None

    def test_prefers_exact_actionable_match(self):
        btn = FakeElement(name="Save", role="Button", x=10, y=20, width=60, height=40)
        txt = FakeElement(name="Save", role="Text", x=100, y=200, width=50, height=30)
        backend = MagicMock()
        backend.get_element_tree.return_value = FakeElement()
        matches = [FakeMatch(element=txt), FakeMatch(element=btn)]
        with patch("naturo.search.search_elements", return_value=matches):
            result = self._call(backend, "Save")
        assert result == (10 + 30, 20 + 20)  # center of button

    def test_falls_back_to_exact_any_match(self):
        txt = FakeElement(name="Save", role="Text", x=100, y=200, width=50, height=30)
        backend = MagicMock()
        backend.get_element_tree.return_value = FakeElement()
        matches = [FakeMatch(element=txt)]
        with patch("naturo.search.search_elements", return_value=matches):
            result = self._call(backend, "Save")
        assert result == (100 + 25, 200 + 15)

    def test_falls_back_to_substring_actionable(self):
        btn = FakeElement(name="Save Document", role="Button", x=0, y=0, width=80, height=40)
        backend = MagicMock()
        backend.get_element_tree.return_value = FakeElement()
        matches = [FakeMatch(element=btn)]
        with patch("naturo.search.search_elements", return_value=matches):
            result = self._call(backend, "Save")
        # "Save" != "Save Document", so exact_actionable/exact_any are empty
        # but "Save Document" contains "Save" → substring_actionable
        assert result == (40, 20)

    def test_skips_zero_bounds_elements(self):
        hidden = FakeElement(name="OK", role="Button", x=0, y=0, width=0, height=0)
        visible = FakeElement(name="OK", role="Text", x=50, y=50, width=40, height=20)
        backend = MagicMock()
        backend.get_element_tree.return_value = FakeElement()
        matches = [FakeMatch(element=hidden), FakeMatch(element=visible)]
        with patch("naturo.search.search_elements", return_value=matches):
            result = self._call(backend, "OK")
        assert result == (50 + 20, 50 + 10)  # visible element, not hidden

    def test_case_insensitive_matching(self):
        btn = FakeElement(name="SAVE", role="Button", x=10, y=10, width=100, height=50)
        backend = MagicMock()
        backend.get_element_tree.return_value = FakeElement()
        matches = [FakeMatch(element=btn)]
        with patch("naturo.search.search_elements", return_value=matches):
            result = self._call(backend, "save")
        assert result == (60, 35)

    def test_passes_app_and_pid_to_tree(self):
        backend = MagicMock()
        backend.get_element_tree.return_value = None
        self._call(backend, "OK", app="notepad", pid=1234)
        backend.get_element_tree.assert_called_once_with(
            app="notepad", window_title=None, hwnd=None, pid=1234, depth=5,
        )


# ── _elementinfo_to_dict tests ────────────────────────────────────────────


class TestElementInfoToDict:

    def test_basic_conversion(self):
        from naturo.cli.interaction._common import _elementinfo_to_dict
        el = FakeElement(
            name="OK", role="Button", value="val",
            x=10, y=20, width=30, height=40, id="auto123",
        )
        d = _elementinfo_to_dict(el)
        assert d["role"] == "Button"
        assert d["name"] == "OK"
        assert d["automationid"] == "auto123"
        assert d["value"] == "val"
        assert d["x"] == 10
        assert d["y"] == 20
        assert d["width"] == 30
        assert d["height"] == 40
        assert d["children"] == []

    def test_includes_classname_from_properties(self):
        from naturo.cli.interaction._common import _elementinfo_to_dict
        el = FakeElement(properties={"className": "Win32Button"})
        d = _elementinfo_to_dict(el)
        assert d["cls"] == "Win32Button"

    def test_recursive_children(self):
        from naturo.cli.interaction._common import _elementinfo_to_dict
        child = FakeElement(name="Child", role="Text")
        parent = FakeElement(name="Parent", role="Group", children=[child])
        d = _elementinfo_to_dict(parent)
        assert len(d["children"]) == 1
        assert d["children"][0]["name"] == "Child"

    def test_none_values_become_empty_strings(self):
        from naturo.cli.interaction._common import _elementinfo_to_dict
        el = FakeElement(name=None, value=None, id=None)
        d = _elementinfo_to_dict(el)
        assert d["name"] == ""
        assert d["value"] == ""
        assert d["automationid"] == ""


# ── _resolve_app_id tests ────────────────────────────────────────────────


class TestResolveAppId:

    def _call(self, app_id, app=None, hwnd=None, pid=None, json_output=False):
        from naturo.cli.interaction._common import _resolve_app_id
        return _resolve_app_id(app_id, app, hwnd, pid, json_output)

    def test_none_app_id_passes_through(self):
        result = self._call(None, app="notepad", hwnd=123, pid=456)
        assert result == ("notepad", 123, 456)

    def test_valid_app_id_returns_hwnd_and_pid(self):
        entry = MagicMock()
        entry.handle = 999
        entry.pid = 888
        mock_map = MagicMock()
        mock_map.resolve.return_value = entry
        with patch("naturo.app_ids.get_app_id_map", return_value=mock_map), \
             patch("naturo.cli.interaction._common._is_hwnd_alive", return_value=True):
            result = self._call("a1")
        assert result == (None, 999, 888)

    def test_invalid_app_id_returns_none_tuple(self):
        mock_map = MagicMock()
        mock_map.resolve.return_value = None
        with patch("naturo.app_ids.get_app_id_map", return_value=mock_map), \
             pytest.raises(SystemExit):
            self._call("a99", json_output=False)

    def test_stale_hwnd_emits_app_id_stale_error(self, capsys):
        """#788: stale HWND after app restart triggers APP_ID_STALE error."""
        entry = MagicMock()
        entry.handle = 0xDEAD
        entry.pid = 999
        mock_map = MagicMock()
        mock_map.resolve.return_value = entry
        with patch("naturo.app_ids.get_app_id_map", return_value=mock_map), \
             patch("naturo.cli.interaction._common._is_hwnd_alive", return_value=False), \
             pytest.raises(SystemExit) as exc_info:
            self._call("a1", json_output=True)
        assert exc_info.value.code == 1
        out = capsys.readouterr().out
        data = json.loads(out)
        assert data["success"] is False
        assert data["error"]["code"] == "APP_ID_STALE"
        assert "stale" in data["error"]["message"].lower()

    def test_stale_hwnd_text_mode(self, capsys):
        """#788: stale HWND in text mode prints error to stderr."""
        entry = MagicMock()
        entry.handle = 0xDEAD
        entry.pid = 999
        mock_map = MagicMock()
        mock_map.resolve.return_value = entry
        with patch("naturo.app_ids.get_app_id_map", return_value=mock_map), \
             patch("naturo.cli.interaction._common._is_hwnd_alive", return_value=False), \
             pytest.raises(SystemExit):
            self._call("a1", json_output=False)
        err = capsys.readouterr().err
        assert "stale" in err.lower()

    def test_alive_hwnd_passes_validation(self):
        """#788: alive HWND proceeds normally."""
        entry = MagicMock()
        entry.handle = 0x1234
        entry.pid = 555
        mock_map = MagicMock()
        mock_map.resolve.return_value = entry
        with patch("naturo.app_ids.get_app_id_map", return_value=mock_map), \
             patch("naturo.cli.interaction._common._is_hwnd_alive", return_value=True):
            result = self._call("a1")
        assert result == (None, 0x1234, 555)


# ── _is_hwnd_alive tests (#788) ─────────────────────────────────────────


class TestIsHwndAlive:
    """Tests for _is_hwnd_alive — HWND validity check."""

    def test_returns_true_on_non_windows(self):
        """On Linux/macOS (sys.platform != win32), always returns True."""
        from naturo.cli.interaction._common import _is_hwnd_alive
        # On Linux this should return True since sys.platform != "win32"
        assert _is_hwnd_alive(0x1234) is True

    def test_returns_false_for_zero_handle(self):
        """A zero/null HWND is never alive."""
        from naturo.cli.interaction._common import _is_hwnd_alive
        assert _is_hwnd_alive(0) is False

    @patch("sys.platform", "win32")
    def test_returns_true_when_window_valid(self):
        """IsWindow() returns nonzero for valid handles on Windows."""
        from naturo.cli.interaction._common import _is_hwnd_alive
        mock_ctypes = MagicMock()
        mock_ctypes.windll.user32.IsWindow.return_value = 1
        with patch.dict("sys.modules", {"ctypes": mock_ctypes}):
            assert _is_hwnd_alive(0x1234) is True

    @patch("sys.platform", "win32")
    def test_returns_false_when_window_dead(self):
        """IsWindow() returns 0 for stale handles on Windows."""
        from naturo.cli.interaction._common import _is_hwnd_alive
        mock_ctypes = MagicMock()
        mock_ctypes.windll.user32.IsWindow.return_value = 0
        with patch.dict("sys.modules", {"ctypes": mock_ctypes}):
            assert _is_hwnd_alive(0xDEAD) is False


# ── _json_ok / _json_err tests ───────────────────────────────────────────


class TestJsonOutput:

    def test_json_ok_json_mode(self, capsys):
        from naturo.cli.interaction._common import _json_ok
        _json_ok({"action": "click", "x": 10}, json_output=True)
        out = capsys.readouterr().out
        data = json.loads(out)
        assert data["success"] is True
        assert data["data"]["action"] == "click"

    def test_json_ok_text_mode(self, capsys):
        from naturo.cli.interaction._common import _json_ok
        _json_ok({"action": "click", "x": 10}, json_output=False)
        out = capsys.readouterr().out
        assert "action: click" in out
        assert "x: 10" in out

    def test_json_ok_text_mode_hides_verification_keys(self, capsys):
        from naturo.cli.interaction._common import _json_ok
        _json_ok(
            {"action": "click", "verified": True, "verification_detail": "ok"},
            json_output=False,
        )
        out = capsys.readouterr().out
        assert "action: click" in out
        assert "verified" not in out
        assert "verification_detail" not in out

    def test_json_err_json_mode(self, capsys):
        from naturo.cli.interaction._common import _json_err
        with pytest.raises(SystemExit) as exc_info:
            _json_err("not found", json_output=True, code="NOT_FOUND")
        assert exc_info.value.code == 1
        out = capsys.readouterr().out
        data = json.loads(out)
        assert data["success"] is False

    def test_json_err_text_mode(self, capsys):
        from naturo.cli.interaction._common import _json_err
        with pytest.raises(SystemExit):
            _json_err("not found", json_output=False)
        err = capsys.readouterr().err
        assert "Error: not found" in err


# ── _validate_method tests ───────────────────────────────────────────────


class TestValidateMethod:

    def test_always_returns_true(self):
        from naturo.cli.interaction._common import _validate_method
        assert _validate_method("auto", False) is True
        assert _validate_method("uia", True) is True
        assert _validate_method("vision", False) is True


# ── _check_desktop_session tests ─────────────────────────────────────────


class TestCheckDesktopSession:

    def _call(self):
        from naturo.cli.interaction._common import _check_desktop_session
        _check_desktop_session()

    @patch("platform.system", return_value="Linux")
    def test_noop_on_linux(self, _):
        self._call()  # Should not raise

    @patch("platform.system", return_value="Windows")
    def test_console_session_passes(self, _):
        with patch.dict(os.environ, {"SESSIONNAME": "Console"}):
            self._call()  # Should not raise

    @patch("platform.system", return_value="Windows")
    def test_rdp_session_passes(self, _):
        with patch.dict(os.environ, {"SESSIONNAME": "RDP-Tcp#42"}):
            self._call()  # Should not raise

    @patch("platform.system", return_value="Windows")
    def test_services_session_raises(self, _):
        from naturo.errors import NoDesktopSessionError
        with patch.dict(os.environ, {"SESSIONNAME": "Services"}):
            with pytest.raises(NoDesktopSessionError):
                self._call()

    @patch("platform.system", return_value="Windows")
    def test_unknown_session_name_passes(self, _):
        with patch.dict(os.environ, {"SESSIONNAME": "ICA-Citrix#5"}):
            self._call()  # Unknown names assumed interactive

    @patch("platform.system", return_value="Windows")
    def test_empty_session_checks_wts(self, _):
        with patch.dict(os.environ, {"SESSIONNAME": ""}, clear=False), \
             patch(
                 "naturo.cli.interaction._common._is_current_session_interactive",
                 return_value=True,
             ):
            self._call()  # WTS says interactive → pass

    @patch("platform.system", return_value="Windows")
    def test_empty_session_no_wts_no_explorer_raises(self, _):
        from naturo.errors import NoDesktopSessionError
        mock_result = MagicMock()
        mock_result.stdout = ""
        with patch.dict(os.environ, {"SESSIONNAME": ""}, clear=False), \
             patch(
                 "naturo.cli.interaction._common._is_current_session_interactive",
                 return_value=False,
             ), \
             patch("subprocess.run", return_value=mock_result):
            with pytest.raises(NoDesktopSessionError):
                self._call()


# ── _auto_route tests ────────────────────────────────────────────────────


class TestAutoRoute:

    def _call(self, app=None, pid=None, method="auto", json_output=False):
        from naturo.cli.interaction._common import _auto_route
        return _auto_route(app, pid, method, json_output)

    def test_returns_empty_dict_when_no_app_or_pid(self):
        assert self._call() == {}

    def test_returns_empty_dict_when_method_not_auto(self):
        assert self._call(app="notepad", method="uia") == {}

    def test_routes_when_app_provided(self):
        mock_result = MagicMock()
        mock_result.pid = 1234
        mock_result.method = "uia"
        mock_result.framework = "win32"
        mock_result.to_dict.return_value = {"method": "uia", "framework": "win32"}
        with patch("naturo.routing.resolve_method", return_value=mock_result):
            info = self._call(app="notepad")
        assert info["method"] == "uia"

    def test_exits_when_app_not_found(self):
        mock_result = MagicMock()
        mock_result.pid = None
        with patch("naturo.routing.resolve_method", return_value=mock_result), \
             pytest.raises(SystemExit):
            self._call(app="nonexistent_app", json_output=True)

    def test_returns_empty_on_routing_exception(self):
        with patch(
            "naturo.routing.resolve_method",
            side_effect=RuntimeError("boom"),
        ):
            assert self._call(app="notepad") == {}

    def test_routes_by_pid(self):
        mock_result = MagicMock()
        mock_result.pid = 5678
        mock_result.method = "msaa"
        mock_result.framework = "unknown"
        mock_result.to_dict.return_value = {"method": "msaa"}
        with patch("naturo.routing.resolve_method", return_value=mock_result):
            info = self._call(pid=5678)
        assert info["method"] == "msaa"


# ── _resolve_selector_target tests ───────────────────────────────────────


class TestResolveSelectorTarget:

    def _call(self, selector_str, backend, **kwargs):
        from naturo.cli.interaction._common import _resolve_selector_target
        defaults = dict(app=None, window_title=None, hwnd=None, pid=None, json_output=True)
        defaults.update(kwargs)
        return _resolve_selector_target(selector_str, backend, **defaults)

    def test_invalid_selector_returns_none(self):
        from naturo.selector import SelectorParseError
        backend = MagicMock()
        with patch("naturo.selector.parse", side_effect=SelectorParseError("bad")), \
             pytest.raises(SystemExit):
            self._call("[invalid", backend)

    def test_no_tree_support_returns_none(self):
        backend = MagicMock(spec=[])  # no get_element_tree
        ast = MagicMock()
        ast.app = None
        with patch("naturo.selector.parse", return_value=ast), \
             pytest.raises(SystemExit):
            self._call("//Button", backend)

    def test_tree_error_returns_none(self):
        backend = MagicMock()
        backend.get_element_tree.side_effect = RuntimeError("fail")
        ast = MagicMock()
        ast.app = None
        with patch("naturo.selector.parse", return_value=ast), \
             pytest.raises(SystemExit):
            self._call("//Button", backend)

    def test_successful_resolution_returns_coordinates(self):
        backend = MagicMock()
        tree = FakeElement(name="Root", role="Window", children=[
            FakeElement(name="Save", role="Button", x=100, y=200, width=80, height=40),
        ])
        backend.get_element_tree.return_value = tree

        ast = MagicMock()
        ast.app = None

        resolved = MagicMock()
        resolved.element = {"role": "Button", "name": "Save", "x": 100, "y": 200, "width": 80, "height": 40}
        resolved.match_quality = "exact"

        with patch("naturo.selector.parse", return_value=ast), \
             patch("naturo.selector.SelectorResolver") as MockResolver:
            MockResolver.return_value.resolve.return_value = resolved
            result = self._call("//Button[@name='Save']", backend)

        assert result == (100 + 40, 200 + 20)  # center

    def test_zero_bounds_match_exits(self):
        backend = MagicMock()
        backend.get_element_tree.return_value = FakeElement()
        ast = MagicMock()
        ast.app = None
        resolved = MagicMock()
        resolved.element = {"role": "Button", "name": "X", "x": 0, "y": 0, "width": 0, "height": 0}
        with patch("naturo.selector.parse", return_value=ast), \
             patch("naturo.selector.SelectorResolver") as MockResolver, \
             pytest.raises(SystemExit):
            MockResolver.return_value.resolve.return_value = resolved
            self._call("//Button", backend)

    def test_selector_app_overrides_cli_app(self):
        backend = MagicMock()
        backend.get_element_tree.return_value = FakeElement()
        ast = MagicMock()
        ast.app = "chrome.exe"
        resolved = MagicMock()
        resolved.element = {"role": "Button", "name": "X", "x": 10, "y": 10, "width": 50, "height": 50}
        resolved.match_quality = "exact"
        with patch("naturo.selector.parse", return_value=ast), \
             patch("naturo.selector.normalize_app_name", return_value="chrome") as mock_norm, \
             patch("naturo.selector.SelectorResolver") as MockResolver:
            MockResolver.return_value.resolve.return_value = resolved
            self._call("app://chrome.exe//Button", backend, app=None)
        mock_norm.assert_called_once_with("chrome.exe")


# ── _post_action_see tests ───────────────────────────────────────────────


class TestPostActionSee:

    def _call(self, backend, **kwargs):
        from naturo.cli.interaction._common import _post_action_see
        defaults = dict(
            settle_ms=0, app=None, window_title=None, hwnd=None,
            json_output=True, depth=7,
        )
        defaults.update(kwargs)
        return _post_action_see(backend, **defaults)

    def test_returns_none_when_tree_fails(self):
        backend = MagicMock()
        backend.get_element_tree.side_effect = RuntimeError("fail")
        result = self._call(backend)
        assert result is None

    def test_returns_none_when_tree_is_none(self):
        backend = MagicMock()
        backend.get_element_tree.return_value = None
        result = self._call(backend)
        assert result is None

    def test_returns_snapshot_data_in_json_mode(self):
        tree = FakeElement(name="Root", role="Window")
        backend = MagicMock()
        backend.get_element_tree.return_value = tree

        mock_mgr = MagicMock()
        mock_mgr.create_snapshot.return_value = "snap_123"

        with patch("naturo.snapshot.get_snapshot_manager", return_value=mock_mgr):
            result = self._call(backend, json_output=True)

        assert result is not None
        assert result["id"] == "snap_123"
        assert "elements" in result

    def test_settle_delay_is_applied(self):
        backend = MagicMock()
        backend.get_element_tree.return_value = None
        with patch("time.sleep") as mock_sleep:
            self._call(backend, settle_ms=500)
        mock_sleep.assert_called_once_with(0.5)

    def test_text_mode_prints_tree(self, capsys):
        tree = FakeElement(name="Root", role="Window", children=[
            FakeElement(name="Button1", role="Button"),
        ])
        backend = MagicMock()
        backend.get_element_tree.return_value = tree

        mock_mgr = MagicMock()
        mock_mgr.create_snapshot.return_value = "snap_456"

        with patch("naturo.snapshot.get_snapshot_manager", return_value=mock_mgr):
            result = self._call(backend, json_output=False)

        out = capsys.readouterr().out
        assert "UI snapshot (updated)" in out
        assert "snap_456" in out
        assert result["id"] == "snap_456"


# ── VALID_METHODS constant test ──────────────────────────────────────────


class TestValidMethods:

    def test_valid_methods_tuple(self):
        from naturo.cli.interaction._common import VALID_METHODS
        assert "auto" in VALID_METHODS
        assert "uia" in VALID_METHODS
        assert "cdp" in VALID_METHODS
        assert "vision" in VALID_METHODS
        assert "msaa" in VALID_METHODS
        assert "ia2" in VALID_METHODS
        assert "jab" in VALID_METHODS
        assert len(VALID_METHODS) == 7


# ── _get_backend tests ───────────────────────────────────────────────────


class TestGetBackend:

    def test_returns_backend_on_success(self):
        from naturo.cli.interaction._common import _get_backend
        mock_backend = MagicMock()
        with patch("naturo.cli.interaction._common._check_desktop_session"), \
             patch("naturo.backends.base.get_backend", return_value=mock_backend):
            result = _get_backend()
        assert result is mock_backend

    def test_raises_usage_error_on_no_desktop(self):
        from naturo.cli.interaction._common import _get_backend
        from naturo.errors import NoDesktopSessionError
        with patch(
            "naturo.cli.interaction._common._check_desktop_session",
            side_effect=NoDesktopSessionError("no desktop"),
        ):
            with pytest.raises(Exception):  # click.UsageError
                _get_backend(json_output=False)

    def test_json_mode_exits_on_no_desktop(self):
        from naturo.cli.interaction._common import _get_backend
        from naturo.errors import NoDesktopSessionError
        with patch(
            "naturo.cli.interaction._common._check_desktop_session",
            side_effect=NoDesktopSessionError("no desktop"),
        ), pytest.raises(SystemExit):
            _get_backend(json_output=True)
