"""Source-level guard against hand-rolled ``-j`` error envelopes (issue #1180).

Background
----------
The six-key JSON **error** envelope (``code``, ``message``, ``category``,
``context``, ``suggested_action``, ``recoverable``) was unified by #884 and is
guarded *positively* by :mod:`test_error_envelope_contract_1001`, which walks the
Click tree and asserts the emitted shape. That contract proves the paths it can
*reach*: parse-stage usage errors across the full tree, plus a hand-curated
sample of runtime failures. But a command body that hand-builds
``json_dumps({"success": False, "error": {...}})`` instead of routing through the
canonical :func:`naturo.cli.error_helpers.json_error` /
:func:`~naturo.cli.error_helpers.emit_error` silently emits a truncated envelope
on a path the curated sample never triggers — which is exactly how #1179
(``find --ai`` emitted a 2-key error) and a cluster of sibling drifts
(``mcp``/``config``/``snapshot``/``clipboard``/``app`` paths) reached users.

This module closes the hole **at the source**, the role #1180 calls out: a
lightweight AST guard that scans the CLI package and fails CI if any module other
than the canonical error builders constructs a ``{"success": False, ...}`` error
envelope as a literal. A new command physically cannot hand-roll an error
envelope and pass CI — it must call the helper, which guarantees all six keys.

Scope
-----
The guard covers ``naturo/cli/**`` — the ``-j`` CLI contract surface #884 fixed.
The MCP-tool error surface (``isError`` flag, #882) is a separate contract and is
out of scope here. The canonical builders in ``error_helpers.py`` are the single
allowed home for the literal (``json_error`` wraps the six-key object in it), so
that module is the lone allowlist entry.

The test is pure static analysis — it parses source files, runs no command, and
needs no DLL or desktop, so it executes on every CI lane.
"""

from __future__ import annotations

import ast
from pathlib import Path

import naturo.cli

# The CLI package whose ``-j`` error paths must funnel through the canonical
# helpers rather than hand-building the envelope.
_CLI_ROOT = Path(naturo.cli.__file__).parent

# The single module allowed to construct the ``{"success": False, "error": ...}``
# literal: it *is* the canonical builder every other path must call. Relative to
# ``_CLI_ROOT`` so the allowlist is stable regardless of checkout location.
_ALLOWED = {"error_helpers.py"}


def _has_success_false_key(node: ast.Dict) -> bool:
    """Return whether *node* is a dict literal with a ``"success": False`` entry.

    That key/value pair is the fingerprint of a hand-rolled error envelope: the
    canonical :func:`success_envelope` only ever sets ``success`` to ``True``, and
    the error builders live in the allowlisted module, so a literal ``False`` here
    anywhere else is a command body bypassing :func:`json_error`/:func:`emit_error`.
    """
    for key, value in zip(node.keys, node.values):
        if (
            isinstance(key, ast.Constant)
            and key.value == "success"
            and isinstance(value, ast.Constant)
            and value.value is False
        ):
            return True
    return False


def _find_handrolled_error_envelopes(source: str) -> list[int]:
    """Return the line numbers of hand-rolled error-envelope literals in *source*."""
    tree = ast.parse(source)
    return [
        node.lineno
        for node in ast.walk(tree)
        if isinstance(node, ast.Dict) and _has_success_false_key(node)
    ]


def _scan_cli_package() -> dict[str, list[int]]:
    """Map each offending CLI module (relative path) to its violation line numbers."""
    violations: dict[str, list[int]] = {}
    for path in sorted(_CLI_ROOT.rglob("*.py")):
        relative = path.relative_to(_CLI_ROOT).as_posix()
        if path.name in _ALLOWED:
            continue
        lines = _find_handrolled_error_envelopes(path.read_text(encoding="utf-8"))
        if lines:
            violations[relative] = lines
    return violations


def test_no_handrolled_error_envelopes_in_cli() -> None:
    """No CLI module outside the canonical builder hand-rolls an error envelope.

    A ``{"success": False, "error": ...}`` literal anywhere but ``error_helpers``
    means a ``-j`` error path skipped :func:`json_error`/:func:`emit_error` and so
    risks emitting fewer than the six #884 keys. Route the error through the helper
    instead — it guarantees the full canonical envelope.
    """
    violations = _scan_cli_package()
    assert not violations, (
        "Hand-rolled error envelopes found — route these through "
        "naturo.cli.error_helpers.json_error()/emit_error() so the full six-key "
        "#884 envelope (code, message, category, context, suggested_action, "
        "recoverable) is emitted, not a truncated subset:\n"
        + "\n".join(
            f"  {module}: line(s) {', '.join(map(str, lines))}"
            for module, lines in violations.items()
        )
    )


def test_guard_detects_a_synthetic_handrolled_envelope() -> None:
    """The detector fires on the exact anti-pattern it is meant to catch.

    Pins the guard itself: a future refactor that weakens ``_has_success_false_key``
    (so it silently matches nothing) would make ``test_no_handrolled_error_...``
    vacuously pass. This positive control keeps the guard honest.
    """
    handrolled = (
        'click.echo(json_dumps({"success": False, '
        '"error": {"code": "BOOM", "message": "boom"}}))'
    )
    assert _find_handrolled_error_envelopes(handrolled) == [1]

    # The canonical success envelope (success=True) must NOT trip the guard.
    canonical_success = 'json_dumps({"success": True, "windows": [], "count": 0})'
    assert _find_handrolled_error_envelopes(canonical_success) == []
