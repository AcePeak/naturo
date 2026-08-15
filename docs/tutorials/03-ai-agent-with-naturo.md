# Tutorial 3 — Build an AI Agent That Uses naturo

**What you'll build:** an AI agent that can see and drive the Windows desktop by
calling naturo. You'll do it two ways: (1) the **zero-code** path — run naturo as
an MCP server and point Claude Desktop (or Claude Code) at it, so Claude gets
60+ desktop tools automatically; and (2) the **code** path — a minimal Python
tool-use loop that hands Claude a couple of naturo actions and lets it decide
when to call them. By the end you'll understand how naturo turns any MCP-capable
model into a desktop agent, and how to wire naturo tools into your own agent loop.

> **Time:** ~15 minutes. **Platform:** Windows 10/11. **Python:** 3.9+.

## Prerequisites

```bash
pip install naturo
```

naturo's MCP server ships in the box. Pull in the MCP runtime dependency once:

```bash
naturo mcp install
```

Confirm the server can enumerate its tools without starting a session:

```bash
naturo mcp tools
```

Expected output (truncated):

```
Naturo MCP Server — 60+ tools available:

  launch_app            Launch an application by name.
  see_ui_tree           Read a window's UI as a structured element tree...
  type_text             Type text into a target window (or the focused window).
  press_key             Press a key or key combination.
  click                 Click at coordinates or on a UI element.
  capture_window        Capture a screenshot of a specific window.
  list_windows          List all visible windows on the desktop.
  ...
```

Those tool names (`launch_app`, `see_ui_tree`, `type_text`, `press_key`,
`click`, `capture_window`, `list_windows`, …) are the real MCP surface — they're
what an AI agent calls.

---

## Path 1 — Run naturo as an MCP server (zero code)

### (a) The one-liner

The MCP server speaks stdio by default (the transport AI agents expect):

```bash
naturo mcp start
```

That's the whole server. Agents launch it for you via their MCP config, so you
rarely run it by hand — but this is the command every config below invokes.

### (b) Point Claude Code at it

One line, then restart Claude Code:

```bash
claude mcp add naturo -- naturo mcp start
```

### (c) Point Claude Desktop at it

Add naturo to `claude_desktop_config.json`, then restart Claude Desktop:

```json
{
  "mcpServers": {
    "naturo": {
      "command": "naturo",
      "args": ["mcp", "start"]
    }
  }
}
```

> **Config file location:**
> - Windows: `%APPDATA%\Claude\claude_desktop_config.json`
> - macOS: `~/Library/Application Support/Claude/claude_desktop_config.json`

This config is exactly what naturo's shipped Claude Desktop bundle
(`packaging/mcpb/manifest.json`) and its MCP registry manifest (`server.json`)
declare — both run `naturo mcp start` over stdio. So whether you install the
`.mcpb` bundle or hand-write the config above, the agent ends up talking to the
same server.

### (d) Try it

Open a chat with Claude (Desktop or Code) and ask:

> Open Notepad, type "Hello from my agent", and save it as `agent-demo.txt`.
> Tell me when the title bar shows the saved file name.

Claude drives naturo's MCP tools to do it — under the hood it runs the same
`launch_app` → `type_text` → `press_key` sequence you'd script by hand, and every
naturo input tool re-reads the UI after acting and reports `"verified": true`
only when the change actually landed. If an action didn't take effect, the tool
returns `"success": false` instead of pretending — so the agent never claims it
worked when it didn't.

---

## Path 2 — Drive naturo from your own agent loop (Python)

If you're building your own agent instead of using Claude Desktop, you give the
model a set of tools and run the tool-use loop yourself. The example below is a
**minimal, illustrative** agent: it defines two tools that map to real naturo SDK
functions (`naturo.launch` and `naturo.type`), then lets Claude decide when to
call them. It is deliberately small — a starting point, not a framework.

