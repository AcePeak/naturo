# Give your AI agent Windows control — in 3 lines

naturo ships an **MCP server** that exposes its Windows desktop automation —
capture, the **unified correctness-tagged element tree**, click, type, read,
window/app control — as clean [Model Context Protocol](https://modelcontextprotocol.io)
tools. Any MCP-capable agent (Claude Code, Claude Desktop, or your own) can drive
a real Windows desktop through it.

## 3 lines

```bash
pip install "naturo[mcp]"                                   # 1. install
claude mcp add naturo -- python -m naturo mcp start         # 2. wire it into Claude Code
claude "open Notepad, type 'hello from naturo', read it back"   # 3. use it
```

That's it — the agent now has naturo's tools. (`naturo mcp start` speaks MCP over
stdio by default; `--transport sse|streamable-http` is available for networked
agents.)

### Other agents (generic MCP config)

Any client that reads an MCP server config works — point it at the same command:

```jsonc
{
  "mcpServers": {
    "naturo": { "command": "python", "args": ["-m", "naturo", "mcp", "start"] }
  }
}
```

No separate API key is needed for naturo itself — it drives the local desktop.
(Your *agent* uses its own model credentials as usual.)

## The moat: one fused, correctness-tagged tree

The `see_ui_tree` tool takes `cascade: true` to return the **Unified Auto Element
Tree** — one fused tree per window where every node is tagged with which
techniques recognized it and how much to trust them:

```jsonc
// see_ui_tree(hwnd=…, cascade=true)  ->
{
  "success": true,
  "tree": {
    "id": "e1", "role": "Window", "name": "Book1 - Excel",
    "techniques": ["uia"], "correctness": "deterministic", "confidence": 1.0,
    "children": [
      { "role": "DataItem", "name": "Widget",
        "techniques": ["com"], "correctness": "deterministic", "confidence": 1.0 },
      { "role": "Text", "name": "Total: 98,765",
        "techniques": ["ocr"], "correctness": "uncertain", "confidence": 0.98 }
    ]
  },
  "recognition_summary": { "by_technique": {"uia": 40, "com": 8}, "uncertain_nodes": 0 }
}
```

- **`correctness`** is `deterministic` (UIA/MSAA/IA2/JAB/CDP/COM — guaranteed) or
  `uncertain` (image/OCR/AI — bounds estimated). Prefer deterministic nodes for
  actions; treat `uncertain` nodes as hints, not ground truth.
- **`recognition_summary`** lets the agent branch on correctness without walking
  the whole tree. Web content (CDP), Java (JAB) and Excel cells (COM) that a
  UIA-only tool cannot see appear here — that's naturo's advantage.

## Self-correcting errors

Every tool error is a machine-readable, self-correcting contract — never a bare
string — so the agent can recover without parsing prose:

```jsonc
{ "success": false,
  "error": {
    "code": "ELEMENT_NOT_FOUND",          // a registered code
    "category": "automation",             // the code's category
    "message": "Element not found: Button:Save",
    "suggested_action": "Run 'naturo see' to inspect the current UI tree, or use a different selector…",
    "recoverable": true } }
```

Dispatch on `code`; use `suggested_action` as the recovery hint.

## Runnable example (end-to-end)

This is what step 3 above does, tool by tool — a complete Notepad round-trip:

1. `launch_app(name="notepad")` — start the app.
2. `see_ui_tree(app="Notepad", cascade=true)` — get the fused tree; find the
   `Document`/`Edit` node (the editable area).
3. `type_text(text="hello from naturo")` — type into the focused edit.
4. `get_element_value(role="Edit")` — read the text back to confirm.

A real Claude-Code agent runs exactly this sequence through the MCP tools with no
naturo-specific code — see `tests/` for the contract the tools honor
(`test_mcp_error_contract.py`, `test_mcp_inspect.py`).

## Tool surface (summary)

`capture_screen` · `capture_window` · `list_windows` · `list_apps` · `launch_app`
· **`see_ui_tree` (+`cascade`)** · `find_element` · `get_element_value` ·
`set_element_value` · `click` · `type_text` · `press_key` · `toggle_element` ·
`select_element` · `expand_collapse_element` · `wait_for` · window & clipboard &
dialog & Excel tools. Every tool advertises a description + input schema; call
`list_tools` to enumerate them.
