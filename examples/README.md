# Examples

Working example scripts demonstrating naturo automation patterns.

The first four use the ergonomic **in-process Python SDK** — `import naturo`
and automate directly, no subprocess and no CLI parsing. The two agent scripts
cover MCP / agent-framework wiring.

## Scripts

| Script | Description | Complexity |
|--------|-------------|------------|
| `notepad_hello.py` | Launch Notepad, type text, capture screenshot, close (SDK) | Beginner |
| `window_capture.py` | Capture screenshots of all visible windows (SDK) | Beginner |
| `ui_inspector.py` | Interactive UI element tree explorer (SDK) | Intermediate |
| `form_filler.py` | Drive form controls, read the tree (Calculator demo, SDK) | Intermediate |
| `agent_demo.py` | AI agent integration patterns (CLI, MCP, vision) | Advanced |
| `agent_frameworks.py` | Plug naturo's tools into OpenAI / Anthropic / LangChain | Advanced |

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

# Explore an app's UI tree interactively (add --cascade for the fused tree)
python ui_inspector.py notepad

# Calculator automation
python form_filler.py

# AI agent integration patterns
python agent_demo.py cli      # CLI subprocess loop
python agent_demo.py mcp      # MCP server setup
python agent_demo.py vision   # AI vision configuration

# Plug naturo's full tool surface into an agent framework
python agent_frameworks.py list        # print the exported tools (no framework needed)
python agent_frameworks.py openai      # OpenAI function-calling wiring
python agent_frameworks.py anthropic   # Anthropic tool-use wiring
python agent_frameworks.py langchain   # LangChain StructuredTool wiring
```

## The Python SDK

`import naturo` gives you an ergonomic, in-process API over the same engine the
CLI and MCP server use. Import-and-go in under 10 lines:

```python
import naturo

app = naturo.launch("notepad")          # App handle (waits until ready)
naturo.type("hello", window="Notepad")  # IME-immune type ladder
tree = naturo.see(window="Notepad")     # root Element; walk .children / .descendants
el = naturo.find("Button:Save", window="Notepad")
if el:
    el.click()                          # elements act on themselves
naturo.capture("shot.png", window="Notepad")
app.quit()
```

Core verbs (module-level, or as `Desktop`/`Session`/`App` methods):
`see`, `find`, `click`, `type`, `press`, `get_value`, `set_value`,
`capture`, `launch`, `quit`, `wait`, `windows`.

### Reusable session

```python
import naturo

desktop = naturo.Desktop()              # or naturo.Session() — reuses one backend
for win in desktop.windows():
    print(win.process_name, win.title)
```

### Context-managed app

```python
import naturo

with naturo.launch("calculator") as app:   # quits on exit
    for key in ("4", "2", "multiply", "7", "enter"):
        app.press(key)
    tree = app.see()
    for el in tree.descendants():
        if el.role == "Text" and el.name:
            print(el.name)
```

### The fused, correctness-tagged tree (the moat)

```python
import naturo

# UIA + web (CDP) + Java (JAB) + Excel cells (COM) merged into one tree,
# each node tagged deterministic vs uncertain.
tree = naturo.see(app="chrome", cascade=True)
```

### Still prefer the CLI?

The `naturo` command remains a first-class surface for shell / subprocess use:

```bash
naturo app launch notepad --wait-until-ready
naturo type "Hello!"
naturo app quit notepad
```
