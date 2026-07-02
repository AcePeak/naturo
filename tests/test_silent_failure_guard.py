"""M4 criterion 1 — behavioral guard against silent failures.

A *silent failure* is any CLI/MCP path that returns ``success: true`` while the
underlying operation actually failed. This guard drives every state-changing MCP
tool with a backend that fails — either by raising, or by returning a falsy
failure indicator — and asserts the tool reports ``success: false`` with a real
error code. A positive control proves the guard is not vacuous (it would catch a
planted regression).

Pure mock backend: no DLL, no desktop — Linux-collectable, runs on every CI lane.
Extends the #885/#1180 no-silent-failure line of guards.
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


def _call(server, name: str, args: dict) -> dict:
    async def _run():
        return await server.call_tool(name, args)

    loop = asyncio.new_event_loop()
    try:
        res = loop.run_until_complete(_run())
    finally:
        loop.close()
    return json.loads(res[0].text)


def _assert_reports_failure(data: dict, ctx: str) -> None:
    """The guard's core assertion: a failed op must not report ``success: true``."""
    assert data.get("success") is not True, (
        f"SILENT FAILURE: {ctx} returned success:true on a failed operation"
    )
    assert data.get("success") is False, f"{ctx} did not report success:false: {data}"
    assert "error" in data and data["error"].get("code"), (
        f"{ctx} failure envelope missing error.code: {data}"
    )


def _server_patches(backend):
    return (
        patch("naturo.mcp_server.get_backend", return_value=backend),
        patch("naturo.snapshot.get_snapshot_manager", return_value=MagicMock()),
    )


# (tool, args, backend method whose failure must surface). Args are valid so the
# tool reaches the backend call rather than short-circuiting on validation.
_RAISE_CASES = [
    ("click", {"x": 100, "y": 200}, "click"),
    ("type_text", {"text": "x"}, "type_text"),
    ("press_key", {"key": "enter"}, "press_key"),
    ("hotkey", {"keys": ["ctrl", "s"]}, "hotkey"),
    ("scroll", {"direction": "down", "amount": 5}, "scroll"),
    ("drag", {"from_x": 0, "from_y": 0, "to_x": 1, "to_y": 1}, "drag"),
    ("move_mouse", {"x": 500, "y": 300}, "move_mouse"),
    ("focus_window", {"title": "Notepad"}, "focus_window"),
    ("window_close", {"title": "Notepad"}, "close_window"),
    ("window_minimize", {"hwnd": 12345}, "minimize_window"),
    ("window_maximize", {"hwnd": 12345}, "maximize_window"),
    ("window_restore", {"hwnd": 12345}, "restore_window"),
    ("window_move", {"x": 50, "y": 100, "hwnd": 12345}, "move_window"),
    ("window_resize", {"width": 1024, "height": 768, "hwnd": 12345}, "resize_window"),
    ("window_set_bounds", {"x": 1, "y": 2, "width": 100, "height": 100, "hwnd": 12345}, "set_bounds"),
    ("quit_app", {"name": "notepad"}, "quit_app"),
    ("clipboard_set", {"text": "x"}, "clipboard_set"),
    ("clipboard_clear", {}, "clipboard_clear"),
    ("set_element_value", {"value": "x", "automation_id": "foo", "hwnd": 123}, "set_element_value"),
    ("toggle_element", {"automation_id": "foo", "hwnd": 123}, "toggle_element"),
    ("select_element", {"name": "Option A", "hwnd": 123}, "select_element"),
    ("expand_collapse_element", {"expand": True, "automation_id": "foo", "hwnd": 123}, "expand_collapse_element"),
]


@pytest.mark.parametrize("tool,args,method", _RAISE_CASES)
def test_backend_exception_reports_failure(tool, args, method):
    """When the backend op raises (even an unexpected error), the tool must
    return success:false — never swallow it into a success envelope."""
    backend = MagicMock()
    backend.set_focused_element_value.return_value = False  # type_text → keystroke path
    getattr(backend, method).side_effect = RuntimeError(f"{method} exploded")
    p1, p2 = _server_patches(backend)
    with p1, p2:
        data = _call(create_server(), tool, args)
    # Non-vacuous: the tool must actually have reached (and failed at) the op,
    # not short-circuited on validation before the backend call.
    getattr(backend, method).assert_called()
    _assert_reports_failure(data, f"{tool} (backend.{method} raised)")


# Tools whose backend method returns a falsy failure indicator (not an exception)
# — the "ignored bool" silent-failure class.
_FALSY_CASES = [
    ("set_element_value", {"value": "x", "automation_id": "foo", "hwnd": 123}, "set_element_value", False),
    ("select_element", {"name": "Option A", "hwnd": 123}, "select_element", False),
    ("expand_collapse_element", {"expand": True, "automation_id": "foo", "hwnd": 123}, "expand_collapse_element", False),
    ("toggle_element", {"automation_id": "foo", "hwnd": 123}, "toggle_element", None),
]


@pytest.mark.parametrize("tool,args,method,failval", _FALSY_CASES)
def test_backend_falsy_return_reports_failure(tool, args, method, failval):
    """When the backend op returns a falsy failure indicator, the tool must still
    report success:false (the ignored-bool class must stay closed)."""
    backend = MagicMock()
    getattr(backend, method).return_value = failval
    p1, p2 = _server_patches(backend)
    with p1, p2:
        data = _call(create_server(), tool, args)
    getattr(backend, method).assert_called()  # non-vacuous: op was reached
    _assert_reports_failure(data, f"{tool} (backend.{method} returned {failval!r})")


def test_guard_positive_control_is_not_vacuous():
    """A success:true envelope on a failed op MUST trip the guard — proves the
    guard would catch a planted regression rather than passing vacuously."""
    planted = {"success": True, "action": "planted"}  # what a silent-failure tool returns
    with pytest.raises(AssertionError):
        _assert_reports_failure(planted, "planted silent failure")
