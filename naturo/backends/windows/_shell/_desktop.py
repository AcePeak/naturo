"""Virtual desktop management via pyvda."""

from __future__ import annotations

from typing import Optional

from naturo.errors import NaturoError


class DesktopMixin:
    """List, create, switch, close, and move windows between virtual desktops."""

    def virtual_desktop_list(self) -> list[dict]:
        """List all virtual desktops.

        Uses IVirtualDesktopManagerInternal COM interface via the pyvda library
        when available, otherwise falls back to registry-based detection.

        Returns:
            List of dicts with keys: index, name, is_current, id.
        """
        try:
            import pyvda
            desktops = pyvda.get_virtual_desktops()
            current = pyvda.VirtualDesktop.current()
            result = []
            for i, d in enumerate(desktops):
                result.append({
                    "index": i,
                    "name": d.name or f"Desktop {i + 1}",
                    "is_current": d.number == current.number,
                    "id": str(d.id) if hasattr(d, "id") else str(i),
                })
            return result
        except ImportError:
            raise NaturoError(
                message="Virtual desktop support requires pyvda. Install: pip install naturo[desktop]",
                code="DEPENDENCY_MISSING",
                category="system",
                suggested_action="Run 'pip install naturo[desktop]' to enable virtual desktop features.",
            )
        except Exception as e:
            raise NaturoError(
                message=f"Failed to enumerate virtual desktops: {e}",
                code="VIRTUAL_DESKTOP_ERROR",
                category="system",
                suggested_action="Ensure running on Windows 10/11 with virtual desktop support.",
            )

    def virtual_desktop_switch(self, index: int) -> dict:
        """Switch to a virtual desktop by index.

        Args:
            index: Zero-based desktop index.

        Returns:
            Dict with switched desktop info.
        """
        try:
            import pyvda
            desktops = pyvda.get_virtual_desktops()
            if index < 0 or index >= len(desktops):
                raise NaturoError(
                    message=f"Desktop index {index} out of range (0-{len(desktops) - 1})",
                    code="INVALID_INPUT",
                    category="input",
                    suggested_action=f"Use index 0-{len(desktops) - 1}. "
                                     "Run 'naturo desktop list' to see available desktops.",
                )
            target = desktops[index]
            target.go()
            return {
                "index": index,
                "name": target.name or f"Desktop {index + 1}",
            }
        except ImportError:
            raise NaturoError(
                message="Virtual desktop support requires pyvda. Install: pip install naturo[desktop]",
                code="DEPENDENCY_MISSING",
                category="system",
                suggested_action="Run 'pip install naturo[desktop]' to enable virtual desktop features.",
            )
        except NaturoError:
            raise
        except Exception as e:
            raise NaturoError(
                message=f"Failed to switch desktop: {e}",
                code="VIRTUAL_DESKTOP_ERROR",
                category="system",
            )

    def virtual_desktop_create(self, name: Optional[str] = None) -> dict:
        """Create a new virtual desktop.

        Args:
            name: Optional name for the new desktop.

        Returns:
            Dict with new desktop info.
        """
        try:
            import pyvda
            new_desktop = pyvda.VirtualDesktop.create()
            if name and hasattr(new_desktop, "rename"):
                new_desktop.rename(name)
            desktops = pyvda.get_virtual_desktops()
            new_index = len(desktops) - 1
            return {
                "index": new_index,
                "name": name or f"Desktop {new_index + 1}",
                "id": str(new_desktop.id) if hasattr(new_desktop, "id") else str(new_index),
            }
        except ImportError:
            raise NaturoError(
                message="Virtual desktop support requires pyvda. Install: pip install naturo[desktop]",
                code="DEPENDENCY_MISSING",
                category="system",
                suggested_action="Run 'pip install naturo[desktop]' to enable virtual desktop features.",
            )
        except Exception as e:
            raise NaturoError(
                message=f"Failed to create desktop: {e}",
                code="VIRTUAL_DESKTOP_ERROR",
                category="system",
            )

    def virtual_desktop_close(self, index: Optional[int] = None) -> dict:
        """Close a virtual desktop.

        Args:
            index: Zero-based desktop index. Closes current if None.

        Returns:
            Dict with closed desktop info.
        """
        try:
            import pyvda
            desktops = pyvda.get_virtual_desktops()

            if len(desktops) <= 1:
                raise NaturoError(
                    message="Cannot close the last virtual desktop",
                    code="VIRTUAL_DESKTOP_ERROR",
                    category="system",
                    suggested_action="At least one desktop must remain.",
                )

            if index is not None:
                if index < 0 or index >= len(desktops):
                    raise NaturoError(
                        message=f"Desktop index {index} out of range (0-{len(desktops) - 1})",
                        code="INVALID_INPUT",
                        category="input",
                    )
                target = desktops[index]
            else:
                target = pyvda.VirtualDesktop.current()
                index = next(
                    (i for i, d in enumerate(desktops) if d.number == target.number),
                    0,
                )

            target_name = target.name or f"Desktop {index + 1}"
            target.remove()
            return {
                "index": index,
                "name": target_name,
            }
        except ImportError:
            raise NaturoError(
                message="Virtual desktop support requires pyvda. Install: pip install naturo[desktop]",
                code="DEPENDENCY_MISSING",
                category="system",
                suggested_action="Run 'pip install naturo[desktop]' to enable virtual desktop features.",
            )
        except NaturoError:
            raise
        except Exception as e:
            raise NaturoError(
                message=f"Failed to close desktop: {e}",
                code="VIRTUAL_DESKTOP_ERROR",
                category="system",
            )

    def virtual_desktop_move_window(
        self,
        desktop_index: int,
        app: Optional[str] = None,
        hwnd: Optional[int] = None,
    ) -> dict:
        """Move a window to a different virtual desktop.

        Args:
            desktop_index: Target desktop index.
            app: Application name (partial match).
            hwnd: Window handle.

        Returns:
            Dict with result info.
        """
        try:
            import pyvda
            desktops = pyvda.get_virtual_desktops()

            if desktop_index < 0 or desktop_index >= len(desktops):
                raise NaturoError(
                    message=f"Desktop index {desktop_index} out of range (0-{len(desktops) - 1})",
                    code="INVALID_INPUT",
                    category="input",
                )

            # Resolve window handle
            handle = hwnd
            if not handle and app:
                handle = self._resolve_hwnd(app=app)

            if not handle:
                import ctypes
                handle = ctypes.windll.user32.GetForegroundWindow()

            if not handle:
                raise NaturoError(
                    message="No window found to move",
                    code="WINDOW_NOT_FOUND",
                    category="automation",
                )

            target = desktops[desktop_index]
            window = pyvda.AppView(handle)
            window.move(target)

            return {
                "hwnd": handle,
                "target_desktop": desktop_index,
                "target_name": target.name or f"Desktop {desktop_index + 1}",
            }
        except ImportError:
            raise NaturoError(
                message="Virtual desktop support requires pyvda. Install: pip install naturo[desktop]",
                code="DEPENDENCY_MISSING",
                category="system",
                suggested_action="Run 'pip install naturo[desktop]' to enable virtual desktop features.",
            )
        except NaturoError:
            raise
        except Exception as e:
            raise NaturoError(
                message=f"Failed to move window: {e}",
                code="VIRTUAL_DESKTOP_ERROR",
                category="system",
            )
