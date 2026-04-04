"""Value commands: get, set.

Split into focused submodules for maintainability.  The public API is
re-exported here so that ``from naturo.cli.values import get_cmd``
and similar imports continue to work.

Submodules:
    _get  — get command (read element text/value via UIA patterns)
    _set  — set command (write element value via UIA patterns)
"""
from __future__ import annotations

from naturo.cli.values._get import get_cmd  # noqa: F401
from naturo.cli.values._set import set_cmd  # noqa: F401
