"""Regression tests for #869 — optional-dep install prompt must not leak into ``-j`` JSON output.

When the global ``-j`` / ``--json`` flag is set, :func:`naturo.deps.ensure_package`
must never call :func:`input` and must never print prose to stdout, even when stdin
looks interactive (on Windows ``sys.stdin.isatty()`` returns ``True`` even for a
DEVNULL-redirected child, so ``_is_interactive`` alone cannot be trusted). The only
content on stdout must be the structured ``{"success": false, "error": {...}}`` envelope.

All tests here are pure CLI/unit level (no DLL, no desktop, no real input injection).
"""

import json

import pytest
from click.testing import CliRunner

from naturo.deps import ensure_package
from naturo.errors import NaturoError


def _boom(*_args, **_kwargs):
    """Stand-in for ``input`` that fails the test if it is ever called."""
    raise AssertionError("input() must not be called in JSON mode")


class TestEnsurePackageJsonOutput:
    """``ensure_package(json_output=True)`` never prompts and never prints prose."""

    def test_json_mode_does_not_prompt_even_when_interactive(self, monkeypatch, capsys):
        """JSON mode must not call input() even when stdin looks like a TTY."""
        monkeypatch.setattr("naturo.deps._is_interactive", lambda: True)
        monkeypatch.setattr("builtins.input", _boom)

        with pytest.raises(NaturoError) as exc_info:
            ensure_package(
                "nonexistent_pkg_xyz_869",
                feature="Virtual desktop",
                install_extra="desktop",
                json_output=True,
            )

        assert exc_info.value.code == "MISSING_DEPENDENCY"
        # No prose may be emitted to stdout in JSON mode.
        assert capsys.readouterr().out == ""

    def test_non_json_interactive_still_prompts(self, monkeypatch):
        """Default (non-JSON) interactive behaviour is unchanged: it still prompts."""
        monkeypatch.setattr("naturo.deps._is_interactive", lambda: True)
        calls = {"n": 0}

        def fake_input(_prompt):
            calls["n"] += 1
            return "n"

        monkeypatch.setattr("builtins.input", fake_input)

        with pytest.raises(NaturoError):
            ensure_package("nonexistent_pkg_xyz_869", feature="Test")

        assert calls["n"] == 1


class TestDesktopListJsonNoLeak:
    """End-to-end: ``naturo desktop list -j`` with pyvda missing yields a single JSON document."""

    def test_desktop_list_json_is_pure_json(self, monkeypatch):
        """The leaky condition (interactive stdin) must still produce parseable JSON."""
        # Simulate the exact bug condition: stdin reports interactive, pyvda absent.
        monkeypatch.setattr("naturo.deps._is_interactive", lambda: True)
        monkeypatch.setattr("builtins.input", _boom)

        from naturo.cli.system._desktop import desktop

        runner = CliRunner()
        result = runner.invoke(desktop, ["list", "-j"])

        # stdout must be a single, parseable JSON document — no leading prose.
        payload = json.loads(result.output)
        assert payload["success"] is False
        assert payload["error"]["code"] == "MISSING_DEPENDENCY"
        assert "Install it now?" not in result.output
