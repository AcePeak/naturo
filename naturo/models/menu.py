"""Menu item data model for menu bar traversal."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import List, Optional


@dataclass
class MenuItem:
    """A single menu item from an application's menu bar.

    Attributes:
        name: Display name of the menu item (e.g., "Save As...").
        shortcut: Keyboard shortcut string (e.g., "Ctrl+S"), or None.
        submenu: Nested menu items, or None if this is a leaf item.
        enabled: Whether the menu item is currently enabled/clickable.
        checked: Whether the menu item is in a checked/toggled state.
    """

    name: str
    shortcut: Optional[str] = None
    submenu: Optional[List["MenuItem"]] = None
    enabled: bool = True
    checked: bool = False

    def to_dict(self) -> dict:
        """Convert to a JSON-serialisable dictionary."""
        d: dict = {"name": self.name}
        if self.shortcut:
            d["shortcut"] = self.shortcut
        if not self.enabled:
            d["enabled"] = False
        if self.checked:
            d["checked"] = True
        if self.submenu:
            d["submenu"] = [item.to_dict() for item in self.submenu]
        return d

    @classmethod
    def from_dict(cls, data: dict) -> "MenuItem":
        """Restore a MenuItem from a dictionary."""
        submenu_raw = data.get("submenu")
        submenu = [cls.from_dict(s) for s in submenu_raw] if submenu_raw else None
        return cls(
            name=data.get("name", ""),
            shortcut=data.get("shortcut"),
            submenu=submenu,
            enabled=data.get("enabled", True),
            checked=data.get("checked", False),
        )

    def flatten(self, prefix: str = "") -> List[dict]:
        """Flatten the menu tree into a list of items with full paths.

        Returns:
            List of dicts with keys: path, shortcut, enabled, checked.
        """
        path = f"{prefix} > {self.name}" if prefix else self.name
        items = [{"path": path, "shortcut": self.shortcut, "enabled": self.enabled, "checked": self.checked}]
        if self.submenu:
            for child in self.submenu:
                items.extend(child.flatten(prefix=path))
        return items
