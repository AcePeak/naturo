"""Data models and parsing helpers for the naturo bridge.

Contains the core data classes (WindowInfo, ElementInfo) and JSON
parsing utilities used throughout the bridge package.
"""
from __future__ import annotations

import ctypes
import json
import logging
import re
import sys
from dataclasses import dataclass, field
from typing import Optional

logger = logging.getLogger(__name__)


def _system_ansi_encoding() -> str:
    """Return the OS ANSI codepage as a Python codec name (e.g. ``"cp936"``).

    On Windows the active ANSI codepage is read from the Win32 ``GetACP`` API.
    ``locale.getpreferredencoding`` must NOT be used for this on Windows because
    it returns ``"utf-8"`` under Python UTF-8 mode (``PYTHONUTF8=1`` / ``-X
    utf8``) regardless of the OS codepage; trusting it there re-decodes ANSI
    (e.g. CP936/GBK) bytes from the native core as UTF-8 and corrupts every
    non-ASCII character to U+FFFD (#1150). Off Windows there is no ANSI
    codepage, so the locale preferred encoding is used, defaulting to
    ``"cp936"`` when it cannot be resolved.

    Returns:
        A codec name suitable for ``bytes.decode``.
    """
    if sys.platform == "win32":
        try:
            acp = ctypes.windll.kernel32.GetACP()  # type: ignore[attr-defined]
            if acp:
                return f"cp{acp}"
        except (OSError, AttributeError, ValueError):
            pass
    import locale
    return locale.getpreferredencoding(False) or "cp936"


def _decode_native(raw: bytes) -> str:
    """Decode bytes from the native DLL, trying UTF-8 then the OS ANSI codepage.

    On a non-UTF-8 Windows desktop (e.g. CP936/GBK on a Chinese-locale system)
    the native core may emit narrow strings in the system ANSI codepage rather
    than UTF-8. A strict UTF-8 decode is attempted first; on failure the bytes
    are decoded with the OS ANSI codepage resolved by ``_system_ansi_encoding``
    (see #1150 for why ``locale.getpreferredencoding`` is unsafe here).

    Args:
        raw: Raw bytes returned by the native library.

    Returns:
        The decoded string.
    """
    try:
        return raw.decode("utf-8")
    except UnicodeDecodeError:
        return raw.decode(_system_ansi_encoding(), errors="replace")


def _safe_json_loads(s: str):
    """Parse JSON with fallback repair for invalid Unicode escapes from C++ DLL.

    Some C++ DLL output contains unpaired surrogate escapes (e.g. \\uD800)
    which are invalid JSON. This function catches the error and repairs
    the string by removing orphaned surrogates before retrying.
    """
    try:
        return json.loads(s)
    except json.JSONDecodeError:
        # Remove unpaired high surrogates (not followed by a low surrogate)
        repaired = re.sub(
            r'\\ud[89a-f][0-9a-f]{2}(?!\\u)', '', s, flags=re.IGNORECASE
        )
        # Remove orphaned low surrogates (not preceded by a high surrogate)
        repaired = re.sub(
            r'(?<!\\ud[89a-f][0-9a-f]{2})\\ud[c-f][0-9a-f]{2}',
            '', repaired, flags=re.IGNORECASE,
        )
        return json.loads(repaired)


@dataclass
class WindowInfo:
    """Information about a top-level window.

    Attributes:
        hwnd: Window handle (HWND on Windows).
        title: Window title text.
        process_name: Full path of the owning process.
        pid: Process ID.
        x: Window left edge X coordinate.
        y: Window top edge Y coordinate.
        width: Window width in pixels.
        height: Window height in pixels.
        is_visible: Whether the window is visible.
        is_minimized: Whether the window is minimized (iconic).
        handle: Alias for ``hwnd`` — matches the cross-platform
            ``backends.base.WindowInfo.handle`` attribute (#504).
    """
    hwnd: int
    title: str
    process_name: str
    pid: int
    x: int
    y: int
    width: int
    height: int
    is_visible: bool
    is_minimized: bool

    @property
    def handle(self) -> int:
        """Alias for ``hwnd`` for cross-platform API compatibility (#504)."""
        return self.hwnd


