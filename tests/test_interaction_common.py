"""Tests for naturo.cli.interaction._common — shared interaction helpers."""
from __future__ import annotations

import json
import os
from unittest.mock import MagicMock, patch

import pytest

from naturo.cli.interaction._common import (
    _check_desktop_session,
    _json_err,
    _json_ok,
    _VERIFICATION_KEYS,
)


# ── _json_ok ─────────────────────────────────────


class TestJsonOk:
    """Tests for _json_ok() output helper."""

    def test_json_mode_wraps_data(self):
        out = []
        with patch("naturo.cli.interaction._common.click.echo", side_effect=out.append):
            _json_ok({"action": "pressed", "key": "enter"}, json_output=True)
        parsed = json.loads(out[0])
        assert parsed["success"] is True
        assert parsed["data"]["action"] == "pressed"

    def test_text_mode_prints_key_value(self):
        out = []
        with patch("naturo.cli.interaction._common.click.echo", side_effect=out.append):
            _json_ok({"action": "pressed", "key": "enter"}, json_output=False)
        assert "action: pressed" in out
        assert "key: enter" in out

    def test_text_mode_hides_verification_keys(self):
        out = []
        data = {
            "action": "pressed",
            "verified": True,
            "verification_detail": "focus changed",
            "verification_method": "focus",
        }
        with patch("naturo.cli.interaction._common.click.echo", side_effect=out.append):
            _json_ok(data, json_output=False)
        joined = " ".join(str(o) for o in out)
        assert "action: pressed" in joined
        assert "verified" not in joined
        assert "verification_detail" not in joined

    def test_json_mode_keeps_verification_keys(self):
        out = []
        data = {
            "action": "pressed",
            "verified": True,
            "verification_detail": "focus changed",
        }
        with patch("naturo.cli.interaction._common.click.echo", side_effect=out.append):
            _json_ok(data, json_output=True)
        parsed = json.loads(out[0])
        assert parsed["data"]["verified"] is True
        assert parsed["data"]["verification_detail"] == "focus changed"


# ── _json_err ────────────────────────────────────


class TestJsonErr:
    """Tests for _json_err() error helper."""

    def test_json_mode_outputs_error_json(self):
        out = []
        with patch("naturo.cli.interaction._common.click.echo", side_effect=out.append):
            with pytest.raises(SystemExit) as exc_info:
                _json_err("something broke", json_output=True, code="TEST_ERROR")
            assert exc_info.value.code == 1
        # Should contain JSON with error info
        assert "TEST_ERROR" in out[0] or "something broke" in out[0]

    def test_text_mode_outputs_to_stderr(self):
        with patch("naturo.cli.interaction._common.click.echo") as mock_echo:
            with pytest.raises(SystemExit) as exc_info:
                _json_err("bad input", json_output=False)
            assert exc_info.value.code == 1
            mock_echo.assert_called_once_with("Error: bad input", err=True)

    def test_custom_exit_code(self):
        with patch("naturo.cli.interaction._common.click.echo"):
            with pytest.raises(SystemExit) as exc_info:
                _json_err("fail", json_output=True, exit_code=2)
            assert exc_info.value.code == 2


# ── _check_desktop_session ───────────────────────


