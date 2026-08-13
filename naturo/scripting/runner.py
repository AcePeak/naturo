"""Execute user Python scripts under the resolver-chosen interpreter (#42).

The runner drives a **subprocess** rather than an in-process ``exec``. A
subprocess buys three properties the in-process route cannot give cleanly:

* **timeout-kill** — a runaway ``while True`` or ``time.sleep(3600)`` can be
  terminated (whole process tree) without leaving the naturo CLI wedged;
* **isolation** — the user's ``sys.exit``/``os._exit``, global state, signal
  handlers, and C-level crashes never touch the naturo process;
* **faithful exit codes** — the child's exit status *is* the script's exit
  status, so ``sys.exit(3)`` propagates verbatim.

The interpreter is chosen by :func:`naturo.runtime.resolver.resolve_python`
(system Python preferred, embedded bundle as fallback — issue #41). The naturo
package directory is injected onto ``PYTHONPATH`` so ``import naturo`` (the #924
SDK) works in the child regardless of which interpreter was picked, and UTF-8 is
forced so CJK output cannot crash on a GBK console.
"""
from __future__ import annotations

import os
import subprocess
from dataclasses import dataclass
from pathlib import Path
from typing import Optional, Sequence

from naturo.runtime.resolver import resolve_python

# ── Error taxonomy ────────────────────────────────────────────────────────────
# Distinct kinds so the CLI (and JSON consumers) can render a specific message
# and so the acceptance criterion "distinct errors" is testable.
ERR_FILE_NOT_FOUND = "file_not_found"
ERR_SYNTAX = "syntax"
ERR_IMPORT = "import"
ERR_RUNTIME = "runtime"
ERR_TIMEOUT = "timeout"

# Exit codes for faults naturo itself detects. When the script actually *runs*,
# its own exit code is propagated verbatim instead of any of these.
EXIT_FILE_NOT_FOUND = 2
EXIT_TIMEOUT = 124  # mirrors GNU coreutils `timeout` for scripted dispatchers

_SYNTAX_EXCEPTIONS = frozenset({"SyntaxError", "IndentationError", "TabError"})
_IMPORT_EXCEPTIONS = frozenset({"ImportError", "ModuleNotFoundError"})
_TRACEBACK_HEADER = "Traceback (most recent call last):"


@dataclass
class RunResult:
    """Outcome of a single ``naturo run`` invocation.

    Attributes:
        exit_code: The process exit code naturo should propagate. Equals the
            script's own exit code on a normal run; a naturo-detected fault
            (missing file, timeout) uses the dedicated codes above.
        stdout: Captured standard output of the script.
        stderr: Captured standard error of the script (includes any traceback).
        error_kind: One of the ``ERR_*`` constants when naturo classified a
            fault, else ``None`` (including an intentional non-zero ``sys.exit``).
        message: Human-readable naturo-style summary of ``error_kind``, or None.
        timed_out: True when the script was killed for exceeding ``--timeout``.
    """

    exit_code: int
    stdout: str = ""
    stderr: str = ""
    error_kind: Optional[str] = None
    message: Optional[str] = None
    timed_out: bool = False


def _naturo_package_root() -> Path:
    """Return the directory that must be on ``PYTHONPATH`` to ``import naturo``.

    That is the parent of the installed ``naturo`` package, so the child
    interpreter resolves the *same* checkout the CLI is running from.
    """
    import naturo

    return Path(naturo.__file__).resolve().parent.parent


def _build_env() -> dict[str, str]:
    """Build the child environment: inherit ours, ensure naturo is importable.

    Prepends the naturo package root to ``PYTHONPATH`` (so the #924 SDK imports
    even under the embedded runtime, which has no naturo installed) and forces
    UTF-8 so CJK output over the UTF-8 pipes never raises on a GBK host.
    """
    env = dict(os.environ)
    root = str(_naturo_package_root())
    existing = env.get("PYTHONPATH", "")
    env["PYTHONPATH"] = os.pathsep.join([root, existing]) if existing else root
    env["PYTHONUTF8"] = "1"
    env["PYTHONIOENCODING"] = "utf-8"
    return env


def _last_nonempty_line(text: str) -> str:
    """Return the last non-blank line of ``text`` (stripped), or ``""``."""
    for line in reversed(text.splitlines()):
        if line.strip():
            return line.strip()
    return ""


def _last_exception_name(stderr: str) -> Optional[str]:
    """Best-effort exception class name from a traceback's final line.

    A Python traceback ends with ``"<ExcName>: <message>"`` (or just
    ``"<ExcName>"``). We take the token before the first colon and, if it reads
    as a bare identifier, treat it as the exception name.
    """
    final = _last_nonempty_line(stderr)
    if not final:
        return None
    head = final.split(":", 1)[0].strip()
    candidate = head.split(".")[-1]
    return candidate if candidate.isidentifier() else None


