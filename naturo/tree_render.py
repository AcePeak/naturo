"""Shared UI-tree rendering constants for BOTH tree renderers.

The CLI `see` renderer (``naturo/cli/core/_see.py``) and the MCP `see_ui_tree`
renderer (``naturo/mcp/_inspect.py``) each decide which nodes are "actionable"
when emitting the compact tree. They had drifted: the MCP set carried
``datagrid``/``dataitem`` that the CLI set lacked, so the *same window* could
produce different compact trees on the two surfaces. This module is the single
source of truth so they cannot disagree again — the eventual home for the fully
unified renderer (task #10); for now it holds the shared role set.
"""

from __future__ import annotations

#: Roles that count as actionable/meaningful for the compact tree walk. The
#: union of what both surfaces historically emitted, so neither loses nodes;
#: datagrid/dataitem are included for spreadsheet / data-grid content.
ACTIONABLE_ROLES = frozenset({
    "button", "hyperlink", "link", "edit", "text", "checkbox",
    "radiobutton", "combobox", "menuitem", "listitem", "tab", "tabitem",
    "treeitem", "slider", "spinner", "document", "datagrid", "dataitem",
})
