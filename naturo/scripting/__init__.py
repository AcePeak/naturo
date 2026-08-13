"""naturo scripting engine — run user Python scripts under the bundled runtime.

Public surface for ``naturo run`` (#42): :func:`run_script` executes a ``.py``
file or an inline ``-c`` code string in a subprocess driven by the resolver's
interpreter (system preferred, embedded fallback — #41), with the #924 naturo
SDK importable inside the script.
"""
from __future__ import annotations

from naturo.scripting.runner import (
    ERR_FILE_NOT_FOUND,
    ERR_IMPORT,
    ERR_RUNTIME,
    ERR_SYNTAX,
    ERR_TIMEOUT,
    EXIT_FILE_NOT_FOUND,
    EXIT_TIMEOUT,
    RunResult,
    run_script,
)

__all__ = [
    "run_script",
    "RunResult",
    "ERR_FILE_NOT_FOUND",
    "ERR_SYNTAX",
    "ERR_IMPORT",
    "ERR_RUNTIME",
    "ERR_TIMEOUT",
    "EXIT_FILE_NOT_FOUND",
    "EXIT_TIMEOUT",
]
