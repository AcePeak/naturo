# Naturo — Cross-Platform Desktop Automation Engine

> See, click, type, automate. Built for AI agents.

This is the npm wrapper for [Naturo](https://github.com/AcePeak/naturo). It delegates to the Python CLI.

**Platform Support:**
- **Windows:** Full support available now
- **Linux:** Coming soon
- **macOS:** Coming soon

## Quick Start

```bash
# Run directly (no install needed)
npx naturo mcp start

# Or install globally
npm install -g naturo
naturo capture live
```

## Requirements

- **Node.js** 16+
- **Python** 3.9+ with `pip install naturo`

## What It Does

The npm package is a thin wrapper that finds and invokes the Python `naturo` CLI. All features are provided by the Python package:

- 🖥️ Screen capture & UI tree inspection
- 🖱️ Click, type, press, scroll, drag
- 🪟 Window management (focus, close, move, resize)
- 🤖 MCP server with 82 tools for AI agents
- 🌐 Chrome DevTools Protocol support
- And much more — see [full documentation](https://github.com/AcePeak/naturo)

## MCP Server

Start the MCP server for AI agent integration:

```bash
# stdio transport (default, for Claude Desktop / OpenClaw)
npx naturo mcp start

# SSE transport (for web-based agents)
npx naturo mcp start --transport sse --port 3100
```

## License

MIT
