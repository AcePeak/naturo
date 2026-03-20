"""Snapshot data models — aligned with Peekaboo's UIAutomationSnapshot architecture.

Mirrors the Swift UIElement and UIAutomationSnapshot structs from Peekaboo,
adapted for Python / Windows (no CoreGraphics dependency).
"""

from __future__ import annotations

import json
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Dict, List, Optional, Tuple


@dataclass
class UIElement:
    """A single UI element captured in a snapshot.

    Mirrors Peekaboo's ``UIElement`` struct (Swift), adapted for cross-platform use.

    Attributes:
        id: Unique element identifier within this snapshot (e.g. ``"e1"``).
        element_id: Stable element reference (e.g. ``"element_0"``).
        role: Accessibility role (e.g. ``"AXButton"``, ``"Edit"``, ``"Button"``).
        title: Element title / name.
        label: Accessibility label.
        value: Current value (e.g. text content of an edit control).
        description: Human-readable description.
        identifier: Automation identifier / AutomationId.
        frame: Bounding rectangle as (x, y, width, height) in screen coordinates.
        is_actionable: Whether the element accepts user input.
        parent_id: Parent element's ``id``, or ``None`` for root elements.
        children: Ordered list of child element ``id`` values.
        keyboard_shortcut: Associated keyboard shortcut string (e.g. ``"Ctrl+S"``).
    """

    id: str
    element_id: str
    role: str
    title: Optional[str] = None
    label: Optional[str] = None
    value: Optional[str] = None
    description: Optional[str] = None
    identifier: Optional[str] = None
    frame: Tuple[int, int, int, int] = (0, 0, 0, 0)  # x, y, width, height
    is_actionable: bool = False
    parent_id: Optional[str] = None
    children: List[str] = field(default_factory=list)
    keyboard_shortcut: Optional[str] = None

    # ── Serialisation ────────────────────────────────────────────────────────

    def to_dict(self) -> dict:
        """Convert to a JSON-serialisable dictionary."""
        return {
            "id": self.id,
            "elementId": self.element_id,
            "role": self.role,
            "title": self.title,
            "label": self.label,
            "value": self.value,
            "description": self.description,
            "identifier": self.identifier,
            "frame": list(self.frame),
            "isActionable": self.is_actionable,
            "parentId": self.parent_id,
            "children": self.children,
            "keyboardShortcut": self.keyboard_shortcut,
        }

    @classmethod
    def from_dict(cls, data: dict) -> "UIElement":
        """Restore a ``UIElement`` from a dictionary (as produced by :meth:`to_dict`)."""
        frame_raw = data.get("frame", [0, 0, 0, 0])
        return cls(
            id=data["id"],
            element_id=data.get("elementId", data.get("element_id", "")),
            role=data.get("role", ""),
            title=data.get("title"),
            label=data.get("label"),
            value=data.get("value"),
            description=data.get("description"),
            identifier=data.get("identifier"),
            frame=tuple(int(v) for v in frame_raw[:4]),  # type: ignore[assignment]
            is_actionable=data.get("isActionable", data.get("is_actionable", False)),
            parent_id=data.get("parentId", data.get("parent_id")),
            children=data.get("children", []),
            keyboard_shortcut=data.get("keyboardShortcut", data.get("keyboard_shortcut")),
        )


