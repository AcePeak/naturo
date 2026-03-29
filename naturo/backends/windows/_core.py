"""Core infrastructure: DPI awareness, coordinate conversion, NaturoCore init."""

from __future__ import annotations

import logging
from typing import Optional

from naturo.bridge import NaturoCore

logger = logging.getLogger(__name__)


class CoreMixin:
    """Core infrastructure: DPI awareness, coordinate conversion, NaturoCore init."""

    def __init__(self) -> None:
        self._core: Optional[NaturoCore] = None
        self._initialized: bool = False
        self._dpi_aware: bool = False
        self._ensure_dpi_awareness()

    def _ensure_dpi_awareness(self) -> None:
        """Set per-monitor DPI awareness for accurate coordinates and capture.

        Strategy (BUG-073):
        1. First, try ``SetThreadDpiAwarenessContext`` (Win10 1607+) which
           always succeeds regardless of process-level manifest or prior
           ``SetProcessDpiAwareness`` calls.  This is the recommended
           approach because Python.exe may ship with a DPI manifest that
           blocks process-level changes.
        2. As fallback, try process-level APIs for older Windows versions.

        The thread-level context is inherited by child threads, so setting
        it once on the main thread covers all subsequent Win32 calls.
        """
        if self._dpi_aware:
            return
        try:
            import ctypes

            user32 = ctypes.windll.user32

            # ── Thread-level DPI (Win10 1607+) — preferred ──
            # DPI_AWARENESS_CONTEXT_PER_MONITOR_AWARE_V2 = -4
            # SetThreadDpiAwarenessContext returns the old context on
            # success, or NULL (0) on failure.
            try:
                _set_thread = user32.SetThreadDpiAwarenessContext
                _set_thread.restype = ctypes.c_void_p
                _set_thread.argtypes = [ctypes.c_void_p]
                old_ctx = _set_thread(-4)
                if old_ctx:
                    self._dpi_aware = True
                    logger.debug(
                        "DPI: SetThreadDpiAwarenessContext(-4) succeeded "
                        "(previous context=%s)",
                        old_ctx,
                    )
                    return
            except (OSError, AttributeError):
                pass

            # ── Process-level fallbacks ──

            # Per-Monitor v2 process-level (may fail if already set)
            try:
                user32.SetProcessDpiAwarenessContext(-4)
                self._dpi_aware = True
                return
            except (OSError, AttributeError):
                pass

            # Per-Monitor v1 (Win8.1+)
            try:
                ctypes.windll.shcore.SetProcessDpiAwareness(2)
                self._dpi_aware = True
                return
            except (OSError, AttributeError):
                pass

            # System DPI aware (Vista+)
            try:
                user32.SetProcessDPIAware()
                self._dpi_aware = True
            except (OSError, AttributeError):
                pass
        except Exception:
            pass  # Non-Windows or no ctypes — skip silently

    def get_dpi_scale(self, screen_index: int = 0) -> float:
        """Get the DPI scale factor for a specific monitor.

        Args:
            screen_index: Zero-based monitor index (0 = primary).

        Returns:
            Scale factor (1.0 = 100%, 1.5 = 150%, 2.0 = 200%).
            Returns 1.0 if monitor not found or API unavailable.
        """
        try:
            monitors = self.list_monitors()
            if 0 <= screen_index < len(monitors):
                return monitors[screen_index].scale_factor
        except Exception:
            pass
        return 1.0

    def physical_to_logical(self, x: int, y: int, screen_index: int = 0) -> tuple[int, int]:
        """Convert physical (pixel) coordinates to logical (DPI-scaled) coordinates.

        Args:
            x: Physical X coordinate.
            y: Physical Y coordinate.
            screen_index: Monitor index for scale factor lookup.

        Returns:
            Tuple of (logical_x, logical_y).
        """
        scale = self.get_dpi_scale(screen_index)
        if scale <= 0 or scale == 1.0:
            return x, y
        return int(x / scale), int(y / scale)

    def logical_to_physical(self, x: int, y: int, screen_index: int = 0) -> tuple[int, int]:
        """Convert logical (DPI-scaled) coordinates to physical (pixel) coordinates.

        Args:
            x: Logical X coordinate.
            y: Logical Y coordinate.
            screen_index: Monitor index for scale factor lookup.

        Returns:
            Tuple of (physical_x, physical_y).
        """
        scale = self.get_dpi_scale(screen_index)
        if scale <= 0 or scale == 1.0:
            return x, y
        return int(x * scale), int(y * scale)

    def _fixup_element_coords(self, root, handle: int):
        """Fix UIA coordinate mismatch on UWP apps with high-DPI displays.

        On 4K displays with DPI scaling, UWP apps hosted by
        ApplicationFrameHost can return element coordinates with a large
        negative offset (e.g. -31991 instead of 777). This happens because
        UIA returns coordinates in a different DPI context than the calling
        thread's Per-Monitor v2 context.

        Detection: root element has zero bounds (0,0,0,0) while children
        have large negative x/y (more than 10000 pixels below zero).

        Fix: get the actual window position via GetWindowRect and compute
        the offset between where elements are and where they should be.

        Args:
            root: Root ElementInfo from the C++ DLL.
            handle: Window handle (HWND).

        Returns:
            The root element, possibly with corrected coordinates.
        """
        # Only trigger when root has zero bounds but children exist
        root_zero = (root.x == 0 and root.y == 0
                     and root.width == 0 and root.height == 0)
        if not root_zero or not root.children:
            return root

        # Check if children have large negative coordinates
        first_child = root.children[0]
        if first_child.x >= -1000 and first_child.y >= -1000:
            return root  # Coordinates look normal, no fixup needed

        # Get actual window rect via Win32 API
        try:
            win_left, win_top, win_right, win_bottom = self._get_window_rect(handle)
        except Exception:
            return root  # Can't get window rect — skip fixup

        win_w = win_right - win_left
        win_h = win_bottom - win_top
        if win_w <= 0 or win_h <= 0:
            return root  # Minimized or invalid — skip

        # Fix root element bounds from the actual window rect
        root.x = win_left
        root.y = win_top
        root.width = win_w
        root.height = win_h

        # Compute the offset: find the first child with reasonable dimensions
        # and check if its coordinates need correction.
        # Strategy: try common offsets (multiples of 32768 from 16-bit wrap,
        # or the direct difference between expected and actual position).
        child_x = first_child.x
        child_y = first_child.y

        # Try 32768 increments (16-bit signed wrap)
        best_offset_x, best_offset_y = 0, 0
        for multiple in range(1, 4):
            candidate_x = child_x + 32768 * multiple
            candidate_y = child_y + 32768 * multiple
            # Check if corrected position falls within or near the window
            if (win_left - 200 <= candidate_x <= win_right + 200
                    and win_top - 200 <= candidate_y <= win_bottom + 200):
                best_offset_x = 32768 * multiple
                best_offset_y = 32768 * multiple
                break

        if best_offset_x == 0 and best_offset_y == 0:
            # No 32768-multiple worked — try direct offset from window position
            # The child's dimensions should roughly match the window, so use
            # the window position as the expected top-left
            if (abs(first_child.width - win_w) < win_w * 0.3
                    and abs(first_child.height - win_h) < win_h * 0.3):
                best_offset_x = win_left - child_x
                best_offset_y = win_top - child_y

        if best_offset_x == 0 and best_offset_y == 0:
            return root  # Can't determine correction — leave as-is

        logger.info(
            "DPI coordinate fixup (#613): applying offset (%+d, %+d) to %d "
            "elements (window at %d,%d %dx%d)",
            best_offset_x, best_offset_y,
            sum(1 for _ in self._iter_elements(root)),
            win_left, win_top, win_w, win_h,
        )

        # Apply offset to all elements in the tree (except root, already fixed)
        for el in self._iter_elements(root):
            if el is not root:
                el.x += best_offset_x
                el.y += best_offset_y

        return root

    @staticmethod
    def _iter_elements(root):
        """Yield all elements in the tree via depth-first traversal."""
        stack = [root]
        while stack:
            el = stack.pop()
            yield el
            stack.extend(reversed(el.children))

    def _ensure_core(self) -> NaturoCore:
        """Lazily load and initialize the native core library.

        Returns:
            The initialized NaturoCore instance.

        Raises:
            NaturoCoreError: If initialization fails.
        """
        if self._core is None:
            self._core = NaturoCore()
        if not self._initialized:
            self._core.init()
            self._initialized = True
        return self._core

    @property
    def platform_name(self) -> str:
        """Return platform identifier."""
        return "windows"

    @property
    def capabilities(self) -> dict:
        """Return backend capabilities and platform-specific features."""
        return {
            "platform": "windows",
            "input_modes": ["normal", "hardware", "hook"],
            "accessibility": ["uia", "msaa", "ia2", "jab"],
            "extensions": ["excel", "java", "sap", "registry", "service"],
        }
