"""UI element inspection, window/process resolution, and element tree retrieval.

``ElementMixin`` is composed from three focused submixins so each concern can
be navigated and tested in isolation (#720):

- :class:`~naturo.backends.windows._element._app_discovery.AppDiscoveryMixin`
  — window/app resolution: matching ``--app``/``--window-title``/``--pid`` to
  a concrete HWND, including the UWP ApplicationFrameHost fallback.
- :class:`~naturo.backends.windows._element._uia.UWPDiscoveryMixin` —
  UWP/WinUI host-window discovery: locating the CoreWindow/XAML content child
  and the real owning process inside an ApplicationFrameHost window.
- :class:`~naturo.backends.windows._element._tree.ElementTreeMixin` — the
  public element interface: ``find_element``, ``get_element_tree``, and
  ``get_element_value``.
"""

from __future__ import annotations

from naturo.backends.windows._element._app_discovery import AppDiscoveryMixin
from naturo.backends.windows._element._tree import ElementTreeMixin
from naturo.backends.windows._element._uia import UWPDiscoveryMixin


class ElementMixin(ElementTreeMixin, UWPDiscoveryMixin, AppDiscoveryMixin):
    """UI element inspection, window/process resolution, and element tree retrieval."""


__all__ = ["ElementMixin"]