@dataclass
class ElementInfo:
    """Information about a UI automation element.

    Attributes:
        id: Automation ID of the element.
        role: Control type / role (e.g., "Button", "Edit").
        name: Element name (accessible name).
        value: Element value, if any.
        x: Bounding rectangle left edge.
        y: Bounding rectangle top edge.
        width: Bounding rectangle width.
        height: Bounding rectangle height.
        children: Child elements.
        parent_id: Parent element's id (filled by Python-layer traversal).
        keyboard_shortcut: Keyboard shortcut string (e.g., "Ctrl+S").
        hwnd: Win32 window handle (Windows only, for hybrid mode and direct messaging).
        states: Accessibility state string emitted by the native layer, if any
            (e.g., "enabled,focusable,visible,checked"). Currently populated by the
            Java Access Bridge backend, which exposes a control's checked/selected
            state; ``None`` for backends that do not emit states. (#1200)
        is_enabled: Whether the element is currently enabled/interactable
            (UIA ``IsEnabled``). ``None`` when the backend does not report it.
        is_offscreen: Whether the element is scrolled/clipped off-screen
            (UIA ``IsOffscreen``). ``None`` when not reported.
        help_text: Extended tooltip/description a screen reader announces
            (UIA ``HelpText``). ``None`` when not reported.
        localized_control_type: Locale-specific role name a screen reader
            announces (UIA ``LocalizedControlType``, e.g. "按钮" for a button).
            ``None`` when not reported.
        is_keyboard_focusable: Whether Tab/Shift+Tab can reach this element
            (UIA ``IsKeyboardFocusable``). ``None`` when not reported.
        has_keyboard_focus: Whether the element currently holds keyboard focus
            (UIA ``HasKeyboardFocus``). ``None`` when not reported. (#896)
    """
    id: str
    role: str
    name: str
    value: Optional[str]
    x: int
    y: int
    width: int
    height: int
    children: list["ElementInfo"] = field(default_factory=list)
    parent_id: Optional[str] = None
    keyboard_shortcut: Optional[str] = None
    hwnd: Optional[int] = None
    states: Optional[str] = None
    # True per-node capabilities reported by the backend (not role-guessed):
    # readable = has readable content (Value/TextPattern, JAB AccessibleText);
    # actionable = clickable/invokable; editable = accepts text input.
    readable: Optional[bool] = None
    actionable: Optional[bool] = None
    editable: Optional[bool] = None
    # (#896) UIA accessibility properties. These are emitted per-element by the
    # native UIA traversal (core/src/element.cpp); a backend that does not read
    # them (MSAA/IA2/JAB/OCR/UWP fallback, test fixtures) leaves them ``None``.
    is_enabled: Optional[bool] = None
    is_offscreen: Optional[bool] = None
    help_text: Optional[str] = None
    localized_control_type: Optional[str] = None
    is_keyboard_focusable: Optional[bool] = None
    has_keyboard_focus: Optional[bool] = None


def _parse_element(data: dict) -> ElementInfo:
    """Parse a JSON dict into an ElementInfo, recursively processing children.

    Args:
        data: Dictionary from parsed JSON.

    Returns:
        An ElementInfo instance.
    """
    children = [_parse_element(c) for c in data.get("children", [])]
    return ElementInfo(
        id=data.get("id", ""),
        role=data.get("role", ""),
        name=data.get("name", ""),
        value=data.get("value"),
        x=data.get("x", 0),
        y=data.get("y", 0),
        width=data.get("width", 0),
        height=data.get("height", 0),
        children=children,
        parent_id=data.get("parent_id"),
        keyboard_shortcut=data.get("keyboard_shortcut"),
        states=data.get("states"),
        readable=data.get("readable"),
        actionable=data.get("actionable"),
        editable=data.get("editable"),
        is_enabled=data.get("is_enabled"),
        is_offscreen=data.get("is_offscreen"),
        help_text=data.get("help_text"),
        localized_control_type=data.get("localized_control_type"),
        is_keyboard_focusable=data.get("is_keyboard_focusable"),
        has_keyboard_focus=data.get("has_keyboard_focus"),
    )


def populate_hierarchy(root: ElementInfo, parent_id: Optional[str] = None, counter: Optional[list] = None) -> None:
    """Fill parent_id for all elements in the tree via depth-first traversal.

    If an element has an empty id, assigns a sequential id like "e0", "e1", etc.

    Args:
        root: Root element of the tree.
        parent_id: Parent's id (None for the root).
        counter: Internal counter list for id generation.
    """
    if counter is None:
        counter = [1]

    if not root.id:
        root.id = f"e{counter[0]}"
        counter[0] += 1

    root.parent_id = parent_id

    for child in root.children:
        populate_hierarchy(child, parent_id=root.id, counter=counter)
