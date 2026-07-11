"""Shared bounded value-preview policy for ``see`` / ``see_ui_tree`` output.

Text elements (Document / Edit / Text) can hold an entire document. Dumping the
full value into the default tree output would blow the token-lean budget that
compact mode exists to protect — a 10 KB Notepad buffer becomes a 10 KB line.

So the default is a *bounded* preview: short values render in full (a search
box, a checkbox label, a few lines — the common case, unchanged), while long
values are truncated to :data:`PREVIEW_LEN` with a marker saying how much was
elided. The complete text is always one ``get eN`` away (which returns the whole
document via TextPattern), and callers that genuinely want everything inline —
"dump all visible text and search it" — opt in with ``full=True``
(``--full-text`` on the CLI, ``full_text=true`` over MCP).
"""
from __future__ import annotations

# Characters of an element value shown inline before truncating. Chosen to keep
# a single tree line small while still carrying enough text for most at-a-glance
# reads and content matches.
PREVIEW_LEN = 200


def bounded_value(value: str, *, full: bool = False) -> tuple[str, int]:
    """Bound ``value`` for inline tree display.

    Returns ``(shown, elided)`` where ``shown`` is the text to display and
    ``elided`` is the number of trailing characters dropped (0 when the whole
    value is shown). ``full=True`` always returns the complete value.
    """
    if full or len(value) <= PREVIEW_LEN:
        return value, 0
    return value[:PREVIEW_LEN], len(value) - PREVIEW_LEN