```python
# agent.py — illustrative: an Anthropic tool-use loop that drives naturo.
# Requires: pip install naturo anthropic   (and an ANTHROPIC_API_KEY)
import anthropic
import naturo

# Two naturo actions, exposed to the model as tools. Each maps to a REAL naturo
# SDK function — no invented APIs.
TOOLS = [
    {
        "name": "launch_app",
        "description": "Launch a Windows application by name (e.g. 'notepad').",
        "input_schema": {
            "type": "object",
            "properties": {"name": {"type": "string"}},
            "required": ["name"],
        },
    },
    {
        "name": "type_text",
        "description": "Type text into a target window (focuses it first).",
        "input_schema": {
            "type": "object",
            "properties": {
                "text": {"type": "string"},
                "window": {"type": "string", "description": "Window title (partial match)"},
            },
            "required": ["text", "window"],
        },
    },
]


def run_tool(name, args):
    """Execute a tool call against naturo's SDK, return a short result string."""
    if name == "launch_app":
        app = naturo.launch(args["name"])
        return f"launched {app.name} (pid {app.pid})"
    if name == "type_text":
        method = naturo.type(args["text"], window=args["window"])
        return f"typed via {method}"
    return f"unknown tool: {name}"


client = anthropic.Anthropic()
messages = [{
    "role": "user",
    "content": "Open Notepad and type 'Hello from my agent' into it.",
}]

# Standard tool-use loop: call the model, run any tools it asks for, feed the
# results back, repeat until it stops calling tools.
while True:
    resp = client.messages.create(
        model="claude-opus-5",
        max_tokens=1024,
        tools=TOOLS,
        messages=messages,
    )
    messages.append({"role": "assistant", "content": resp.content})

    if resp.stop_reason != "tool_use":
        break

    results = []
    for block in resp.content:
        if block.type == "tool_use":
            output = run_tool(block.name, block.input)
            results.append({
                "type": "tool_result",
                "tool_use_id": block.id,
                "content": output,
            })
    messages.append({"role": "user", "content": results})

# Print the model's final text.
print("".join(b.text for b in resp.content if b.type == "text"))
```

Run it with naturo's runner so `import naturo` resolves without any environment
setup:

```bash
naturo run agent.py
```

> **Why this stays honest:** the tool bodies call `naturo.launch` and
> `naturo.type` — the same SDK verbs from
> [Tutorial 1](01-automate-notepad.md). `naturo.type` routes through the
> IME-immune ladder and returns the delivery method, so the tool result tells the
> model *how* the text landed. Add more tools (`naturo.see`, `naturo.press`,
> `naturo.click`, `naturo.capture`) the same way to widen what the agent can do.

> **MCP vs. your own loop:** Path 1 gives the agent *all* 60+ naturo tools with
> zero glue code and is the right default. Path 2 is for when you're embedding
> desktop control inside your own application and want to choose exactly which
> actions the model may take.

---

## Next steps

- **Learn the verbs** the agent is calling, by hand first:
  [Tutorial 1 — Automate Notepad](01-automate-notepad.md) and
  [Tutorial 2 — Automate Excel](02-automate-excel.md).
- **Full MCP tool reference** — every tool, its parameters, and worked examples:
  [docs/MCP_SERVER.md](../MCP_SERVER.md).
- **Agent integration guide** — [docs/AGENT_INTEGRATION.md](../AGENT_INTEGRATION.md).

## Troubleshooting

| Symptom | Fix |
|---------|-----|
| Claude does not see naturo's tools | Restart the client after editing its MCP config; run `naturo mcp tools` to confirm the server starts and lists tools. |
| `naturo mcp start` exits immediately | Run `naturo mcp install` to pull the MCP runtime dependency. |
| `naturo: command not found` inside the config | naturo must be on the `PATH` the agent launches with. It is after `pip install naturo`; if the agent runs in a different environment, give the full path to the `naturo` executable in the config `command`. |
| A tool reports `"success": false` | naturo refuses to fake success — read `error.message`; the window may not be focused yet or the target may not exist. |
| The Python agent can't authenticate | Set `ANTHROPIC_API_KEY` in the environment before `naturo run agent.py`. The API example is illustrative — swap in whatever model/provider your app uses. |
