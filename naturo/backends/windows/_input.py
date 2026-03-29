"""Input handling: mouse, keyboard, clipboard, and UIA element interaction."""

from __future__ import annotations

import logging
from typing import Optional

from naturo.errors import NaturoError

logger = logging.getLogger(__name__)


class InputMixin:
    """Input handling: mouse, keyboard, clipboard, and UIA element interaction."""

    # === Phase 2: Input ===

    def click(self, x: Optional[int] = None, y: Optional[int] = None,
              element_id: Optional[str] = None, button: str = "left",
              double: bool = False, input_mode: str = "normal",
              hwnd: Optional[int] = None) -> None:
        """Click at coordinates or on a UI element.

        If an element_id is provided, finds the element first and clicks its
        center. If x/y coordinates are provided, moves to them first.
        At least one of x/y or element_id must be given.

        Args:
            x: Target X coordinate. Required if element_id not given.
            y: Target Y coordinate. Required if element_id not given.
            element_id: Automation element ID to find and click.
            button: Mouse button — "left", "right", or "middle".
            double: True for double-click.
            input_mode: Ignored for now (Phase 3 will add hardware/hook modes).
            hwnd: Target window handle for element search.  When provided,
                searches within this window instead of the foreground
                window (#525).

        Raises:
            ValueError: If neither coordinates nor element_id is provided.
            ElementNotFoundError: When element_id is given but not found.
            NaturoCoreError: On system error.
        """
        core = self._ensure_core()

        BUTTON_MAP = {"left": 0, "right": 1, "middle": 2}
        btn = BUTTON_MAP.get(button.lower(), 0)

        if element_id is not None:
            # Find element and click its center
            el = self.find_element(selector=element_id, hwnd=hwnd)
            if el is None:
                from naturo.errors import ElementNotFoundError
                raise ElementNotFoundError(element_id)
            cx = el.x + el.width // 2
            cy = el.y + el.height // 2
            core.mouse_move(cx, cy)
        elif x is not None and y is not None:
            core.mouse_move(x, y)
        else:
            raise ValueError("click: provide either (x, y) or element_id")

        core.mouse_click(btn, double)

    def click_element_uia(
        self,
        x: int,
        y: int,
        app: Optional[str] = None,
        hwnd: Optional[int] = None,
    ) -> bool:
        """Click a UI element at (x, y) using UIA patterns instead of SendInput.

        For UWP apps hosted by ApplicationFrameHost.exe, SendInput clicks
        don't reach the inner content.  This method uses UIA to find the
        element at the given point and invokes it via InvokePattern,
        TogglePattern, or SelectionItemPattern (#248).

        Args:
            x: Screen X coordinate of the target element center.
            y: Screen Y coordinate of the target element center.
            app: Application name (used to resolve window handle).
            hwnd: Direct window handle.

        Returns:
            True if UIA invoke succeeded, False otherwise.
        """
        try:
            uia, mod = self._init_comtypes_uia()
        except (ImportError, Exception) as exc:
            logger.debug("comtypes not available for UIA click: %s", exc)
            return False

        try:
            from ctypes import wintypes
            from comtypes import COMError  # type: ignore[import-untyped]

            # Use UIA.ElementFromPoint to find the element at coordinates
            point = wintypes.POINT(x, y)
            element = uia.ElementFromPoint(point)
            if element is None:
                logger.debug("UIA click: no element found at (%d, %d)", x, y)
                return False

            elem_name = element.CurrentName or ""
            logger.debug("UIA click: found element %r at (%d, %d)", elem_name, x, y)

            # Try InvokePattern first (buttons, links, menu items)
            try:
                pattern = element.GetCurrentPattern(mod.UIA_InvokePatternId)
                if pattern is not None:
                    invoke = pattern.QueryInterface(mod.IUIAutomationInvokePattern)
                    invoke.Invoke()
                    logger.info("UIA click: invoked %r via InvokePattern", elem_name)
                    return True
            except (COMError, AttributeError):
                pass

            # Try TogglePattern (checkboxes, toggle buttons)
            try:
                pattern = element.GetCurrentPattern(mod.UIA_TogglePatternId)
                if pattern is not None:
                    toggle = pattern.QueryInterface(mod.IUIAutomationTogglePattern)
                    toggle.Toggle()
                    logger.info("UIA click: toggled %r via TogglePattern", elem_name)
                    return True
            except (COMError, AttributeError):
                pass

            # Try SelectionItemPattern (radio buttons, list items)
            try:
                pattern = element.GetCurrentPattern(mod.UIA_SelectionItemPatternId)
                if pattern is not None:
                    sel = pattern.QueryInterface(mod.IUIAutomationSelectionItemPattern)
                    sel.Select()
                    logger.info("UIA click: selected %r via SelectionItemPattern", elem_name)
                    return True
            except (COMError, AttributeError):
                pass

            logger.debug(
                "UIA click: element %r at (%d, %d) supports no invoke/toggle/select pattern",
                elem_name, x, y,
            )
            return False

        except Exception as exc:
            logger.debug("UIA click failed at (%d, %d): %s", x, y, exc)
            return False

    def invoke_element(self, name: str, role: str) -> bool:
        """Invoke a UI element by name and role using UIA InvokePattern.

        This is a fallback for elements whose bounding rects are zero-size
        (e.g. TitleBar buttons after a window state change).  Instead of
        coordinate-based clicking, it searches the UIA tree for a matching
        element and calls ``IUIAutomationInvokePattern::Invoke()``.

        Args:
            name: The element's accessible name (e.g. "Minimize", "Close").
            role: The element's UIA control type (e.g. "Button").

        Returns:
            True if the element was found and Invoke succeeded, False otherwise.
        """
        try:
            import comtypes.client  # type: ignore[import-untyped]
            from comtypes import COMError  # type: ignore[import-untyped]
        except ImportError:
            logger.warning("comtypes not available — cannot use Invoke fallback")
            return False

        try:
            # Ensure comtypes gen modules are initialized before importing
            # from comtypes.gen.UIAutomationClient (#200).  GetModule triggers
            # type-library code generation on first use.
            try:
                from comtypes.gen.UIAutomationClient import IUIAutomation  # type: ignore[import-untyped]
            except (ImportError, ModuleNotFoundError):
                comtypes.client.GetModule("UIAutomationCore.dll")

            uia = comtypes.client.CreateObject(
                "{ff48dba4-60ef-4201-aa87-54103eef594e}",
                interface=None,
            )
            # IUIAutomation interface
            from comtypes.gen.UIAutomationClient import (  # type: ignore[import-untyped]
                IUIAutomation,
                TreeScope_Descendants,
                UIA_NamePropertyId,
                UIA_InvokePatternId,
            )
            uia = uia.QueryInterface(IUIAutomation)
            root = uia.GetRootElement()

            # Build a condition: Name == name
            name_cond = uia.CreatePropertyCondition(UIA_NamePropertyId, name)
            found = root.FindFirst(TreeScope_Descendants, name_cond)
            if found is None:
                logger.warning("Invoke fallback: element %r not found in UIA tree", name)
                return False

            # Try InvokePattern
            pattern = found.GetCurrentPattern(UIA_InvokePatternId)
            if pattern is None:
                logger.warning("Invoke fallback: element %r does not support InvokePattern", name)
                return False

            from comtypes.gen.UIAutomationClient import IUIAutomationInvokePattern  # type: ignore[import-untyped]
            invoke = pattern.QueryInterface(IUIAutomationInvokePattern)
            invoke.Invoke()
            logger.info("Invoke fallback: successfully invoked %r (%s)", name, role)
            return True

        except (COMError, OSError, AttributeError) as exc:
            logger.warning("Invoke fallback failed for %r: %s", name, exc)
            return False
        except Exception as exc:
            logger.warning("Invoke fallback unexpected error for %r: %s", name, exc)
            return False

    def _init_comtypes_uia(self):
        """Initialize comtypes UIA and return (uia, module) tuple.

        Ensures comtypes gen modules are generated before importing from them.
        Returns a tuple of (IUIAutomation instance, module reference).

        Raises:
            ImportError: If comtypes is not available.
            Exception: If UIA COM initialization fails.
        """
        import comtypes.client  # type: ignore[import-untyped]
        try:
            from comtypes.gen import UIAutomationClient as mod  # type: ignore[import-untyped]
        except (ImportError, ModuleNotFoundError):
            comtypes.client.GetModule("UIAutomationCore.dll")
            from comtypes.gen import UIAutomationClient as mod  # type: ignore[import-untyped]

        uia = comtypes.client.CreateObject(
            "{ff48dba4-60ef-4201-aa87-54103eef594e}",
            interface=mod.IUIAutomation,
        )
        return uia, mod

    def _find_uia_element(self, uia, mod, hwnd: int = 0,
                          name: Optional[str] = None,
                          automation_id: Optional[str] = None,
                          role: Optional[str] = None):
        """Find a UIA element in the tree by name, automationId, or role.

        Searches under the given window (by hwnd) or the entire desktop.

        Args:
            uia: IUIAutomation instance from _init_comtypes_uia.
            mod: UIAutomationClient module.
            hwnd: Window handle to scope the search.  0 = desktop root.
            name: Accessible name of the element.
            automation_id: UIA AutomationId of the element.
            role: UIA control type name (e.g. "Edit", "Button").

        Returns:
            IUIAutomationElement if found, None otherwise.
        """

        if hwnd:
            root = uia.ElementFromHandle(hwnd)
        else:
            root = uia.GetRootElement()

        conditions = []
        if automation_id:
            conditions.append(
                uia.CreatePropertyCondition(mod.UIA_AutomationIdPropertyId, automation_id)
            )
        if name:
            conditions.append(
                uia.CreatePropertyCondition(mod.UIA_NamePropertyId, name)
            )

        if not conditions:
            return None

        # Combine conditions with AND
        if len(conditions) == 1:
            cond = conditions[0]
        else:
            cond = conditions[0]
            for c in conditions[1:]:
                cond = uia.CreateAndCondition(cond, c)

        return root.FindFirst(mod.TreeScope_Descendants, cond)

    def set_element_value(
        self,
        text: str,
        hwnd: int = 0,
        name: Optional[str] = None,
        automation_id: Optional[str] = None,
        role: Optional[str] = None,
    ) -> bool:
        """Set text on a UI element using UIA ValuePattern.SetValue().

        This bypasses SendInput entirely, directly setting the element's
        value through the UIA accessibility interface. Works reliably in
        schtasks / remote session contexts where SendInput has no effect.

        Args:
            text: Text to set on the element.
            hwnd: Window handle to scope the search. 0 = desktop root.
            name: Accessible name of the target element.
            automation_id: UIA AutomationId of the target element.
            role: UIA control type (e.g. "Edit").

        Returns:
            True if SetValue succeeded, False otherwise.
        """
        try:
            uia, mod = self._init_comtypes_uia()
        except (ImportError, Exception):
            logger.debug("comtypes not available — cannot use SetValue")
            return False

        try:
            elem = self._find_uia_element(uia, mod, hwnd=hwnd, name=name,
                                          automation_id=automation_id, role=role)
            if elem is None:
                # If targeting by name/automation_id failed, try finding the
                # first editable element (e.g. Edit control) in the window
                if hwnd and role:
                    root = uia.ElementFromHandle(hwnd)
                    # Map common role names to UIA ControlTypeId
                    role_map = {
                        "Edit": 50004, "Document": 50030, "Text": 50020,
                    }
                    ctl_type_id = role_map.get(role)
                    if ctl_type_id:
                        cond = uia.CreatePropertyCondition(
                            mod.UIA_ControlTypePropertyId, ctl_type_id
                        )
                        elem = root.FindFirst(mod.TreeScope_Descendants, cond)

                if elem is None:
                    logger.debug("SetValue: target element not found (name=%r, aid=%r, role=%r)",
                                 name, automation_id, role)
                    return False

            # Try ValuePattern
            pat_unk = elem.GetCurrentPattern(mod.UIA_ValuePatternId)
            if pat_unk is None:
                logger.debug("SetValue: element does not support ValuePattern")
                return False

            vp = pat_unk.QueryInterface(mod.IUIAutomationValuePattern)

            # Check if the value is read-only
            if vp.CurrentIsReadOnly:
                logger.debug("SetValue: element's ValuePattern is read-only")
                return False

            vp.SetValue(text)
            logger.info("SetValue: successfully set text on element (name=%r, len=%d)",
                        name, len(text))
            return True

        except (OSError, AttributeError) as exc:
            logger.debug("SetValue failed: %s", exc)
            return False
        except Exception as exc:
            logger.debug("SetValue unexpected error: %s", exc)
            return False

    def toggle_element(
        self,
        hwnd: int = 0,
        automation_id: Optional[str] = None,
        role: Optional[str] = None,
        name: Optional[str] = None,
    ) -> Optional[str]:
        """Toggle a UI element via UIA TogglePattern.

        Args:
            hwnd: Window handle to scope the search.  0 = desktop root.
            automation_id: UIA AutomationId.
            role: Element role (e.g. ``"CheckBox"``).
            name: Element name.

        Returns:
            New toggle state string (``"On"``, ``"Off"``, or
            ``"Indeterminate"``), or ``None`` if the element was not found
            or does not support TogglePattern.
        """
        try:
            uia, mod = self._init_comtypes_uia()
        except (ImportError, Exception):
            logger.debug("comtypes not available — cannot use TogglePattern")
            return None

        try:
            from comtypes import COMError  # type: ignore[import-untyped]

            elem = self._find_uia_element(uia, mod, hwnd=hwnd, name=name,
                                          automation_id=automation_id, role=role)
            if elem is None:
                logger.debug("Toggle: target element not found")
                return None

            pat_unk = elem.GetCurrentPattern(mod.UIA_TogglePatternId)
            if pat_unk is None:
                logger.debug("Toggle: element does not support TogglePattern")
                return None

            tp = pat_unk.QueryInterface(mod.IUIAutomationTogglePattern)
            tp.Toggle()

            # Read new state: 0=Off, 1=On, 2=Indeterminate
            state_map = {0: "Off", 1: "On", 2: "Indeterminate"}
            new_state = state_map.get(tp.CurrentToggleState, "Unknown")
            logger.info("Toggle: toggled element (name=%r) → %s", name, new_state)
            return new_state

        except (COMError, OSError, AttributeError) as exc:
            logger.debug("Toggle failed: %s", exc)
            return None
        except Exception as exc:
            logger.debug("Toggle unexpected error: %s", exc)
            return None

    def select_element(
        self,
        hwnd: int = 0,
        automation_id: Optional[str] = None,
        role: Optional[str] = None,
        name: Optional[str] = None,
    ) -> bool:
        """Select a UI element via UIA SelectionItemPattern.

        Args:
            hwnd: Window handle to scope the search.  0 = desktop root.
            automation_id: UIA AutomationId.
            role: Element role (e.g. ``"ListItem"``, ``"RadioButton"``).
            name: Element name.

        Returns:
            True if the element was selected, False otherwise.
        """
        try:
            uia, mod = self._init_comtypes_uia()
        except (ImportError, Exception):
            logger.debug("comtypes not available — cannot use SelectionItemPattern")
            return False

        try:
            from comtypes import COMError  # type: ignore[import-untyped]

            elem = self._find_uia_element(uia, mod, hwnd=hwnd, name=name,
                                          automation_id=automation_id, role=role)
            if elem is None:
                logger.debug("Select: target element not found")
                return False

            pat_unk = elem.GetCurrentPattern(mod.UIA_SelectionItemPatternId)
            if pat_unk is None:
                logger.debug("Select: element does not support SelectionItemPattern")
                return False

            sp = pat_unk.QueryInterface(mod.IUIAutomationSelectionItemPattern)
            sp.Select()
            logger.info("Select: selected element (name=%r)", name)
            return True

        except (COMError, OSError, AttributeError) as exc:
            logger.debug("Select failed: %s", exc)
            return False
        except Exception as exc:
            logger.debug("Select unexpected error: %s", exc)
            return False

    def expand_collapse_element(
        self,
        hwnd: int = 0,
        automation_id: Optional[str] = None,
        role: Optional[str] = None,
        name: Optional[str] = None,
        expand: bool = True,
    ) -> bool:
        """Expand or collapse a UI element via UIA ExpandCollapsePattern.

        Args:
            hwnd: Window handle to scope the search.  0 = desktop root.
            automation_id: UIA AutomationId.
            role: Element role (e.g. ``"ComboBox"``, ``"TreeItem"``).
            name: Element name.
            expand: True to expand, False to collapse.

        Returns:
            True if the operation succeeded, False otherwise.
        """
        try:
            uia, mod = self._init_comtypes_uia()
        except (ImportError, Exception):
            logger.debug("comtypes not available — cannot use ExpandCollapsePattern")
            return False

        try:
            from comtypes import COMError  # type: ignore[import-untyped]

            elem = self._find_uia_element(uia, mod, hwnd=hwnd, name=name,
                                          automation_id=automation_id, role=role)
            if elem is None:
                logger.debug("ExpandCollapse: target element not found")
                return False

            pat_unk = elem.GetCurrentPattern(mod.UIA_ExpandCollapsePatternId)
            if pat_unk is None:
                logger.debug("ExpandCollapse: element does not support ExpandCollapsePattern")
                return False

            ecp = pat_unk.QueryInterface(mod.IUIAutomationExpandCollapsePattern)
            if expand:
                ecp.Expand()
                logger.info("ExpandCollapse: expanded element (name=%r)", name)
            else:
                ecp.Collapse()
                logger.info("ExpandCollapse: collapsed element (name=%r)", name)
            return True

        except (COMError, OSError, AttributeError) as exc:
            logger.debug("ExpandCollapse failed: %s", exc)
            return False
        except Exception as exc:
            logger.debug("ExpandCollapse unexpected error: %s", exc)
            return False

    def focus_element_uia(
        self,
        hwnd: int = 0,
        name: Optional[str] = None,
        automation_id: Optional[str] = None,
        role: Optional[str] = None,
    ) -> bool:
        """Focus a UI element using UIA SetFocus().

        Directly sets keyboard focus on a UIA element. Works in schtasks
        context where SetForegroundWindow + mouse click may not deliver
        actual focus.

        Args:
            hwnd: Window handle to scope the search.
            name: Accessible name of the target element.
            automation_id: UIA AutomationId.
            role: UIA control type.

        Returns:
            True if SetFocus succeeded, False otherwise.
        """
        try:
            uia, mod = self._init_comtypes_uia()
        except (ImportError, Exception):
            logger.debug("comtypes not available — cannot use UIA SetFocus")
            return False

        try:
            elem = self._find_uia_element(uia, mod, hwnd=hwnd, name=name,
                                          automation_id=automation_id, role=role)

            # (#441) When called with only hwnd (no name/role/automationId),
            # _find_uia_element returns None because there are no conditions.
            # Fall back to finding the first Edit or Document control in the
            # window — this restores keyboard focus to the main content area
            # after menu interactions or other focus-stealing events.
            if elem is None and hwnd and not name and not automation_id and not role:
                root = uia.ElementFromHandle(hwnd)
                for ctl_type_id in (50004, 50030):  # Edit, Document
                    cond = uia.CreatePropertyCondition(
                        mod.UIA_ControlTypePropertyId, ctl_type_id
                    )
                    elem = root.FindFirst(mod.TreeScope_Descendants, cond)
                    if elem is not None:
                        break

            if elem is None:
                logger.debug("UIA SetFocus: element not found (name=%r, role=%r)", name, role)
                return False

            elem.SetFocus()
            logger.info("UIA SetFocus: focused element (name=%r, role=%r)", name, role)
            return True

        except (OSError, AttributeError) as exc:
            logger.debug("UIA SetFocus failed: %s", exc)
            return False
        except Exception as exc:
            logger.debug("UIA SetFocus unexpected error: %s", exc)
            return False

    def type_text(self, text: str = "", delay_ms: int = 5, profile: str = "linear",
                  wpm: int = 120, input_mode: str = "normal") -> None:
        """Type text using SendInput.

        Args:
            text: UTF-8 string to type.
            delay_ms: Delay between keystrokes (milliseconds). Default: 5.
                For "human" profile, this is the base delay.
            profile: "linear" for constant delay, "human" for variable speed.
                     Human profile uses wpm to calculate delay.
            wpm: Words per minute (used only when profile="human").
            input_mode: Input method — "normal" (virtual key / Unicode) or
                "hardware" (scan code / Phys32, bypasses game anti-cheat).

        Raises:
            NaturoCoreError: On system error.
        """
        core = self._ensure_core()

        actual_delay = delay_ms
        if profile == "human" and wpm > 0:
            # Average word = 5 chars, convert wpm to ms per char
            ms_per_char = int(60_000 / (wpm * 5))
            actual_delay = max(1, ms_per_char)

        if input_mode == "hardware":
            core.phys_key_type(text, actual_delay)
        else:
            core.key_type(text, actual_delay)

    def press_key(self, key: str = "", input_mode: str = "normal") -> None:
        """Press and release a named key.

        Args:
            key: Key name (enter, tab, escape, f1-f12, a-z, 0-9, etc.).
            input_mode: Input method — "normal" (virtual key) or
                "hardware" (scan code / Phys32).

        Raises:
            NaturoCoreError: If key name is unrecognized or on system error.
        """
        core = self._ensure_core()
        if input_mode == "hardware":
            core.phys_key_press(key)
        else:
            core.key_press(key)

    def hotkey(self, *keys: str, hold_duration_ms: int = 50,
              input_mode: str = "normal") -> None:
        """Press a hotkey combination.

        Args:
            *keys: Key names. Modifiers (ctrl, alt, shift, win) are recognized
                   automatically. One non-modifier key is the base key.
            hold_duration_ms: Not yet used.
            input_mode: Input method — "normal" (virtual key) or
                "hardware" (scan code / Phys32).

        Example:
            backend.hotkey("ctrl", "c")   # Copy
            backend.hotkey("ctrl", "z")   # Undo

        Raises:
            NaturoCoreError: On invalid argument or system error.
        """
        core = self._ensure_core()
        if input_mode == "hardware":
            core.phys_key_hotkey(*keys)
        else:
            core.key_hotkey(*keys)

    def scroll(self, direction: str = "down", amount: int = 3,
               x: Optional[int] = None, y: Optional[int] = None,
               smooth: bool = False) -> None:
        """Scroll the mouse wheel.

        Args:
            direction: "up", "down", "left", or "right".
            amount: Number of wheel notches (each = 120 delta units).
            x: Move mouse to this X before scrolling. None = current position.
            y: Move mouse to this Y before scrolling. None = current position.
            smooth: Ignored (Phase 3 will add smooth scroll support).

        Raises:
            NaturoCoreError: On system error.
        """
        core = self._ensure_core()

        if x is not None and y is not None:
            core.mouse_move(x, y)

        WHEEL_DELTA = 120
        horizontal = direction in ("left", "right")
        # Up/right = positive, Down/left = negative
        sign = 1 if direction in ("up", "right") else -1
        delta = sign * amount * WHEEL_DELTA

        core.mouse_scroll(delta, horizontal)

    def drag(self, from_x: int = 0, from_y: int = 0, to_x: int = 0, to_y: int = 0,
             duration_ms: int = 500, steps: int = 10) -> None:
        """Drag from one point to another.

        Moves mouse to (from_x, from_y), holds left button, interpolates to
        (to_x, to_y) in `steps` increments, then releases the button.

        Args:
            from_x: Source X coordinate.
            from_y: Source Y coordinate.
            to_x: Destination X coordinate.
            to_y: Destination Y coordinate.
            duration_ms: Total drag duration in milliseconds.
            steps: Number of intermediate move steps.

        Raises:
            NaturoCoreError: On system error.
        """
        import time
        core = self._ensure_core()

        steps = max(1, steps)
        delay_s = (duration_ms / 1000.0) / steps

        core.mouse_move(from_x, from_y)
        time.sleep(0.05)  # Brief settle before pressing
        core.mouse_down(0)  # Press and hold left button

        try:
            for i in range(1, steps + 1):
                t = i / steps
                ix = int(from_x + (to_x - from_x) * t)
                iy = int(from_y + (to_y - from_y) * t)
                core.mouse_move(ix, iy)
                time.sleep(delay_s)
        finally:
            core.mouse_up(0)  # Always release, even on error

    def move_mouse(self, x: int = 0, y: int = 0) -> None:
        """Move the mouse cursor to absolute screen coordinates.

        Args:
            x: Target X coordinate.
            y: Target Y coordinate.

        Raises:
            NaturoCoreError: On system error.
        """
        core = self._ensure_core()
        core.mouse_move(x, y)

    def clipboard_get(self) -> str:
        """Get text content from the clipboard.

        Uses the pyperclip library as a portable clipboard interface.

        Returns:
            Clipboard text, or empty string if clipboard is empty.
        """
        try:
            import pyperclip  # type: ignore
            return pyperclip.paste() or ""
        except ImportError:
            # Fallback: use ctypes Win32 API directly
            try:
                import ctypes
                import ctypes.wintypes
                user32 = ctypes.windll.user32
                kernel32 = ctypes.windll.kernel32
                # Set proper restype/argtypes for 64-bit pointer safety
                user32.GetClipboardData.restype = ctypes.c_void_p
                kernel32.GlobalLock.restype = ctypes.c_void_p
                kernel32.GlobalLock.argtypes = [ctypes.c_void_p]
                kernel32.GlobalUnlock.argtypes = [ctypes.c_void_p]
                if not user32.OpenClipboard(0):
                    raise NaturoError("Failed to open clipboard")
                try:
                    CF_UNICODETEXT = 13
                    h = user32.GetClipboardData(CF_UNICODETEXT)
                    if not h:
                        return ""
                    ptr = kernel32.GlobalLock(h)
                    if not ptr:
                        raise NaturoError("Failed to lock clipboard memory")
                    try:
                        return ctypes.wstring_at(ptr)
                    finally:
                        kernel32.GlobalUnlock(h)
                finally:
                    user32.CloseClipboard()
            except NaturoError:
                raise
            except Exception as exc:
                raise NaturoError(f"Clipboard read failed: {exc}") from exc

    def clipboard_set(self, text: str = "") -> None:
        """Set the clipboard text content.

        Args:
            text: Text to place on the clipboard.
        """
        try:
            import pyperclip  # type: ignore
            pyperclip.copy(text)
        except ImportError:
            try:
                import ctypes
                import ctypes.wintypes
                user32 = ctypes.windll.user32
                kernel32 = ctypes.windll.kernel32
                # Set proper restype/argtypes for 64-bit pointer safety
                kernel32.GlobalAlloc.restype = ctypes.c_void_p
                kernel32.GlobalAlloc.argtypes = [ctypes.c_uint, ctypes.c_size_t]
                kernel32.GlobalLock.restype = ctypes.c_void_p
                kernel32.GlobalLock.argtypes = [ctypes.c_void_p]
                kernel32.GlobalUnlock.argtypes = [ctypes.c_void_p]
                user32.SetClipboardData.restype = ctypes.c_void_p
                user32.SetClipboardData.argtypes = [ctypes.c_uint, ctypes.c_void_p]
                CF_UNICODETEXT = 13
                GMEM_MOVEABLE = 2
                encoded = (text + "\0").encode("utf-16-le")
                h = kernel32.GlobalAlloc(GMEM_MOVEABLE, len(encoded))
                if not h:
                    raise NaturoError("Failed to allocate clipboard memory")
                ptr = kernel32.GlobalLock(h)
                if not ptr:
                    kernel32.GlobalFree = kernel32.GlobalFree  # noqa: E731
                    raise NaturoError("Failed to lock clipboard memory")
                ctypes.memmove(ptr, encoded, len(encoded))
                kernel32.GlobalUnlock(h)
                if not user32.OpenClipboard(0):
                    raise NaturoError("Failed to open clipboard")
                try:
                    user32.EmptyClipboard()
                    user32.SetClipboardData(CF_UNICODETEXT, h)
                finally:
                    user32.CloseClipboard()
            except NaturoError:
                raise
            except Exception as exc:
                raise NaturoError(f"Clipboard write failed: {exc}") from exc

    def clipboard_clear(self) -> None:
        """Clear the clipboard contents."""
        try:
            import pyperclip  # type: ignore
            pyperclip.copy("")
        except ImportError:
            try:
                import ctypes
                user32 = ctypes.windll.user32
                if not user32.OpenClipboard(0):
                    raise NaturoError("Failed to open clipboard")
                try:
                    user32.EmptyClipboard()
                finally:
                    user32.CloseClipboard()
            except NaturoError:
                raise
            except Exception as exc:
                raise NaturoError(f"Clipboard clear failed: {exc}") from exc

    def clipboard_info(self) -> dict:
        """Return information about the current clipboard contents.

        Checks for text, image (CF_DIB/CF_BITMAP), and file (CF_HDROP)
        formats using the Win32 API.

        Returns:
            Dictionary with format, size, has_text, has_image, has_files.
        """
        try:
            import ctypes
            user32 = ctypes.windll.user32
            kernel32 = ctypes.windll.kernel32
            user32.GetClipboardData.restype = ctypes.c_void_p
            kernel32.GlobalLock.restype = ctypes.c_void_p
            kernel32.GlobalLock.argtypes = [ctypes.c_void_p]
            kernel32.GlobalUnlock.argtypes = [ctypes.c_void_p]
            kernel32.GlobalSize.restype = ctypes.c_size_t
            kernel32.GlobalSize.argtypes = [ctypes.c_void_p]

            if not user32.OpenClipboard(0):
                raise NaturoError("Failed to open clipboard")
            try:
                CF_UNICODETEXT = 13
                CF_BITMAP = 2
                CF_DIB = 8
                CF_HDROP = 15

                has_text = bool(user32.IsClipboardFormatAvailable(CF_UNICODETEXT))
                has_image = bool(
                    user32.IsClipboardFormatAvailable(CF_BITMAP)
                    or user32.IsClipboardFormatAvailable(CF_DIB)
                )
                has_files = bool(user32.IsClipboardFormatAvailable(CF_HDROP))

                size = 0
                if has_text:
                    fmt = "text"
                    h = user32.GetClipboardData(CF_UNICODETEXT)
                    if h:
                        size = kernel32.GlobalSize(h)
                elif has_image:
                    fmt = "image"
                    h = user32.GetClipboardData(CF_DIB)
                    if h:
                        size = kernel32.GlobalSize(h)
                elif has_files:
                    fmt = "files"
                else:
                    fmt = "empty"

                return {
                    "format": fmt,
                    "size": size,
                    "has_text": has_text,
                    "has_image": has_image,
                    "has_files": has_files,
                }
            finally:
                user32.CloseClipboard()
        except NaturoError:
            raise
        except Exception as exc:
            raise NaturoError(f"Clipboard info failed: {exc}") from exc

    # System/framework processes to exclude from app list — these have visible
    # windows but are not user-facing applications.
    _SYSTEM_PROCESS_NAMES: set[str] = {
        "textinputhost.exe", "shellexperiencehost.exe",
        "searchhost.exe", "startmenuexperiencehost.exe", "lockapp.exe",
        "systemsettings.exe", "gamebar.exe", "gamebarftserver.exe",
        "windowsinternal.composableshell.experiences.textinput.inputapp.exe",
        "widgets.exe", "widgetservice.exe", "people.exe", "cortana.exe",
        "secureinput.exe", "dwm.exe", "csrss.exe", "winlogon.exe",
        "fontdrvhost.exe", "dllhost.exe", "sihost.exe", "ctfmon.exe",
        "runtimebroker.exe", "backgroundtaskhost.exe", "taskhostw.exe",
        "smartscreen.exe", "searchui.exe", "shellhost.exe",
    }

    # ApplicationFrameHost.exe hosts UWP apps (Calculator, Settings, etc.).
    # Unlike other system processes, AFH windows with non-empty titles are
    # real user-facing apps that should appear in app list.
    _UWP_HOST_PROCESS: str = "applicationframehost.exe"

