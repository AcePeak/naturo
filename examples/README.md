# Examples

Working example scripts demonstrating naturo automation patterns.

## Scripts

| Script | Description | Complexity |
|--------|-------------|------------|
| `notepad_hello.py` | Launch Notepad, type text, capture screenshot, close | Beginner |
| `window_capture.py` | Capture screenshots of all visible windows | Beginner |
| `ui_inspector.py` | Interactive UI element tree explorer | Intermediate |
| `form_filler.py` | Auto-fill form controls (Calculator demo) | Intermediate |
| `agent_demo.py` | AI agent integration patterns (CLI, MCP, vision) | Advanced |

## Prerequisites

- Windows 10/11 with a desktop session
- Python 3.9+
- `pip install naturo`

## Quick Start

```bash
# Simple: open Notepad and type text
python notepad_hello.py

# Capture all visible windows
python window_capture.py --output-dir ./screenshots

# Explore an app's UI tree interactively
python ui_inspector.py notepad

# Calculator automation
python form_filler.py

# AI agent integration patterns
python agent_demo.py cli      # CLI subprocess loop
python agent_demo.py mcp      # MCP server setup
python agent_demo.py vision   # AI vision configuration
```

## Common Patterns

### Run a command and parse JSON output

```python
import json, subprocess

result = subprocess.run(
    ["naturo", "app", "list", "--json"],
    capture_output=True, text=True,
)
data = json.loads(result.stdout)
for app in data["apps"]:
    print(app["process_name"], app["title"])
```

### Launch, interact, close

```python
subprocess.run(["naturo", "app", "launch", "notepad", "--wait-until-ready"])
subprocess.run(["naturo", "type", "Hello!"])
subprocess.run(["naturo", "app", "quit", "notepad"])
```

### Target by app ID

```python
# List apps to assign IDs
subprocess.run(["naturo", "app", "list"])
# Use the assigned ID
subprocess.run(["naturo", "app", "focus", "a1"])
subprocess.run(["naturo", "click", "--on", "e3", "--app", "a1"])
```
