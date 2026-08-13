"""Runtime resolution for naturo.

Decides which Python interpreter should drive naturo: a system Python when one
is available, otherwise the embedded CPython runtime produced by
``scripts/bundle_python.py``. See :mod:`naturo.runtime.resolver` for the pure,
testable implementation and :doc:`docs/EMBEDDED_RUNTIME` for the architecture.
"""
from __future__ import annotations

from naturo.runtime.resolver import (
    MIN_PYTHON,
    find_embedded_python,
    find_system_python,
    resolve_python,
)

__all__ = [
    "MIN_PYTHON",
    "find_embedded_python",
    "find_system_python",
    "resolve_python",
]
