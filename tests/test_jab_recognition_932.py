"""Live Java Access Bridge recognition tests against the owned Swing fixture (#932).

These prove that naturo recognizes Java/Swing controls through the Java Access
Bridge (JAB) where a UIA-only baseline sees only opaque window chrome — the
recognition moat for Java desktop apps.

They are ``@pytest.mark.desktop`` because they launch a real JVM window and call
the native DLL, so they run on an interactive Windows desktop that has a JDK
with Java Access Bridge enabled (``jabswitch -enable`` and
``WindowsAccessBridge-64.dll`` on ``PATH``) — not on the headless CI runners.
When that environment is absent the whole module is skipped.
"""
from __future__ import annotations

import platform
import time

import pytest

from benchmarks.recognition.harness import JavaSwingFixtureApp
from naturo.backends.base import get_backend

#: Accessible control names defined by ``SwingControlsFixture.java`` — the
#: ground truth that JAB must recover and UIA cannot see.
EXPECTED_CONTROLS = {
    "Submit Order",
    "Cancel Order",
    "Customer Name",
    "Express Shipping",
    "Catalog Tree",
}

pytestmark = pytest.mark.desktop


def _fixture_available() -> bool:
    """Whether this host can build and run the Java Swing fixture."""
    return platform.system() == "Windows" and JavaSwingFixtureApp().available


requires_fixture = pytest.mark.skipif(
    not _fixture_available(),
    reason="requires an interactive Windows desktop with a JDK (JAVA_HOME)",
)


def _names_in_tree(tree) -> set:
    """Collect every non-empty element name in an element tree.

    Args:
        tree: Root :class:`~naturo.backends.base.ElementInfo`, or ``None``.

    Returns:
        Set of stripped, non-empty element names found anywhere in the tree.
    """
    names: set = set()
    stack = [tree]
    while stack:
        node = stack.pop()
        if node is None:
            continue
        if node.name and node.name.strip():
            names.add(node.name.strip())
        stack.extend(node.children or [])
    return names


@pytest.fixture(scope="module")
def swing_app():
    """Launch the owned Swing fixture once for the module and tear it down."""
    app = JavaSwingFixtureApp()
    if not _fixture_available():
        pytest.skip("Java Swing fixture unavailable on this host")
    with app:
        window = app.find_window()
        assert window is not None, "fixture window did not appear"
        yield app, window


@requires_fixture
def test_uia_only_is_blind_to_swing_controls(swing_app):
    """A UIA-only walk sees window chrome but none of the Swing controls.

    This establishes the moat premise: the controls genuinely live outside the
    UIA tree, so any recognition of them must come from JAB.
    """
    _app, window = swing_app
    backend = get_backend()
    tree = backend.get_element_tree(hwnd=window.hwnd, depth=15, backend="uia")
    uia_names = _names_in_tree(tree)
    assert EXPECTED_CONTROLS.isdisjoint(uia_names), (
        "UIA unexpectedly saw Swing controls: "
        f"{sorted(EXPECTED_CONTROLS & uia_names)}"
    )


@requires_fixture
def test_jab_attaches_to_live_jvm(swing_app):
    """JAB completes its asynchronous handshake and attaches to the live JVM.

    Direct regression for the #1096 attach defect: the pre-fix init called
    ``Windows_run`` exactly once, pumped the message queue for a fixed 1 s, then
    cached ``initialized=True`` *without confirming attachment*. On a loaded
    desktop the asynchronous JVM handshake did not finish in that window, so
    ``isJavaWindow`` returned false permanently and ``jab_check_support`` was
    ``False`` forever. The fix pumps-and-retries (re-invoking ``Windows_run``)
    until a Java window is discoverable, so support must now resolve true — and
    well within the bounded attach budget rather than hanging.
    """
    _app, window = swing_app
    from naturo.bridge import NaturoCore

    core = NaturoCore()
    start = time.monotonic()
    assert core.jab_check_support(window.hwnd) is True, (
        "JAB did not attach to the live Swing JVM (issue #1096 regression)"
    )
    elapsed = time.monotonic() - start
    assert elapsed < 10.0, (
        f"JAB attach took {elapsed:.1f}s; expected to complete within the "
        "bounded handshake budget, not hang"
    )


@requires_fixture
def test_jab_recognizes_swing_controls(swing_app):
    """The JAB backend recovers every named Swing control.

    Fails against a core DLL whose Java Access Bridge never initializes (the
    pre-#932 defect) and passes once JAB attaches to the JVM.
    """
    _app, window = swing_app
    backend = get_backend()
    tree = backend.get_element_tree(hwnd=window.hwnd, depth=15, backend="jab")
    assert tree is not None, "JAB returned no tree for a live Swing window"
    jab_names = _names_in_tree(tree)
    missing = EXPECTED_CONTROLS - jab_names
    assert not missing, f"JAB did not recognize controls: {sorted(missing)}"


def _find_by_name(tree, name: str):
    """Return the first element in ``tree`` whose name matches ``name``.

    Args:
        tree: Root :class:`~naturo.backends.base.ElementInfo`, or ``None``.
        name: Exact (stripped) accessible name to look for.

    Returns:
        The matching :class:`ElementInfo`, or ``None`` if not found.
    """
    stack = [tree]
    while stack:
        node = stack.pop()
        if node is None:
            continue
        if node.name and node.name.strip() == name:
            return node
        stack.extend(node.children or [])
    return None


@requires_fixture
def test_jab_exposes_control_states(swing_app):
    """The JAB backend surfaces accessibility ``states`` to the Python layer (#1200).

    ``core/src/jab.cpp`` computes a ``states`` string for every element, but the
    Python parser used to discard it, so a Swing ``JCheckBox``'s checked/unchecked
    state never reached any consumer — blocking honest verify-after-action for
    JAB-driven checkbox/toggle automation. This proves the field now round-trips
    natively: the fixture's checkbox exposes a non-empty states string.
    """
    _app, window = swing_app
    backend = get_backend()
    tree = backend.get_element_tree(hwnd=window.hwnd, depth=15, backend="jab")
    assert tree is not None, "JAB returned no tree for a live Swing window"

    checkbox = _find_by_name(tree, "Express Shipping")
    assert checkbox is not None, "JAB did not recognize the 'Express Shipping' checkbox"
    states = checkbox.properties.get("states")
    assert states is not None and states.strip(), (
        "JAB checkbox exposed no accessibility states — the native 'states' field "
        f"was dropped before reaching the backend element (got {states!r})"
    )


@requires_fixture
def test_cascade_shows_positive_jab_delta(swing_app):
    """The full cascade recognizes more than UIA alone, with JAB as the source."""
    app, _window = swing_app
    result = app.measure()
    assert result.delta > 0, (
        f"expected a positive JAB delta, got UIA={result.uia_only_count} "
        f"cascade={result.cascade_count}"
    )
    assert "jab" in result.extra_sources, (
        f"expected JAB to contribute extra elements, got {result.extra_sources}"
    )
