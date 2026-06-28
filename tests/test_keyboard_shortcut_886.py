"""Live UIA keyboard-shortcut recognition against an owned WPF fixture (#886).

These prove that the UIA backend now populates the ``keyboard_shortcut`` field
from the UIA ``AcceleratorKey`` / ``AccessKey`` properties.  Before #886 the
UIA C++ backend never queried either property, so every element in a ``see``
snapshot had ``keyboard_shortcut == null`` regardless of the app — a silent
accessibility-metadata gap (the field looked supported but no data ever
arrived).

The fixture is a tiny WPF window driven by PowerShell + PresentationFramework
(present on any interactive Windows desktop).  WPF lets us set the two UIA
properties deterministically, which classic Win32 controls do not expose:

* ``AutomationProperties.AcceleratorKey`` -> UIA AcceleratorKey (e.g. "Ctrl+S")
* a ``_``-prefixed access key in the button content -> UIA AccessKey (e.g. "O")

The tests are ``@pytest.mark.desktop`` because they launch a real GUI window and
call the native DLL, so they run on an interactive Windows desktop, not on the
headless CI runners.  When that environment is absent the whole module is
skipped.
"""
from __future__ import annotations

import os
import platform
import shutil
import subprocess
import tempfile
import time
from typing import Optional

import pytest

from naturo.backends.base import ElementInfo, get_backend
from naturo.errors import WindowNotFoundError

pytestmark = pytest.mark.desktop

#: Unique per-process window title so a fixture run never matches a stray window.
_WINDOW_TITLE = f"naturo_ks_886_fixture_{os.getpid()}"

#: WPF fixture source.  Three buttons exercise every branch of the shortcut
#: resolution: AcceleratorKey only, AccessKey only, and both (accelerator wins).
#: The DispatcherTimer is a backstop so an orphaned process self-exits even if
#: teardown is skipped; ShowDialog keeps the UI thread pumping until then.
_FIXTURE_PS1 = r"""
Add-Type -AssemblyName PresentationFramework
$w = New-Object System.Windows.Window
$w.Title = "__TITLE__"; $w.Width = 420; $w.Height = 280
$panel = New-Object System.Windows.Controls.StackPanel

# AcceleratorKey only -> "Ctrl+S"
$save = New-Object System.Windows.Controls.Button
$save.Content = "SaveBtn"
[System.Windows.Automation.AutomationProperties]::SetAcceleratorKey($save, "Ctrl+S")
$panel.Children.Add($save) | Out-Null

# AccessKey only (the leading underscore registers the WPF access key) -> "O"
$open = New-Object System.Windows.Controls.Button
$open.Content = "_OpenBtn"
$panel.Children.Add($open) | Out-Null

# Both set -> accelerator preferred -> "Ctrl+P"
$print = New-Object System.Windows.Controls.Button
$print.Content = "_PrintBtn"
[System.Windows.Automation.AutomationProperties]::SetAcceleratorKey($print, "Ctrl+P")
$panel.Children.Add($print) | Out-Null

# Neither set -> stays null
$plain = New-Object System.Windows.Controls.Button
$plain.Content = "PlainBtn"
$panel.Children.Add($plain) | Out-Null

$w.Content = $panel
$t = New-Object System.Windows.Threading.DispatcherTimer
$t.Interval = [TimeSpan]::FromSeconds(60)
$t.Add_Tick({ $w.Close() })
$t.Start()
$null = $w.ShowDialog()
"""


def _fixture_available() -> bool:
    """Whether this host can launch the PowerShell/WPF fixture."""
    return platform.system() == "Windows" and shutil.which("powershell") is not None


requires_fixture = pytest.mark.skipif(
    not _fixture_available(),
    reason="requires an interactive Windows desktop with PowerShell + WPF",
)


