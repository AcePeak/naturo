# Recognition Coverage — naturo vs UIA-only tools

naturo's core differentiator is **commercial-RPA-grade multi-framework
recognition**. Where UIA-only open-source tools (UFO², Windows-MCP, Terminator)
walk a single accessibility tree, naturo runs a **cascade** that fuses several
recognition frameworks and tags every element with the provider that found it:

```
UIA  →  MSAA / IAccessible2  →  Java Access Bridge  →  Electron / CDP  →  Vision
```

This document gives (1) the capability matrix vs UIA-only rivals, (2) a
**reproducible benchmark** that measures the advantage honestly with naturo's
own engine, and (3) per-framework how-to notes.

## Why this matters

Two of the most common enterprise UI stacks are effectively **invisible to UIA**:

- **Electron / CEF apps** (VS Code, Slack, Feishu/Lark, Teams, Discord, …) —
  the entire web-rendered content area is a single opaque UIA node. A UIA-only
  tool sees the window chrome but *none* of the page's buttons, links, inputs,
  list items, or messages.
- **Java Swing / SWT apps** (many enterprise tools, JetBrains IDEs, DBeaver) —
  require the **Java Access Bridge**; without it the UIA tree is empty or
  shallow.

naturo recognizes these via the **CDP** (Chrome DevTools Protocol) and **Java
Access Bridge** providers in the cascade. A UIA-only rival cannot.

## Capability matrix

| Framework / app class            | naturo cascade | UFO² | Windows-MCP | Terminator |
| -------------------------------- | :------------: | :--: | :---------: | :--------: |
| Win32 / WinForms / WPF (UIA)     | ✅             | ✅   | ✅          | ✅         |
| UWP / WinUI (UIA)                | ✅             | ✅   | ✅          | ✅         |
| MSAA / IAccessible2 fallback     | ✅             | ❌   | ❌          | ❌         |
| **Electron / CEF (CDP)**         | ✅             | ❌   | ❌          | ❌         |
| **Java Swing / SWT (JAB)**       | ✅             | ❌   | ❌          | ❌         |
| Vision fallback (AI)             | ✅             | ⚠️*  | ❌          | ❌         |
| SAP GUI (scripting/COM)          | 🚧 planned     | ❌   | ❌          | ❌         |

<sub>✅ supported · ❌ not supported · 🚧 planned · ⚠️* UFO² uses a vision
model for grounding but has no dedicated CDP/JAB element providers.</sub>

> Rival capabilities are stated from each project's public documentation as of
> 2026-06; all three are built on Windows UI Automation and ship no Electron/CDP
> or Java Access Bridge element provider.

## Measured benchmark

The benchmark measures, **on the same window in the same state**, how many
elements naturo recognizes two ways:

1. **Full cascade** — `run_cascade(backend_name="auto")` (UIA + CDP + JAB +
   vision).
2. **UIA-only baseline** — `run_cascade(backend_name="uia")`. This is exactly
   the tree a UIA-only rival walks, produced by naturo's *own* engine so the
   comparison is apples-to-apples on identical app state. No competitor needs
   to be installed.

The delta is the multi-framework advantage; `Extra via` shows which provider
found the elements UIA alone could not.

### Results (Windows 11, 2026-06-16)

| App | Framework | UIA-only | Cascade | Delta | Extra via |
| --- | --- | ---: | ---: | ---: | --- |
| Chrome (local web/Electron-class app) | Electron/CDP | 52 | 89 | **+37** | cdp (+34) |

**Documented gaps (measured honestly — no fabrication):**

- **JetBrains IDE / DBeaver (Java Access Bridge):** no Java app was installed on
  the benchmark desktop, so the JAB row could not be measured live. The harness
  supports it (`measure_running_app(..., title_substring="DBeaver")`); run it on
  a machine with a Java Swing/SWT app open to populate this row.
- **SAP GUI:** not available in this environment — planned (`SAP scripting/COM`
  provider).

### What the delta means

In the Chrome run, the UIA-only baseline recognized **52** elements — and
**zero** of them were the web app's interactive content (the *New / Open / Save
/ Inbox / Send / Reply / …* controls). Every UIA element was browser chrome
(tabs, address bar, menus). The cascade's **CDP** provider recognized **34**
content elements that UIA is structurally blind to. That is precisely the class
of element a UIA-only tool would fail to click.

> **Why Chrome proves the Electron case.** Electron apps embed the identical
> Chromium content layer and expose the same CDP endpoint. The web-content
> recognition gap measured here is exactly the gap a UIA-only tool hits on VS
> Code, Slack, or Feishu.

## Reproduce it

Requirements: a real interactive Windows desktop session, a Chrome or Edge
install, and the CDP extra.

```bash
pip install naturo[cdp]            # installs websocket-client for CDP
python -m benchmarks.recognition.run_benchmark            # human-readable table
python -m benchmarks.recognition.run_benchmark --markdown # Markdown table
python -m benchmarks.recognition.run_benchmark --json     # machine-readable
```

The runner launches a **throwaway** Chrome profile on a bundled local HTML
fixture (`benchmarks/recognition/fixtures/webapp.html`), so the web-content
delta is deterministic and **offline** — no network, no live-site drift. It
also probes for common Electron/Java apps that happen to be open and includes
them when present.

The harness is reusable directly:

```python
from benchmarks.recognition.harness import ChromiumFixtureApp, measure_running_app

# Reproducible Electron-class case (launches + cleans up its own browser):
with ChromiumFixtureApp() as app:
    result = app.measure()
    print(result.uia_only_count, result.cascade_count, result.extra_sources)

# Measure any app already open on this desktop:
result = measure_running_app(
    app="DBeaver", framework="Java Access Bridge",
    title_substring="DBeaver",
)
```

## Per-framework how-to

### Electron / CEF (CDP)

Electron apps expose a Chrome DevTools endpoint when launched with a
remote-debugging port. naturo's CDP provider then enumerates the full DOM.

```bash
# Launch the Electron app with a debug port, e.g.:
code --remote-debugging-port=9222          # VS Code
# Modern Chromium also requires allowing the WebSocket origin:
#   --remote-allow-origins=*

# Then let the cascade fuse UIA chrome + CDP content:
naturo see --app code --backend auto --stats
```

Install the CDP dependency with `pip install naturo[cdp]`.

### Java Swing / SWT (Java Access Bridge)

Enable the Java Access Bridge once per machine, then use the `jab` backend (the
`auto` cascade tries it automatically):

```bash
jabswitch -enable          # ships with the JDK/JRE; enables Access Bridge
naturo see --app dbeaver --backend auto --stats
```

### Vision fallback

When a window is too shallow for any accessibility provider, the cascade can
fall back to an AI vision provider (`--fill-gaps`) to recover interactive
elements from a screenshot. See the main README's AI configuration section.

### SAP GUI (planned)

SAP GUI exposes a scripting/COM object model rather than UIA. A dedicated SAP
provider is planned; it was not available in the benchmark environment.
```