class TestCheckDesktopSession:
    """Tests for _check_desktop_session() pre-flight check."""

    @patch("platform.system", return_value="Linux")
    def test_non_windows_is_noop(self, _mock):
        _check_desktop_session()  # No exception on non-Windows

    @patch("platform.system", return_value="Windows")
    @patch.dict(os.environ, {"SESSIONNAME": "Console"}, clear=False)
    def test_console_session_passes(self, _mock):
        _check_desktop_session()

    @patch("platform.system", return_value="Windows")
    @patch.dict(os.environ, {"SESSIONNAME": "RDP-Tcp#0"}, clear=False)
    def test_rdp_session_passes(self, _mock):
        _check_desktop_session()

    @patch("platform.system", return_value="Windows")
    @patch.dict(os.environ, {"SESSIONNAME": "Services"}, clear=False)
    def test_services_session_raises(self, _mock):
        from naturo.errors import NoDesktopSessionError
        with pytest.raises(NoDesktopSessionError):
            _check_desktop_session()

    @patch("platform.system", return_value="Windows")
    @patch.dict(os.environ, {"SESSIONNAME": "ICA-tcp#1"}, clear=False)
    def test_citrix_session_passes(self, _mock):
        _check_desktop_session()

    @patch("naturo.cli.interaction._common._is_current_session_interactive", return_value=True)
    @patch("platform.system", return_value="Windows")
    @patch.dict(os.environ, {"SESSIONNAME": ""}, clear=False)
    def test_empty_sessionname_wts_interactive_passes(self, _mock_plat, _mock_wts):
        _check_desktop_session()

    @patch("naturo.cli.interaction._common._is_current_session_interactive", return_value=False)
    @patch("platform.system", return_value="Windows")
    @patch.dict(os.environ, {"SESSIONNAME": ""}, clear=False)
    def test_empty_sessionname_not_interactive_raises(self, _mock_plat, _mock_wts):
        from naturo.errors import NoDesktopSessionError
        # Mock subprocess to return no explorer
        with patch("subprocess.run") as mock_run:
            mock_run.return_value = MagicMock(stdout="")
            with pytest.raises(NoDesktopSessionError):
                _check_desktop_session()


# ── _VERIFICATION_KEYS ───────────────────────────


class TestVerificationKeys:
    """Verify the constant set is correctly defined."""

    def test_contains_expected_keys(self):
        assert "verified" in _VERIFICATION_KEYS
        assert "verification_detail" in _VERIFICATION_KEYS
        assert "verification_method" in _VERIFICATION_KEYS
        assert "verification_ms" in _VERIFICATION_KEYS
        assert "verification_error" in _VERIFICATION_KEYS

    def test_is_frozen(self):
        assert isinstance(_VERIFICATION_KEYS, frozenset)


# ── _find_element_by_text_fallback ──────────────


class TestFindElementByTextFallback:
    """Tests for _find_element_by_text_fallback() tree search."""

    def _make_element(self, role="Button", name="OK", x=100, y=200, w=80, h=30, children=None):
        el = MagicMock()
        el.role = role
        el.name = name
        el.x = x
        el.y = y
        el.width = w
        el.height = h
        el.children = children or []
        return el

    def _make_match(self, element):
        m = MagicMock()
        m.element = element
        return m

    def test_no_get_element_tree_returns_none(self):
        from naturo.cli.interaction._common import _find_element_by_text_fallback
        backend = MagicMock(spec=[])  # no get_element_tree
        assert _find_element_by_text_fallback(backend, "OK") is None

    def test_empty_tree_returns_none(self):
        from naturo.cli.interaction._common import _find_element_by_text_fallback
        backend = MagicMock()
        backend.get_element_tree.return_value = None
        assert _find_element_by_text_fallback(backend, "OK") is None

    def test_no_matches_returns_none(self):
        from naturo.cli.interaction._common import _find_element_by_text_fallback
        backend = MagicMock()
        backend.get_element_tree.return_value = self._make_element()
        with patch("naturo.search.search_elements", return_value=[]):
            assert _find_element_by_text_fallback(backend, "OK") is None

    def test_exact_actionable_match(self):
        from naturo.cli.interaction._common import _find_element_by_text_fallback
        backend = MagicMock()
        btn = self._make_element(role="Button", name="OK", x=100, y=200, w=80, h=30)
        backend.get_element_tree.return_value = btn
        with patch("naturo.search.search_elements",
                   return_value=[self._make_match(btn)]):
            result = _find_element_by_text_fallback(backend, "OK")
        assert result == (140, 215)  # center: 100+80//2, 200+30//2

    def test_exact_any_match_when_no_actionable(self):
        from naturo.cli.interaction._common import _find_element_by_text_fallback
        backend = MagicMock()
        text_el = self._make_element(role="Text", name="OK", x=50, y=60, w=40, h=20)
        backend.get_element_tree.return_value = text_el
        with patch("naturo.search.search_elements",
                   return_value=[self._make_match(text_el)]):
            result = _find_element_by_text_fallback(backend, "OK")
        assert result == (70, 70)  # 50+40//2, 60+20//2

    def test_zero_bounds_skipped(self):
        from naturo.cli.interaction._common import _find_element_by_text_fallback
        backend = MagicMock()
        offscreen = self._make_element(role="Button", name="OK", x=0, y=0, w=0, h=0)
        backend.get_element_tree.return_value = offscreen
        with patch("naturo.search.search_elements",
                   return_value=[self._make_match(offscreen)]):
            result = _find_element_by_text_fallback(backend, "OK")
        assert result is None

    def test_case_insensitive_match(self):
        from naturo.cli.interaction._common import _find_element_by_text_fallback
        backend = MagicMock()
        btn = self._make_element(role="Button", name="ok", x=10, y=20, w=60, h=40)
        backend.get_element_tree.return_value = btn
        with patch("naturo.search.search_elements",
                   return_value=[self._make_match(btn)]):
            result = _find_element_by_text_fallback(backend, "OK")
        assert result == (40, 40)  # 10+60//2, 20+40//2

    def test_tree_fetch_exception_returns_none(self):
        from naturo.cli.interaction._common import _find_element_by_text_fallback
        backend = MagicMock()
        backend.get_element_tree.side_effect = RuntimeError("no tree")
        assert _find_element_by_text_fallback(backend, "OK") is None


