"""Tests for #1022 — output `--path` parent-directory handling.

`capture` and `see` write a screenshot to a user-supplied ``--path``. When the
parent directory did not exist, the underlying ``FileNotFoundError`` leaked out
as a raw ``[Errno 2]`` string and the JSON envelope was mislabeled
(``CAPTURE_ERROR`` with minimized-window guidance for ``capture``,
``UNKNOWN_ERROR`` with no guidance for ``see``).

The fix (option A in the issue) auto-creates the parent directory before the
backend write. If the directory genuinely cannot be created, a clear
``INVALID_INPUT`` error is emitted instead of a raw OS errno.
"""
from __future__ import annotations

import inspect
import json
from dataclasses import dataclass
from unittest.mock import MagicMock, patch

import pytest
from click.testing import CliRunner

import naturo.cli.core._common as _common
from naturo.cli.core._capture import capture
from naturo.cli.core._see import see


@dataclass
class FakeCaptureResult:
    path: str = "/tmp/test.png"
    width: int = 1920
    height: int = 1080
    format: str = "png"
    scale_factor: float = 1.0
    dpi: int = 96


@pytest.fixture
def runner():
    return CliRunner()


def _patch_backend(mock_backend):
    return patch("naturo.cli.core._common._get_backend", return_value=mock_backend)


def _patch_platform(supports=True):
    return patch("naturo.cli.core._common._platform_supports_gui", return_value=supports)


# ── Shared helper: _ensure_output_dir ─────────────────────────────────────────


class TestEnsureOutputDir:
    """Unit tests for the shared parent-directory helper."""

    def test_creates_missing_nested_parent(self, tmp_path):
        target = tmp_path / "a" / "b" / "c" / "shot.png"
        assert not target.parent.exists()
        _common._ensure_output_dir(str(target), json_output=False)
        assert target.parent.is_dir()

    def test_noop_when_parent_exists(self, tmp_path):
        target = tmp_path / "shot.png"  # tmp_path already exists
        _common._ensure_output_dir(str(target), json_output=False)
        assert tmp_path.is_dir()

    def test_bare_filename_does_not_raise(self):
        # No directory component → nothing to create, must not error.
        _common._ensure_output_dir("shot.png", json_output=False)

    def test_uncreatable_dir_raises_invalid_input_json(self, tmp_path):
        # A file occupies what would have to be a directory → makedirs fails.
        blocker = tmp_path / "blocker"
        blocker.write_text("x")
        target = blocker / "sub" / "shot.png"
        with pytest.raises(SystemExit) as exc:
            _common._ensure_output_dir(str(target), json_output=True)
        assert exc.value.code == 1

    def test_uncreatable_dir_plain_message(self, tmp_path, capsys):
        blocker = tmp_path / "blocker"
        blocker.write_text("x")
        target = blocker / "sub" / "shot.png"
        with pytest.raises(SystemExit):
            _common._ensure_output_dir(str(target), json_output=False)
        err = capsys.readouterr().err
        assert "Error:" in err


# ── capture auto-creates the parent directory ─────────────────────────────────


class TestCaptureAutoCreate:

    def test_capture_creates_missing_parent_dir(self, runner, tmp_path):
        target = tmp_path / "no_such_subdir" / "shot.png"
        backend = MagicMock()
        backend.list_monitors.return_value = [MagicMock(index=0)]
        backend.capture_screen.return_value = FakeCaptureResult(path=str(target))
        with _patch_platform(), _patch_backend(backend):
            result = runner.invoke(
                capture, ["-p", str(target), "--no-snapshot"],
                catch_exceptions=False,
            )
        assert result.exit_code == 0
        assert target.parent.is_dir()

    def test_capture_json_success_after_autocreate(self, runner, tmp_path):
        target = tmp_path / "deep" / "nested" / "out.png"
        backend = MagicMock()
        backend.list_monitors.return_value = [MagicMock(index=0)]
        backend.capture_screen.return_value = FakeCaptureResult(path=str(target))
        with _patch_platform(), _patch_backend(backend):
            result = runner.invoke(
                capture, ["-p", str(target), "--json", "--no-snapshot"],
                catch_exceptions=False,
            )
        assert result.exit_code == 0
        data = json.loads(result.output)
        assert data["success"] is True
        assert target.parent.is_dir()

    def test_capture_uncreatable_dir_is_invalid_input_not_capture_error(
        self, runner, tmp_path,
    ):
        # Regression: a save-path failure must NOT be mislabeled as a
        # CAPTURE_ERROR with misleading minimized-window guidance.
        blocker = tmp_path / "blocker"
        blocker.write_text("x")
        target = blocker / "sub" / "shot.png"
        backend = MagicMock()
        backend.capture_screen.return_value = FakeCaptureResult(path=str(target))
        with _patch_platform(), _patch_backend(backend):
            result = runner.invoke(
                capture, ["-p", str(target), "--json", "--no-snapshot"],
                catch_exceptions=False,
            )
        assert result.exit_code != 0
        data = json.loads(result.output)
        assert data["error"]["code"] == "INVALID_INPUT"
        assert "minimized" not in json.dumps(data).lower()
        assert "[errno" not in data["error"]["message"].lower()


# ── Source guard: both commands invoke the helper before the backend write ────


class TestBothCommandsGuardOutputDir:

    @pytest.mark.parametrize("command", [capture, see])
    def test_command_calls_ensure_output_dir(self, command):
        source = inspect.getsource(command.callback)
        assert "_ensure_output_dir" in source, (
            f"{command.name} must call _ensure_output_dir to auto-create the "
            "parent directory of --path (#1022)"
        )
