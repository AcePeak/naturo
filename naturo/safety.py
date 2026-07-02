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
opt-in.  The guard activates when **either** of two independent signals is
present (#972):

* the ``NATURO_SAFE_INPUT=1`` environment variable, or
* a sentinel lock file at ``~/.naturo/safe-input.lock``.

The sentinel file exists because the environment variable alone proved
fragile: it has to be inherited by every process in the chain that ultimately
injects keystrokes, and on 2026-06-17 a QA cycle still typed ``$(rm -rf /)``
because the opt-in env var was not effective for that cycle.  A file-based
signal survives across process boundaries with no env-inheritance dependency,
so the loop drops the lock once and every later ``naturo`` invocation sees it.

Normal users — for whom typing shell commands into an editor is a legitimate
use of a general automation tool — are unaffected: neither signal is present
for interactive/TTY use, so the guard stays off.

The matcher is deliberately conservative: for a destructive-command blocker a
false positive (refusing a benign-but-suspicious string in a QA probe) is
cheap, while a false negative is catastrophic.
"""
from __future__ import annotations

import os
import re
from pathlib import Path
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


def _safe_input_lock_path() -> Path:
    """Return the path to the sentinel lock file that activates the guard.

    Uses the same ``~/.naturo`` directory naturo already uses for snapshots,
    app-id maps and other per-user state, so the signal lives alongside the
    rest of naturo's runtime files.  Resolved on each call (not cached) so a
    test that points ``HOME``/``USERPROFILE`` at a temporary directory, or a
    user whose home moves, is honoured.
    """
    return Path.home() / ".naturo" / "safe-input.lock"


def _safe_input_active() -> bool:
    """Return whether the opt-in input-content guard is currently active.

    The guard activates when **either** signal is present (#972):

    * the ``NATURO_SAFE_INPUT`` environment variable is exactly ``"1"``, or
    * the sentinel lock file ``~/.naturo/safe-input.lock`` exists.

    Either signal alone is sufficient.  The env var is kept as a fallback for
    callers that still set it, but the file-based signal is the robust primary
    because it does not depend on environment inheritance across process
    boundaries.  When neither is present the guard is a no-op, so interactive
    and normal-user sessions are never affected.
    """
    if os.environ.get(SAFE_INPUT_ENV) == "1":
        return True
    try:
        return _safe_input_lock_path().exists()
    except (OSError, RuntimeError):
        # Probing the sentinel must never crash input.  ``Path.home()`` raises
        # ``RuntimeError`` when the home directory cannot be determined (e.g. no
        # HOME/USERPROFILE), and ``exists()`` can raise ``OSError``; in either
        # case fall back to "not active via the file" (env was already checked).
        return False


def is_safe_input_enabled() -> bool:
    """Return whether the opt-in input-content guard is active.

    Retained as the stable public name; delegates to :func:`_safe_input_active`
    so the env var **or** the sentinel lock file enables the guard.

    Returns:
        ``True`` when ``NATURO_SAFE_INPUT`` is exactly ``"1"`` or the sentinel
        file ``~/.naturo/safe-input.lock`` exists; otherwise ``False`` so
        normal users are never affected.
    """
    return _safe_input_active()


def contains_dangerous_input(text: Optional[str]) -> Optional[str]:
    """Return why ``text`` looks like shell-command content, or ``None``.

    This is the *ungated* matcher: unlike :func:`unsafe_input_reason`, it does
    **not** consult :func:`is_safe_input_enabled`, so it classifies content the
    same way whether or not the opt-in runtime guard is armed.  It carries no
    policy of its own — it never blocks anything — and so does not change
    runtime behaviour.  It exists so a safety *backstop* (e.g. the test-suite
    tripwire that refuses live keystrokes of shell metacharacters, #976) can
    detect the unsafe shape unconditionally, since such a backstop must hold
    regardless of whether a given run happened to arm the opt-in guard.

    Args:
        text: The literal content that would be injected as keystrokes (or via
            clipboard paste).  ``None`` or empty text is always safe.

    Returns:
        A short human-readable reason (e.g. ``"destructive command 'rm'"``)
        when the content matches a dangerous pattern; otherwise ``None``.
    """
    if not text:
        return None
    for reason, pattern in _DANGEROUS_PATTERNS:
        if pattern.search(text):
            return reason
    return None


def unsafe_input_reason(text: Optional[str]) -> Optional[str]:
    """Return why ``text`` is unsafe to inject, or ``None`` if it may proceed.

    The guard is a no-op (always returns ``None``) when it is inactive — that
    is, when neither ``NATURO_SAFE_INPUT=1`` nor the sentinel lock file
    ``~/.naturo/safe-input.lock`` is present — so callers can invoke this
    unconditionally before typing/pasting without affecting normal users.  When
    the guard is active it delegates to :func:`contains_dangerous_input` for the
    actual content classification.

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
    return contains_dangerous_input(text)