# ── _resolve_app_id ─────────────────────────────


class TestResolveAppId:
    """Tests for _resolve_app_id() app-id resolution."""

    def test_none_app_id_passthrough(self):
        from naturo.cli.interaction._common import _resolve_app_id
        result = _resolve_app_id(None, "notepad", 123, 456, False)
        assert result == ("notepad", 123, 456)

    def test_valid_app_id_returns_handle_and_pid(self):
        from naturo.cli.interaction._common import _resolve_app_id
        entry = MagicMock(handle=999, pid=111)
        fake_map = MagicMock()
        fake_map.resolve.return_value = entry
        with patch("naturo.app_ids.get_app_id_map", return_value=fake_map):
            result = _resolve_app_id("a1", "notepad", None, None, False)
        assert result == (None, 999, 111)

    def test_invalid_app_id_exits(self):
        from naturo.cli.interaction._common import _resolve_app_id
        fake_map = MagicMock()
        fake_map.resolve.return_value = None
        with patch("naturo.app_ids.get_app_id_map", return_value=fake_map):
            with pytest.raises(SystemExit):
                _resolve_app_id("a99", None, None, None, True)


# ── _elementinfo_to_dict ────────────────────────


class TestElementInfoToDict:
    """Tests for _elementinfo_to_dict() conversion."""

    def test_basic_conversion(self):
        from naturo.cli.interaction._common import _elementinfo_to_dict
        el = MagicMock()
        el.role = "Button"
        el.name = "OK"
        el.id = "btn1"
        el.value = ""
        el.x = 10
        el.y = 20
        el.width = 80
        el.height = 30
        el.properties = {}
        el.children = []
        result = _elementinfo_to_dict(el)
        assert result["role"] == "Button"
        assert result["name"] == "OK"
        assert result["automationid"] == "btn1"
        assert result["children"] == []

    def test_classname_from_properties(self):
        from naturo.cli.interaction._common import _elementinfo_to_dict
        el = MagicMock()
        el.role = "Edit"
        el.name = "Input"
        el.id = "edit1"
        el.value = "hello"
        el.x = 0
        el.y = 0
        el.width = 200
        el.height = 30
        el.properties = {"className": "TextBox"}
        el.children = []
        result = _elementinfo_to_dict(el)
        assert result["cls"] == "TextBox"

    def test_recursive_children(self):
        from naturo.cli.interaction._common import _elementinfo_to_dict
        child = MagicMock()
        child.role = "Text"
        child.name = "Label"
        child.id = "lbl"
        child.value = ""
        child.x = 5
        child.y = 5
        child.width = 50
        child.height = 20
        child.properties = {}
        child.children = []

        parent = MagicMock()
        parent.role = "Group"
        parent.name = "Panel"
        parent.id = "grp"
        parent.value = ""
        parent.x = 0
        parent.y = 0
        parent.width = 100
        parent.height = 100
        parent.properties = {}
        parent.children = [child]

        result = _elementinfo_to_dict(parent)
        assert len(result["children"]) == 1
        assert result["children"][0]["role"] == "Text"


