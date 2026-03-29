"""Data models and parsing helpers for the naturo bridge.

Contains the core data classes (WindowInfo, ElementInfo) and JSON
parsing utilities used throughout the bridge package.
"""
from __future__ import annotations

import json
import logging
import re
from dataclasses import dataclass, field
from typing import Optional

logger = logging.getLogger(__name__)


def _decode_native(raw: bytes) -> str:
    """Decode bytes from native DLL, trying UTF-8 first then system codepage.

    On Chinese Windows the DLL may return GBK/CP936 encoded strings.
    """
    try:
        return raw.decode("utf-8")
    except UnicodeDecodeError:
        import locale
        encoding = locale.getpreferredencoding(False) or "cp936"
        return raw.decode(encoding, errors="replace")


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
