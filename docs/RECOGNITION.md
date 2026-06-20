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
| **Java Swing / SWT (JAB)**       | 🔧 repair†     | ❌   | ❌          | ❌         |
| Vision fallback (AI)             | ✅             | ⚠️*  | ❌          | ❌         |
| SAP GUI (scripting/COM)          | 🚧 planned     | ❌   | ❌          | ❌         |

<sub>✅ supported · ❌ not supported · 🚧 planned · 🔧 implemented but under
repair · ⚠️* UFO² uses a vision model for grounding but has no dedicated CDP/JAB
element providers.</sub>

<sub>**🔧† Java Access Bridge — known regression (tracking [#1096]).** The JAB
provider is implemented, but on a correctly-provisioned desktop (JDK 21 + Access
Bridge enabled) naturo's one-shot init currently fails to complete the async
JVM↔AT handshake, so JAB does not attach and the Swing delta below does **not**
reproduce. Honesty over polish (SOUL.md never-lie): the cell is marked under
repair until [#1096] lands and `tests/test_jab_recognition_932.py` is green
again on a JAB desktop.</sub>

[#1096]: https://github.com/AcePeak/naturo/issues/1096

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

### Results (Windows 11; Electron rows measured 2026-06-16)

| App | Framework | UIA-only | Cascade | Delta | Extra via |
| --- | --- | ---: | ---: | ---: | --- |
| Chrome (local web/Electron-class app) | Electron/CDP | 52 | 89 | **+37** | cdp (+34) |
| Owned Electron fixture (real Electron app) | Electron/CDP | 83 | 113 | **+30** | cdp (+30) |
| Owned Java Swing fixture (real Swing app) | Java Access Bridge | — | — | _under repair†_ | — |

> **🔧† Known regression — Java Access Bridge ([#1096]).** An earlier draft of
> this row published a measured `6 → 46, +40 via jab`. On re-verification on a
> correctly-provisioned desktop (OpenJDK 21 + Access Bridge enabled), naturo's
> JAB init **does not attach** (`jab_check_support` → `False`,
> `naturo_jab_get_element_tree` → `-6`), so the cascade recovers the Swing
> controls via **no** JAB provider and the delta does **not** currently
> reproduce. Per never-lie (SOUL.md) the number is withdrawn rather than left
> standing while unreproducible. The native fix and the restored, re-verified
> row are owned by **[#1096]**; `tests/test_jab_recognition_932.py` is the
> desktop regression that must go green again before the number is republished.
> The Electron/CDP rows above are unaffected and reproduce as documented.

**Documented gaps (measured honestly — no fabrication):**

- **Mature external Java apps (JetBrains IDE / DBeaver):** the owned-fixture JAB
  row above is measured live, but the larger external Java apps are not installed
  on the benchmark desktop. The harness supports them
  (`measure_running_app(..., title_substring="DBeaver")`); QA tracks measuring
  them in #935.
- **SAP GUI:** not available in this environment — planned (`SAP scripting/COM`
  provider).

### What the delta means

In the Chrome run, the UIA-only baseline recognized **52** elements — and
**zero** of them were the web app's interactive content (the *New / Open / Save
/ Inbox / Send / Reply / …* controls). Every UIA element was browser chrome
(tabs, address bar, menus). The cascade's **CDP** provider recognized **34**
content elements that UIA is structurally blind to. That is precisely the class
of element a UIA-only tool would fail to click.

The second row is the **literal Electron case**: naturo's own Electron fixture
(`benchmarks/recognition/fixtures/electron/`) is a genuine Electron main process
rendering a `BrowserWindow`, not a browser standing in for one. There, UIA-only
recognized **83** elements (the native window frame) while the cascade reached
**113** — the **CDP** provider recovered **30** renderer controls (toolbar
buttons, the environment tree, release-form inputs, the task list, the
deployments table) that the Windows UIA tree collapses into one opaque node.

> **Why Chrome also proves the Electron case.** Electron apps embed the identical
> Chromium content layer and expose the same CDP endpoint, so the Chrome row and
> the owned-Electron row measure the same recognition gap two ways — the gap a
> UIA-only tool hits on VS Code, Slack, or Feishu.

The third row is the **literal Java/Swing case**: naturo's own Swing fixture is a
real JVM window whose controls live below a `SunAwtFrame`, where the UIA-only
baseline sees only window chrome (the title bar and its system buttons) — **none**
of the app's *Submit Order / Cancel Order / Customer Name / Express Shipping*
controls — and the **Java Access Bridge** provider is the cascade leg that
recovers them. **This row is the known regression noted above ([#1096]):** on the
current build naturo's JAB init does not attach on a loaded desktop, so the
`--backend auto` cascade does **not** yet fuse JAB and the delta does not
reproduce. The description here states the **intended** behavior the JAB provider
is designed to deliver; the measured number is withdrawn until [#1096] restores
attachment and `tests/test_jab_recognition_932.py` is green again.

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

To include the **owned, real Electron** row, install the fixture's toolchain
once (Node.js required); the runner adds the row automatically when present and
documents it as a gap when not:

```bash
cd benchmarks/recognition/fixtures/electron && npm install   # pins electron via package-lock.json
```

The harness is reusable directly:

```python
from benchmarks.recognition.harness import (
    ChromiumFixtureApp,
    ElectronFixtureApp,
    measure_running_app,
)

# Reproducible Electron-class case (launches + cleans up its own browser):
with ChromiumFixtureApp() as app:
    result = app.measure()
    print(result.uia_only_count, result.cascade_count, result.extra_sources)

# Literal Electron case (launches + cleans up a real Electron process):
with ElectronFixtureApp() as app:        # requires `npm install` in the fixture dir
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

**Try it against the owned fixture (no external app required).** The repo ships a
real Electron app under `benchmarks/recognition/fixtures/electron/`, so you can
reproduce the CDP recognition delta end-to-end without installing VS Code, Slack
or any third-party Electron app:

```bash
# 1. Build the owned fixture once (Node.js required; electron is pinned by the lockfile):
cd benchmarks/recognition/fixtures/electron && npm install

# 2. Launch it with a CDP endpoint (main.js also reads NATURO_FIXTURE_CDP_PORT):
npx electron . --remote-debugging-port=9222 --remote-allow-origins=*

# 3. From another shell, let the cascade fuse UIA window chrome + CDP renderer
#    content. `--stats` prints the per-provider breakdown; the `cdp` rows are the
#    renderer controls (toolbar, release form, task list, deployments table) that
#    a UIA-only tool collapses into one opaque node.
naturo see --window "Naturo Electron Recognition Fixture" --cascade --stats

# 4. Find a renderer control by its visible label — recognized via CDP, not UIA:
naturo find "Submit release" --app electron

# 5. Click one (e.g. the toolbar's Deploy button) by text within the window:
naturo click "Deploy" --window "Naturo Electron Recognition Fixture"
```

### Java Swing / SWT (Java Access Bridge)

> **🔧 Under repair ([#1096]).** JAB attach is currently regressed: on a loaded
> desktop naturo's one-shot init does not complete the async JVM handshake, so
> the steps below do not yet recover Swing controls. They document the intended
> workflow and will work again once [#1096] lands. Track progress there.

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
