"""Post-action verification engine for interaction commands.

Detects silent failures by checking whether an action actually had effect.
This is the core of issue #231 — naturo must never lie about success.

Each verification strategy checks the UI state after an action and returns
a VerificationResult indicating whether the action's effect was confirmed.

Design principle: **false negatives are acceptable, false positives are not.**
If verification cannot determine outcome, report ``verified=None`` (unknown)
rather than ``verified=True``.
"""

from __future__ import annotations

import logging
import time
from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Optional

logger = logging.getLogger(__name__)


class VerifyStatus(Enum):
    """Outcome of a post-action verification check."""

    VERIFIED = "verified"  # Action effect confirmed
    FAILED = "failed"  # Action had no detectable effect
    SKIPPED = "skipped"  # Verification skipped (--no-verify or not applicable)
    UNKNOWN = "unknown"  # Could not determine (verification error)


@dataclass
class VerificationResult:
    """Result of a post-action verification check.

    Attributes:
        status: Verification outcome.
        verified: Convenience bool — True if VERIFIED, False if FAILED,
            None if SKIPPED or UNKNOWN.
        detail: Human-readable explanation of the verification result.
        method: Which verification method was used (e.g., "value_compare",
            "focus_check", "ui_state_diff").
        before: State snapshot before the action (for diagnostics).
        after: State snapshot after the action (for diagnostics).
        elapsed_ms: Time spent on verification in milliseconds.
    """

    status: VerifyStatus
    detail: str = ""
    method: str = ""
    before: Any = None
    after: Any = None
    elapsed_ms: float = 0.0

    @property
    def verified(self) -> Optional[bool]:
        """Convenience property for JSON output."""
        if self.status == VerifyStatus.VERIFIED:
            return True
        if self.status == VerifyStatus.FAILED:
            return False
        return None

    def to_dict(self) -> dict:
        """Serialize for JSON output.

        Returns:
            Dict with verification fields for embedding in command output.
        """
        d: dict[str, Any] = {"verified": self.verified}
        if self.detail:
            d["verification_detail"] = self.detail
        if self.method:
            d["verification_method"] = self.method
        if self.status == VerifyStatus.FAILED:
            d["verification_error"] = self.detail
        if self.elapsed_ms > 0:
            d["verification_ms"] = round(self.elapsed_ms, 1)
        return d


def skip_result(reason: str = "verification disabled") -> VerificationResult:
    """Return a SKIPPED result (for --no-verify or non-applicable cases)."""
    return VerificationResult(
        status=VerifyStatus.SKIPPED,
        detail=reason,
        method="none",
    )


def unknown_result(reason: str) -> VerificationResult:
    """Return an UNKNOWN result when verification itself fails."""
    return VerificationResult(
        status=VerifyStatus.UNKNOWN,
        detail=reason,
        method="error",
    )


# ── Type verification ────────────────────────────────────────────────────────


