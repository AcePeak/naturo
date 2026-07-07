#!/usr/bin/env python3
"""Plug naturo into any AI-agent framework — copy-paste tool wiring.

naturo exports its full Windows-automation tool surface in the two
function-calling shapes every framework speaks (OpenAI + Anthropic). Give your
agent those tools, then route each tool call the model returns back to naturo.

    from naturo.agent_tools import to_openai_tools, to_anthropic_tools

    tools = to_openai_tools()      # OpenAI SDK / Agents SDK / LangChain / LiteLLM
    tools = to_anthropic_tools()   # Anthropic Messages API

This file shows the wiring for three popular frameworks plus a single
dispatcher (`run_tool`) that executes a tool call against the local desktop via
the naturo CLI. The framework SDKs are imported lazily, so this module imports
fine even when they are not installed.

Requirements:
    - Windows 10/11 with a desktop session (to actually *run* the tools)
    - pip install naturo
    - plus the SDK for whichever framework you use:
        pip install openai        # openai_chat_demo
        pip install anthropic      # anthropic_demo
        pip install langchain-core # langchain_demo

Usage:
    python agent_frameworks.py list        # print the exported tool surface
    python agent_frameworks.py openai       # OpenAI function-calling wiring
    python agent_frameworks.py anthropic    # Anthropic tool-use wiring
    python agent_frameworks.py langchain    # LangChain StructuredTool wiring
"""
from __future__ import annotations

import argparse
import json
import subprocess
from typing import Any, Dict

from naturo.agent_tools import naturo_tool_specs, to_anthropic_tools, to_openai_tools

# --- Dispatcher: execute one tool call against the local desktop -------------
# The model returns a tool name + JSON arguments; map that to a naturo command.
# The simplest robust bridge is the CLI (`naturo <tool> --json`); an MCP client
# session works too if you prefer structured transport.


def run_tool(name: str, arguments: Dict[str, Any]) -> Dict[str, Any]:
    """Execute a tool call by shelling out to the naturo CLI, return its JSON."""
    cmd = ["naturo", name.replace("_", "-")]
    for key, value in arguments.items():
        flag = "--" + key.replace("_", "-")
        if isinstance(value, bool):
            if value:
                cmd.append(flag)
        else:
            cmd += [flag, str(value)]
    cmd.append("--json")
    proc = subprocess.run(cmd, capture_output=True, text=True)
    try:
        return json.loads(proc.stdout)
    except json.JSONDecodeError:
        return {"success": proc.returncode == 0, "raw": proc.stdout, "error": proc.stderr}


# --- Framework wiring --------------------------------------------------------


def openai_demo() -> None:
    """OpenAI function-calling (also OpenAI Agents SDK / LiteLLM / autogen)."""
    from openai import OpenAI  # pip install openai

    client = OpenAI()
    tools = to_openai_tools()  # naturo's full surface, ready to pass through

    messages = [{"role": "user", "content": "Open Notepad and type 'hi from naturo'."}]
    resp = client.chat.completions.create(model="gpt-4o", messages=messages, tools=tools)

    for call in resp.choices[0].message.tool_calls or []:
        result = run_tool(call.function.name, json.loads(call.function.arguments))
        print(call.function.name, "->", result.get("success"))


def anthropic_demo() -> None:
    """Anthropic Messages tool-use."""
    import anthropic  # pip install anthropic

    client = anthropic.Anthropic()
    tools = to_anthropic_tools()  # naturo's full surface, ready to pass through

    resp = client.messages.create(
        model="claude-sonnet-4-20250514",
        max_tokens=1024,
        tools=tools,
        messages=[{"role": "user", "content": "Open Notepad and type 'hi from naturo'."}],
    )
    for block in resp.content:
        if getattr(block, "type", None) == "tool_use":
            result = run_tool(block.name, dict(block.input))
            print(block.name, "->", result.get("success"))


def langchain_demo() -> None:
    """LangChain / LangGraph StructuredTool wiring built from the OpenAI specs."""
    from langchain_core.tools import StructuredTool  # pip install langchain-core

    lc_tools = [
        StructuredTool.from_function(
            name=spec["function"]["name"],
            description=spec["function"]["description"],
            func=(lambda _name: (lambda **kwargs: run_tool(_name, kwargs)))(spec["function"]["name"]),
        )
        for spec in to_openai_tools()
    ]
    # Bind to any LangChain chat model:  model.bind_tools(lc_tools)
    print(f"Built {len(lc_tools)} LangChain tools, e.g. {lc_tools[0].name}")


def list_demo() -> None:
    """Print the exported tool surface (no framework or desktop needed)."""
    specs = naturo_tool_specs()
    print(f"naturo exports {len(specs)} tools:")
    for spec in specs:
        summary = (spec["description"].splitlines() or [""])[0][:60]
        print(f"  {spec['name']:<28} {summary}")


DEMOS = {
    "list": list_demo,
    "openai": openai_demo,
    "anthropic": anthropic_demo,
    "langchain": langchain_demo,
}


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("demo", choices=sorted(DEMOS), help="which framework wiring to run")
    args = parser.parse_args()
    DEMOS[args.demo]()


if __name__ == "__main__":
    main()
