"""Bridge to naturo_core native library via ctypes.

Provides a Pythonic interface to the C++ core DLL, handling type
conversions, JSON parsing, and error code translation.
"""

from __future__ import annotations

import ctypes
import json
import os
import platform
import re
import sys
from dataclasses import dataclass, field
from pathlib import Path
from typing import Optional


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


# ── Win32 HWND Enumeration Fallback (Issue #308) ──

# Win32 class name → UIA-style role mapping for VB6/ActiveX controls
_WIN32_CLASS_ROLE_MAP = {
    "Static": "Text",
    "Edit": "Edit",
    "Button": "Button",
    "ComboBox": "ComboBox",
    "ComboBoxEx32": "ComboBox",
    "ListBox": "List",
    "SysListView32": "DataGrid",
    "SysTreeView32": "Tree",
    "msctls_statusbar32": "StatusBar",
    "ThunderRT6FormDC": "Window",
    "ThunderRT6UserControlDC": "Pane",
    "ThunderRT6PictureBoxDC": "Pane",
    "ThunderRT6TextBox": "Edit",
    "ThunderRT6CommandButton": "Button",
    "ThunderRT6ComboBox": "ComboBox",
    "ThunderRT6ListBox": "List",
    "ThunderRT6Frame": "Group",
    "ThunderRT6OptionButton": "RadioButton",
    "ThunderRT6CheckBox": "CheckBox",
}


def _get_role_from_class_name(cls_name: str, is_top_level: bool = False) -> str:
    """Map Win32 class name to UIA-style role.

    Handles WindowsForms dynamic class names (e.g., WindowsForms10.EDIT.app.0.xxx).

    Args:
        cls_name: Win32 class name from GetClassName
        is_top_level: If True, default to "Window" instead of "Pane"

    Returns:
        UIA role string (Button, Edit, Text, etc.)
    """
    # Direct match (e.g., "Button", "ThunderRT6CommandButton")
    role = _WIN32_CLASS_ROLE_MAP.get(cls_name)
    if role:
        return role

    # WindowsForms class name pattern: WindowsForms10.{TYPE}.app.{version}.{hash}
    # Examples:
    #   WindowsForms10.STATIC.app.0.xxx → TYPE=STATIC → Text
    #   WindowsForms10.EDIT.app.0.xxx → TYPE=EDIT → Edit
    #   WindowsForms10.Window.8.app.0.xxx → TYPE=Window → Pane (generic container)
    if cls_name.startswith("WindowsForms10."):
        parts = cls_name.split(".")
        if len(parts) >= 3:
            inner_type = parts[1]  # e.g., "EDIT", "STATIC", "Window", "SysTreeView32"
            # Try exact match first (handles "SysTreeView32" embedded in WindowsForms)
            role = _WIN32_CLASS_ROLE_MAP.get(inner_type)
            if role:
                return role
            # Fallback: uppercase TYPE might be uppercase version of base class
            # (STATIC → Static, EDIT → Edit)
            if inner_type.isupper():
                role = _WIN32_CLASS_ROLE_MAP.get(inner_type.capitalize())
                if role:
                    return role

    return "Window" if is_top_level else "Pane"


