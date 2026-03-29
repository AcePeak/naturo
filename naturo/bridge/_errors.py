"""Error classes for the naturo bridge."""
from __future__ import annotations


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