def _buttons_by_name(tree: Optional[ElementInfo]) -> dict[str, Optional[str]]:
    """Map each Button element's name to its resolved keyboard_shortcut.

    Args:
        tree: Root element tree from the backend, or ``None``.

    Returns:
        ``{button_name: keyboard_shortcut_or_None}`` for every Button in the
        tree.  The shortcut lives in ``BaseElementInfo.properties`` after the
        backend's post-processing.
    """
    found: dict[str, Optional[str]] = {}
    stack = [tree]
    while stack:
        node = stack.pop()
        if node is None:
            continue
        if node.role == "Button" and node.name:
            props = getattr(node, "properties", {}) or {}
            found[node.name] = props.get("keyboard_shortcut")
        stack.extend(node.children or [])
    return found


@pytest.fixture(scope="module")
def fixture_buttons():
    """Launch the WPF fixture, collect its buttons' shortcuts, then tear down."""
    if not _fixture_available():
        pytest.skip("PowerShell/WPF fixture unavailable on this host")

    script = _FIXTURE_PS1.replace("__TITLE__", _WINDOW_TITLE)
    script_dir = tempfile.mkdtemp(prefix="naturo_ks_886_")
    script_path = os.path.join(script_dir, "fixture.ps1")
    with open(script_path, "w", encoding="utf-8") as handle:
        handle.write(script)

    proc = subprocess.Popen(
        ["powershell", "-NoProfile", "-ExecutionPolicy", "Bypass", "-File", script_path],
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
    )
    try:
        backend = get_backend()
        buttons: dict[str, Optional[str]] = {}
        deadline = time.monotonic() + 30.0
        while time.monotonic() < deadline:
            try:
                tree = backend.get_element_tree(
                    window_title=_WINDOW_TITLE, depth=10, backend="uia",
                )
            except WindowNotFoundError:
                tree = None  # window not up yet — keep polling
            buttons = _buttons_by_name(tree)
            # Wait until the WPF content (our four named buttons) has rendered,
            # not just the window chrome.
            if {"SaveBtn", "OpenBtn", "PrintBtn", "PlainBtn"} <= set(buttons):
                break
            time.sleep(0.5)
        else:
            pytest.fail(
                f"WPF fixture window '{_WINDOW_TITLE}' did not expose its "
                f"buttons; saw: {sorted(buttons)}"
            )
        yield buttons
    finally:
        proc.terminate()
        try:
            proc.wait(timeout=5)
        except subprocess.TimeoutExpired:
            proc.kill()
        shutil.rmtree(script_dir, ignore_errors=True)


@requires_fixture
def test_accelerator_key_is_populated(fixture_buttons):
    """A UIA AcceleratorKey surfaces as the element's keyboard_shortcut."""
    assert fixture_buttons["SaveBtn"] == "Ctrl+S"


@requires_fixture
def test_access_key_is_used_as_fallback(fixture_buttons):
    """With no AcceleratorKey, the UIA AccessKey is used instead."""
    assert fixture_buttons["OpenBtn"] == "O"


@requires_fixture
def test_accelerator_key_preferred_over_access_key(fixture_buttons):
    """When both properties are set, the actionable AcceleratorKey wins."""
    assert fixture_buttons["PrintBtn"] == "Ctrl+P"


@requires_fixture
def test_element_without_shortcut_stays_none(fixture_buttons):
    """An element with neither property keeps keyboard_shortcut == None.

    This guards against the field being filled with a spurious value — the
    "never lie" contract: absence of a shortcut must read as ``None``.
    """
    assert fixture_buttons["PlainBtn"] is None


@requires_fixture
def test_field_emitted_for_every_element(fixture_buttons):
    """The regression itself: the UIA backend now participates in the contract.

    Before #886 *no* UIA element carried a shortcut (the C++ backend never
    queried the property), so at least one real value proves the backend now
    emits the field rather than silently dropping it.
    """
    populated = {name: ks for name, ks in fixture_buttons.items() if ks}
    assert populated, (
        "no UIA element exposed a keyboard_shortcut — the backend is not "
        "querying AcceleratorKey/AccessKey"
    )
