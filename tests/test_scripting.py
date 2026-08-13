"""Hermetic tests for ``naturo run`` (#42).

Every test writes a tiny script (or uses ``-c``) that does **not** drive the
desktop — it prints, reads ``sys.argv``, or at most *imports* the naturo SDK
without ever calling an input verb. The scripts run under the resolver's system
Python (fast, deterministic); the embedded runtime is not required.
"""
from __future__ import annotations

from pathlib import Path

from click.testing import CliRunner

from naturo.cli.run_cmd import run_cmd
from naturo.scripting import (
    ERR_FILE_NOT_FOUND,
    ERR_IMPORT,
    ERR_RUNTIME,
    ERR_SYNTAX,
    ERR_TIMEOUT,
    EXIT_TIMEOUT,
    run_script,
)


def _write(tmp_path: Path, name: str, body: str) -> Path:
    """Write ``body`` to ``tmp_path/name`` and return the path."""
    script = tmp_path / name
    script.write_text(body, encoding="utf-8")
    return script


# ── 1. run a file ────────────────────────────────────────────────────────────
def test_run_file_prints_marker(tmp_path: Path) -> None:
    script = _write(tmp_path, "hello.py", "print('MARKER_OK')\n")
    runner = CliRunner()
    result = runner.invoke(run_cmd, [str(script)])
    assert result.exit_code == 0, result.output
    assert "MARKER_OK" in result.output


# ── 2. inline -c ─────────────────────────────────────────────────────────────
def test_run_dash_c_prints_marker() -> None:
    runner = CliRunner()
    result = runner.invoke(run_cmd, ["-c", "print('INLINE_OK')"])
    assert result.exit_code == 0, result.output
    assert "INLINE_OK" in result.output


# ── 3. the naturo SDK is importable inside a run script (import-only!) ────────
def test_naturo_api_importable(tmp_path: Path) -> None:
    # Import the input verbs but NEVER call them — calling would SendInput to the
    # live desktop. We only assert the names import cleanly under the child.
    script = _write(
        tmp_path,
        "imp.py",
        "from naturo import click, see, type\nprint('IMPORT_OK')\n",
    )
    runner = CliRunner()
    result = runner.invoke(run_cmd, [str(script)])
    assert result.exit_code == 0, result.output
    assert "IMPORT_OK" in result.output
    assert "ImportError" not in result.output
    assert "ModuleNotFoundError" not in result.output


# ── 4. --args become sys.argv[1:] ────────────────────────────────────────────
def test_args_forwarded_as_argv(tmp_path: Path) -> None:
    script = _write(tmp_path, "argv.py", "import sys\nprint(sys.argv[1:])\n")
    runner = CliRunner()
    result = runner.invoke(run_cmd, [str(script), "--args", "x y"])
    assert result.exit_code == 0, result.output
    assert "['x', 'y']" in result.output


def test_argv0_is_script_path(tmp_path: Path) -> None:
    script = _write(tmp_path, "argv0.py", "import sys, os\nprint(os.path.basename(sys.argv[0]))\n")
    result = run_script(script=str(script))
    assert result.exit_code == 0
    assert "argv0.py" in result.stdout


# ── 5. --timeout kills a long run ────────────────────────────────────────────
def test_timeout_kills_long_script(tmp_path: Path) -> None:
    script = _write(tmp_path, "slow.py", "import time\ntime.sleep(30)\nprint('SHOULD_NOT_PRINT')\n")
    runner = CliRunner()
    result = runner.invoke(run_cmd, [str(script), "--timeout", "2"])
    assert result.exit_code == EXIT_TIMEOUT
    assert result.exit_code != 0
    assert "timed out" in result.output.lower()
    assert "SHOULD_NOT_PRINT" not in result.output


# ── 6. distinct errors ───────────────────────────────────────────────────────
def test_file_not_found(tmp_path: Path) -> None:
    missing = tmp_path / "does_not_exist.py"
    result = run_script(script=str(missing))
    assert result.exit_code != 0
    assert result.error_kind == ERR_FILE_NOT_FOUND
    assert "not found" in (result.message or "").lower()


def test_syntax_error() -> None:
    result = run_script(code="def (")
    assert result.exit_code != 0
    assert result.error_kind == ERR_SYNTAX


def test_import_error(tmp_path: Path) -> None:
    script = _write(tmp_path, "bad_import.py", "import nonexistent_xyz\n")
    result = run_script(script=str(script))
    assert result.exit_code != 0
    assert result.error_kind == ERR_IMPORT


def test_runtime_error(tmp_path: Path) -> None:
    script = _write(tmp_path, "boom.py", "raise ValueError('boom')\n")
    result = run_script(script=str(script))
    assert result.exit_code != 0
    assert result.error_kind == ERR_RUNTIME
    assert "ValueError" in result.stderr


def test_error_kinds_are_distinct(tmp_path: Path) -> None:
    kinds = {
        run_script(script=str(tmp_path / "nope.py")).error_kind,
        run_script(code="def (").error_kind,
        run_script(script=str(_write(tmp_path, "i.py", "import nonexistent_xyz\n"))).error_kind,
        run_script(script=str(_write(tmp_path, "r.py", "raise RuntimeError('x')\n"))).error_kind,
    }
    assert kinds == {ERR_FILE_NOT_FOUND, ERR_SYNTAX, ERR_IMPORT, ERR_RUNTIME}


# ── 7. exit-code propagation ─────────────────────────────────────────────────
def test_exit_code_propagated(tmp_path: Path) -> None:
    script = _write(tmp_path, "exit7.py", "import sys\nsys.exit(7)\n")
    runner = CliRunner()
    result = runner.invoke(run_cmd, [str(script)])
    assert result.exit_code == 7


def test_intentional_exit_is_not_classified_as_error(tmp_path: Path) -> None:
    # A deliberate non-zero sys.exit is propagated, not reported as a fault.
    script = _write(tmp_path, "exit3.py", "import sys\nsys.exit(3)\n")
    result = run_script(script=str(script))
    assert result.exit_code == 3
    assert result.error_kind is None


# ── usage errors ─────────────────────────────────────────────────────────────
def test_requires_script_or_code() -> None:
    result = CliRunner().invoke(run_cmd, [])
    assert result.exit_code == 2


def test_script_and_code_mutually_exclusive(tmp_path: Path) -> None:
    script = _write(tmp_path, "x.py", "print('x')\n")
    result = CliRunner().invoke(run_cmd, [str(script), "-c", "print('y')"])
    assert result.exit_code == 2


def test_timeout_error_kind_symbol() -> None:
    assert ERR_TIMEOUT == "timeout"
