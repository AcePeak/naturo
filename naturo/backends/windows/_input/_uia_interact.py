"""UIA element interaction: invoke, toggle, select, expand/collapse, focus.

These methods drive UI elements through UI Automation patterns instead of
synthetic ``SendInput`` events.  They are essential for UWP apps (hosted by
ApplicationFrameHost.exe) where coordinate-based clicks do not reach inner
content, and for schtasks / remote-session contexts where SendInput has no
effect.
"""

from __future__ import annotations

import logging
from typing import Optional

logger = logging.getLogger(__name__)


class UIAInteractMixin:
    """UIA element interaction via UI Automation patterns (no SendInput)."""

    def click_element_uia(
        self,
        x: int,
        y: int,
        app: Optional[str] = None,
        hwnd: Optional[int] = None,
        element_name: Optional[str] = None,
        element_automation_id: Optional[str] = None,
        element_role: Optional[str] = None,
    ) -> bool:
        """Click a UI element using UIA patterns instead of SendInput.

        For UWP apps hosted by ApplicationFrameHost.exe, SendInput clicks
        don't reach the inner content.  This method finds the element via
        UIA and invokes it via ExpandCollapsePattern, InvokePattern,
        TogglePattern, or SelectionItemPattern (#248).

        When ``element_name`` or ``element_automation_id`` is provided (e.g.
        from a cached snapshot), the element is located by identity via
        ``_find_uia_element`` first — this is more reliable than
        ``ElementFromPoint`` which can resolve to the wrong element when
        coordinates are slightly stale or the window has repositioned (#681).
        Falls back to ``ElementFromPoint(x, y)`` if the identity search
        finds nothing.

        Args:
            x: Screen X coordinate of the target element center.
            y: Screen Y coordinate of the target element center.
            app: Application name (used to resolve window handle).
            hwnd: Direct window handle.
            element_name: Accessible name from snapshot (e.g. "File").
            element_automation_id: UIA AutomationId from snapshot.
            element_role: UIA control type from snapshot (e.g. "MenuItem").

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

            element = None

            # (#681) Prefer identity-based lookup over coordinate-based when
            # element metadata is available from the snapshot.  This avoids
            # ElementFromPoint resolving to the wrong element when cached
            # coordinates are slightly off (e.g. after window reposition).
            if element_name or element_automation_id:
                search_hwnd = hwnd or 0
                if not search_hwnd and app:
                    try:
                        search_hwnd = self._resolve_hwnd(app=app)
                    except Exception:
                        search_hwnd = 0
                element = self._find_uia_element(
                    uia, mod, hwnd=search_hwnd,
                    name=element_name,
                    automation_id=element_automation_id,
                )
                if element is not None:
                    logger.debug(
                        "UIA click: found element by identity (name=%r, id=%r)",
                        element_name, element_automation_id,
                    )

            # Fallback: locate element by screen coordinates
            if element is None:
                point = wintypes.POINT(x, y)
                element = uia.ElementFromPoint(point)
                if element is None:
                    logger.debug("UIA click: no element found at (%d, %d)", x, y)
                    return False

            elem_name = element.CurrentName or ""
            logger.debug("UIA click: target element %r at (%d, %d)", elem_name, x, y)

            # (#672) Try ExpandCollapsePattern first (menu items, combo boxes,
            # tree items).  Top-level menu bar items (File, Edit, View…) support
            # ExpandCollapsePattern to open their dropdown.  InvokePattern on
            # these elements fires the command action instead of expanding,
            # causing wrong behaviour on UWP apps like Notepad.
            try:
                pattern = element.GetCurrentPattern(mod.UIA_ExpandCollapsePatternId)
                if pattern is not None:
                    ecp = pattern.QueryInterface(mod.IUIAutomationExpandCollapsePattern)
                    # Only expand if currently collapsed — avoids toggling an
                    # already-open menu closed.
                    state = ecp.CurrentExpandCollapseState
                    if state == 0:  # ExpandCollapseState_Collapsed
                        ecp.Expand()
                        logger.info("UIA click: expanded %r via ExpandCollapsePattern", elem_name)
                        return True
                    elif state == 1:  # ExpandCollapseState_Expanded
                        ecp.Collapse()
                        logger.info("UIA click: collapsed %r via ExpandCollapsePattern", elem_name)
                        return True
            except (COMError, AttributeError):
                pass

            # Try InvokePattern (buttons, links, simple menu items)
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
                "UIA click: element %r at (%d, %d) supports no expand/invoke/toggle/select pattern",
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

        On many deployed/enterprise hosts ``site-packages`` is read-only, so a
        stale generated typelib in ``comtypes/gen`` cannot be regenerated in
        place — comtypes raises ``PermissionError`` / a "Typelib different than
        module" error and naturo's whole UIA layer (SetValue, ValuePattern
        reads, …) silently dies (#1219). If the normal path fails for any
        reason, redirect codegen to a writable per-user dir and retry once.

        Raises:
            ImportError: If comtypes is not available.
            Exception: If UIA COM initialization fails even after the retry.
        """
        import comtypes.client  # type: ignore[import-untyped]  # noqa: F401
        try:
            return self._create_uia_via_comtypes()
        except (ImportError, ModuleNotFoundError):
            raise
        except Exception:
            self._redirect_comtypes_gen_dir()
            return self._create_uia_via_comtypes()

    @staticmethod
    def _create_uia_via_comtypes():
        """Build the IUIAutomation instance from the (possibly regenerated) gen."""
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

    @staticmethod
    def _redirect_comtypes_gen_dir():
        """Point comtypes codegen at a writable per-user dir and drop stale gen.

        Fixes the read-only-``site-packages`` + stale-cache deadlock (#1219): a
        fresh writable ``gen_dir`` lets ``GetModule`` regenerate the typelib, and
        restricting ``comtypes.gen.__path__`` to it prevents a stale read-only
        cached module from shadowing the fresh one.
        """
        import os
        import sys
        import tempfile

        import comtypes.client  # type: ignore[import-untyped]
        import comtypes.gen  # type: ignore[import-untyped]

        target = os.path.join(tempfile.gettempdir(), "naturo_comtypes_gen")
        os.makedirs(target, exist_ok=True)
        comtypes.client.gen_dir = target
        comtypes.gen.__path__[:] = [target]
        # Drop any already-imported (stale) gen submodules so the retry
        # regenerates them into the writable dir instead of reusing the cache.
        for name in [n for n in sys.modules if n.startswith("comtypes.gen.")]:
            del sys.modules[name]
        logger.warning(
            "comtypes gen cache was unusable (stale/read-only); redirected "
            "codegen to %s to keep the UIA ValuePattern path working (#1219)",
            target,
        )

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

    def _resolve_interaction_element(
        self,
        uia,
        mod,
        *,
        hwnd: int = 0,
        name: Optional[str] = None,
        automation_id: Optional[str] = None,
        role: Optional[str] = None,
        x: Optional[int] = None,
        y: Optional[int] = None,
    ):
        """Resolve a live UIA element for interaction, by identity then point.

        Resolution order, most precise first:

        1. **Specific identity** (``name`` / ``automation_id``) — survives small
           coordinate drift, so it is preferred when available.
        2. **Screen point** (``x``, ``y``) — ``ElementFromPoint`` against the
           cached bounding-box centre. This lets naturo act on *any* element it
           previously located, even one with no ``AutomationId`` and no name
           (e.g. the Property Tab Builder ``Message`` Edit). Tried before a
           role-only match because a point is unambiguous (#1208).
        3. **Role-only match** — last resort; ambiguous when several elements
           share a role, so it runs only when nothing more specific resolved.

        Args:
            uia: The UI Automation root object from ``_init_comtypes_uia``.
            mod: The comtypes UIAutomationClient module.
            hwnd: Window handle to scope identity searches. 0 = desktop root.
            name: Accessible name of the target element.
            automation_id: UIA AutomationId of the target element.
            role: UIA control type (e.g. ``"Edit"``).
            x: Screen X of the cached element centre, or ``None``.
            y: Screen Y of the cached element centre, or ``None``.

        Returns:
            The resolved UIA element, or ``None`` if every strategy failed.
        """
        elem = None
        if name or automation_id:
            elem = self._find_uia_element(
                uia, mod, hwnd=hwnd, name=name,
                automation_id=automation_id, role=role,
            )
        if elem is None and x is not None and y is not None:
            # Occlusion-independent: match the cached point inside the *target
            # window's own* UIA tree. ElementFromPoint is avoided because it
            # returns whichever window is topmost at the screen point, so an
            # overlapping window (e.g. a terminal) would hijack the hit (#1208).
            elem = self._find_element_in_window_at_point(
                uia, mod, hwnd, int(x), int(y),
            )
            if elem is None and not hwnd:
                # No window scope to walk — last-resort screen hit test.
                from ctypes import wintypes
                try:
                    elem = uia.ElementFromPoint(wintypes.POINT(int(x), int(y)))
                except Exception as exc:  # noqa: BLE001 — COM/OS errors vary
                    logger.debug("ElementFromPoint(%s, %s) failed: %s", x, y, exc)
                    elem = None
            if elem is not None:
                logger.debug(
                    "Resolved interaction element by cached point (%d, %d) (#1208)",
                    int(x), int(y),
                )
        if elem is None and role and not name and not automation_id:
            elem = self._find_uia_element(
                uia, mod, hwnd=hwnd, name=name,
                automation_id=automation_id, role=role,
            )
        return elem

    def _find_element_in_window_at_point(self, uia, mod, hwnd, x, y):
        """Find the element in ``hwnd``'s UIA tree whose bounds enclose ``(x, y)``.

        Walks the *target window's* own subtree via ``ElementFromHandle`` and
        returns the smallest element whose bounding rectangle contains the
        point (i.e. the most specific leaf control there). Unlike
        ``ElementFromPoint``, this is unaffected by other windows overlapping
        the target on screen, so it resolves cached snapshot elements even when
        the window is occluded or not foreground (#1208).

        Args:
            uia: UI Automation root object.
            mod: comtypes UIAutomationClient module.
            hwnd: Target window handle. ``0``/falsy returns ``None``.
            x: Screen X of the cached element centre.
            y: Screen Y of the cached element centre.

        Returns:
            The smallest enclosing UIA element, or ``None`` if none was found.
        """
        if not hwnd:
            return None
        try:
            root = uia.ElementFromHandle(hwnd)
            if root is None:
                return None
            elements = root.FindAll(
                mod.TreeScope_Descendants, uia.CreateTrueCondition()
            )
        except Exception as exc:  # noqa: BLE001 — COM/OS errors vary
            logger.debug("ElementFromHandle/FindAll for point match failed: %s", exc)
            return None

        best = None
        best_area = None
        length = elements.Length if elements is not None else 0
        for i in range(length):
            try:
                el = elements.GetElement(i)
                rect = el.CurrentBoundingRectangle
            except Exception:  # noqa: BLE001 — skip elements that error
                continue
            left, top, right, bottom = rect.left, rect.top, rect.right, rect.bottom
            if right <= left or bottom <= top:
                continue
            if left <= x <= right and top <= y <= bottom:
                area = (right - left) * (bottom - top)
                if best_area is None or area < best_area:
                    best, best_area = el, area
        return best

    def set_element_value(
        self,
        text: str,
        hwnd: int = 0,
        name: Optional[str] = None,
        automation_id: Optional[str] = None,
        role: Optional[str] = None,
        x: Optional[int] = None,
        y: Optional[int] = None,
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
            x: Screen X of the cached element centre (point fallback). (#1208)
            y: Screen Y of the cached element centre (point fallback). (#1208)

        Returns:
            True if SetValue succeeded, False otherwise.
        """
        try:
            uia, mod = self._init_comtypes_uia()
        except (ImportError, Exception):
            logger.debug("comtypes not available — cannot use SetValue")
            return False

        try:
            elem = self._resolve_interaction_element(
                uia, mod, hwnd=hwnd, name=name,
                automation_id=automation_id, role=role, x=x, y=y,
            )
            if elem is None:
                # If targeting by name/automation_id/point failed, try finding
                # the first editable element (e.g. Edit control) in the window
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

    def set_focused_element_value(self, text: str, append: bool = True) -> bool:
        """IME-immune text entry: write to the focused element via ValuePattern.

        Keystroke injection (SendInput) is intercepted by CJK/TSF IMEs and can
        corrupt typed text (#1219: "naturo" -> "nature"). When the focused
        control exposes a writable ValuePattern, set its value directly through
        UIA — bypassing the keyboard and the IME entirely. Returns False (so the
        caller falls back to keystrokes) when there is no focused element, no
        ValuePattern, or the pattern is read-only.

        Args:
            text: Text to insert.
            append: When True, append to the element's current value so a
                ``type`` after existing text matches keystroke semantics; when
                False, replace the whole value.

        Returns:
            True if the value was set via ValuePattern, False otherwise.
        """
        try:
            uia, mod = self._init_comtypes_uia()
        except (ImportError, Exception):
            return False
        try:
            elem = uia.GetFocusedElement()
            if elem is None:
                return False
            pat_unk = elem.GetCurrentPattern(mod.UIA_ValuePatternId)
            if pat_unk is None:
                return False
            vp = pat_unk.QueryInterface(mod.IUIAutomationValuePattern)
            if vp.CurrentIsReadOnly:
                return False
            new_value = ((vp.CurrentValue or "") + text) if append else text
            vp.SetValue(new_value)
            logger.info(
                "type: set focused element via ValuePattern (IME-immune, len=%d)",
                len(text),
            )
            return True
        except (OSError, AttributeError) as exc:
            logger.debug("set_focused_element_value failed: %s", exc)
            return False
        except Exception as exc:
            logger.debug("set_focused_element_value unexpected error: %s", exc)
            return False

    def get_element_value_uia(
        self,
        hwnd: int = 0,
        name: Optional[str] = None,
        automation_id: Optional[str] = None,
        role: Optional[str] = None,
        x: Optional[int] = None,
        y: Optional[int] = None,
    ) -> Optional[dict]:
        """Read an element's current value via UIA patterns (Python/comtypes).

        Mirrors :meth:`set_element_value`'s resolution so naturo can READ the
        value of an element it already located even when that element has no
        AutomationId and no name — resolving it inside its source window's own
        UIA tree at the cached point (occlusion-independent) and querying
        ValuePattern, then TextPattern, TogglePattern, and finally the Name
        property. (#1208)

        Args:
            hwnd: Window handle to scope identity/tree search. 0 = desktop root.
            name: Accessible name of the target element.
            automation_id: UIA AutomationId of the target element.
            role: UIA control type (e.g. ``"Edit"``).
            x: Screen X of the cached element centre (point fallback).
            y: Screen Y of the cached element centre (point fallback).

        Returns:
            A dict with ``value``, ``pattern``, ``role``, ``name`` and
            ``automation_id``, or ``None`` if no element or value was found.
        """
        try:
            uia, mod = self._init_comtypes_uia()
        except (ImportError, Exception):
            logger.debug("comtypes not available — cannot read value via UIA")
            return None

        _CTRL_TYPE_TO_ROLE = {
            50000: "Button", 50002: "CheckBox", 50003: "ComboBox",
            50004: "Edit", 50007: "ListItem", 50008: "List",
            50020: "Text", 50026: "Group", 50030: "Document",
        }
        try:
            from comtypes import COMError  # type: ignore[import-untyped]

            elem = self._resolve_interaction_element(
                uia, mod, hwnd=hwnd, name=name,
                automation_id=automation_id, role=role, x=x, y=y,
            )
            if elem is None:
                return None

            try:
                _role = _CTRL_TYPE_TO_ROLE.get(elem.CurrentControlType)
            except (COMError, AttributeError):
                _role = None
            try:
                _name = elem.CurrentName or ""
            except (COMError, AttributeError):
                _name = ""
            try:
                _aid = elem.CurrentAutomationId or ""
            except (COMError, AttributeError):
                _aid = ""

            value = None
            pattern = None
            try:
                pat = elem.GetCurrentPattern(mod.UIA_ValuePatternId)
                if pat is not None:
                    value = pat.QueryInterface(
                        mod.IUIAutomationValuePattern).CurrentValue
                    pattern = "ValuePattern"
            except (COMError, AttributeError):
                pass
            # Multiline WinForms edits often expose an empty ValuePattern but
            # carry the real text in TextPattern — so fall through on an empty
            # (not just None) value. (#1208)
            if not value:
                try:
                    pat = elem.GetCurrentPattern(mod.UIA_TextPatternId)
                    if pat is not None:
                        rng = pat.QueryInterface(
                            mod.IUIAutomationTextPattern).DocumentRange
                        _text = rng.GetText(-1)
                        if _text:
                            value = _text
                            pattern = "TextPattern"
                except (COMError, AttributeError):
                    pass
            if not value:
                try:
                    pat = elem.GetCurrentPattern(mod.UIA_TogglePatternId)
                    if pat is not None:
                        state = pat.QueryInterface(
                            mod.IUIAutomationTogglePattern).CurrentToggleState
                        value = {0: "Off", 1: "On", 2: "Indeterminate"}.get(
                            state, "Unknown")
                        pattern = "TogglePattern"
                except (COMError, AttributeError):
                    pass
            if not value and _name:
                value = _name
                pattern = "Name"
            if value is None:
                return None

            return {
                "value": value,
                "pattern": pattern,
                "role": _role,
                "name": _name,
                "automation_id": _aid,
            }
        except Exception as exc:  # noqa: BLE001 — COM/OS errors vary
            logger.debug("get_element_value_uia failed: %s", exc)
            return None

    def toggle_element(
        self,
        hwnd: int = 0,
        automation_id: Optional[str] = None,
        role: Optional[str] = None,
        name: Optional[str] = None,
        x: Optional[int] = None,
        y: Optional[int] = None,
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

            elem = self._resolve_interaction_element(
                uia, mod, hwnd=hwnd, name=name,
                automation_id=automation_id, role=role, x=x, y=y,
            )
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
        x: Optional[int] = None,
        y: Optional[int] = None,
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

            elem = self._resolve_interaction_element(
                uia, mod, hwnd=hwnd, name=name,
                automation_id=automation_id, role=role, x=x, y=y,
            )
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
        x: Optional[int] = None,
        y: Optional[int] = None,
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

            elem = self._resolve_interaction_element(
                uia, mod, hwnd=hwnd, name=name,
                automation_id=automation_id, role=role, x=x, y=y,
            )
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
