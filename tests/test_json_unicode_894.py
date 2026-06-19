"""Non-ASCII (CJK / emoji) must round-trip *literally* through CLI ``-j`` output (#894).

Python's ``json.dumps`` defaults to ``ensure_ascii=True``, which rewrites every
non-ASCII code point as a ``\\uXXXX`` escape. For naturo's ``-j`` output that means
Chinese window titles, user-supplied paths, selector names and error messages come
back mangled (``记事本`` → ``\\u8bb0\\u4e8b\\u672c``) — unreadable for CJK users and
inconsistent with the non-JSON path, which already prints literal Unicode. The CLI
already reconfigures stdout/stderr to UTF-8 (``naturo/cli/__init__.py``), so emitting
literal Unicode is safe on every platform.

These tests pin the contract: the shared :func:`naturo.cli._jsonio.json_dumps` helper
defaults to ``ensure_ascii=False``, the canonical error envelope preserves literal
Unicode, and an end-to-end command echoes CJK input without escaping.

#1025 is an incomplete-fix regression of #894: a large set of ``-j`` emit sites were
missed because they call the raw stdlib ``json`` (often aliased as
``import json as json_module``) instead of :func:`json_dumps`, so ``see`` / ``find`` /
``menu-inspect`` / ``list windows`` / ``get`` / ``set`` still emitted ``\\uXXXX``. The
:class:`TestNoRawJsonDumpsInCliOutput` AST guard pins the whole class shut: every CLI
emit site must route through :func:`json_dumps`, never the stdlib ``json.dumps``.
"""
from __future__ import annotations

import ast
import json
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest
from click.testing import CliRunner

# A sampling of non-ASCII the field cares about: CJK app names and an emoji.
_CJK = "记事本"  # "Notepad"
_EMOJI = "🚀"


@pytest.fixture
def runner():
    return CliRunner()


class TestJsonDumpsHelper:
    """The shared helper defaults to literal (non-escaped) Unicode."""

    def test_defaults_to_literal_unicode(self):
        from naturo.cli._jsonio import json_dumps

        out = json_dumps({"title": _CJK, "icon": _EMOJI})
        assert _CJK in out
        assert _EMOJI in out
        assert "\\u" not in out
        # Still valid JSON that round-trips to the original values.
        assert json.loads(out) == {"title": _CJK, "icon": _EMOJI}

    def test_ascii_output_is_unchanged(self):
        from naturo.cli._jsonio import json_dumps

        payload = {"success": True, "count": 3, "name": "Save"}
        assert json_dumps(payload) == json.dumps(payload)

    def test_explicit_ensure_ascii_true_is_honored(self):
        from naturo.cli._jsonio import json_dumps

        out = json_dumps({"title": _CJK}, ensure_ascii=True)
        assert _CJK not in out
        assert "\\u" in out

    def test_passes_through_other_kwargs(self):
        from naturo.cli._jsonio import json_dumps

        out = json_dumps({"b": 1, "a": 2}, indent=2, sort_keys=True)
        assert out == json.dumps({"b": 1, "a": 2}, indent=2,
                                 sort_keys=True, ensure_ascii=False)


class TestErrorEnvelopePreservesUnicode:
    """The canonical error envelope (every command's ``-j`` error path) stays literal."""

    def test_json_error_message_is_literal(self):
        from naturo.cli.error_helpers import json_error

        out = json_error("INVALID_INPUT", f"bad path: {_CJK}")
        assert _CJK in out
        assert "\\u" not in out
        assert json.loads(out)["error"]["message"] == f"bad path: {_CJK}"

    def test_json_error_context_is_literal(self):
        from naturo.cli.error_helpers import json_error

        out = json_error("WINDOW_NOT_FOUND", "not found",
                         context={"app": _CJK})
        assert _CJK in out
        assert json.loads(out)["error"]["context"]["app"] == _CJK


def _make_mock_backend():
    """Minimal element tree whose only Button is named 'Save' (ASCII)."""
    backend = MagicMock()
    button = MagicMock()
    button.id, button.role, button.name, button.value = "btn", "Button", "Save", ""
    button.x, button.y, button.width, button.height = 100, 200, 80, 30
    button.children, button.properties = [], {"className": "Button"}
    root = MagicMock()
    root.id, root.role, root.name, root.value = "root", "Window", "Untitled", ""
    root.x, root.y, root.width, root.height = 0, 0, 800, 600
    root.children, root.properties = [button], {"className": "Notepad"}
    backend.get_element_tree.return_value = root
    return backend


