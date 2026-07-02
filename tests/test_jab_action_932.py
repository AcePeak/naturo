"""Live Java Access Bridge *action* assertions against the owned Swing fixture (#932).

The recognition tests (``test_jab_recognition_932.py``) prove naturo *sees* Java
controls through the Java Access Bridge (JAB) where a UIA-only baseline is blind.
These tests close the remaining #932 slice: they prove naturo can *act* on a
JAB-recognized Swing control and that the action genuinely takes effect — the
"naturo click ... via JAB" half of the acceptance criteria.

The proof is honest end-to-end and avoids self-confirmation:

1. naturo recognizes a button through JAB (its screen rectangle comes from the
   JAB tree — UIA cannot see it, as the recognition tests establish).
2. naturo clicks the button's center via real ``SendInput`` injection.
3. naturo re-reads the window through JAB and observes that the button's action
   listener changed a *different* control's accessible name. The state that
   changes is read back through the same JAB provider, so the assertion proves
   the click reached the live Swing control — verify-after-action, not a
   recognition tautology.

A discriminating second action (Cancel → a different status) rules out the
"any click flips to one fixed string" false positive.

These are ``@pytest.mark.desktop`` because they launch a real JVM window, inject
real input, and call the native DLL, so they run on an interactive Windows
desktop with a JDK and JAB enabled — not on the headless CI runners. When that
environment is absent the whole module is skipped.
"""
from __future__ import annotations

import platform
import time

import pytest

from benchmarks.recognition.harness import JavaSwingFixtureApp
from naturo.backends.base import get_backend

pytestmark = pytest.mark.desktop

#: Status-label accessible-name states defined by ``SwingControlsFixture.java``.
STATUS_PENDING = "Order Status: Pending"
STATUS_SUBMITTED = "Order Status: Submitted"
STATUS_CANCELLED = "Order Status: Cancelled"

#: Bounded wait for the Swing event-dispatch thread to apply a click's action
#: and for the JAB tree to reflect the new accessible name.
_ACTION_SETTLE_SECONDS = 0.7
_ACTION_POLL_TIMEOUT = 5.0


def _fixture_available() -> bool:
    """Whether this host can build and run the Java Swing fixture."""
    return platform.system() == "Windows" and JavaSwingFixtureApp().available


requires_fixture = pytest.mark.skipif(
    not _fixture_available(),
    reason="requires an interactive Windows desktop with a JDK (JAVA_HOME)",
)


def _find(node, predicate):
    """Return the first element in ``node``'s subtree matching ``predicate``.

    Args:
        node: Root :class:`~naturo.backends.base.ElementInfo`, or ``None``.
        predicate: Callable taking an element and returning ``True`` on a match.

    Returns:
        The first matching element, or ``None`` if none matches.
    """
    stack = [node]
    while stack:
        current = stack.pop()
        if current is None:
            continue
        if predicate(current):
            return current
        stack.extend(current.children or [])
    return None


def _status_name(tree) -> str | None:
    """Read the fixture's status-label accessible name from a JAB tree.

    Args:
        tree: Root JAB element tree for the fixture window.

    Returns:
        The status label's accessible name (e.g. ``"Order Status: Pending"``),
        or ``None`` if the label is not present in the tree.
    """
    label = _find(tree, lambda element: (element.name or "").startswith("Order Status"))
    return label.name if label is not None else None


@pytest.fixture
def swing_app():
    """Launch a fresh Swing fixture per test so the initial status is known."""
    if not _fixture_available():
        pytest.skip("Java Swing fixture unavailable on this host")
    app = JavaSwingFixtureApp()
    with app:
        window = app.find_window()
        assert window is not None, "fixture window did not appear"
        yield app, window


def _jab_tree(backend, hwnd):
    """Read the JAB element tree for ``hwnd`` (focused first for a stable read)."""
    tree = backend.get_element_tree(hwnd=hwnd, depth=15, backend="jab")
    assert tree is not None, "JAB returned no tree for the live Swing window"
    return tree


def _click_control_via_jab(backend, hwnd, control_name: str) -> None:
    """Recognize a control through JAB and click its center via real input.

    Args:
        backend: The active naturo backend.
        hwnd: The fixture window handle.
        control_name: Accessible name of the control to click.

    Raises:
        AssertionError: If JAB does not recognize ``control_name``.
    """
    tree = _jab_tree(backend, hwnd)
    control = _find(tree, lambda element: element.name == control_name)
    assert control is not None, f"JAB did not recognize control {control_name!r}"
    center_x = control.x + control.width // 2
    center_y = control.y + control.height // 2
    # Foreground the fixture so the injected click lands on it, then click the
    # JAB-recognized coordinates through naturo's real input path.
    backend.focus_window(hwnd=hwnd)
    time.sleep(0.3)
    backend.click(x=center_x, y=center_y)


def _wait_for_status(backend, hwnd, expected: str) -> str:
    """Poll the JAB tree until the status label reads ``expected`` (bounded).

    Args:
        backend: The active naturo backend.
        hwnd: The fixture window handle.
        expected: The accessible name the status label should reach.

    Returns:
        The status label's accessible name once it equals ``expected``, or its
        last observed value if the timeout elapses (so the caller's assertion
        reports the real divergence).
    """
    deadline = time.monotonic() + _ACTION_POLL_TIMEOUT
    last = None
    time.sleep(_ACTION_SETTLE_SECONDS)
    while time.monotonic() < deadline:
        last = _status_name(_jab_tree(backend, hwnd))
        if last == expected:
            return last
        time.sleep(0.25)
    return last


@requires_fixture
def test_naturo_click_actuates_jab_recognized_button(swing_app):
    """naturo clicks a JAB-recognized Swing button and the action takes effect.

    Causation chain, all observed through JAB:
    * the status label starts at ``Pending``;
    * clicking the JAB-recognized ``Submit Order`` button drives it to
      ``Submitted``;
    * clicking the JAB-recognized ``Cancel Order`` button then drives it to
      ``Cancelled`` — a *different* result for a *different* button, ruling out
      a fixed-string false positive.
    """
    _app, window = swing_app
    backend = get_backend()

    initial = _status_name(_jab_tree(backend, window.hwnd))
    assert initial == STATUS_PENDING, (
        f"fixture should start at {STATUS_PENDING!r}, got {initial!r}"
    )

    _click_control_via_jab(backend, window.hwnd, "Submit Order")
    after_submit = _wait_for_status(backend, window.hwnd, STATUS_SUBMITTED)
    assert after_submit == STATUS_SUBMITTED, (
        "clicking the JAB-recognized 'Submit Order' button did not take effect: "
        f"status is {after_submit!r}, expected {STATUS_SUBMITTED!r}"
    )

    _click_control_via_jab(backend, window.hwnd, "Cancel Order")
    after_cancel = _wait_for_status(backend, window.hwnd, STATUS_CANCELLED)
    assert after_cancel == STATUS_CANCELLED, (
        "clicking the JAB-recognized 'Cancel Order' button did not take effect: "
        f"status is {after_cancel!r}, expected {STATUS_CANCELLED!r}"
    )
