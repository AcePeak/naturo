"""Regression test for #1146.

`naturo find --help` documented a bare ``@save-btn`` / ``@name`` saved-selector
form, but the resolver requires the two-part ``@app/name`` shape and rejects the
bare form at parse time with::

    Invalid selector reference '@save-btn': expected @app/name format

A user copy-pasting the documented example hit an error. This test pins the help
text to the actual parse contract: every saved-selector (``@...``) example shown
in ``find``'s help must be in a format the resolver accepts.
"""
from __future__ import annotations

import re

import click
import pytest

from naturo.cli.core import find_cmd
from naturo.cli.selector_cmd import resolve_named_selector

# A standalone saved-selector argument: an ``@`` token preceded by whitespace
# (so XPath attribute syntax like ``[@name="Save"]`` — preceded by ``[`` — is
# excluded) and made of name chars, optionally with one ``/`` separator.
_SAVED_SELECTOR_RE = re.compile(r"(?:^|\s)(@[A-Za-z0-9_.-]+(?:/[A-Za-z0-9_.-]+)?)")


def _find_help_text() -> str:
    """All saved-selector-bearing help a user sees in ``naturo find --help``:
    the command docstring plus every option's ``help`` string (the ``--selector``
    option, for one, documents the saved form there — not in the docstring)."""
    parts = [find_cmd.help or ""]
    parts.extend(param.help or "" for param in find_cmd.params
                 if isinstance(param, click.Option))
    return "\n".join(parts)


def _saved_selector_examples() -> list[str]:
    return _SAVED_SELECTOR_RE.findall(_find_help_text())


def test_find_help_advertises_saved_selector_examples() -> None:
    """Guard against the regex silently matching nothing (which would make the
    contract assertion below vacuously pass)."""
    assert _saved_selector_examples(), (
        "expected at least one '@...' saved-selector example in find --help"
    )


@pytest.mark.parametrize("reference", _saved_selector_examples())
def test_find_help_saved_selector_examples_parse(reference: str) -> None:
    """Every ``@...`` example in find's help must satisfy the resolver's
    ``@app/name`` parse contract (a missing selector raises ``KeyError`` — that
    is fine; an invalid *format* raises ``ValueError`` — that is the #1146 bug)."""
    try:
        resolve_named_selector(reference)
    except ValueError as exc:  # invalid format == documented-but-rejected
        pytest.fail(
            f"find --help shows saved-selector example {reference!r} that the "
            f"resolver rejects as malformed: {exc}"
        )
    except KeyError:
        # Well-formed @app/name, just not a real saved selector — acceptable.
        pass
