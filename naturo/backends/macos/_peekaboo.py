"""Peekaboo CLI runner — process execution and JSON parsing.

Provides :class:`PeekabooError` and the :class:`_PeekabooRunner` mixin that
wraps the ``peekaboo`` command-line tool. All other macOS mixins delegate
their work to this runner via ``self._run`` / ``self._run_raw``.
"""
from __future__ import annotations

import json
import shutil
import subprocess
from typing import Any

from naturo.errors import NaturoError


class PeekabooError(NaturoError):
    """Error from Peekaboo CLI execution."""

    def __init__(self, message: str, code: str = "PEEKABOO_ERROR"):
        super().__init__(message)
        self.code = code


class _PeekabooRunner:
    """Locate and execute the Peekaboo CLI, parsing its JSON output.

    Holds the resolved peekaboo executable path and the low-level command
    runners shared by every macOS backend domain mixin.
    """

    def __init__(self) -> None:
        self._peekaboo_path = shutil.which("peekaboo")

    def _require_peekaboo(self) -> str:
        """Ensure Peekaboo is available, raising a clear error if not.

        Returns:
            Path to the peekaboo executable.

        Raises:
            NaturoError: If peekaboo is not found on PATH.
        """
        if not self._peekaboo_path:
            raise NaturoError(
                "Peekaboo is not installed. Install it from "
                "https://github.com/AcePeak/peekaboo or via Homebrew."
            )
        return self._peekaboo_path

    def _run(
        self,
        args: list[str],
        *,
        timeout: int = 30,
        check: bool = True,
    ) -> dict[str, Any]:
        """Run a Peekaboo CLI command and parse JSON output.

        Args:
            args: Command arguments (without 'peekaboo' prefix).
            timeout: Command timeout in seconds.
            check: If True, raise on non-zero exit or error response.

        Returns:
            Parsed JSON response dict.

        Raises:
            PeekabooError: On command failure or invalid output.
        """
        peekaboo = self._require_peekaboo()
        cmd = [peekaboo] + args + ["--json"]

        try:
            result = subprocess.run(
                cmd,
                capture_output=True,
                text=True,
                timeout=timeout,
            )
        except subprocess.TimeoutExpired:
            raise PeekabooError(
                f"Peekaboo command timed out after {timeout}s: {' '.join(args)}",
                code="TIMEOUT",
            )
        except OSError as e:
            raise PeekabooError(f"Failed to run Peekaboo: {e}")

        # Try to parse JSON from stdout
        output = result.stdout.strip()
        if not output:
            # Some commands output to stderr on error
            stderr = result.stderr.strip()
            if result.returncode != 0:
                raise PeekabooError(
                    stderr or f"Peekaboo command failed with exit code {result.returncode}",
                    code="COMMAND_FAILED",
                )
            return {"success": True}

        try:
            data = json.loads(output)
        except json.JSONDecodeError:
            if result.returncode != 0:
                raise PeekabooError(
                    output or result.stderr.strip(),
                    code="COMMAND_FAILED",
                )
            raise PeekabooError(
                f"Invalid JSON from Peekaboo: {output[:200]}",
                code="PARSE_ERROR",
            )

        # Check for error in response
        if check and isinstance(data, dict):
            if data.get("success") is False:
                error = data.get("error", {})
                msg = error.get("message", str(data)) if isinstance(error, dict) else str(error)
                code = error.get("code", "PEEKABOO_ERROR") if isinstance(error, dict) else "PEEKABOO_ERROR"
                raise PeekabooError(msg, code=code)

        return data

    def _run_raw(
        self,
        args: list[str],
        *,
        timeout: int = 30,
    ) -> subprocess.CompletedProcess:
        """Run a Peekaboo CLI command without JSON parsing.

        Args:
            args: Command arguments (without 'peekaboo' prefix).
            timeout: Command timeout in seconds.

        Returns:
            CompletedProcess result.
        """
        peekaboo = self._require_peekaboo()
        cmd = [peekaboo] + args

        try:
            return subprocess.run(
                cmd,
                capture_output=True,
                text=True,
                timeout=timeout,
            )
        except subprocess.TimeoutExpired:
            raise PeekabooError(
                f"Peekaboo command timed out after {timeout}s: {' '.join(args)}",
                code="TIMEOUT",
            )
