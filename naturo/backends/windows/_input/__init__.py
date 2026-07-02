"""Input handling: mouse, keyboard, clipboard, and UIA element interaction.

``InputMixin`` is composed from four focused submixins so each input domain
can be navigated and tested in isolation (#861):

- :class:`~naturo.backends.windows._input._mouse.MouseMixin` — click, scroll,
  drag, cursor movement.
- :class:`~naturo.backends.windows._input._keyboard.KeyboardMixin` — text
  typing, key presses, hotkeys.
- :class:`~naturo.backends.windows._input._uia_interact.UIAInteractMixin` —
  UIA-pattern element interaction (invoke/toggle/select/expand/focus).
- :class:`~naturo.backends.windows._input._clipboard.ClipboardMixin` —
  clipboard get/set/clear/info.

``get_input_strategy`` is re-exported here for backward compatibility with
code (and tests) that referenced ``naturo.backends.windows._input``.
"""

from __future__ import annotations

from naturo.backends.windows._input._clipboard import ClipboardMixin
from naturo.backends.windows._input._keyboard import KeyboardMixin
from naturo.backends.windows._input._mouse import MouseMixin
from naturo.backends.windows._input._uia_interact import UIAInteractMixin
from naturo.backends.windows._strategies import get_input_strategy  # noqa: F401


class InputMixin(MouseMixin, KeyboardMixin, UIAInteractMixin, ClipboardMixin):
    """Input handling: mouse, keyboard, clipboard, and UIA element interaction."""

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


__all__ = ["InputMixin"]