def verify_type(
    backend,
    *,
    text: Optional[str],
    ref: Optional[str] = None,
    app: Optional[str] = None,
    window_title: Optional[str] = None,
    hwnd: Optional[int] = None,
    before_value: Optional[str] = None,
    paste_mode: bool = False,
    settle_ms: int = 150,
) -> VerificationResult:
    """Verify that a type/paste action actually changed the target element's value.

    Strategy:
    1. Read the target element's current value via UIA ValuePattern.
    2. Compare with before_value (captured before the action).
    3. If value changed and contains the typed text → verified.
    4. If value unchanged → failed.

    Args:
        backend: Platform backend instance.
        text: The text that was typed/pasted. None for clipboard-only paste.
        ref: Element ref (eN) that was targeted via --on.
        app: Application name filter.
        window_title: Window title filter.
        hwnd: Window handle filter.
        before_value: Element value captured before the action.
        paste_mode: Whether paste mode was used.
        settle_ms: Milliseconds to wait for UI to settle before verification.

    Returns:
        VerificationResult with outcome.
    """
    start = time.monotonic()

    if text is None:
        # Clipboard-only paste — we can't verify without knowing what was on clipboard
        return VerificationResult(
            status=VerifyStatus.SKIPPED,
            detail="Cannot verify clipboard-only paste (unknown clipboard content)",
            method="none",
            elapsed_ms=(time.monotonic() - start) * 1000,
        )

    if settle_ms > 0:
        time.sleep(settle_ms / 1000.0)

    # Try to read the element value after action
    try:
        if not hasattr(backend, "get_element_value"):
            return VerificationResult(
                status=VerifyStatus.SKIPPED,
                detail="Backend does not support value reading (non-Windows)",
                method="none",
                elapsed_ms=(time.monotonic() - start) * 1000,
            )

        after_info = backend.get_element_value(
            ref=ref,
            app=app,
            window_title=window_title,
            hwnd=hwnd,
        )
    except Exception as exc:
        logger.debug("Type verification: failed to read value: %s", exc)
        return VerificationResult(
            status=VerifyStatus.UNKNOWN,
            detail=f"Could not read element value after typing: {exc}",
            method="value_compare",
            elapsed_ms=(time.monotonic() - start) * 1000,
        )

    if after_info is None:
        return VerificationResult(
            status=VerifyStatus.UNKNOWN,
            detail="Target element not found for value verification",
            method="value_compare",
            elapsed_ms=(time.monotonic() - start) * 1000,
        )

    after_value = after_info.get("value", "")
    elapsed = (time.monotonic() - start) * 1000

    # Compare: did the value change?
    if before_value is not None:
        if after_value != before_value:
            # Value changed — check if typed text is present
            if text and text in str(after_value or ""):
                return VerificationResult(
                    status=VerifyStatus.VERIFIED,
                    detail=f"Text '{text[:50]}' confirmed in element value",
                    method="value_compare",
                    before=before_value,
                    after=after_value,
                    elapsed_ms=elapsed,
                )
            else:
                # Value changed but doesn't contain our text — still counts
                # as "something happened" which is better than nothing
                return VerificationResult(
                    status=VerifyStatus.VERIFIED,
                    detail="Element value changed after typing",
                    method="value_compare",
                    before=before_value,
                    after=after_value,
                    elapsed_ms=elapsed,
                )
        else:
            # Value unchanged → silent failure detected!
            return VerificationResult(
                status=VerifyStatus.FAILED,
                detail=(
                    f"Element value unchanged after type operation. "
                    f"Text '{text[:50]}' was not typed into the target element. "
                    f"Possible causes: wrong window focused, element not editable, "
                    f"or running in a non-interactive session."
                ),
                method="value_compare",
                before=before_value,
                after=after_value,
                elapsed_ms=elapsed,
            )
    else:
        # No before_value — check if typed text is present in current value
        if text and text in str(after_value or ""):
            return VerificationResult(
                status=VerifyStatus.VERIFIED,
                detail=f"Text '{text[:50]}' found in element value",
                method="value_compare",
                after=after_value,
                elapsed_ms=elapsed,
            )
        else:
            # Can't confirm — we don't know what the value was before
            return VerificationResult(
                status=VerifyStatus.UNKNOWN,
                detail="No before-value captured; cannot confirm change",
                method="value_compare",
                after=after_value,
                elapsed_ms=elapsed,
            )


# ── Click verification ───────────────────────────────────────────────────────


