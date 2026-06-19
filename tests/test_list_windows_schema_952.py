"""Tests for #952 — ``list windows -j`` / ``list apps -j`` window-schema parity.

Both commands enumerate top-level windows, but historically returned
incompatible JSON window objects: ``list apps`` used ``handle`` + ``id`` while
``list windows`` used ``hwnd`` and omitted ``id``. A programmatic consumer could
not treat the two outputs interchangeably, nor target a ``list windows`` entry
with ``--app-id``.

These tests pin the fixed contract:

* both commands emit the **same set of window keys**;
* the window-handle value is reachable under both ``handle`` and ``hwnd``
  (additive aliases — neither original key is removed);
* ``list windows -j`` emits the stable ``id`` (``a1`` …) and persists it via the
  app-id map so the entry is directly usable with ``--app-id``.

All mock-based, CI-safe (no real desktop / DLL).
"""
from __future__ import annotations

import json
from unittest.mock import MagicMock, patch

import pytest
from click.testing import CliRunner

from naturo.backends.base import WindowInfo
from naturo.cli._app.lifecycle import app_list
from naturo.cli.core._list import list_cmd


@pytest.fixture
def runner():
    return CliRunner()


def _make_window(**overrides):
    """Create a real WindowInfo (avoids MagicMock attribute pitfalls)."""
    return WindowInfo(
        handle=overrides.get("handle", 1182906),
        title=overrides.get("title", "Untitled - Notepad"),
        process_name=overrides.get("process_name", "notepad.exe"),
        pid=overrides.get("pid", 31912),
        x=overrides.get("x", 100),
        y=overrides.get("y", 100),
        width=overrides.get("width", 800),
        height=overrides.get("height", 600),
        is_visible=overrides.get("is_visible", True),
        is_minimized=overrides.get("is_minimized", False),
    )


def _list_windows_json(runner, windows):
    """Invoke ``list windows -j`` with a mocked backend; return (payload, id_map mock)."""
    backend = MagicMock()
    backend.list_windows.return_value = windows
    with patch("naturo.cli.core._common._platform_supports_gui", return_value=True), \
         patch("naturo.cli.core._common._get_backend", return_value=backend), \
         patch("naturo.app_ids.get_app_id_map") as mock_map, \
         patch("os.getpid", return_value=99999), patch("os.getppid", return_value=99998):
        result = runner.invoke(list_cmd, ["windows", "--json"], catch_exceptions=False)
    assert result.exit_code == 0, result.output
    return json.loads(result.output), mock_map


def _list_apps_json(runner, windows):
    """Invoke ``app list -j`` (== ``list apps``) with a mocked backend."""
    backend = MagicMock()
    backend.list_windows.return_value = windows
    backend._SYSTEM_PROCESS_NAMES = set()
    backend._UWP_HOST_PROCESS = "applicationframehost.exe"
    with patch("naturo.backends.base.get_backend", return_value=backend), \
         patch("naturo.cli.interaction._check_desktop_session"), \
         patch("naturo.app_ids.get_app_id_map"):
        result = runner.invoke(app_list, ["--json"], obj={}, catch_exceptions=False)
    assert result.exit_code == 0, result.output
    return json.loads(result.output)


class TestSchemaParity:

    def test_window_key_sets_match(self, runner):
        """The same window concept must expose identical keys in both commands."""
        windows_payload, _ = _list_windows_json(runner, [_make_window()])
        apps_payload = _list_apps_json(runner, [_make_window()])

        win_keys = set(windows_payload["windows"][0].keys())
        app_keys = set(apps_payload["windows"][0].keys())
        assert win_keys == app_keys, (
            f"key drift: only in windows={win_keys - app_keys}, "
            f"only in apps={app_keys - win_keys}"
        )

    def test_handle_and_hwnd_both_present_and_equal(self, runner):
        """Handle value reachable under both names (additive alias, nothing removed)."""
        windows_payload, _ = _list_windows_json(runner, [_make_window(handle=1182906)])
        apps_payload = _list_apps_json(runner, [_make_window(handle=1182906)])

        w = windows_payload["windows"][0]
        assert w["hwnd"] == 1182906          # original key preserved (back-compat)
        assert w["handle"] == 1182906        # new alias matches list apps
        a = apps_payload["windows"][0]
        assert a["handle"] == 1182906        # original key preserved
        assert a["hwnd"] == 1182906          # new alias matches list windows


class TestStableId:

    def test_list_windows_emits_stable_id(self, runner):
        """``list windows -j`` must emit consumable ``id`` (a1, a2, ...)."""
        windows_payload, _ = _list_windows_json(
            runner,
            [_make_window(title="Notepad"), _make_window(title="Calc", pid=200)],
        )
        ids = [w["id"] for w in windows_payload["windows"]]
        assert ids == ["a1", "a2"]

    def test_list_windows_persists_ids_for_app_id_targeting(self, runner):
        """Emitted ids are registered via assign_ids so ``--app-id`` resolves them."""
        win = _make_window()
        _, mock_map = _list_windows_json(runner, [win])
        mock_map.return_value.assign_ids.assert_called_once()
        passed = mock_map.return_value.assign_ids.call_args.args[0]
        assert list(passed) == [win]
