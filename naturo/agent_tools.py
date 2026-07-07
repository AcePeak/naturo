"""Framework-ready tool specs — give any AI-agent framework naturo's Windows tools.

naturo's MCP server exposes its Windows desktop automation (the unified
correctness-tagged element tree, click, type, read, window/app/Excel/Word
control, …) as tools with JSON-Schema inputs. This module re-emits that same
surface in the two function-calling shapes every framework speaks:

- **OpenAI** (also OpenAI Agents SDK, LangChain, LiteLLM, autogen, …):
  ``{"type": "function", "function": {"name", "description", "parameters"}}``
- **Anthropic** (Messages tool-use): ``{"name", "description", "input_schema"}``

So any framework can drive a real Windows desktop through naturo without
naturo-specific glue::

    from naturo.agent_tools import to_openai_tools, to_anthropic_tools

    tools = to_openai_tools()      # -> pass straight to client.chat.completions.create(tools=...)
    tools = to_anthropic_tools()   # -> pass straight to client.messages.create(tools=...)

The specs are derived from the *same* MCP registry the server serves, so they
never drift from what the agent can actually call. Deriving them needs no
Windows desktop — the schemas are declared statically — so this is safe to run
anywhere (CI, macOS, Linux) to inspect or ship the tool surface.

Dispatching a tool call the model returns is the framework's job; a copy-paste
executor that routes a call to naturo (via MCP or the CLI) lives in
``examples/agent_frameworks.py``.
"""
from __future__ import annotations

import asyncio
from typing import Any, Dict, List, Optional

__all__ = [
    "ToolSpec",
    "naturo_tool_specs",
    "to_openai_tools",
    "to_anthropic_tools",
]

# Canonical, framework-neutral spec: {"name", "description", "parameters"}
# where ``parameters`` is a JSON-Schema object. Mirrors the internal shape used
# by naturo.providers.agent_base.AGENT_TOOLS so the two never diverge in shape.
ToolSpec = Dict[str, Any]


def _run_coro(coro: Any) -> Any:
    """Run *coro* to completion from sync code, tolerating an already-open loop.

    ``asyncio.run`` raises if a loop is already running in this thread; in that
    case we drive the coroutine on a throwaway loop in a worker thread so this
    stays callable from notebooks / async apps as well as plain scripts.
    """
    try:
        asyncio.get_running_loop()
    except RuntimeError:
        return asyncio.run(coro)

    import concurrent.futures

    with concurrent.futures.ThreadPoolExecutor(max_workers=1) as pool:
        return pool.submit(lambda: asyncio.run(coro)).result()


def naturo_tool_specs() -> List[ToolSpec]:
    """Return naturo's full tool surface as canonical, framework-neutral specs.

    Each entry is ``{"name", "description", "parameters"}`` with ``parameters``
    a JSON-Schema object. Sorted by name for deterministic, diff-friendly
    output. Derived from the live MCP tool registry — no desktop required.
    """
    from naturo.mcp_server import create_server

    server = create_server()
    tools = _run_coro(server.list_tools())

    specs: List[ToolSpec] = []
    for tool in tools:
        schema = getattr(tool, "inputSchema", None) or {"type": "object", "properties": {}}
        specs.append(
            {
                "name": tool.name,
                "description": tool.description or "",
                "parameters": schema,
            }
        )
    specs.sort(key=lambda s: s["name"])
    return specs


def to_openai_tools(specs: Optional[List[ToolSpec]] = None) -> List[Dict[str, Any]]:
    """Convert canonical specs to OpenAI function-calling tool definitions.

    Accepted as-is by the OpenAI SDK (``tools=``), the OpenAI Agents SDK,
    LangChain, LiteLLM and any framework that speaks the OpenAI function shape.
    Defaults to naturo's full tool surface when *specs* is omitted.
    """
    if specs is None:
        specs = naturo_tool_specs()
    return [
        {
            "type": "function",
            "function": {
                "name": s["name"],
                "description": s["description"],
                "parameters": s["parameters"],
            },
        }
        for s in specs
    ]


def to_anthropic_tools(specs: Optional[List[ToolSpec]] = None) -> List[Dict[str, Any]]:
    """Convert canonical specs to Anthropic Messages tool-use definitions.

    Accepted as-is by the Anthropic SDK (``client.messages.create(tools=...)``).
    Defaults to naturo's full tool surface when *specs* is omitted.
    """
    if specs is None:
        specs = naturo_tool_specs()
    return [
        {
            "name": s["name"],
            "description": s["description"],
            "input_schema": s["parameters"],
        }
        for s in specs
    ]
