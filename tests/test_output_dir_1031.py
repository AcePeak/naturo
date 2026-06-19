"""Tests for #1031 — `_ensure_output_dir` must not leak localized OS text.

The shared :func:`naturo.cli.core._common._ensure_output_dir` helper (used by
``capture``, ``see``, ``selector export``, ``record export`` and
``visual diff`` for the uncreatable ``--path``/``-o`` parent-dir case) built an
English error message but interpolated the raw OS ``strerror``, which the
platform renders in the **system locale**. On a non-English Windows that leaked
a verbatim localized substring (e.g. the zh-CN "系统找不到指定的路径。") into the
otherwise all-English ``INVALID_INPUT`` message / ``-j`` contract.

The fix maps the ``OSError`` to a stable English reason by ``errno`` (keeping
the numeric errno for diagnostics, never the localized text), so the
user-facing message is ASCII/English-only regardless of system locale.
"""
from __future__ import annotations

import errno
import json
from unittest.mock import patch

import pytest

import naturo.cli.core._common as _common

# A deliberately non-ASCII (zh-CN) OS strerror, as produced on a localized
# Windows for ERROR_PATH_NOT_FOUND. This is exactly what used to leak.
_LOCALIZED_STRERROR = "系统找不到指定的路径。"


def _run_ensure_output_dir(capsys, *, json_output: bool, exc: OSError):
    """Drive ``_ensure_output_dir`` against a forced ``makedirs`` failure.

    Returns the captured ``(stdout, stderr)`` produced by the helper before it
    raised ``SystemExit``.
    """
    # A parent that does not exist yet, so the helper attempts ``makedirs``.
    path = "no_such_dir_1031/sub/out.png"
    with patch.object(_common.os.path, "isdir", return_value=False), \
            patch.object(_common.os, "makedirs", side_effect=exc):
        with pytest.raises(SystemExit) as excinfo:
            _common._ensure_output_dir(path, json_output)
    assert excinfo.value.code == 1
    return capsys.readouterr()


def _message_is_english_only(message: str) -> None:
    """A user-facing message must be ASCII/English-only (no localized OS text)."""
    assert message.isascii(), f"non-ASCII text leaked into message: {message!r}"
    assert _LOCALIZED_STRERROR not in message


class TestEnsureOutputDirEnglishOnly:
    def test_json_envelope_has_no_localized_text(self, capsys):
        exc = OSError(errno.ENOENT, _LOCALIZED_STRERROR)
        out, _err = _run_ensure_output_dir(capsys, json_output=True, exc=exc)

        data = json.loads(out)
        assert data["success"] is False
        assert data["error"]["code"] == "INVALID_INPUT"
        _message_is_english_only(data["error"]["message"])
        # The mapped English reason for a missing path component is surfaced.
        assert "missing" in data["error"]["message"]
        # errno is preserved for diagnostics (the number, not localized text).
        assert "errno 2" in data["error"]["message"]

    def test_plain_text_error_has_no_localized_text(self, capsys):
        exc = OSError(errno.ENOENT, _LOCALIZED_STRERROR)
        _out, err = _run_ensure_output_dir(capsys, json_output=False, exc=exc)

        assert err.startswith("Error:")
        _message_is_english_only(err)

    def test_permission_denied_maps_to_english(self, capsys):
        exc = OSError(errno.EACCES, _LOCALIZED_STRERROR)
        out, _err = _run_ensure_output_dir(capsys, json_output=True, exc=exc)

        message = json.loads(out)["error"]["message"]
        _message_is_english_only(message)
        assert "permission denied" in message

    def test_unknown_errno_falls_back_to_english(self, capsys):
        # An OSError carrying only a localized strerror and an errno we do not
        # map must still produce English-only output (never the raw strerror).
        exc = OSError(errno.EBUSY, _LOCALIZED_STRERROR)
        out, _err = _run_ensure_output_dir(capsys, json_output=True, exc=exc)

        _message_is_english_only(json.loads(out)["error"]["message"])

    def test_errno_none_falls_back_to_english(self, capsys):
        exc = OSError()  # no errno, no strerror
        out, _err = _run_ensure_output_dir(capsys, json_output=True, exc=exc)

        _message_is_english_only(json.loads(out)["error"]["message"])
