"""Tests for naturo.agent_tools — framework-ready tool-spec export.

These pin the *contract* of the exported specs (shape + fidelity to the MCP
registry) so any framework can consume them. They run with no Windows desktop —
tool schemas are declared statically — so they are Linux/CI-collectable.
"""
from __future__ import annotations

import json

from naturo.agent_tools import (
    naturo_tool_specs,
    to_anthropic_tools,
    to_openai_tools,
)


def test_specs_are_non_empty_and_canonical() -> None:
    specs = naturo_tool_specs()
    assert specs, "expected naturo to export at least one tool spec"
    for s in specs:
        assert set(s) == {"name", "description", "parameters"}
        assert isinstance(s["name"], str) and s["name"]
        assert isinstance(s["description"], str) and s["description"].strip()
        params = s["parameters"]
        assert isinstance(params, dict)
        # A function-calling parameters block is a JSON-Schema object.
        assert params.get("type") == "object"


def test_specs_are_sorted_and_unique() -> None:
    names = [s["name"] for s in naturo_tool_specs()]
    assert names == sorted(names), "specs must be deterministically ordered by name"
    assert len(names) == len(set(names)), "tool names must be unique"


def test_specs_match_the_live_mcp_registry() -> None:
    """The export is derived from — and complete against — the MCP server."""
    import asyncio

    from naturo.mcp_server import create_server

    server = create_server()
    registry_names = {t.name for t in asyncio.run(server.list_tools())}
    exported_names = {s["name"] for s in naturo_tool_specs()}
    assert exported_names == registry_names


def test_openai_shape() -> None:
    tools = to_openai_tools()
    assert len(tools) == len(naturo_tool_specs())
    for t in tools:
        assert t["type"] == "function"
        fn = t["function"]
        assert set(fn) == {"name", "description", "parameters"}
        assert fn["name"] and fn["description"]
        assert fn["parameters"]["type"] == "object"


def test_anthropic_shape() -> None:
    tools = to_anthropic_tools()
    assert len(tools) == len(naturo_tool_specs())
    for t in tools:
        assert set(t) == {"name", "description", "input_schema"}
        assert t["name"] and t["description"]
        assert t["input_schema"]["type"] == "object"


def test_both_formats_carry_the_same_tool_names() -> None:
    openai_names = {t["function"]["name"] for t in to_openai_tools()}
    anthropic_names = {t["name"] for t in to_anthropic_tools()}
    assert openai_names == anthropic_names


def test_exported_tools_are_json_serializable() -> None:
    # Frameworks send these over the wire — they must round-trip through JSON.
    json.dumps(to_openai_tools())
    json.dumps(to_anthropic_tools())


def test_conversion_helpers_accept_explicit_specs() -> None:
    specs = [
        {"name": "demo", "description": "d", "parameters": {"type": "object", "properties": {}}}
    ]
    assert to_openai_tools(specs) == [
        {
            "type": "function",
            "function": {
                "name": "demo",
                "description": "d",
                "parameters": {"type": "object", "properties": {}},
            },
        }
    ]
    assert to_anthropic_tools(specs) == [
        {
            "name": "demo",
            "description": "d",
            "input_schema": {"type": "object", "properties": {}},
        }
    ]