@dataclass
class Snapshot:
    """Full UI automation snapshot — screenshot + element map + window metadata.

    Mirrors Peekaboo's ``UIAutomationSnapshot`` struct, adapted for Windows /
    cross-platform use (``window_handle`` replaces ``windowID``/``windowAXIdentifier``).

    Attributes:
        snapshot_id: Unique snapshot identifier (timestamp + random suffix).
        version: Schema version; always :attr:`CURRENT_VERSION`.
        screenshot_path: Absolute path to the raw screenshot (``raw.png``).
        annotated_path: Absolute path to the annotated screenshot (``annotated.png``).
        ui_map: Mapping of ``element.id`` → :class:`UIElement`.
        last_update_time: Timestamp of the most recent update.
        application_name: Display name of the captured application.
        application_pid: Process ID of the captured application.
        window_title: Title of the captured window.
        window_bounds: Window bounding rectangle as (x, y, width, height).
        window_handle: Platform window handle (HWND on Windows, ``None`` on other platforms).
    """

    CURRENT_VERSION: int = field(default=1, init=False, repr=False, compare=False)

    snapshot_id: str
    version: int = 1
    screenshot_path: Optional[str] = None
    annotated_path: Optional[str] = None
    ui_map: Dict[str, UIElement] = field(default_factory=dict)
    last_update_time: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    application_name: Optional[str] = None
    application_pid: Optional[int] = None
    window_title: Optional[str] = None
    window_bounds: Optional[Tuple[int, int, int, int]] = None
    window_handle: Optional[int] = None  # HWND on Windows

    # ── Serialisation ────────────────────────────────────────────────────────

    def to_dict(self) -> dict:
        """Convert to a JSON-serialisable dictionary."""
        return {
            "version": self.version,
            "snapshotId": self.snapshot_id,
            "screenshotPath": self.screenshot_path,
            "annotatedPath": self.annotated_path,
            "uiMap": {k: v.to_dict() for k, v in self.ui_map.items()},
            "lastUpdateTime": self.last_update_time.isoformat(),
            "applicationName": self.application_name,
            "applicationPid": self.application_pid,
            "windowTitle": self.window_title,
            "windowBounds": list(self.window_bounds) if self.window_bounds else None,
            "windowHandle": self.window_handle,
        }

    @classmethod
    def from_dict(cls, data: dict) -> "Snapshot":
        """Restore a :class:`Snapshot` from a dictionary."""
        ui_map_raw = data.get("uiMap", {})
        ui_map = {k: UIElement.from_dict(v) for k, v in ui_map_raw.items()}

        wb_raw = data.get("windowBounds")
        window_bounds: Optional[Tuple[int, int, int, int]] = (
            tuple(int(v) for v in wb_raw[:4])  # type: ignore[assignment]
            if wb_raw
            else None
        )

        last_update_raw = data.get("lastUpdateTime")
        if last_update_raw:
            # Handle both ISO strings and unix timestamps
            if isinstance(last_update_raw, (int, float)):
                last_update_time = datetime.fromtimestamp(last_update_raw, tz=timezone.utc)
            else:
                parsed = datetime.fromisoformat(str(last_update_raw).rstrip("Z"))
                last_update_time = parsed.replace(tzinfo=timezone.utc) if parsed.tzinfo is None else parsed
        else:
            last_update_time = datetime.now(timezone.utc)

        return cls(
            snapshot_id=data.get("snapshotId", data.get("snapshot_id", "")),
            version=data.get("version", 1),
            screenshot_path=data.get("screenshotPath", data.get("screenshot_path")),
            annotated_path=data.get("annotatedPath", data.get("annotated_path")),
            ui_map=ui_map,
            last_update_time=last_update_time,
            application_name=data.get("applicationName", data.get("application_name")),
            application_pid=data.get("applicationPid", data.get("application_pid")),
            window_title=data.get("windowTitle", data.get("window_title")),
            window_bounds=window_bounds,
            window_handle=data.get("windowHandle", data.get("window_handle")),
        )

    def to_json(self, indent: int = 2) -> str:
        """Serialise snapshot to a JSON string."""
        return json.dumps(self.to_dict(), indent=indent, ensure_ascii=False)

    @classmethod
    def from_json(cls, text: str) -> "Snapshot":
        """Deserialise snapshot from a JSON string."""
        return cls.from_dict(json.loads(text))


@dataclass
class SnapshotInfo:
    """Lightweight summary of a stored snapshot, returned by :meth:`SnapshotManager.list_snapshots`.

    Attributes:
        id: Snapshot identifier.
        created_at: Directory creation timestamp.
        last_accessed_at: Time of most recent data update.
        size_in_bytes: Total on-disk size of the snapshot directory.
        screenshot_count: Number of ``*.png`` files inside the directory.
        application_name: Captured application name (may be ``None``).
    """

    id: str
    created_at: datetime
    last_accessed_at: datetime
    size_in_bytes: int = 0
    screenshot_count: int = 0
    application_name: Optional[str] = None


class SnapshotError(Exception):
    """Base class for snapshot-related errors."""


class SnapshotNotFoundError(SnapshotError):
    """Raised when a requested snapshot does not exist or has expired."""

    def __init__(self, snapshot_id: str) -> None:
        super().__init__(f"Snapshot not found or expired: {snapshot_id}")
        self.snapshot_id = snapshot_id


class SnapshotVersionError(SnapshotError):
    """Raised when the on-disk schema version is incompatible."""

    def __init__(self, found: int, expected: int) -> None:
        super().__init__(f"Snapshot version mismatch (found: {found}, expected: {expected})")
        self.found = found
        self.expected = expected


class SnapshotStorageError(SnapshotError):
    """Raised on I/O or serialisation failures."""
