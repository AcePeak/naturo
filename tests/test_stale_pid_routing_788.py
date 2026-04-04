"""Tests for #788: stale HWND detection in app ID and direct HWND resolution.

After an app restarts, cached HWNDs from app_ids become stale. Previously,
_resolve_app_id returned them without validation, causing focus_window to
silently fail and keystrokes to be delivered to the wrong foreground window.
"""
from __future__ import annotations

from unittest.mock import patch, MagicMock
from types import SimpleNamespace

import pytest

from naturo.cli.interaction._common import _resolve_app_id, _is_hwnd_alive


class TestIsHwndAlive:
    """Tests for the _is_hwnd_alive helper."""

    def test_zero_hwnd_is_not_alive(self):
        assert _is_hwnd_alive(0) is False

    def test_none_hwnd_is_not_alive(self):
        assert _is_hwnd_alive(None) is False

    def test_nonwindows_always_returns_true(self):
        """On non-Windows platforms, HWND validation is not possible."""
        with patch("naturo.cli.interaction._common.sys") as mock_sys:
            mock_sys.platform = "linux"
            assert _is_hwnd_alive(12345) is True


class TestResolveAppIdStaleness:
    """_resolve_app_id must detect stale HWNDs and emit APP_ID_STALE."""

    def _make_entry(self, handle=1001, pid=100, process_name="notepad.exe"):
        return SimpleNamespace(handle=handle, pid=pid, process_name=process_name)

    def _make_id_map(self, entry):
        id_map = MagicMock()
        id_map.resolve.return_value = entry
        return id_map

    def test_stale_hwnd_emits_error(self):
        """When HWND is dead, _resolve_app_id exits with error."""
        entry = self._make_entry(handle=1001)
        id_map = self._make_id_map(entry)

        with patch("naturo.cli.interaction._common._is_hwnd_alive", return_value=False), \
             patch("naturo.app_ids.get_app_id_map", return_value=id_map), \
             pytest.raises(SystemExit):
            _resolve_app_id("a1", None, None, None, json_output=False)

    def test_live_hwnd_returns_entry(self):
        """When HWND is alive, _resolve_app_id returns the stored handle+pid."""
        entry = self._make_entry(handle=1001, pid=100)
        id_map = self._make_id_map(entry)

        with patch("naturo.cli.interaction._common._is_hwnd_alive", return_value=True), \
             patch("naturo.app_ids.get_app_id_map", return_value=id_map):
            result = _resolve_app_id("a1", None, None, None, json_output=False)
        assert result == (None, 1001, 100)

    def test_stale_hwnd_json_output(self, capsys):
        """In JSON mode, stale HWND should produce APP_ID_STALE error JSON."""
        entry = self._make_entry(handle=1001)
        id_map = self._make_id_map(entry)

        with patch("naturo.cli.interaction._common._is_hwnd_alive", return_value=False), \
             patch("naturo.app_ids.get_app_id_map", return_value=id_map), \
             pytest.raises(SystemExit):
            _resolve_app_id("a1", None, None, None, json_output=True)

    def test_no_app_id_passthrough(self):
        """When app_id is None, function should pass through unchanged."""
        result = _resolve_app_id(None, "notepad", 999, 42, json_output=False)
        assert result == ("notepad", 999, 42)
