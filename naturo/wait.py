"""Wait functions — poll for UI elements and windows, aligned with Peekaboo's waitForElement.

All wait functions poll at configurable intervals (default 100ms to match Peekaboo)
and return structured :class:`WaitResult` objects.
"""

from __future__ import annotations

import time
from dataclasses import dataclass, field
from typing import Optional

from naturo.backends.base import Backend, ElementInfo, get_backend


@dataclass
class WaitResult:
    """Outcome of a wait operation.

    Attributes:
        found: Whether the target was found before timeout.
        element: The found ElementInfo (None if not found or waiting for gone).
        wait_time: Seconds spent waiting.
        warnings: Any warnings generated during the wait.
    """

    found: bool
    element: Optional[ElementInfo] = None
    wait_time: float = 0.0
    warnings: list[str] = field(default_factory=list)


def wait_for_element(
    selector: str,
    timeout: float = 10.0,
    poll_interval: float = 0.1,
    window_title: str | None = None,
    backend: Backend | None = None,
) -> WaitResult:
    """Poll for a UI element until found or timeout.

    Args:
        selector: Element selector string (e.g. "Button:Save").
        timeout: Maximum seconds to wait.
        poll_interval: Seconds between polls (default 100ms like Peekaboo).
        window_title: Optional window to search within.
        backend: Backend instance (auto-detected if None).

    Returns:
        WaitResult with found=True if element appeared, False on timeout.
    """
    if backend is None:
        backend = get_backend()

    start = time.monotonic()
    warnings: list[str] = []
    last_error: str | None = None

    while True:
        elapsed = time.monotonic() - start
        if elapsed >= timeout:
            break

        try:
            element = backend.find_element(selector, window_title=window_title)
            if element is not None:
                return WaitResult(
                    found=True,
                    element=element,
                    wait_time=time.monotonic() - start,
                    warnings=warnings,
                )
        except Exception as exc:
            err_msg = str(exc)
            if err_msg != last_error:
                warnings.append(f"Poll error: {err_msg}")
                last_error = err_msg

        remaining = timeout - (time.monotonic() - start)
        if remaining > 0:
            time.sleep(min(poll_interval, remaining))

    return WaitResult(
        found=False,
        element=None,
        wait_time=time.monotonic() - start,
        warnings=warnings,
    )


def wait_until_gone(
    selector: str,
    timeout: float = 10.0,
    poll_interval: float = 0.1,
    window_title: str | None = None,
    backend: Backend | None = None,
) -> WaitResult:
    """Wait until a UI element disappears.

    Args:
        selector: Element selector string.
        timeout: Maximum seconds to wait.
        poll_interval: Seconds between polls (default 100ms).
        window_title: Optional window to search within.
        backend: Backend instance (auto-detected if None).

    Returns:
        WaitResult with found=True if element disappeared, False if still present.
    """
    if backend is None:
        backend = get_backend()

    start = time.monotonic()
    warnings: list[str] = []

    while True:
        elapsed = time.monotonic() - start
        if elapsed >= timeout:
            break

        try:
            element = backend.find_element(selector, window_title=window_title)
            if element is None:
                return WaitResult(
                    found=True,
                    element=None,
                    wait_time=time.monotonic() - start,
                    warnings=warnings,
                )
        except Exception as exc:
            # If the search itself fails, the element is likely gone
            warnings.append(f"Poll error (treating as gone): {str(exc)}")
            return WaitResult(
                found=True,
                element=None,
                wait_time=time.monotonic() - start,
                warnings=warnings,
            )

        remaining = timeout - (time.monotonic() - start)
        if remaining > 0:
            time.sleep(min(poll_interval, remaining))

    return WaitResult(
        found=False,
        element=None,
        wait_time=time.monotonic() - start,
        warnings=warnings,
    )


def wait_for_window(
    title: str,
    timeout: float = 10.0,
    poll_interval: float = 0.5,
    backend: Backend | None = None,
) -> WaitResult:
    """Wait for a window with matching title to appear.

    Args:
        title: Window title pattern (case-insensitive substring match).
        timeout: Maximum seconds to wait.
        poll_interval: Seconds between polls.
        backend: Backend instance (auto-detected if None).

    Returns:
        WaitResult with found=True and element info if window appeared.
    """
    if backend is None:
        backend = get_backend()

    start = time.monotonic()
    warnings: list[str] = []
    title_lower = title.lower()

    while True:
        elapsed = time.monotonic() - start
        if elapsed >= timeout:
            break

        try:
            windows = backend.list_windows()
            for w in windows:
                if title_lower in w.title.lower():
                    # Convert WindowInfo to a pseudo-ElementInfo for WaitResult
                    elem = ElementInfo(
                        id=str(w.handle),
                        role="Window",
                        name=w.title,
                        value=None,
                        x=w.x,
                        y=w.y,
                        width=w.width,
                        height=w.height,
                        children=[],
                        properties={"pid": w.pid, "process_name": w.process_name},
                    )
                    return WaitResult(
                        found=True,
                        element=elem,
                        wait_time=time.monotonic() - start,
                        warnings=warnings,
                    )
        except Exception as exc:
            warnings.append(f"Poll error: {str(exc)}")

        remaining = timeout - (time.monotonic() - start)
        if remaining > 0:
            time.sleep(min(poll_interval, remaining))

    return WaitResult(
        found=False,
        element=None,
        wait_time=time.monotonic() - start,
        warnings=warnings,
    )