def highlight_elements(hwnd: int, depth: int = 10, duration: float = 5.0,
                       refs: Optional[list] = None) -> None:
    """Draw colored borders and labels on Win32 child windows for visual identification.

    Uses Win32 GDI to draw directly on screen. Each element gets a colored
    rectangle border with its ref (eN) and name/class label.

    Args:
        hwnd: Parent window handle.
        depth: Max depth for enumeration.
        duration: How long to show highlights (seconds).
        refs: Optional list of specific refs to highlight (e.g. ['e5', 'e10']).
              If None, highlights all elements.
    """
    import ctypes
    from ctypes import wintypes
    import platform
    import time
    import threading

    if platform.system() != "Windows":
        return

    user32 = ctypes.windll.user32
    gdi32 = ctypes.windll.gdi32

    # Collect all child windows with their info
    def _get_direct_children(parent):
        children = []
        child = user32.FindWindowExW(parent, None, None, None)
        while child:
            children.append(child)
            child = user32.FindWindowExW(parent, child, None, None)
        return children

    elements = []  # list of (ref, hwnd, title, class_name, rect)
    counter = [1]

    def _collect(h, current_depth):
        if current_depth > depth:
            return
        for child_hwnd in _get_direct_children(h):
            ref = f"e{counter[0]}"
            counter[0] += 1

            title_buf = ctypes.create_unicode_buffer(256)
            user32.GetWindowTextW(child_hwnd, title_buf, 256)
            title = title_buf.value or ""

            cls_buf = ctypes.create_unicode_buffer(256)
            user32.GetClassNameW(child_hwnd, cls_buf, 256)
            cls_name = cls_buf.value or ""

            rect = wintypes.RECT()
            user32.GetWindowRect(child_hwnd, ctypes.byref(rect))

            # Skip invisible/zero-size windows
            w = rect.right - rect.left
            h_size = rect.bottom - rect.top
            if w <= 0 or h_size <= 0:
                continue
            # Skip off-screen windows
            if rect.left < -10000 or rect.top < -10000:
                continue

            if refs is None or ref in refs:
                # Build display label
                short_cls = cls_name.split(".")[-1] if "." in cls_name else cls_name
                label = title if title else short_cls
                if len(label) > 20:
                    label = label[:18] + ".."
                elements.append((ref, child_hwnd, label, cls_name, rect))

            _collect(child_hwnd, current_depth + 1)

    _collect(hwnd, 0)

    if not elements:
        return

    # Colors for cycling (RGB)
    COLORS = [
        0x0000FF,  # Red
        0x00FF00,  # Green
        0xFF0000,  # Blue
        0x00FFFF,  # Yellow
        0xFF00FF,  # Magenta
        0xFFFF00,  # Cyan
    ]

    # Get screen DC
    hdc = user32.GetDC(None)

    # Create font for labels
    font = gdi32.CreateFontW(
        14, 0, 0, 0, 700,  # height, width, escapement, orientation, weight (bold)
        0, 0, 0,  # italic, underline, strikeout
        0, 0, 0, 0, 0,  # charset, precision, clip, quality, pitch
        "Consolas"
    )

    try:
        # Flash 3 times
        for flash in range(3):
            # Draw borders and labels
            for i, (ref, child_hwnd, label, cls_name, rect) in enumerate(elements):
                color = COLORS[i % len(COLORS)]
                pen = gdi32.CreatePen(0, 2, color)  # PS_SOLID, width=2
                old_pen = gdi32.SelectObject(hdc, pen)
                old_brush = gdi32.SelectObject(hdc, gdi32.GetStockObject(5))  # NULL_BRUSH

                # Draw rectangle
                gdi32.Rectangle(hdc, rect.left, rect.top, rect.right, rect.bottom)

                # Draw label background
                gdi32.SelectObject(hdc, old_brush)
                label_text = f" {ref}: {label} "

                # Set text properties
                gdi32.SetBkColor(hdc, color)
                gdi32.SetTextColor(hdc, 0xFFFFFF)  # White text
                old_font = gdi32.SelectObject(hdc, font)

                # Draw label at top-left of element
                text_bytes = label_text.encode("utf-16-le") + b"\x00\x00"
                text_buf = ctypes.create_unicode_buffer(label_text)
                gdi32.TextOutW(hdc, rect.left + 1, rect.top + 1, text_buf, len(label_text))

                gdi32.SelectObject(hdc, old_font)
                gdi32.SelectObject(hdc, old_pen)
                gdi32.DeleteObject(pen)

            time.sleep(0.8)

            # Force redraw to clear (invalidate screen regions)
            for _, child_hwnd, _, _, rect in elements:
                r = wintypes.RECT(rect.left - 3, rect.top - 3,
                                  rect.right + 3, rect.bottom + 3)
                user32.InvalidateRect(None, ctypes.byref(r), True)
            user32.UpdateWindow(user32.GetDesktopWindow())

            time.sleep(0.4)

    finally:
        gdi32.DeleteObject(font)
        user32.ReleaseDC(None, hdc)
        # Final cleanup: redraw everything
        user32.InvalidateRect(None, None, True)


def enumerate_child_windows(hwnd: int, depth: int = 10) -> Optional[ElementInfo]:
    """Enumerate child windows using Win32 FindWindowEx as UIA fallback.

    For VB6/ActiveX applications (e.g., 用友U8 ERP) where UIA/MSAA see
    controls as opaque Pane containers, this function walks the Win32 HWND
    tree directly and constructs an ElementInfo tree from GetClassName,
    GetWindowText, and GetWindowRect.

    Uses FindWindowEx (not EnumChildWindows) to enumerate only DIRECT
    children at each level, then recurses. EnumChildWindows returns ALL
    descendants which causes exponential duplication when recursing.

    Args:
        hwnd: Parent window handle. 0 for the foreground window.
        depth: Maximum recursion depth. Default 10.

    Returns:
        Root ElementInfo with children, or None if enumeration fails.
    """
    import ctypes
    from ctypes import wintypes
    import platform

    if platform.system() != "Windows":
        return None

    if depth < 1:
        depth = 1

    user32 = ctypes.windll.user32

    # Resolve foreground window if hwnd is 0
    if hwnd == 0:
        hwnd = user32.GetForegroundWindow()
        if not hwnd:
            return None

    def _get_window_info(h):
        """Get title, class name, and rect for a window handle."""
        title_buf = ctypes.create_unicode_buffer(256)
        user32.GetWindowTextW(h, title_buf, 256)
        cls_buf = ctypes.create_unicode_buffer(256)
        user32.GetClassNameW(h, cls_buf, 256)
        rect = wintypes.RECT()
        user32.GetWindowRect(h, ctypes.byref(rect))
        return title_buf.value or "", cls_buf.value or "", rect

    def _get_direct_children(parent_hwnd):
        """Get only DIRECT child HWNDs using FindWindowEx."""
        children = []
        child = user32.FindWindowExW(parent_hwnd, None, None, None)
        while child:
            children.append(child)
            child = user32.FindWindowExW(parent_hwnd, child, None, None)
        return children

    # Counter for sequential IDs
    counter = [0]

    def _build_tree(h, current_depth):
        """Recursively build ElementInfo tree from HWND hierarchy."""
        title, cls_name, rect = _get_window_info(h)
        is_top_level = (current_depth == 0)
        role = _get_role_from_class_name(cls_name, is_top_level=is_top_level)

        # Include class name in display for debugging and identification
        display_name = title
        if cls_name and cls_name not in (title, ""):
            display_name = f"{title} [{cls_name}]" if title else f"[{cls_name}]"

        elem = ElementInfo(
            id=f"e{counter[0]}",
            role=role,
            name=display_name,
            value=None,
            x=rect.left,
            y=rect.top,
            width=rect.right - rect.left,
            height=rect.bottom - rect.top,
            children=[],
            hwnd=h,
        )
        counter[0] += 1

        # Recurse into direct children
        if current_depth < depth:
            for child_hwnd in _get_direct_children(h):
                child_elem = _build_tree(child_hwnd, current_depth + 1)
                if child_elem:
                    elem.children.append(child_elem)

        return elem

    root = _build_tree(hwnd, 0)

    # Populate parent IDs
    populate_hierarchy(root)

    return root


