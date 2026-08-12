"""Self-maintaining contract: one canonical window-selector name across MCP (#900).

The MCP window-targeting parameter name used to drift across tools —
``focus_window``/``window_*``/``wait_for_window`` took ``title`` while
``see_ui_tree``/``capture_window``/``wait_for_element`` took ``window_title`` —
so an agent had to remember a different name per tool (and, combined with #891's
unknown-arg drop, a wrong guess failed silently). #900 unifies on
``window_title`` as the single canonical selector, keeping ``title`` as a
deprecated alias where a tool's primary name changed.

These tests pin the fix:

* Every window-targeting MCP tool exposes ``window_title`` in its schema.
* No window-targeting tool exposes ``title`` as its *only* window selector
  (the drift is gone) — where ``title`` survives it is strictly a back-compat
  alias sitting alongside ``window_title``.
* The deprecated ``title`` alias still resolves on the renamed tools, and
  ``window_title`` wins when both are supplied.

All desktop-independent: schema introspection + a mocked backend.
"""
from __future__ import annotations

import asyncio
import json
from unittest.mock import MagicMock, patch

import pytest

mcp_available = True
try:
    from naturo.mcp_server import create_server
except ImportError:  # pragma: no cover - mcp optional
    mcp_available = False

pytestmark = pytest.mark.skipif(not mcp_available, reason="mcp package not installed")

# The window-targeting MCP tools that MUST expose the canonical ``window_title``
# selector. These are the surfaces enumerated in #900 (the renamed ``title``
# outliers) plus the tools that already used ``window_title``. A new
# window-targeting tool should be added here so the drift cannot silently return.
_EXPECTED_WINDOW_TARGET_TOOLS = frozenset({
    # Renamed by #900 (were ``title``):
    "focus_window", "window_close", "window_minimize", "window_maximize",
    "window_restore", "window_move", "window_resize", "window_set_bounds",
    "wait_for_window",
    # Already canonical:
    "capture_window", "see_ui_tree", "read_web_text", "find_element",
    "get_element_value", "set_element_value", "toggle_element",
    "select_element", "expand_collapse_element", "wait_for_element",
    "wait_until_gone", "type_text", "press_key",
})

# Tools that legitimately still declare a ``title`` parameter meaning something
# other than a window selector, so the "no bare title selector" guard must not
# flag them.
_TITLE_MEANS_SOMETHING_ELSE: frozenset = frozenset()


def _list_tools():
    server = create_server()
    loop = asyncio.new_event_loop()
    try:
        return loop.run_until_complete(server.list_tools())
    finally:
        loop.close()


def _props(tool) -> dict:
    return (tool.inputSchema or {}).get("properties", {})


def _call_tool(server, tool_name: str, arguments: dict):
    async def _run():
        return await server.call_tool(tool_name, arguments)

    loop = asyncio.new_event_loop()
    try:
        return loop.run_until_complete(_run())
    finally:
        loop.close()


@pytest.fixture
def tools():
    return {t.name: t for t in _list_tools()}


# ── Schema-level unification ─────────────────────────────────────────────


def test_expected_window_tools_are_all_registered(tools):
    """Guard the guard: every tool this contract names must exist."""
    missing = _EXPECTED_WINDOW_TARGET_TOOLS - set(tools)
    assert not missing, f"contract names unregistered tools: {sorted(missing)}"


@pytest.mark.parametrize("tool_name", sorted(_EXPECTED_WINDOW_TARGET_TOOLS))
def test_window_tool_exposes_window_title(tool_name, tools):
    """Every window-targeting tool exposes the canonical ``window_title``."""
    props = _props(tools[tool_name])
    assert "window_title" in props, (
        f"{tool_name} does not expose canonical 'window_title'; params={sorted(props)}"
    )


def test_no_tool_uses_title_as_its_only_window_selector(tools):
    """The drift is gone: no tool offers ``title`` without ``window_title``.

    Any tool that still declares ``title`` must also declare ``window_title``
    (i.e. ``title`` survives only as a back-compat alias, never as the sole
    window-selector name).
    """
    offenders = []
    for name, tool in tools.items():
        if name in _TITLE_MEANS_SOMETHING_ELSE:
            continue
        props = _props(tool)
        if "title" in props and "window_title" not in props:
            offenders.append(name)
    assert not offenders, (
        f"tools expose 'title' as their only window selector (param drift): {offenders}"
    )


# ── Deprecated-alias behaviour ───────────────────────────────────────────


@pytest.fixture
def mock_backend():
    return MagicMock()


@pytest.fixture
def server(mock_backend):
    with patch("naturo.mcp_server.get_backend", return_value=mock_backend):
        yield create_server()


def test_focus_window_window_title_selector(server, mock_backend):
    """The canonical ``window_title`` selects the target window."""
    result = _call_tool(server, "focus_window", {"window_title": "Notepad"})
    assert json.loads(result[0].text)["success"] is True
    mock_backend.focus_window.assert_called_once_with(title="Notepad", hwnd=None)


def test_focus_window_title_alias_still_resolves(server, mock_backend):
    """The deprecated ``title`` alias keeps working (back-compat)."""
    result = _call_tool(server, "focus_window", {"title": "Notepad"})
    assert json.loads(result[0].text)["success"] is True
    mock_backend.focus_window.assert_called_once_with(title="Notepad", hwnd=None)


def test_focus_window_window_title_wins_over_alias(server, mock_backend):
    """When both are given, canonical ``window_title`` wins over ``title``."""
    result = _call_tool(
        server, "focus_window",
        {"window_title": "Chosen", "title": "Ignored"},
    )
    assert json.loads(result[0].text)["success"] is True
    mock_backend.focus_window.assert_called_once_with(title="Chosen", hwnd=None)


def test_wait_for_window_window_title_selector(server, mock_backend):
    wait_result = MagicMock(found=True, wait_time=0.1)
    with patch("naturo.wait.wait_for_window", return_value=wait_result) as m:
        result = _call_tool(server, "wait_for_window", {"window_title": "Notepad"})
    assert json.loads(result[0].text)["success"] is True
    assert m.call_args.kwargs["title"] == "Notepad"


def test_wait_for_window_title_alias_still_resolves(server, mock_backend):
    wait_result = MagicMock(found=True, wait_time=0.1)
    with patch("naturo.wait.wait_for_window", return_value=wait_result) as m:
        result = _call_tool(server, "wait_for_window", {"title": "Notepad"})
    assert json.loads(result[0].text)["success"] is True
    assert m.call_args.kwargs["title"] == "Notepad"


def test_wait_for_window_missing_selector_is_invalid(server, mock_backend):
    """With neither selector supplied the tool reports INVALID_INPUT, not a crash."""
    result = _call_tool(server, "wait_for_window", {})
    data = json.loads(result[0].text)
    assert data["success"] is False
    assert data["error"]["code"] == "INVALID_INPUT"
