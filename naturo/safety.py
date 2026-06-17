"""Opt-in input-content safety guard for unattended/agent sessions (#960).

``SendInput`` is global: it delivers keystrokes to whatever window owns the
foreground at the moment of injection.  In an unattended automation loop a focus
race can therefore route part of a keystroke stream to the *wrong* window —
including a terminal.  An autonomous QA agent once improvised a
``"test$(rm -rf /)"`` probe string and a truncated ``est$(rm -rf /)`` fragment
was observed reaching a command line.  Had a runnable fragment landed followed
by Enter, it could have wiped the machine.

Instruction-level guardrails are necessary but not sufficient once an agent can
improvise input, so this module adds *code* enforcement.  It is strictly
opt-in: the guard activates only when ``NATURO_SAFE_INPUT=1`` is set in the
environment (the unattended QA role sets it).  Normal users — for whom typing
shell commands into an editor is a legitimate use of a general automation tool —
are unaffected when the variable is unset.

The matcher is deliberately conservative: for a destructive-command blocker a
false positive (refusing a benign-but-suspicious string in a QA probe) is
cheap, while a false negative is catastrophic.
"""
from __future__ import annotations

import os
import re
from typing import Optional

#: Environment variable that, when set to ``"1"``, enables the input guard.
SAFE_INPUT_ENV = "NATURO_SAFE_INPUT"

#: Error code returned when injection is refused because the content is unsafe.
UNSAFE_INPUT_CODE = "UNSAFE_INPUT_BLOCKED"

# Dangerous content patterns, paired with a human-readable reason for the error
# message.  Order matters only for which reason is reported first; the more
# specific shell operators precede the generic single-character ones so the
# message is as descriptive as possible.  Command verbs use word boundaries so
# benign substrings ("warm", "delete", "reformatted") do not trip the guard.
_DANGEROUS_PATTERNS: tuple[tuple[str, "re.Pattern[str]"], ...] = (
    ("command substitution '$(...)'", re.compile(r"\$\(")),
    ("backtick command substitution", re.compile(r"`")),
    ("logical AND '&&'", re.compile(r"&&")),
    ("logical OR '||'", re.compile(r"\|\|")),
    ("command separator ';'", re.compile(r";")),
    ("pipe '|'", re.compile(r"\|")),
    ("output redirect '>'", re.compile(r">")),
    ("input redirect '<'", re.compile(r"<")),
    ("destructive command 'rm'", re.compile(r"\brm\b", re.IGNORECASE)),
    ("destructive command 'rmdir'", re.compile(r"\brmdir\b", re.IGNORECASE)),
    ("destructive command 'del'", re.compile(r"\bdel\b", re.IGNORECASE)),
    ("destructive command 'format'", re.compile(r"\bformat\b", re.IGNORECASE)),
    ("destructive command 'shutdown'", re.compile(r"\bshutdown\b", re.IGNORECASE)),
    ("privilege escalation 'sudo'", re.compile(r"\bsudo\b", re.IGNORECASE)),
)


def is_safe_input_enabled() -> bool:
    """Return whether the opt-in input-content guard is active.

    Returns:
        ``True`` only when the ``NATURO_SAFE_INPUT`` environment variable is
        exactly ``"1"``.  Any other value (including unset) leaves the guard
        disabled so normal users are never affected.
    """
    return os.environ.get(SAFE_INPUT_ENV) == "1"


def unsafe_input_reason(text: Optional[str]) -> Optional[str]:
    """Return why ``text`` is unsafe to inject, or ``None`` if it may proceed.

    The guard is a no-op (always returns ``None``) when
    ``NATURO_SAFE_INPUT`` is not set to ``"1"``, so callers can invoke this
    unconditionally before typing/pasting without affecting normal users.

    Args:
        text: The literal content that would be injected as keystrokes (or via
            clipboard paste).  ``None`` or empty text is always safe.

    Returns:
        A short human-readable reason (e.g. ``"destructive command 'rm'"``)
        when the guard is enabled and the content matches a dangerous pattern;
        otherwise ``None``.
    """
    if not is_safe_input_enabled():
        return None
    if not text:
        return None
    for reason, pattern in _DANGEROUS_PATTERNS:
        if pattern.search(text):
            return reason
    return None
