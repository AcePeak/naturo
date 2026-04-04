"""Tests for #788: stale PID/HWND routing detection.

When a process dies, its HWND becomes stale.  _resolve_app_id and
_resolve_hwnd must detect this and raise clear errors rather than
silently operating on dead windows.
"""

from unittest.mock import patch, MagicMock

import pytest

from naturo.cli.interaction._common import _is_hwnd_alive, _resolve_app_id


class TestIsHwndAlive:
    """_is_hwnd_alive checks window handle liveness."""

    def test_non_windows_always_true(self):
        """On non-Windows platforms, always returns True."""
        with patch("naturo.cli.interaction._common.sys") as mock_sys:
            mock_sys.platform = "linux"
            assert _is_hwnd_alive(12345) is True

    def test_zero_hwnd(self):
        """Zero HWND is falsy, but _is_hwnd_alive is only called for truthy HWNDs."""
        # The function should handle 0 gracefully
        result = _is_hwnd_alive(0)
        assert isinstance(result, bool)


class TestResolveAppIdStaleCheck:
    """_resolve_app_id rejects stale window handles."""

    def test_stale_hwnd_emits_error(self):
        """When IsWindow returns False, _resolve_app_id should error."""
        mock_entry = MagicMock()
        mock_entry.handle = 99999
        mock_entry.pid = 12345

        mock_id_map = MagicMock()
        mock_id_map.resolve.return_value = mock_entry

        with patch("naturo.app_ids.get_app_id_map", return_value=mock_id_map) as _, \
             patch("naturo.cli.interaction._common._is_hwnd_alive", return_value=False):
            # Should call sys.exit(1) via _json_err
            with pytest.raises(SystemExit):
                _resolve_app_id("a1", None, None, None, json_output=True)

    def test_live_hwnd_returns_entry(self):
        """When IsWindow returns True, _resolve_app_id returns the entry."""
        mock_entry = MagicMock()
        mock_entry.handle = 12345
        mock_entry.pid = 6789

        mock_id_map = MagicMock()
        mock_id_map.resolve.return_value = mock_entry

        with patch("naturo.app_ids.get_app_id_map", return_value=mock_id_map), \
             patch("naturo.cli.interaction._common._is_hwnd_alive", return_value=True):
            app, hwnd, pid = _resolve_app_id("a1", None, None, None, json_output=True)
            assert hwnd == 12345
            assert pid == 6789
            assert app is None

    def test_no_app_id_passthrough(self):
        """When app_id is None, original values pass through unchanged."""
        app, hwnd, pid = _resolve_app_id(None, "notepad", 111, 222, json_output=False)
        assert app == "notepad"
        assert hwnd == 111
        assert pid == 222

    def test_expired_entry_emits_not_found(self):
        """When the ID map returns None (expired), emit APP_ID_NOT_FOUND."""
        mock_id_map = MagicMock()
        mock_id_map.resolve.return_value = None

        with patch("naturo.app_ids.get_app_id_map", return_value=mock_id_map):
            with pytest.raises(SystemExit):
                _resolve_app_id("a99", None, None, None, json_output=True)


class TestResolveHwndStaleCheck:
    """_resolve_hwnd rejects stale directly-passed HWNDs."""

    def test_stale_hwnd_raises(self, monkeypatch):
        """Passing a dead HWND directly should raise WindowNotFoundError."""
        from naturo.backends.windows import WindowsBackend
        from naturo.errors import WindowNotFoundError

        backend = WindowsBackend()
        monkeypatch.setattr(
            "naturo.cli.interaction._common._is_hwnd_alive",
            lambda h: False,
        )

        with pytest.raises(WindowNotFoundError):
            backend._resolve_hwnd(hwnd=99999)

    def test_live_hwnd_returns(self, monkeypatch):
        """Passing a live HWND should return it directly."""
        from naturo.backends.windows import WindowsBackend

        backend = WindowsBackend()
        monkeypatch.setattr(
            "naturo.cli.interaction._common._is_hwnd_alive",
            lambda h: True,
        )

        result = backend._resolve_hwnd(hwnd=12345)
        assert result == 12345