class TestCliEndToEnd:
    """A real command's ``-j`` error path echoes CJK input without escaping."""

    def test_selector_not_found_error_keeps_cjk_literal(self, runner):
        mock_be = _make_mock_backend()
        patches = [
            patch("naturo.cli.interaction._common._get_backend",
                  return_value=mock_be),
            patch("naturo.cli.interaction._common._check_desktop_session"),
            patch("naturo.cli.interaction._common._auto_route", return_value={}),
        ]
        for p in patches:
            p.start()
        try:
            from naturo.cli.interaction import click_cmd
            result = runner.invoke(click_cmd, [
                "--selector", f'app://*/Button[@name="{_CJK}"]',
                "--json",
            ])
            assert result.exit_code != 0
            assert "SELECTOR_NOT_FOUND" in result.output
            # The echoed selector must contain literal CJK, not \uXXXX escapes.
            assert _CJK in result.output
            assert "\\u" not in result.output
        finally:
            for p in patches:
                p.stop()


def _stdlib_json_names(tree: ast.Module) -> set[str]:
    """Return the names the stdlib ``json`` module is bound to in a module.

    Handles ``import json`` (name ``json``), ``import json as json_module``
    (the alias used by the modules #1025 missed), and module-level
    ``from json import dumps`` (name ``dumps``).

    Args:
        tree: Parsed AST of a Python module.

    Returns:
        The set of identifiers that refer to the stdlib ``json`` module, plus
        ``"dumps"`` if it was imported directly from ``json``.
    """
    names: set[str] = set()
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            for alias in node.names:
                if alias.name == "json":
                    names.add(alias.asname or "json")
        elif isinstance(node, ast.ImportFrom) and node.module == "json":
            for alias in node.names:
                if alias.name == "dumps":
                    names.add(alias.asname or "dumps")
    return names


def _raw_json_dumps_callsites(path: Path) -> list[int]:
    """Find line numbers in ``path`` that call the stdlib ``json.dumps``.

    Detects both ``<json-alias>.dumps(...)`` (e.g. ``json_module.dumps``) and a
    bare ``dumps(...)`` imported via ``from json import dumps`` — the patterns
    that bypass :func:`naturo.cli._jsonio.json_dumps` and re-introduce the #894
    ``\\uXXXX`` escaping regression (#1025).

    Args:
        path: Path to the Python source file to scan.

    Returns:
        Sorted line numbers of offending callsites (empty if the file is clean).
    """
    tree = ast.parse(path.read_text(encoding="utf-8"))
    json_names = _stdlib_json_names(tree)
    hits: list[int] = []
    for node in ast.walk(tree):
        if not isinstance(node, ast.Call):
            continue
        func = node.func
        if (isinstance(func, ast.Attribute) and func.attr == "dumps"
                and isinstance(func.value, ast.Name)
                and func.value.id in json_names):
            hits.append(node.lineno)
        elif (isinstance(func, ast.Name) and func.id == "dumps"
                and "dumps" in json_names):
            hits.append(node.lineno)
    return sorted(hits)


class TestNoRawJsonDumpsInCliOutput:
    """Every CLI ``-j`` emit site must route through :func:`json_dumps` (#1025).

    The original #894 fix added the helper but missed many callsites that use
    the raw stdlib ``json`` (frequently aliased ``import json as json_module``),
    which kept emitting ``\\uXXXX`` escapes. A grep audit missed them because of
    the alias; this AST scan does not.
    """

    def test_no_module_uses_stdlib_json_dumps(self):
        cli_dir = Path(__file__).resolve().parent.parent / "naturo" / "cli"
        # The shared helper is the one and only sanctioned ``json.dumps`` call.
        sanctioned = cli_dir / "_jsonio.py"

        offenders: dict[str, list[int]] = {}
        for path in sorted(cli_dir.rglob("*.py")):
            if path == sanctioned:
                continue
            lines = _raw_json_dumps_callsites(path)
            if lines:
                offenders[str(path.relative_to(cli_dir.parent.parent))] = lines

        assert not offenders, (
            "CLI modules must serialize -j output via "
            "naturo.cli._jsonio.json_dumps (ensure_ascii=False), not the "
            "stdlib json.dumps which escapes non-ASCII as \\uXXXX (#1025). "
            f"Offending callsites: {offenders}"
        )


class TestElementTreeSurfacesKeepCjkLiteral:
    """The element-tree ``-j`` surfaces #1025 called out echo CJK literally."""

    def test_find_ai_error_envelope_keeps_cjk_literal(self, runner):
        """``find --ai`` JSON error envelope (``_find.py:294``) stays literal.

        This callsite — one of the raw ``json_module.dumps`` sites #1025
        flagged — echoes the underlying failure message; a CJK message must
        survive without ``\\uXXXX`` escaping.
        """
        with patch("naturo.ai_find.ai_find_element",
                   side_effect=RuntimeError(f"detector crashed: {_CJK}")):
            from naturo.cli.core._find import find_cmd
            result = runner.invoke(
                find_cmd, ["the close button", "--ai", "--json"],
            )

        assert result.exit_code != 0
        assert "AI_FIND_FAILED" in result.output
        assert _CJK in result.output
        assert "\\u" not in result.output
