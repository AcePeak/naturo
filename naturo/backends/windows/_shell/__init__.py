"""Application control, menus, dialogs, taskbar, tray, and virtual desktops.

Split into focused submodules for maintainability.  The public API is the
single ``ShellMixin`` class, which composes all sub-mixins via MRO.
"""

from naturo.backends.windows._shell._app import AppMixin
from naturo.backends.windows._shell._desktop import DesktopMixin
from naturo.backends.windows._shell._dialog import DialogMixin
from naturo.backends.windows._shell._menu import MenuMixin
from naturo.backends.windows._shell._taskbar import TaskbarMixin
from naturo.backends.windows._shell._tray import TrayMixin


class ShellMixin(
    AppMixin,
    MenuMixin,
    DialogMixin,
    TaskbarMixin,
    TrayMixin,
    DesktopMixin,
):
    """Application control, menus, dialogs, taskbar, tray, and virtual desktops."""