def _classify(
    returncode: int, stderr: str, timed_out: bool, timeout: Optional[float]
) -> tuple[Optional[str], Optional[str]]:
    """Map a finished child into ``(error_kind, message)``.

    A zero exit — or a non-zero exit with no traceback (an intentional
    ``sys.exit(code)``) — is *not* an error to reclassify: it returns
    ``(None, None)`` and the caller propagates the code as-is.
    """
    if timed_out:
        secs = "" if timeout is None else f" after {timeout:g}s"
        return ERR_TIMEOUT, f"Script timed out{secs} and was terminated."
    if returncode == 0:
        return None, None

    exc = _last_exception_name(stderr)
    has_traceback = _TRACEBACK_HEADER in stderr

    # SyntaxError/IndentationError are reported at compile time *without* a
    # "Traceback" header, so they are matched on the exception name alone.
    if exc in _SYNTAX_EXCEPTIONS:
        return ERR_SYNTAX, "The script could not be compiled — it has a syntax error."
    if has_traceback and exc in _IMPORT_EXCEPTIONS:
        return ERR_IMPORT, f"The script failed to import a module: {_last_nonempty_line(stderr)}"
    if has_traceback:
        return ERR_RUNTIME, f"The script raised an unhandled exception: {_last_nonempty_line(stderr)}"

    # Non-zero exit, no traceback: a deliberate sys.exit(code). Propagate it.
    return None, None


def _terminate(proc: "subprocess.Popen[str]") -> None:
    """Kill the child *and its descendants*.

    On Windows a script may have spawned children; ``taskkill /T`` tears down
    the whole tree, where ``proc.kill()`` would only reap the direct child.
    """
    if os.name == "nt":
        subprocess.run(
            ["taskkill", "/F", "/T", "/PID", str(proc.pid)],
            capture_output=True,
            check=False,
        )
    else:  # pragma: no cover - runner targets the Windows host
        proc.kill()


def run_script(
    *,
    script: Optional[str] = None,
    code: Optional[str] = None,
    args: Optional[Sequence[str]] = None,
    timeout: Optional[float] = None,
    python: Optional[str] = None,
) -> RunResult:
    """Run a user script (``script``) or inline ``code`` in a subprocess.

    Exactly one of ``script`` / ``code`` must be given. Extra ``args`` are
    forwarded as the child's ``sys.argv[1:]`` (``sys.argv[0]`` is the script
    path, or ``"-c"`` for inline code — Python's own convention). ``timeout``,
    when set, kills the child (and tree) after that many seconds.

    Args:
        script: Path to a ``.py`` file to execute.
        code: Inline Python source to execute (``python -c``).
        args: Arguments exposed to the script as ``sys.argv[1:]``.
        timeout: Wall-clock seconds before the child is killed, or None.
        python: Explicit interpreter path; defaults to :func:`resolve_python`.

    Returns:
        A :class:`RunResult` with the propagated exit code, captured streams,
        and any classified fault.

    Raises:
        ValueError: If not exactly one of ``script``/``code`` is provided.
    """
    if (script is None) == (code is None):
        raise ValueError("Provide exactly one of `script` or `code`.")

    interpreter = python or resolve_python(prefer_system=True)
    forwarded = [str(a) for a in (args or [])]

    if code is not None:
        cmd = [interpreter, "-c", code, *forwarded]
    else:
        script_path = Path(str(script))
        if not script_path.is_file():
            return RunResult(
                exit_code=EXIT_FILE_NOT_FOUND,
                error_kind=ERR_FILE_NOT_FOUND,
                message=f"Script not found: {script}",
            )
        cmd = [interpreter, str(script_path), *forwarded]

    creationflags = subprocess.CREATE_NEW_PROCESS_GROUP if os.name == "nt" else 0
    proc = subprocess.Popen(
        cmd,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        env=_build_env(),
        encoding="utf-8",
        errors="replace",
        creationflags=creationflags,
    )

    timed_out = False
    try:
        out, err = proc.communicate(timeout=timeout)
    except subprocess.TimeoutExpired:
        timed_out = True
        _terminate(proc)
        out, err = proc.communicate()

    returncode = proc.returncode if proc.returncode is not None else 1
    kind, message = _classify(returncode, err or "", timed_out, timeout)
    exit_code = EXIT_TIMEOUT if timed_out else returncode
    return RunResult(
        exit_code=exit_code,
        stdout=out or "",
        stderr=err or "",
        error_kind=kind,
        message=message,
        timed_out=timed_out,
    )
