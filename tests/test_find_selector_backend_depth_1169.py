"""Tests for ``naturo find --selector`` honoring ``--backend`` and ``--depth`` (#1169).

The unified find engine's selector strategy (#1061) silently ignored two
documented, already-parsed ``find`` options on its tree-fetch:

* ``--backend`` / ``--method`` — the selector path called
  ``backend.get_element_tree(...)`` without forwarding the chosen accessibility
  backend, so it always ran the backend default (``"uia"`` — UIA only, no
  fallback), while the text-query path forwards ``backend="auto"`` (UIA first,
  then hybrid Win32+UIA / IA2 / JAB / MSAA). On WinUI/XAML apps (e.g. Windows 11
  Notepad) pure UIA returns a shallow tree, so ``find --selector '//Document'``
  resolved nothing while ``find 'role:Document'`` (auto) matched the same window
  — the by-scope/by-strategy divergence reported in #1169 facet 1.
* ``--depth`` — the selector path hardcoded ``depth=20``, so a user-supplied
  ``--depth`` was ignored.

These tests stub ``backend.get_element_tree`` so they need neither a desktop
session nor the native DLL, and pin the Option-Coverage contract: every
documented option the selector mode can touch is explicitly honored, not
silently dropped to a default path that returns confidently-wrong output
(the #1070 lesson).
"""
from __future__ import annotations

from dataclasses import dataclass, field

import pytest
from click.testing import CliRunner
from unittest.mock import MagicMock, patch

from naturo.cli.core import find_cmd


@dataclass
class _FakeElement:
    """Minimal stand-in for a backend ``ElementInfo`` node."""

    role: str
    name: str = ""
    id: str = ""
    value: str = ""
    x: int = 0
    y: int = 0
    width: int = 0
    height: int = 0
    children: list = field(default_factory=list)
    properties: dict = field(default_factory=dict)


def _sample_tree() -> _FakeElement:
    return _FakeElement(
        role="Window", name="Untitled - Notepad", width=800, height=600,
        children=[
            _FakeElement(role="Button", name="Save", x=700, y=8, width=60, height=24),
        ],
    )


def _backend_returning(tree) -> MagicMock:
    backend = MagicMock()
    backend.get_element_tree.return_value = tree
    return backend


@pytest.fixture
def runner() -> CliRunner:
    return CliRunner()


def _invoke(runner, backend, args):
    with patch("naturo.cli.core._common._platform_supports_gui", return_value=True), \
         patch("naturo.cli.core._common._get_backend", return_value=backend):
        return runner.invoke(find_cmd, args)


class TestSelectorForwardsBackendAndDepth:
    """``find --selector`` must forward ``--backend`` and ``--depth`` to the tree fetch."""

    def test_explicit_backend_is_forwarded(self, runner) -> None:
        backend = _backend_returning(_sample_tree())
        result = _invoke(
            runner, backend,
            ["--selector", "//Button", "--backend", "msaa", "--json"],
        )
        assert result.exit_code == 0, result.output
        backend.get_element_tree.assert_called_once()
        assert backend.get_element_tree.call_args.kwargs["backend"] == "msaa"

    def test_explicit_depth_is_forwarded(self, runner) -> None:
        backend = _backend_returning(_sample_tree())
        result = _invoke(
            runner, backend,
            ["--selector", "//Button", "--depth", "35", "--json"],
        )
        assert result.exit_code == 0, result.output
        assert backend.get_element_tree.call_args.kwargs["depth"] == 35

    def test_default_backend_is_auto_not_uia_only(self, runner) -> None:
        """With no ``--backend`` the selector path must use the CLI default ``auto``.

        Regression guard for #1169 facet 1: the selector path previously omitted
        ``backend=`` and fell to the backend's ``"uia"`` default (UIA only), so a
        WinUI/XAML element visible to ``auto``'s hybrid fallback resolved to
        ``SELECTOR_NOT_FOUND``. It must match the text-query path's ``auto``.
        """
        backend = _backend_returning(_sample_tree())
        result = _invoke(runner, backend, ["--selector", "//Button", "--json"])
        assert result.exit_code == 0, result.output
        assert backend.get_element_tree.call_args.kwargs["backend"] == "auto"

    def test_default_depth_matches_cli_default(self, runner) -> None:
        backend = _backend_returning(_sample_tree())
        result = _invoke(runner, backend, ["--selector", "//Button", "--json"])
        assert result.exit_code == 0, result.output
        assert backend.get_element_tree.call_args.kwargs["depth"] == 20