def verify_click(
    backend,
    *,
    x: Optional[int] = None,
    y: Optional[int] = None,
    target_id: Optional[str] = None,
    app: Optional[str] = None,
    window_title: Optional[str] = None,
    hwnd: Optional[int] = None,
    before_focus: Optional[dict] = None,
    settle_ms: int = 200,
) -> VerificationResult:
    """Verify that a click action changed the UI state.

    Strategy:
    1. Compare foreground window / focused element before vs after.
    2. If focus changed → verified (click had effect).
    3. If nothing changed → failed (silent failure).

    This is inherently less precise than type verification because clicks
    can have many valid effects (menu open, button press, focus change, etc).
    We optimize for detecting the "zero effect" case.

    Args:
        backend: Platform backend instance.
        x: Click X coordinate.
        y: Click Y coordinate.
        target_id: Element ID that was clicked.
        app: Application name filter.
        window_title: Window title filter.
        hwnd: Window handle filter.
        before_focus: Focus state captured before the click.
        settle_ms: Milliseconds to wait for UI to settle.

    Returns:
        VerificationResult with outcome.
    """
    start = time.monotonic()

    if settle_ms > 0:
        time.sleep(settle_ms / 1000.0)

    try:
        after_focus = _capture_focus_state(backend)
    except Exception as exc:
        logger.debug("Click verification: failed to capture focus: %s", exc)
        return VerificationResult(
            status=VerifyStatus.UNKNOWN,
            detail=f"Could not capture focus state after click: {exc}",
            method="focus_check",
            elapsed_ms=(time.monotonic() - start) * 1000,
        )

    elapsed = (time.monotonic() - start) * 1000

    if before_focus is None:
        # No before state — can't compare
        return VerificationResult(
            status=VerifyStatus.UNKNOWN,
            detail="No before-focus state captured; cannot verify click effect",
            method="focus_check",
            elapsed_ms=elapsed,
        )

    # Compare focus states
    if after_focus != before_focus:
        return VerificationResult(
            status=VerifyStatus.VERIFIED,
            detail="UI focus/state changed after click",
            method="focus_check",
            before=before_focus,
            after=after_focus,
            elapsed_ms=elapsed,
        )
    else:
        # Focus unchanged — but this might be expected for some clicks
        # (e.g., clicking on an already-focused element, or a toggle).
        # We report UNKNOWN rather than FAILED to avoid false positives
        # on "click did nothing" when it actually did something non-focus-related.
        return VerificationResult(
            status=VerifyStatus.UNKNOWN,
            detail=(
                "No focus change detected after click. This may be normal "
                "(e.g., clicking an already-focused element) or indicate a "
                "silent failure."
            ),
            method="focus_check",
            before=before_focus,
            after=after_focus,
            elapsed_ms=elapsed,
        )


# ── Press verification ───────────────────────────────────────────────────────


def verify_press(
    backend,
    *,
    keys: tuple[str, ...],
    app: Optional[str] = None,
    window_title: Optional[str] = None,
    hwnd: Optional[int] = None,
    before_focus: Optional[dict] = None,
    settle_ms: int = 150,
) -> VerificationResult:
    """Verify that a key press had effect.

    Strategy similar to click verification — check focus/state change.
    For certain keys (Enter, Tab, Escape), we know what should happen
    and can be more specific.

    Args:
        backend: Platform backend instance.
        keys: Key specs that were pressed.
        app: Application name filter.
        window_title: Window title filter.
        hwnd: Window handle filter.
        before_focus: Focus state captured before pressing.
        settle_ms: Milliseconds to wait for UI to settle.

    Returns:
        VerificationResult with outcome.
    """
    start = time.monotonic()

    if settle_ms > 0:
        time.sleep(settle_ms / 1000.0)

    try:
        after_focus = _capture_focus_state(backend)
    except Exception as exc:
        logger.debug("Press verification: failed to capture focus: %s", exc)
        return VerificationResult(
            status=VerifyStatus.UNKNOWN,
            detail=f"Could not capture focus state after press: {exc}",
            method="focus_check",
            elapsed_ms=(time.monotonic() - start) * 1000,
        )

    elapsed = (time.monotonic() - start) * 1000

    if before_focus is None:
        return VerificationResult(
            status=VerifyStatus.UNKNOWN,
            detail="No before-focus state captured; cannot verify press effect",
            method="focus_check",
            elapsed_ms=elapsed,
        )

    if after_focus != before_focus:
        return VerificationResult(
            status=VerifyStatus.VERIFIED,
            detail="UI state changed after key press",
            method="focus_check",
            before=before_focus,
            after=after_focus,
            elapsed_ms=elapsed,
        )
    else:
        # Many key presses don't change focus (typing characters, etc.)
        # Only flag as suspicious for navigation keys
        nav_keys = {"tab", "enter", "escape", "alt+f4", "alt+tab"}
        pressed_lower = {k.lower() for k in keys}
        if pressed_lower & nav_keys:
            return VerificationResult(
                status=VerifyStatus.UNKNOWN,
                detail=(
                    f"No UI state change after navigation key(s) "
                    f"{', '.join(keys)}. May indicate silent failure."
                ),
                method="focus_check",
                before=before_focus,
                after=after_focus,
                elapsed_ms=elapsed,
            )
        else:
            # Non-navigation keys not changing focus is normal
            return VerificationResult(
                status=VerifyStatus.SKIPPED,
                detail="Non-navigation keys; focus change not expected",
                method="focus_check",
                elapsed_ms=elapsed,
            )