# ── _auto_route ─────────────────────────────────


class TestAutoRoute:
    """Tests for _auto_route() auto-routing helper."""

    def test_explicit_method_skips_routing(self):
        from naturo.cli.interaction._common import _auto_route
        result = _auto_route(app="notepad", pid=None, method="uia", json_output=False)
        assert result == {}

    def test_no_app_no_pid_skips_routing(self):
        from naturo.cli.interaction._common import _auto_route
        result = _auto_route(app=None, pid=None, method="auto", json_output=False)
        assert result == {}

    def test_auto_with_app_calls_resolve_method(self):
        from naturo.cli.interaction._common import _auto_route
        fake_result = MagicMock()
        fake_result.pid = 123
        fake_result.method = "uia"
        fake_result.framework = "WPF"
        fake_result.to_dict.return_value = {"method": "uia", "framework": "WPF"}
        with patch("naturo.routing.resolve_method", return_value=fake_result):
            result = _auto_route(app="notepad", pid=None, method="auto", json_output=False)
        assert result["method"] == "uia"

    def test_auto_with_app_not_found_exits(self):
        from naturo.cli.interaction._common import _auto_route
        fake_result = MagicMock()
        fake_result.pid = None  # app not found
        with patch("naturo.routing.resolve_method", return_value=fake_result):
            with pytest.raises(SystemExit):
                _auto_route(app="nonexistent", pid=None, method="auto", json_output=True)

    def test_routing_exception_returns_empty(self):
        from naturo.cli.interaction._common import _auto_route
        with patch("naturo.routing.resolve_method", side_effect=RuntimeError("fail")):
            result = _auto_route(app="notepad", pid=None, method="auto", json_output=False)
        assert result == {}


# ── _get_backend ────────────────────────────────


class TestGetBackend:
    """Tests for _get_backend() in interaction module."""

    @patch("naturo.cli.interaction._common._check_desktop_session")
    @patch("naturo.backends.base.get_backend")
    def test_returns_backend(self, mock_get, mock_check):
        from naturo.cli.interaction._common import _get_backend
        mock_get.return_value = MagicMock()
        backend = _get_backend(json_output=False)
        mock_check.assert_called_once()
        assert backend is mock_get.return_value

    @patch("naturo.cli.interaction._common._check_desktop_session",
           side_effect=Exception("no desktop"))
    def test_no_desktop_json_exits(self, _mock):
        from naturo.cli.interaction._common import _get_backend
        with pytest.raises(SystemExit):
            _get_backend(json_output=True)

    @patch("naturo.cli.interaction._common._check_desktop_session",
           side_effect=Exception("no desktop"))
    def test_no_desktop_text_exits_1(self, _mock):
        # A missing desktop is a runtime failure: exit 1, never Click's exit-2
        # UsageError / 'Usage:' banner (#866).
        from naturo.cli.interaction._common import _get_backend
        with pytest.raises(SystemExit) as exc_info:
            _get_backend(json_output=False)
        assert exc_info.value.code == 1


# ── _validate_method ────────────────────────────


class TestValidateMethod:
    """Tests for _validate_method()."""

    def test_always_returns_true(self):
        from naturo.cli.interaction._common import _validate_method
        assert _validate_method("auto", False) is True
        assert _validate_method("uia", True) is True
        assert _validate_method("cdp", False) is True
