"""Application control — list, launch, quit, open URIs, menu inspection."""
from __future__ import annotations

from typing import Optional

from naturo.backends.macos._peekaboo import PeekabooError
from naturo.errors import NaturoError


class AppMixin:
    """Application lifecycle and menu inspection via Peekaboo."""

    def list_apps(self) -> list[dict]:
        """List running applications.

        Returns:
            List of dicts with app info (name, pid, bundleIdentifier, etc.).
        """
        data = self._run(["app", "list"])
        data_section = data.get("data", {})
        apps = (
            data_section.get("apps")
            or data_section.get("applications")
            or data.get("apps")
            or data.get("applications", [])
        )
        result = []
        for app in apps:
            result.append({
                "name": app.get("name", ""),
                "pid": app.get("processIdentifier", app.get("pid", 0)),
                "bundle_id": app.get("bundleIdentifier", app.get("bundle_id", "")),
                "bundle_path": app.get("bundlePath", app.get("bundle_path", "")),
                "is_active": app.get("isActive", app.get("is_active", False)),
                "is_hidden": app.get("isHidden", app.get("is_hidden", False)),
                "window_count": app.get("windowCount", app.get("window_count", 0)),
            })
        return result

    def launch_app(self, name: str = "") -> None:
        """Launch an application by name.

        Args:
            name: Application name (e.g., 'Safari', 'Terminal').

        Raises:
            NaturoError: If the application cannot be found.
        """
        if not name:
            raise NaturoError("Application name is required")
        try:
            self._run(["app", "launch", name])
        except PeekabooError as e:
            if "not found" in str(e).lower():
                raise NaturoError(f"Application not found: {name}") from e
            raise

    def quit_app(self, name: str = "", force: bool = False) -> None:
        """Quit an application.

        Args:
            name: Application name.
            force: If True, force-quit the application.
        """
        if not name:
            raise NaturoError("Application name is required")
        args = ["app", "quit", "--app", name]
        if force:
            args.append("--force")
        self._run(args)

    # === Open ===

    def open_uri(self, uri: str = "") -> None:
        """Open a URL or file with the default application.

        Args:
            uri: URL or file path to open.
        """
        if not uri:
            raise NaturoError("URI is required")
        self._run(["open", uri])

    # === Menu ===

    def get_menu_items(self, window_title: Optional[str] = None,
                       hwnd: Optional[int] = None) -> list:
        """Get menu items from the application menu bar.

        Args:
            window_title: Application name to inspect menus for.
            hwnd: Window handle (ignored on macOS).

        Returns:
            List of menu item dicts.
        """
        args = ["menu", "list"]
        if window_title:
            args += ["--app", window_title]
        data = self._run(args, timeout=15)
        return data.get("data", {}).get("menuItems", data.get("menu_items", []))