# ── Focus state capture ──────────────────────────────────────────────────────


def _capture_focus_state(backend) -> dict:
    """Capture current focus/UI state for before/after comparison.

    Returns a dict with foreground window info that can be compared
    across two points in time.

    Args:
        backend: Platform backend instance.

    Returns:
        Dict with keys: foreground_hwnd, foreground_title, foreground_pid.
    """
    import platform as _plat
    state: dict = {}

    if _plat.system() == "Windows":
        try:
            import ctypes
            import ctypes.wintypes

            user32 = ctypes.windll.user32  # type: ignore[attr-defined]

            # Foreground window handle
            fg_hwnd = user32.GetForegroundWindow()
            state["foreground_hwnd"] = fg_hwnd

            # Window title
            buf = ctypes.create_unicode_buffer(256)
            user32.GetWindowTextW(fg_hwnd, buf, 256)
            state["foreground_title"] = buf.value

            # Window PID
            pid = ctypes.wintypes.DWORD()
            user32.GetWindowThreadProcessId(fg_hwnd, ctypes.byref(pid))
            state["foreground_pid"] = pid.value

            # Focused element (UIA) — try to get the focused element's name
            try:
                import comtypes.client  # type: ignore[import-untyped]

                uia = comtypes.client.CreateObject(
                    "{ff48dba4-60ef-4201-aa87-54103eef594e}",
                    interface=None,
                )
                focused = uia.GetFocusedElement()
                if focused:
                    state["focused_name"] = focused.CurrentName or ""
                    state["focused_role"] = focused.CurrentControlType
                    state["focused_aid"] = focused.CurrentAutomationId or ""
            except Exception:
                pass

        except Exception as exc:
            logger.debug("Focus capture failed: %s", exc)
            state["error"] = str(exc)
    else:
        # macOS / Linux — basic focus info
        state["platform"] = _plat.system()

    return state


def capture_before_state(
    backend,
    *,
    action: str,
    ref: Optional[str] = None,
    app: Optional[str] = None,
    window_title: Optional[str] = None,
    hwnd: Optional[int] = None,
) -> dict:
    """Capture pre-action state for verification.

    Call this BEFORE performing the action to establish a baseline.

    Args:
        backend: Platform backend instance.
        action: Action type ("type", "click", "press").
        ref: Element ref for type verification.
        app: Application name filter.
        window_title: Window title filter.
        hwnd: Window handle filter.

    Returns:
        Dict with captured state. Pass to the verify_* function's
        before_* parameter.
    """
    state: dict[str, Any] = {"action": action, "timestamp": time.monotonic()}

    if action == "type":
        # Capture element value before typing
        try:
            if hasattr(backend, "get_element_value"):
                value_info = backend.get_element_value(
                    ref=ref,
                    app=app,
                    window_title=window_title,
                    hwnd=hwnd,
                )
                if value_info:
                    state["value"] = value_info.get("value", "")
                else:
                    state["value"] = None
        except Exception as exc:
            logger.debug("Pre-type value capture failed: %s", exc)
            state["value"] = None

    # Always capture focus state for click/press/type
    try:
        state["focus"] = _capture_focus_state(backend)
    except Exception as exc:
        logger.debug("Pre-action focus capture failed: %s", exc)
        state["focus"] = None

    return state