class NaturoCoreError(Exception):
    """Error raised when a naturo_core function fails.

    Attributes:
        code: The native error code returned by the C function.
    """

    ERROR_MESSAGES = {
        -1: "Invalid argument",
        -2: "System/COM error",
        -3: "File I/O error",
        -4: "Buffer too small",
    }

    def __init__(self, code: int, context: str = ""):
        self.code = code
        msg = self.ERROR_MESSAGES.get(code, f"Unknown error ({code})")
        if context:
            msg = f"{context}: {msg}"
        super().__init__(msg)


class NaturoCore:
    """Wrapper around naturo_core.dll/.so native library.

    Provides Python methods for all exported C functions, handling ctypes
    setup, buffer management, and JSON parsing.

    Args:
        lib_path: Explicit path to the native library. If None, searches
            standard locations (env var, package bin/, cwd, system PATH).
    """

    def __init__(self, lib_path: str | None = None):
        self._lib = self._load(lib_path)
        self._setup_signatures()

    def _bind(self, name: str, restype, argtypes) -> None:
        """Bind a single DLL function, skip silently if not exported."""
        try:
            fn = getattr(self._lib, name)
            fn.restype = restype
            fn.argtypes = argtypes
        except AttributeError:
            pass  # Function not in this DLL version — will raise at call time

    def _setup_signatures(self) -> None:
        """Configure ctypes function signatures for all exported functions."""
        # Version
        self._lib.naturo_version.restype = ctypes.c_char_p
        self._lib.naturo_version.argtypes = []

        # Lifecycle
        self._lib.naturo_init.restype = ctypes.c_int
        self._lib.naturo_init.argtypes = []
        self._lib.naturo_shutdown.restype = ctypes.c_int
        self._lib.naturo_shutdown.argtypes = []

        # Screen capture
        self._lib.naturo_capture_screen.restype = ctypes.c_int
        self._lib.naturo_capture_screen.argtypes = [ctypes.c_int, ctypes.c_char_p]

        # Window capture
        self._lib.naturo_capture_window.restype = ctypes.c_int
        self._lib.naturo_capture_window.argtypes = [ctypes.c_size_t, ctypes.c_char_p]

        # Window listing
        self._lib.naturo_list_windows.restype = ctypes.c_int
        self._lib.naturo_list_windows.argtypes = [ctypes.c_char_p, ctypes.c_int]

        # Window info
        self._lib.naturo_get_window_info.restype = ctypes.c_int
        self._lib.naturo_get_window_info.argtypes = [ctypes.c_size_t, ctypes.c_char_p, ctypes.c_int]

        # Element tree
        self._lib.naturo_get_element_tree.restype = ctypes.c_int
        self._lib.naturo_get_element_tree.argtypes = [
            ctypes.c_size_t, ctypes.c_int, ctypes.c_char_p, ctypes.c_int
        ]

        # Find element
        self._lib.naturo_find_element.restype = ctypes.c_int
        self._lib.naturo_find_element.argtypes = [
            ctypes.c_size_t, ctypes.c_char_p, ctypes.c_char_p,
            ctypes.c_char_p, ctypes.c_int
        ]

        # Phase 2 — Mouse input
        self._lib.naturo_mouse_move.restype = ctypes.c_int
        self._lib.naturo_mouse_move.argtypes = [ctypes.c_int, ctypes.c_int]

        self._lib.naturo_mouse_click.restype = ctypes.c_int
        self._lib.naturo_mouse_click.argtypes = [ctypes.c_int, ctypes.c_int]

        self._bind("naturo_mouse_down", ctypes.c_int, [ctypes.c_int])
        self._bind("naturo_mouse_up", ctypes.c_int, [ctypes.c_int])

        self._lib.naturo_mouse_scroll.restype = ctypes.c_int
        self._lib.naturo_mouse_scroll.argtypes = [ctypes.c_int, ctypes.c_int]

        # Phase 2 — Keyboard input
        self._lib.naturo_key_type.restype = ctypes.c_int
        self._lib.naturo_key_type.argtypes = [ctypes.c_char_p, ctypes.c_int]

        self._lib.naturo_key_press.restype = ctypes.c_int
        self._lib.naturo_key_press.argtypes = [ctypes.c_char_p]

        self._lib.naturo_key_hotkey.restype = ctypes.c_int
        self._lib.naturo_key_hotkey.argtypes = [ctypes.c_int, ctypes.c_char_p]

        # Phase 5B — MSAA / IAccessible
        self._lib.naturo_msaa_get_element_tree.restype = ctypes.c_int
        self._lib.naturo_msaa_get_element_tree.argtypes = [
            ctypes.c_size_t, ctypes.c_int, ctypes.c_char_p, ctypes.c_int
        ]

        self._lib.naturo_msaa_find_element.restype = ctypes.c_int
        self._lib.naturo_msaa_find_element.argtypes = [
            ctypes.c_size_t, ctypes.c_char_p, ctypes.c_char_p,
            ctypes.c_char_p, ctypes.c_int
        ]

        # Phase 5B.2 — IAccessible2
        self._lib.naturo_ia2_get_element_tree.restype = ctypes.c_int
        self._lib.naturo_ia2_get_element_tree.argtypes = [
            ctypes.c_size_t, ctypes.c_int, ctypes.c_char_p, ctypes.c_int
        ]

        self._lib.naturo_ia2_find_element.restype = ctypes.c_int
        self._lib.naturo_ia2_find_element.argtypes = [
            ctypes.c_size_t, ctypes.c_char_p, ctypes.c_char_p,
            ctypes.c_char_p, ctypes.c_int
        ]

        self._lib.naturo_ia2_check_support.restype = ctypes.c_int
        self._lib.naturo_ia2_check_support.argtypes = [ctypes.c_size_t]

        # JAB (Java Access Bridge)
        self._lib.naturo_jab_get_element_tree.restype = ctypes.c_int
        self._lib.naturo_jab_get_element_tree.argtypes = [
            ctypes.c_size_t, ctypes.c_int, ctypes.c_char_p, ctypes.c_int
        ]

        self._lib.naturo_jab_find_element.restype = ctypes.c_int
        self._lib.naturo_jab_find_element.argtypes = [
            ctypes.c_size_t, ctypes.c_char_p, ctypes.c_char_p,
            ctypes.c_char_p, ctypes.c_int
        ]

        self._lib.naturo_jab_check_support.restype = ctypes.c_int
        self._lib.naturo_jab_check_support.argtypes = [ctypes.c_size_t]

        # Element value reading (may be absent in older DLL builds)
        try:
            self._lib.naturo_get_element_value.restype = ctypes.c_int
            self._lib.naturo_get_element_value.argtypes = [
                ctypes.c_size_t, ctypes.c_char_p, ctypes.c_char_p,
                ctypes.c_char_p, ctypes.c_char_p, ctypes.c_int
            ]
        except AttributeError:
            pass  # DLL lacks this export; get_element_value() will raise

        # Phase 5B.5 — Hardware-level keyboard (Phys32)
        self._lib.naturo_phys_key_type.restype = ctypes.c_int
        self._lib.naturo_phys_key_type.argtypes = [ctypes.c_char_p, ctypes.c_int]

        self._lib.naturo_phys_key_press.restype = ctypes.c_int
        self._lib.naturo_phys_key_press.argtypes = [ctypes.c_char_p]

        self._lib.naturo_phys_key_hotkey.restype = ctypes.c_int
        self._lib.naturo_phys_key_hotkey.argtypes = [ctypes.c_int, ctypes.c_char_p]

    def _load(self, lib_path: str | None) -> ctypes.CDLL:
        """Load the native library from the given path or search standard locations.

        Args:
            lib_path: Explicit path, or None to search.

        Returns:
            Loaded ctypes.CDLL instance.

        Raises:
            FileNotFoundError: If the library cannot be found.
        """
        if lib_path:
            return ctypes.CDLL(lib_path)

        # Search order:
        # 1. NATURO_CORE_PATH env var
        # 2. Package bin/ directory (bundled in wheel)
        # 3. Current directory
        # 4. System PATH

        env_path = os.environ.get("NATURO_CORE_PATH")
        if env_path and os.path.exists(env_path):
            return ctypes.CDLL(env_path)

        system = platform.system()
        if system == "Windows":
            lib_name = "naturo_core.dll"
        elif system == "Linux":
            lib_name = "libnaturo_core.so"
        elif system == "Darwin":
            lib_name = "libnaturo_core.dylib"
        else:
            raise OSError(f"Unsupported platform: {system}")

        # Check package bin/ directory
        pkg_dir = Path(__file__).parent / "bin"
        pkg_lib = pkg_dir / lib_name
        if pkg_lib.exists():
            return ctypes.CDLL(str(pkg_lib))

        # Check current directory
        cwd_lib = Path.cwd() / lib_name
        if cwd_lib.exists():
            return ctypes.CDLL(str(cwd_lib))

        # Fall back to system search
        try:
            return ctypes.CDLL(lib_name)
        except OSError:
            from naturo.errors import DependencyMissingError
            raise DependencyMissingError(
                dependency="naturo_core",
                message=(
                    f"Native library {lib_name} not found. "
                    f"This command requires the naturo_core native engine.\n"
                    f"Install the pre-built wheel: pip install naturo\n"
                    f"Or set NATURO_CORE_PATH to the library location.\n"
                    f"Searched: {env_path}, {pkg_lib}, {cwd_lib}, system PATH"
                ),
                suggested_action=(
                    "Install naturo with the native library: pip install naturo. "
                    "Commands that don't need the native engine (--help, --version, "
                    "chrome, electron, mcp, learn) will work without it."
                ),
            )

    def version(self) -> str:
        """Get the library version string.

        Returns:
            Version string (e.g., "0.1.0").
        """
        return _decode_native(self._lib.naturo_version())

    def init(self) -> int:
        """Initialize the native library.

        Returns:
            0 on success.

        Raises:
            NaturoCoreError: On initialization failure.
        """
        rc = self._lib.naturo_init()
        if rc != 0:
            raise NaturoCoreError(rc, "naturo_init")
        return rc

    def shutdown(self) -> int:
        """Shut down the native library.

        Returns:
            0 on success.
        """
        return self._lib.naturo_shutdown()

    def capture_screen(self, screen_index: int = 0, output_path: str = "capture.bmp") -> str:
        """Capture a screenshot of the entire screen or a specific monitor.

        Args:
            screen_index: Zero-based monitor index. 0 for primary screen.
            output_path: File path to save the screenshot (BMP format).

        Returns:
            The output file path.

        Raises:
            NaturoCoreError: On capture failure or invalid arguments.
        """
        if output_path is None:
            raise NaturoCoreError(-1, "capture_screen")
        rc = self._lib.naturo_capture_screen(
            screen_index, output_path.encode("utf-8")
        )
        if rc != 0:
            raise NaturoCoreError(rc, "capture_screen")
        return output_path

    def capture_window(self, hwnd: int = 0, output_path: str = "capture.bmp") -> str:
        """Capture a screenshot of a specific window.

        Args:
            hwnd: Window handle. Pass 0 to capture the foreground window.
            output_path: File path to save the screenshot (BMP format).

        Returns:
            The output file path.

        Raises:
            NaturoCoreError: On capture failure or invalid arguments.
        """
        if output_path is None:
            raise NaturoCoreError(-1, "capture_window")
        rc = self._lib.naturo_capture_window(
            hwnd, output_path.encode("utf-8")
        )
        if rc != 0:
            raise NaturoCoreError(rc, "capture_window")
        return output_path

    def list_windows(self) -> list[WindowInfo]:
        """List all visible top-level windows.

        Returns:
            List of WindowInfo objects.

        Raises:
            NaturoCoreError: On enumeration failure.
        """
        buf_size = 1 << 20  # 1 MB initial buffer
        buf = ctypes.create_string_buffer(buf_size)
        count = self._lib.naturo_list_windows(buf, buf_size)

        if count == -4:
            # Buffer too small — retry with larger buffer
            buf_size = 4 << 20  # 4 MB
            buf = ctypes.create_string_buffer(buf_size)
            count = self._lib.naturo_list_windows(buf, buf_size)

        if count < 0:
            raise NaturoCoreError(count, "list_windows")

        data = _safe_json_loads(_decode_native(buf.value))
        return [
            WindowInfo(
                hwnd=w["hwnd"],
                title=w["title"],
                process_name=w["process_name"],
                pid=w["pid"],
                x=w["x"],
                y=w["y"],
                width=w["width"],
                height=w["height"],
                is_visible=w["is_visible"],
                is_minimized=w["is_minimized"],
            )
            for w in data
        ]

    def get_window_info(self, hwnd: int) -> WindowInfo:
        """Get information about a specific window.

        Args:
            hwnd: Window handle.

        Returns:
            WindowInfo for the specified window.

        Raises:
            NaturoCoreError: If the window is not found or on error.
        """
        buf_size = 4096
        buf = ctypes.create_string_buffer(buf_size)
        rc = self._lib.naturo_get_window_info(hwnd, buf, buf_size)
        if rc != 0:
            raise NaturoCoreError(rc, "get_window_info")

        w = _safe_json_loads(_decode_native(buf.value))
        return WindowInfo(
            hwnd=w["hwnd"],
            title=w["title"],
            process_name=w["process_name"],
            pid=w["pid"],
            x=w["x"],
            y=w["y"],
            width=w["width"],
            height=w["height"],
            is_visible=w["is_visible"],
            is_minimized=w["is_minimized"],
        )

    def get_element_tree(self, hwnd: int = 0, depth: int = 3) -> Optional[ElementInfo]:
        """Inspect the UI element tree of a window.

        Args:
            hwnd: Window handle. 0 for the foreground window.
            depth: Maximum tree depth (1-10).

        Returns:
            Root ElementInfo with children, or None if no window found.

        Raises:
            NaturoCoreError: On UIAutomation or buffer error.
        """
        buf_size = 1 << 20  # 1 MB
        buf = ctypes.create_string_buffer(buf_size)
        count = self._lib.naturo_get_element_tree(hwnd, depth, buf, buf_size)

        if count == -4:
            buf_size = 8 << 20  # 8 MB retry
            buf = ctypes.create_string_buffer(buf_size)
            count = self._lib.naturo_get_element_tree(hwnd, depth, buf, buf_size)

        if count == -2:
            return None  # No foreground window or COM error
        if count < 0:
            raise NaturoCoreError(count, "get_element_tree")

        data = _safe_json_loads(_decode_native(buf.value))
        return _parse_element(data)

    def find_element(
        self, hwnd: int = 0, role: Optional[str] = None, name: Optional[str] = None
    ) -> Optional[ElementInfo]:
        """Find a UI element by role and/or name within a window.

        Args:
            hwnd: Window handle. 0 for the foreground window.
            role: Element role filter (e.g., "Button"). None for any.
            name: Element name filter. None for any.

        Returns:
            ElementInfo if found, None if not found.

        Raises:
            NaturoCoreError: On error (invalid args, COM failure, etc.).
        """
        buf_size = 4096
        buf = ctypes.create_string_buffer(buf_size)

        role_bytes = role.encode("utf-8") if role else None
        name_bytes = name.encode("utf-8") if name else None

        rc = self._lib.naturo_find_element(hwnd, role_bytes, name_bytes, buf, buf_size)

        if rc == 1:
            return None  # Not found
        if rc == -2:
            return None  # No foreground window
        if rc < 0:
            raise NaturoCoreError(rc, "find_element")

        data = _safe_json_loads(_decode_native(buf.value))
        return _parse_element(data)

    def get_element_value(
        self,
        hwnd: int = 0,
        automation_id: Optional[str] = None,
        role: Optional[str] = None,
        name: Optional[str] = None,
    ) -> Optional[dict]:
        """Read the current value of a UI element using UIA patterns.

        Queries ValuePattern, TogglePattern, SelectionPattern,
        RangeValuePattern, and TextPattern to retrieve the element's
        current value.

        Args:
            hwnd: Window handle. 0 for the foreground window.
            automation_id: AutomationId of the target element.
            role: Element role filter (used when automation_id is None).
            name: Element name filter (used when automation_id is None).

        Returns:
            Dict with keys: value, pattern, role, name, automation_id,
            x, y, width, height.  None if element not found.

        Raises:
            NaturoCoreError: On error (invalid args, COM failure, etc.).
        """
        buf_size = 4 * 1024 * 1024  # 4MB for large documents (e.g. Win11 Notepad TextPattern)
        buf = ctypes.create_string_buffer(buf_size)

        aid_bytes = automation_id.encode("utf-8") if automation_id else None
        role_bytes = role.encode("utf-8") if role else None
        name_bytes = name.encode("utf-8") if name else None

        try:
            fn = self._lib.naturo_get_element_value
        except AttributeError:
            raise NaturoCoreError(
                -1,
                "get_element_value: DLL does not export naturo_get_element_value "
                "(recompile the DLL with the latest source)",
            )

        rc = fn(hwnd, aid_bytes, role_bytes, name_bytes, buf, buf_size)

        if rc == 1:
            return None  # Not found
        if rc == -2:
            return None  # No foreground window / COM error
        if rc < 0:
            raise NaturoCoreError(rc, "get_element_value")

        return _safe_json_loads(_decode_native(buf.value))

    # ── Phase 2: Mouse Input ─────────────────────────

    def mouse_move(self, x: int, y: int) -> None:
        """Move the mouse cursor to absolute screen coordinates.

        Args:
            x: Target X coordinate (screen pixels, top-left origin).
            y: Target Y coordinate.

        Raises:
            NaturoCoreError: On system error.
        """
        rc = self._lib.naturo_mouse_move(x, y)
        if rc != 0:
            raise NaturoCoreError(rc, "mouse_move")

    def mouse_click(self, button: int = 0, double: bool = False) -> None:
        """Click the mouse at the current cursor position.

        Args:
            button: Mouse button (0=left, 1=right, 2=middle).
            double: True for double-click.

        Raises:
            NaturoCoreError: On invalid argument or system error.
        """
        rc = self._lib.naturo_mouse_click(button, 1 if double else 0)
        if rc != 0:
            raise NaturoCoreError(rc, "mouse_click")

    def mouse_down(self, button: int = 0) -> None:
        """Press a mouse button down without releasing.

        Used for drag operations where the button must remain held
        during cursor movement.

        Args:
            button: Mouse button: 0 = left, 1 = right, 2 = middle.

        Raises:
            NaturoCoreError: On invalid argument or system error.
        """
        rc = self._lib.naturo_mouse_down(button)
        if rc != 0:
            raise NaturoCoreError(rc, "mouse_down")

    def mouse_up(self, button: int = 0) -> None:
        """Release a mouse button.

        Used to complete drag operations by releasing the held button.

        Args:
            button: Mouse button: 0 = left, 1 = right, 2 = middle.

        Raises:
            NaturoCoreError: On invalid argument or system error.
        """
        rc = self._lib.naturo_mouse_up(button)
        if rc != 0:
            raise NaturoCoreError(rc, "mouse_up")

    def mouse_scroll(self, delta: int, horizontal: bool = False) -> None:
        """Scroll the mouse wheel.

        Args:
            delta: Scroll amount. Positive = up/forward, negative = down/backward.
                   One standard notch = 120 (Windows WHEEL_DELTA).
            horizontal: True for horizontal scroll.

        Raises:
            NaturoCoreError: On system error.
        """
        rc = self._lib.naturo_mouse_scroll(delta, 1 if horizontal else 0)
        if rc != 0:
            raise NaturoCoreError(rc, "mouse_scroll")

    # ── Phase 2: Keyboard Input ──────────────────────

    def key_type(self, text: str, delay_ms: int = 0) -> None:
        """Type a string using Unicode SendInput.

        Args:
            text: UTF-8 string to type.
            delay_ms: Delay between keystrokes in milliseconds.

        Raises:
            NaturoCoreError: On invalid argument or system error.
        """
        if text is None:
            raise NaturoCoreError(-1, "key_type")
        rc = self._lib.naturo_key_type(text.encode("utf-8"), delay_ms)
        if rc != 0:
            raise NaturoCoreError(rc, "key_type")

    def key_press(self, key_name: str) -> None:
        """Press and release a named key.

        Args:
            key_name: Key name (e.g., "enter", "tab", "f5", "escape").

        Raises:
            NaturoCoreError: If the key name is unknown or on system error.
        """
        if not key_name:
            raise NaturoCoreError(-1, "key_press")
        rc = self._lib.naturo_key_press(key_name.encode("utf-8"))
        if rc != 0:
            raise NaturoCoreError(rc, f"key_press({key_name!r})")

    def key_hotkey(self, *keys: str) -> None:
        """Press a hotkey combination.

        Args:
            *keys: Key names. Modifier keys (ctrl, alt, shift, win) are
                   detected automatically; one non-modifier key is the base key.

        Example:
            core.key_hotkey("ctrl", "a")   # Select All
            core.key_hotkey("ctrl", "shift", "z")  # Redo

        Raises:
            NaturoCoreError: On invalid argument or system error.
        """
        MODIFIER_MAP = {"ctrl": 0, "alt": 1, "shift": 2, "win": 3}
        modifiers = 0
        base_key: Optional[str] = None

        for k in keys:
            k_lower = k.lower()
            if k_lower in MODIFIER_MAP:
                modifiers |= (1 << MODIFIER_MAP[k_lower])
            else:
                if base_key is not None:
                    raise NaturoCoreError(-1, f"key_hotkey: multiple base keys ({base_key!r}, {k!r})")
                base_key = k_lower

        key_bytes = base_key.encode("utf-8") if base_key else None
        rc = self._lib.naturo_key_hotkey(modifiers, key_bytes)
        if rc != 0:
            raise NaturoCoreError(rc, f"key_hotkey({keys!r})")

    # ── Phase 5B.5: Hardware-level Keyboard (Phys32) ──

    def phys_key_type(self, text: str, delay_ms: int = 0) -> None:
        """Type text using hardware scan codes (Phys32 mode).

        Uses KEYEVENTF_SCANCODE to send raw PS/2 scan codes, which
        are harder for games and anti-cheat software to detect as
        synthetic input. Characters without keyboard mappings fall
        back to Unicode input transparently.

        Args:
            text: UTF-8 string to type.
            delay_ms: Delay between keystrokes in milliseconds.

        Raises:
            NaturoCoreError: On invalid argument or system error.
        """
        if not text:
            raise NaturoCoreError(-1, "phys_key_type")
        rc = self._lib.naturo_phys_key_type(text.encode("utf-8"), delay_ms)
        if rc != 0:
            raise NaturoCoreError(rc, "phys_key_type")

    def phys_key_press(self, key_name: str) -> None:
        """Press and release a key using hardware scan codes (Phys32 mode).

        Uses PS/2 Set 1 scan codes with KEYEVENTF_SCANCODE. Extended keys
        (arrows, home, end, etc.) include the E0 prefix automatically.

        Args:
            key_name: Key name (same set as key_press).

        Raises:
            NaturoCoreError: If key unrecognized or on system error.
        """
        if not key_name:
            raise NaturoCoreError(-1, "phys_key_press")
        rc = self._lib.naturo_phys_key_press(key_name.encode("utf-8"))
        if rc != 0:
            raise NaturoCoreError(rc, f"phys_key_press({key_name!r})")

    def phys_key_hotkey(self, *keys: str) -> None:
        """Press a hotkey combination using hardware scan codes (Phys32 mode).

        Uses KEYEVENTF_SCANCODE for all modifier and base key events.

        Args:
            *keys: Key names. Modifiers (ctrl, alt, shift, win) are detected
                   automatically; one non-modifier key is the base key.

        Example:
            core.phys_key_hotkey("ctrl", "a")   # Select All (hardware)
            core.phys_key_hotkey("ctrl", "c")   # Copy (hardware)

        Raises:
            NaturoCoreError: On invalid argument or system error.
        """
        MODIFIER_MAP = {"ctrl": 0, "alt": 1, "shift": 2, "win": 3}
        modifiers = 0
        base_key: Optional[str] = None

        for k in keys:
            k_lower = k.lower()
            if k_lower in MODIFIER_MAP:
                modifiers |= (1 << MODIFIER_MAP[k_lower])
            else:
                if base_key is not None:
                    raise NaturoCoreError(
                        -1, f"phys_key_hotkey: multiple base keys ({base_key!r}, {k!r})")
                base_key = k_lower

        key_bytes = base_key.encode("utf-8") if base_key else None
        rc = self._lib.naturo_phys_key_hotkey(modifiers, key_bytes)
        if rc != 0:
            raise NaturoCoreError(rc, f"phys_key_hotkey({keys!r})")

    # ── Phase 5B: MSAA / IAccessible ─────────────────

    def msaa_get_element_tree(self, hwnd: int = 0, depth: int = 3) -> Optional[ElementInfo]:
        """Inspect the MSAA (IAccessible) element tree of a window.

        Provides element inspection for legacy applications that lack
        UIAutomation support (MFC, VB6, Delphi, native Win32, etc.).

        Args:
            hwnd: Window handle. 0 for the foreground window.
            depth: Maximum tree depth (1-10).

        Returns:
            Root ElementInfo with children, or None if no window found.

        Raises:
            NaturoCoreError: On MSAA/COM or buffer error.
        """
        buf_size = 1 << 20  # 1 MB
        buf = ctypes.create_string_buffer(buf_size)
        count = self._lib.naturo_msaa_get_element_tree(hwnd, depth, buf, buf_size)

        if count == -4:
            buf_size = 8 << 20  # 8 MB retry
            buf = ctypes.create_string_buffer(buf_size)
            count = self._lib.naturo_msaa_get_element_tree(hwnd, depth, buf, buf_size)

        if count == -2:
            return None
        if count < 0:
            raise NaturoCoreError(count, "msaa_get_element_tree")

        data = _safe_json_loads(_decode_native(buf.value))
        return _parse_element(data)

    def msaa_find_element(
        self, hwnd: int = 0, role: Optional[str] = None, name: Optional[str] = None
    ) -> Optional[ElementInfo]:
        """Find an MSAA element by role and/or name within a window.

        Uses BFS traversal of the IAccessible tree. Role matching uses
        human-readable names (e.g., "Button", "Edit", "MenuItem").

        Args:
            hwnd: Window handle. 0 for the foreground window.
            role: Element role filter (case-insensitive). None for any.
            name: Element name filter (case-insensitive). None for any.

        Returns:
            ElementInfo if found, None if not found.

        Raises:
            NaturoCoreError: On error (invalid args, COM failure, etc.).
        """
        buf_size = 4096
        buf = ctypes.create_string_buffer(buf_size)

        role_bytes = role.encode("utf-8") if role else None
        name_bytes = name.encode("utf-8") if name else None

        rc = self._lib.naturo_msaa_find_element(hwnd, role_bytes, name_bytes, buf, buf_size)

        if rc == 1:
            return None
        if rc == -2:
            return None
        if rc < 0:
            raise NaturoCoreError(rc, "msaa_find_element")

        data = _safe_json_loads(_decode_native(buf.value))
        return _parse_element(data)

    # ── Phase 5B.2: IAccessible2 ─────────────────────

    def ia2_check_support(self, hwnd: int = 0) -> bool:
        """Check if a window supports IAccessible2.

        Args:
            hwnd: Window handle. 0 for the foreground window.

        Returns:
            True if the window's application implements IA2.
        """
        rc = self._lib.naturo_ia2_check_support(hwnd)
        return rc == 1

    def ia2_get_element_tree(self, hwnd: int = 0, depth: int = 3) -> Optional[ElementInfo]:
        """Inspect the IAccessible2 element tree of a window.

        Provides extended accessibility info for IA2-enabled applications
        (Firefox, Thunderbird, LibreOffice, etc.). Includes IA2-specific
        properties like object attributes, extended roles, and states.

        Args:
            hwnd: Window handle. 0 for the foreground window.
            depth: Maximum tree depth (1-10).

        Returns:
            Root ElementInfo with children, or None if no window found
            or IA2 not supported.

        Raises:
            NaturoCoreError: On COM or buffer error.
        """
        buf_size = 1 << 20  # 1 MB
        buf = ctypes.create_string_buffer(buf_size)
        count = self._lib.naturo_ia2_get_element_tree(hwnd, depth, buf, buf_size)

        if count == -4:
            buf_size = 8 << 20  # 8 MB retry
            buf = ctypes.create_string_buffer(buf_size)
            count = self._lib.naturo_ia2_get_element_tree(hwnd, depth, buf, buf_size)

        if count == -2:
            return None
        if count == -5:
            return None  # IA2 not supported
        if count < 0:
            raise NaturoCoreError(count, "ia2_get_element_tree")

        data = _safe_json_loads(_decode_native(buf.value))
        return _parse_element(data)

    def ia2_find_element(
        self, hwnd: int = 0, role: Optional[str] = None, name: Optional[str] = None
    ) -> Optional[ElementInfo]:
        """Find an IA2 element by role and/or name within a window.

        Uses BFS traversal of the IAccessible2 tree. Role matching uses
        both MSAA and IA2-extended role names (e.g., "Heading", "Paragraph",
        "Landmark").

        Args:
            hwnd: Window handle. 0 for the foreground window.
            role: Element role filter (case-insensitive). None for any.
            name: Element name filter (case-insensitive). None for any.

        Returns:
            ElementInfo if found, None if not found or IA2 not supported.

        Raises:
            NaturoCoreError: On error (invalid args, COM failure, etc.).
        """
        buf_size = 4096
        buf = ctypes.create_string_buffer(buf_size)

        role_bytes = role.encode("utf-8") if role else None
        name_bytes = name.encode("utf-8") if name else None

        rc = self._lib.naturo_ia2_find_element(hwnd, role_bytes, name_bytes, buf, buf_size)

        if rc == 1:
            return None
        if rc == -2 or rc == -5:
            return None
        if rc < 0:
            raise NaturoCoreError(rc, "ia2_find_element")

        data = _safe_json_loads(_decode_native(buf.value))
        return _parse_element(data)

    # ── JAB (Java Access Bridge) ─────────────────────

    def jab_check_support(self, hwnd: int = 0) -> bool:
        """Check if a window supports Java Access Bridge.

        Args:
            hwnd: Window handle. 0 to check for any Java window.

        Returns:
            True if JAB is available for the window.
        """
        rc = self._lib.naturo_jab_check_support(hwnd)
        return rc == 1

    def jab_get_element_tree(self, hwnd: int = 0, depth: int = 3) -> Optional[ElementInfo]:
        """Inspect the Java Access Bridge element tree of a window.

        Provides element inspection for Java/Swing/AWT applications.
        Requires a JRE/JDK with accessibility enabled and
        WindowsAccessBridge-64.dll on the system PATH.

        Args:
            hwnd: Window handle. 0 for the foreground window.
            depth: Maximum tree depth (1-10). Default 3.

        Returns:
            Root ElementInfo, or None if no Java window or JAB unavailable.

        Raises:
            NaturoCoreError: On error (invalid args, buffer too small).
        """
        buf_size = 2 << 20  # 2 MB
        buf = ctypes.create_string_buffer(buf_size)

        count = self._lib.naturo_jab_get_element_tree(hwnd, depth, buf, buf_size)

        if count == -4:
            buf_size = 8 << 20  # 8 MB retry
            buf = ctypes.create_string_buffer(buf_size)
            count = self._lib.naturo_jab_get_element_tree(hwnd, depth, buf, buf_size)

        if count == -2:
            return None
        if count == -6:
            return None  # JAB not available
        if count < 0:
            raise NaturoCoreError(count, "jab_get_element_tree")

        data = _safe_json_loads(_decode_native(buf.value))
        return _parse_element(data)

    def jab_find_element(
        self, hwnd: int = 0, role: Optional[str] = None, name: Optional[str] = None
    ) -> Optional[ElementInfo]:
        """Find a JAB element by role and/or name within a window.

        Uses BFS traversal of the Java accessibility tree. Role matching
        uses normalized role names (e.g., "Button", "Edit", "MenuItem").

        Args:
            hwnd: Window handle. 0 for the foreground window.
            role: Element role filter (case-insensitive). None for any.
            name: Element name filter (case-insensitive). None for any.

        Returns:
            ElementInfo if found, None if not found or JAB unavailable.

        Raises:
            NaturoCoreError: On error (invalid args, COM failure, etc.).
        """
        buf_size = 4096
        buf = ctypes.create_string_buffer(buf_size)

        role_bytes = role.encode("utf-8") if role else None
        name_bytes = name.encode("utf-8") if name else None

        rc = self._lib.naturo_jab_find_element(hwnd, role_bytes, name_bytes, buf, buf_size)

        if rc == 1:
            return None
        if rc == -2 or rc == -6:
            return None
        if rc < 0:
            raise NaturoCoreError(rc, "jab_find_element")

        data = _safe_json_loads(_decode_native(buf.value))
        return _parse_element(data)
