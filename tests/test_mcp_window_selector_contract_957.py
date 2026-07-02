"""Self-maintaining loud-failure contract for MCP window-selector resolution (#957).

Root cause (silent-failure class): several MCP tools accept a window selector
(``window_title``), fail to resolve it, and *silently* proceed against the
foreground/default window — returning ``success:true`` on the wrong window.
``#954`` (``capture_window``) and ``#956`` (``create_snapshot``) were two
instances; the ``_inspect.py`` action tools (``set_element_value``,
``toggle_element``, ``select_element``, ``expand_collapse_element``) swallowed
the resolution failure at debug level and acted on the foreground window.

Instead of fixing this one tool at a time, this module enforces a single
contract over the whole MCP surface, enumerated from the live server registry:

    A tool that takes ``window_title`` and resolves it to act on / read a
    concrete window MUST, when given a window title that does not resolve,
    return ``success:false`` with ``error.code == "WINDOW_NOT_FOUND"`` — it
    must NEVER fall back to the foreground window and report success.

Because the tool list is read from the registry, a newly-added tool that takes
``window_title`` is covered automatically: it must either honour the contract
or be added to :data:`_SEMANTIC_EXCEPTIONS` with an explicit justification, so
the silent-fallback bug can no longer ship unnoticed. Mirrors the
self-maintaining guards in ``tests/test_no_desktop_guard_885.py`` (#885/#912).

Closes #957.
"""
from __future__ import annotations

import asyncio
import json
from unittest.mock import MagicMock, patch

import pytest

from naturo.errors import WindowNotFoundError

mcp_available = True
try:
    from naturo.mcp_server import create_server
except ImportError:  # pragma: no cover - mcp optional
    mcp_available = False

pytestmark = pytest.mark.skipif(not mcp_available, reason="mcp package not installed")

# A window title guaranteed not to match any real window.
_BOGUS_TITLE = "__no_such_window_zzz__"

# Tools that accept ``window_title`` but whose not-found semantics legitimately
# differ from the loud-WINDOW_NOT_FOUND contract. Each entry is a conscious
# decision, not an oversight — a new tool is NOT exempt unless added here.
_SEMANTIC_EXCEPTIONS = {
    # Wait tools: a window that is not (yet) present is a valid target, not an
    # immediate error. ``wait_until_gone`` on an absent window even succeeds
    # immediately ("already gone"); ``wait_for_element`` times out. Neither is
    # the silent-foreground-fallback bug this contract guards against.
    "wait_for_element",
    "wait_until_gone",
}


def _tools_with_window_title():
    """Return every registered MCP tool whose input schema exposes ``window_title``."""
    server = create_server()
    loop = asyncio.new_event_loop()
    try:
        tools = loop.run_until_complete(server.list_tools())
    finally:
        loop.close()
    return [
        t for t in tools
        if "window_title" in (t.inputSchema or {}).get("properties", {})
    ]


def _synthesize_required_args(tool):
    """Build a minimal valid argument set for *tool* (excluding window_title).

    Supplies a benign placeholder for every required parameter other than the
    window selector, so a tool with required fields (e.g. ``value``,
    ``selector``) can be invoked. Keeps the contract self-maintaining: a new
    required field gets a placeholder automatically from its declared type.
    """
    schema = tool.inputSchema or {}
    props = schema.get("properties", {})
    args: dict = {}
    for name in schema.get("required", []):
        if name in ("window_title", "hwnd", "pid", "app"):
            continue
        json_type = props.get(name, {}).get("type")
        if json_type == "integer":
            args[name] = 1
        elif json_type == "number":
            args[name] = 1.0
        elif json_type == "boolean":
            args[name] = True
        else:
            args[name] = "x"
    return args


def _make_backend():
    """A backend that cannot resolve the bogus title — every window-resolution
    entrypoint raises WindowNotFoundError, exactly as the real backend does for
    a non-existent window. Non-resolution methods return plausible foreground
    data, so a tool that *does* silently fall back would visibly return
    ``success:true`` and fail the contract.
    """
    backend = MagicMock()
    not_found = WindowNotFoundError(_BOGUS_TITLE)
    backend._resolve_hwnd.side_effect = not_found
    backend._resolve_hwnds.side_effect = not_found
    backend.get_element_tree.side_effect = not_found
    backend.get_element_value.side_effect = not_found
    # find_element resolves window_title internally via _resolve_hwnd (#963), so
    # an unmatched title raises here exactly as the real backend does.
    backend.find_element.side_effect = not_found
    return backend


def _call(server, tool_name, arguments):
    async def _run():
        return await server.call_tool(tool_name, arguments)

    loop = asyncio.new_event_loop()
    try:
        return loop.run_until_complete(_run())
    finally:
        loop.close()


def _response_payload(result):
    """Extract the JSON dict a tool returned via the MCP text-content channel."""
    content = result[0] if isinstance(result, tuple) else result
    text = content[0].text
    return json.loads(text)


_CONTRACT_TOOLS = [
    pytest.param(t, id=t.name)
    for t in (_tools_with_window_title() if mcp_available else [])
    if t.name not in _SEMANTIC_EXCEPTIONS
]


def test_some_tools_are_under_contract():
    """Guard the guard: the registry must actually expose window_title tools."""
    assert _CONTRACT_TOOLS, "no MCP tools with window_title found — registry probe broken"


@pytest.mark.parametrize("tool", _CONTRACT_TOOLS)
def test_unresolvable_window_title_fails_loudly(tool):
    """An unresolved window_title must yield WINDOW_NOT_FOUND, never silent success."""
    backend = _make_backend()
    arguments = {"window_title": _BOGUS_TITLE, **_synthesize_required_args(tool)}
    with patch("naturo.mcp_server.get_backend", return_value=backend), \
         patch("naturo.cli.interaction._check_desktop_session"):
        server = create_server()
        result = _call(server, tool.name, arguments)

    payload = _response_payload(result)
    assert payload.get("success") is False, (
        f"{tool.name} returned success on a bogus window_title — silent "
        f"foreground fallback: {payload}"
    )
    code = payload.get("error", {}).get("code")
    assert code == "WINDOW_NOT_FOUND", (
        f"{tool.name} failed with {code!r}, expected WINDOW_NOT_FOUND: {payload}"
    )
