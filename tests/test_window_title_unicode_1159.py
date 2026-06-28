"""Live round-trip of non-codepage window titles through the native core (#1159).

These prove that ``list_windows`` (and therefore ``app list`` / ``app windows``
/ ``app find``, which all funnel through it) preserves window titles containing
characters outside the active ANSI codepage — emoji and cross-script text.

Before #1159 the native core read titles with the narrow ``GetWindowTextA``
Win32 API, which encodes its result in the system ANSI codepage and silently
replaces every character it cannot represent with ``'?'`` (U+003F) — *before*
Python ever sees the bytes, so the loss is irreversible.  On a Chinese-locale
(cp936) desktop that corrupts emoji, Japanese kana, etc.  The fix reads titles
via the wide ``GetWindowTextW`` API and converts to UTF-8, which the Python
bridge already decodes losslessly (``_decode_native`` tries UTF-8 first).

The fixture is a tiny WinForms window driven by PowerShell (present on any
interactive Windows desktop) whose title mixes a BMP emoji (U+2733), Japanese,
Cyrillic, and an astral-plane emoji (U+1F600, a 4-byte UTF-8 / surrogate-pair
case).  The tests are ``@pytest.mark.desktop`` because they launch a real GUI
window and call the native DLL; when that environment is absent the whole
module is skipped (it never runs on the headless CI runners).
"""
from __future__ import annotations

import os
import platform
import shutil
import subprocess
import tempfile
import time
from typing import Optional

import pytest

from naturo.backends.base import get_backend

pytestmark = pytest.mark.desktop

#: Characters chosen to exercise distinct UTF-8 widths and codepage gaps:
#:   * U+2733 EIGHT SPOKED ASTERISK — BMP symbol absent from cp936 (the headline
#:     data-loss case from the issue), 3-byte UTF-8.
#:   * Japanese ideographs / Cyrillic — cross-script, present in cp936 but not in
#:     a Western codepage; together they prove the path is codepage-independent.
#:   * U+1F600 GRINNING FACE — astral plane, 4-byte UTF-8 / UTF-16 surrogate pair.
_EMOJI_BMP = "✳"
_JAPANESE = "日本語"
_CYRILLIC = "Ки"
_EMOJI_ASTRAL = "\U0001f600"

#: Unique per-process marker (pure ASCII, so the host codepage cannot mangle it
#: and a fixture run never matches a stray window).
_MARKER = f"naturo_unicode_1159_{os.getpid()}"

#: WinForms fixture.  ``-STA`` is required for WinForms message pumping; the
#: Timer backstop is a one-shot so an orphaned process self-exits even if
#: teardown is skipped.  The title is built from explicit code points rather
#: than from literal characters in the script body, because Windows PowerShell
#: reads a no-BOM ``.ps1`` as the active ANSI codepage and would itself mangle
#: any non-codepage literal before the window is ever created — that would test
#: PowerShell's file decoding, not naturo's core read path.
_FIXTURE_PS1 = r"""
Add-Type -AssemblyName System.Windows.Forms
$title = "__MARKER__" + " " + [char]0x2733 + " " `
    + [char]0x65E5 + [char]0x672C + [char]0x8A9E + " " `
    + [char]0x041A + [char]0x0438 + " " `
    + [System.Char]::ConvertFromUtf32(0x1F600)
$form = New-Object System.Windows.Forms.Form
$form.Text = $title
$form.Width = 360
$form.Height = 140
$timer = New-Object System.Windows.Forms.Timer
$timer.Interval = 60000
$timer.Add_Tick({ $form.Close() })
$timer.Start()
$form.Add_Shown({ $form.Activate() })
[System.Windows.Forms.Application]::Run($form)
"""


def _fixture_available() -> bool:
    """Whether this host can launch the PowerShell/WinForms fixture."""
    return platform.system() == "Windows" and shutil.which("powershell") is not None


requires_fixture = pytest.mark.skipif(
    not _fixture_available(),
    reason="requires an interactive Windows desktop with PowerShell + WinForms",
)


@pytest.fixture(scope="module")
def fixture_title() -> str:
    """Launch the WinForms fixture and return its title as ``list_windows`` sees it.

    Yields the title string read back from the native core for the fixture
    window, so each test can assert on the round-tripped value.  Tears the
    fixture process down afterwards.
    """
    if not _fixture_available():
        pytest.skip("PowerShell/WinForms fixture unavailable on this host")

    script = _FIXTURE_PS1.replace("__MARKER__", _MARKER)
    script_dir = tempfile.mkdtemp(prefix="naturo_unicode_1159_")
    script_path = os.path.join(script_dir, "fixture.ps1")
    with open(script_path, "w", encoding="utf-8") as handle:
        handle.write(script)

    proc = subprocess.Popen(
        ["powershell", "-NoProfile", "-STA", "-ExecutionPolicy", "Bypass", "-File", script_path],
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
    )
    try:
        backend = get_backend()
        title: Optional[str] = None
        deadline = time.monotonic() + 30.0
        while time.monotonic() < deadline:
            for window in backend.list_windows():
                if _MARKER in (window.title or ""):
                    title = window.title
                    break
            if title is not None:
                break
            time.sleep(0.5)
        else:
            pytest.fail(
                f"WinForms fixture window '{_MARKER}' never appeared in list_windows()"
            )
        yield title
    finally:
        proc.terminate()
        try:
            proc.wait(timeout=5)
        except subprocess.TimeoutExpired:
            proc.kill()
        shutil.rmtree(script_dir, ignore_errors=True)


@requires_fixture
def test_bmp_emoji_preserved(fixture_title: str) -> None:
    """A BMP emoji outside the ANSI codepage survives the core read path."""
    assert _EMOJI_BMP in fixture_title


@requires_fixture
def test_cross_script_text_preserved(fixture_title: str) -> None:
    """Japanese and Cyrillic characters round-trip losslessly."""
    assert _JAPANESE in fixture_title
    assert _CYRILLIC in fixture_title


@requires_fixture
def test_astral_emoji_preserved(fixture_title: str) -> None:
    """An astral-plane emoji (4-byte UTF-8 / surrogate pair) round-trips."""
    assert _EMOJI_ASTRAL in fixture_title


@requires_fixture
def test_no_replacement_or_question_mark(fixture_title: str) -> None:
    """No character is lost to the ANSI ``'?'`` (or Unicode replacement) fallback.

    The fixture title contains no literal ``'?'`` or U+FFFD, so either appearing
    in the round-tripped title means a character was destroyed on the read path.
    """
    assert "?" not in fixture_title
    assert "�" not in fixture_title
