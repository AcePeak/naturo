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
    before_ui_texts: Optional[dict[str, str]] = None,
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
        before_ui_texts: Mapping of element identifiers to their text/value
            captured before the action. Used as fallback when ValuePattern
            comparison fails (e.g., WinUI 3 apps where ValuePattern doesn't
            reflect typed text). See ``_capture_ui_texts``.
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
            # Value unchanged via ValuePattern — try UI text diff fallback
            # (#398) Some apps (Win11 Notepad WinUI 3, RichEditTextBlock)
            # don't expose typed text through UIA ValuePattern, causing
            # false negatives. Fall back to comparing child window texts
            # and UIA element names (same approach as verify_click #263).
            if before_ui_texts is not None:
                try:
                    after_ui_texts = _capture_ui_texts(
                        backend, app=app, window_title=window_title, hwnd=hwnd,
                    )
                    if after_ui_texts and after_ui_texts != before_ui_texts:
                        # (#403) Only report VERIFIED if the typed text
                        # actually appears in one of the changed values.
                        # Without this check, irrelevant text changes
                        # (e.g., window title "Untitled" → "*Untitled")
                        # cause false positives — the verification engine
                        # claims typing succeeded when the editor is empty.
                        typed_found = _typed_text_in_ui_diff(
                            text, before_ui_texts, after_ui_texts,
                        )
                        elapsed = (time.monotonic() - start) * 1000
                        if typed_found:
                            return VerificationResult(
                                status=VerifyStatus.VERIFIED,
                                detail=(
                                    "Typed text confirmed in UI text diff "
                                    "(ValuePattern unchanged but text found "
                                    "in window content)"
                                ),
                                method="ui_text_diff",
                                before=before_ui_texts,
                                after=after_ui_texts,
                                elapsed_ms=elapsed,
                            )
                        else:
                            # UI text changed but typed text not found —
                            # likely title bar or irrelevant element.
                            # Report UNKNOWN, not VERIFIED (#403).
                            logger.debug(
                                "UI text changed but typed text %r not "
                                "found in changed values — likely "
                                "irrelevant change (title bar, etc.)",
                                text[:50],
                            )
                except Exception as exc:
                    logger.debug("Type UI text fallback failed: %s", exc)

            # (#398) If even the UI text fallback shows no change, report
            # UNKNOWN instead of FAILED. The ValuePattern may not work for
            # certain app frameworks, so a "no change detected" is not
            # definitive evidence of failure — it's inconclusive.
            elapsed = (time.monotonic() - start) * 1000
            return VerificationResult(
                status=VerifyStatus.UNKNOWN,
                detail=(
                    f"Element value unchanged after type operation. "
                    f"Text '{text[:50]}' may not have been typed, or the app "
                    f"framework does not expose typed text via UIA ValuePattern. "
                    f"Consider using screenshot verification for confirmation."
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
    before_ui_texts: Optional[dict[str, str]] = None,
    uia_invoked: bool = False,
    settle_ms: int = 200,
) -> VerificationResult:
    """Verify that a click action changed the UI state.

    Strategy:
    0. If UIA Invoke pattern was used successfully → verified (the COM
       call itself confirms the button was activated; #270).
    1. Compare foreground window / focused element before vs after.
    2. If focus changed → verified (click had effect).
    3. If focus unchanged, fall back to UI text comparison — check whether
       any sibling/nearby element text changed (e.g., calculator display
       updates after pressing a digit button).
    4. If nothing changed → report UNKNOWN (not FAILED, to avoid false
       positives on idempotent clicks).

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
        before_ui_texts: Mapping of element identifiers to their text/value
            captured before the click. Used as fallback when focus doesn't
            change (e.g., UWP Calculator display).
        uia_invoked: If True, the click was performed via UIA Invoke
            pattern (COM call succeeded). This is strong evidence the
            button was activated, even when focus/UI text checks fail.
        settle_ms: Milliseconds to wait for UI to settle.

    Returns:
        VerificationResult with outcome.
    """
    start = time.monotonic()

    # (#270) UIA Invoke pattern succeeded — the COM call itself confirms
    # the control was activated. No need for heuristic focus/text checks.
    if uia_invoked:
        return VerificationResult(
            status=VerifyStatus.VERIFIED,
            detail="UIA Invoke pattern succeeded — control was activated",
            method="uia_invoke",
            elapsed_ms=(time.monotonic() - start) * 1000,
        )

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

    # Focus unchanged — try UI text comparison as fallback (#263).
    # This catches cases like UWP Calculator where button clicks update
    # a display element without changing focus.
    if before_ui_texts is not None:
        try:
            after_ui_texts = _capture_ui_texts(
                backend, app=app, window_title=window_title, hwnd=hwnd,
            )
            if after_ui_texts and after_ui_texts != before_ui_texts:
                elapsed = (time.monotonic() - start) * 1000
                return VerificationResult(
                    status=VerifyStatus.VERIFIED,
                    detail="UI element text changed after click (display updated)",
                    method="ui_text_diff",
                    before=before_ui_texts,
                    after=after_ui_texts,
                    elapsed_ms=elapsed,
                )
        except Exception as exc:
            logger.debug("Click UI text comparison failed: %s", exc)

    elapsed = (time.monotonic() - start) * 1000

    # Nothing detected — report UNKNOWN (not FAILED) to avoid false
    # positives on idempotent clicks or clicks with non-observable effects.
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


def _typed_text_in_ui_diff(
    text: str,
    before: dict[str, str],
    after: dict[str, str],
) -> bool:
    """Check whether typed text appears in any changed UI text value.

    Compares before/after UI text snapshots and checks if the typed text
    (or a significant prefix) appears in any value that is new or changed.
    This prevents false positives from irrelevant text changes such as
    window title updates (e.g., "Untitled" → "*Untitled").

    Args:
        text: The text that was typed.
        before: UI text snapshot before the action.
        after: UI text snapshot after the action.

    Returns:
        True if the typed text (or prefix ≥ 3 chars) appears in a changed
        value; False otherwise.
    """
    if not text:
        return False

    # Collect values that are new or changed
    changed_values: list[str] = []
    for key, val in after.items():
        if key not in before or before[key] != val:
            changed_values.append(val)

    if not changed_values:
        return False

    # Check if typed text appears in any changed value.
    # Use case-insensitive comparison and also check for a prefix
    # (typing may be partially completed before verification).
    text_lower = text.lower()
    min_prefix = min(len(text), 3)  # At least 3 chars to avoid spurious matches

    for val in changed_values:
        val_lower = val.lower()
        # Full text match
        if text_lower in val_lower:
            return True
        # Prefix match (at least min_prefix chars)
        if min_prefix > 0 and text_lower[:min_prefix] in val_lower:
            return True

    return False


def _capture_ui_texts(
    backend,
    *,
    app: Optional[str] = None,
    window_title: Optional[str] = None,
    hwnd: Optional[int] = None,
    max_children: int = 50,
) -> dict[str, str]:
    """Capture a lightweight snapshot of child window texts for diff.

    Uses Win32 ``EnumChildWindows`` + ``GetWindowTextW`` which is fast and
    does not require UIA traversal.  This captures text from child HWNDs —
    sufficient for detecting display changes in apps like UWP Calculator
    where button clicks update a child window's text without focus change.

    Args:
        backend: Platform backend instance.
        app: Application name filter.
        window_title: Window title filter.
        hwnd: Window handle filter.
        max_children: Maximum child windows to enumerate.

    Returns:
        Dict mapping ``"child:<hwnd>"`` to the window text.
        Empty dict on non-Windows or failure.
    """
    import platform as _plat

    texts: dict[str, str] = {}
    if _plat.system() != "Windows":
        return texts

    # Only attempt UI text capture when we have an explicit target.
    # Without a target (app/window_title/hwnd), the text diff is
    # unreliable (we'd snapshot random foreground windows) and the
    # Win32/COM calls can hang on headless environments.
    if not (app or window_title or hwnd):
        return texts

    try:
        import ctypes
        import ctypes.wintypes

        user32 = ctypes.windll.user32  # type: ignore[attr-defined]

        # Resolve target window handle.
        # Use the backend's _resolve_hwnd when available (#266) — this
        # matches the same window that click/type commands target,
        # avoiding capture from the wrong (foreground) window.
        target_hwnd = hwnd or 0
        if not target_hwnd and hasattr(backend, "_resolve_hwnd"):
            try:
                target_hwnd = backend._resolve_hwnd(
                    app=app, window_title=window_title,
                )
            except Exception:
                pass
        if not target_hwnd:
            target_hwnd = user32.GetForegroundWindow()
        if not target_hwnd:
            return texts

        # Enumerate child windows and collect their text
        collected: list[tuple[int, str]] = []
        buf = ctypes.create_unicode_buffer(512)

        @ctypes.WINFUNCTYPE(ctypes.wintypes.BOOL, ctypes.wintypes.HWND, ctypes.wintypes.LPARAM)
        def _enum_callback(child_hwnd, _lparam):
            if len(collected) >= max_children:
                return False
            length = user32.GetWindowTextLengthW(child_hwnd)
            if length > 0:
                user32.GetWindowTextW(child_hwnd, buf, min(length + 1, 512))
                text = buf.value
                if text:
                    collected.append((child_hwnd, text))
            return True

        user32.EnumChildWindows(target_hwnd, _enum_callback, 0)

        for child_hwnd_val, text in collected:
            texts[f"child:{child_hwnd_val}"] = text

        # Also capture the foreground window's own text
        user32.GetWindowTextW(target_hwnd, buf, 512)
        if buf.value:
            texts[f"main:{target_hwnd}"] = buf.value

        # For UWP/XAML apps, child HWNDs may not have meaningful text.
        # Use a lightweight UIA scan of direct children to capture element
        # names (e.g., Calculator display "0" → "56").
        if len(texts) <= 1:
            try:
                _uia_texts = _capture_uia_child_names(target_hwnd, max_children)
                texts.update(_uia_texts)
            except Exception:
                pass

    except Exception as exc:
        logger.debug("UI text capture failed: %s", exc)

    return texts


def _capture_uia_child_names(
    hwnd: int,
    max_elements: int = 30,
    timeout_s: float = 3.0,
) -> dict[str, str]:
    """Capture UIA element names for a window's direct children.

    Uses ``TreeScope_Descendants`` to walk all descendant elements and
    collect their Name properties.  Used as fallback for UWP apps where
    Win32 ``GetWindowTextW`` returns nothing on child windows.

    Previous depth=2 approach missed UWP display elements (e.g.,
    Calculator's CalculatorResults) that sit at depth 3+ under the
    ApplicationFrameHost window (#270).

    The UIA scan runs in a daemon thread with a timeout to prevent hangs
    on headless CI runners or unresponsive UIA providers.

    Args:
        hwnd: Target window handle.
        max_elements: Maximum elements to inspect.
        timeout_s: Maximum seconds to wait for UIA scan (default 3).

    Returns:
        Dict mapping ``"uia:<ControlType>:<AutomationId or Name>"`` to Name.
    """
    import threading

    result_holder: dict[str, dict[str, str]] = {}

    def _scan() -> None:
        texts: dict[str, str] = {}
        try:
            import comtypes.client  # type: ignore[import-untyped]

            uia = comtypes.client.CreateObject(
                "{ff48dba4-60ef-4201-aa87-54103eef594e}",
                interface=None,
            )
            root = uia.ElementFromHandle(hwnd)
            if not root:
                result_holder["texts"] = texts
                return

            # TreeScope_Descendants = 4 — walk all descendants to capture
            # deeply-nested display elements in UWP/XAML apps (#270).
            true_cond = uia.CreateTrueCondition()
            descendants = root.FindAll(4, true_cond)
            if not descendants:
                result_holder["texts"] = texts
                return

            count = min(descendants.Length, max_elements)
            for i in range(count):
                elem = descendants.GetElement(i)
                name = elem.CurrentName or ""
                if not name:
                    continue
                aid = elem.CurrentAutomationId or ""
                ctrl_type = elem.CurrentControlType
                key = f"uia:{ctrl_type}:{aid}" if aid else f"uia:{ctrl_type}:{name}"
                texts[key] = name

        except Exception as exc:
            logger.debug("UIA child name capture failed: %s", exc)

        result_holder["texts"] = texts

    thread = threading.Thread(target=_scan, daemon=True)
    thread.start()
    thread.join(timeout=timeout_s)

    if "texts" not in result_holder:
        logger.debug("UIA child name capture timed out after %.1fs", timeout_s)
        return {}

    return result_holder["texts"]


def _capture_focus_state(backend, timeout_s: float = 3.0) -> dict:
    """Capture current focus/UI state for before/after comparison.

    Returns a dict with foreground window info that can be compared
    across two points in time.

    Win32 calls (GetForegroundWindow, GetWindowText) are fast and safe.
    The UIA portion (GetFocusedElement via comtypes) runs in a daemon
    thread with a timeout to prevent hangs on headless CI runners or
    unresponsive UIA providers.

    Args:
        backend: Platform backend instance.
        timeout_s: Maximum seconds to wait for UIA focus capture (default 3).

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

            # Foreground window handle — fast Win32 call, no timeout needed
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

            # Focused element (UIA) — run in daemon thread with timeout
            # to prevent hangs on headless CI runners.
            import threading

            uia_result: dict[str, dict] = {}

            def _uia_focus() -> None:
                uia_state: dict = {}
                try:
                    import comtypes.client  # type: ignore[import-untyped]

                    uia = comtypes.client.CreateObject(
                        "{ff48dba4-60ef-4201-aa87-54103eef594e}",
                        interface=None,
                    )
                    focused = uia.GetFocusedElement()
                    if focused:
                        uia_state["focused_name"] = focused.CurrentName or ""
                        uia_state["focused_role"] = focused.CurrentControlType
                        uia_state["focused_aid"] = focused.CurrentAutomationId or ""
                except Exception:
                    pass
                uia_result["state"] = uia_state

            thread = threading.Thread(target=_uia_focus, daemon=True)
            thread.start()
            thread.join(timeout=timeout_s)

            if "state" in uia_result:
                state.update(uia_result["state"])
            else:
                logger.debug("UIA focus capture timed out after %.1fs", timeout_s)

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

    # (#263, #398) For click and type actions, capture UI texts for fallback
    # verification. For clicks, this detects display changes without focus
    # shifts. For type, this catches apps where ValuePattern doesn't reflect
    # typed text (e.g., Win11 Notepad WinUI 3 RichEditTextBlock).
    if action in ("click", "type"):
        try:
            state["ui_texts"] = _capture_ui_texts(
                backend, app=app, window_title=window_title, hwnd=hwnd,
            )
        except Exception as exc:
            logger.debug("Pre-%s UI text capture failed: %s", action, exc)
            state["ui_texts"] = None

    return state
