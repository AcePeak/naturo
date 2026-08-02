"""Window-selector resolution for MCP tools.

The loud-failure ``require_hwnd`` contract now lives in :mod:`naturo.window` so
the CLI and MCP surfaces share ONE implementation (it previously had two copies:
MCP #957 here and CLI #964 in ``cli/values/_set.py``). Re-exported here so the
existing ``from naturo.mcp._resolve import require_hwnd`` call sites are unchanged.
"""
from __future__ import annotations

from naturo.window import require_hwnd

__all__ = ["require_hwnd"]
