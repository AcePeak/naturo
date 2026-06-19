"""Tests for #1029 — `--output`/`-o` parent-directory handling for export commands.

Follow-on to #1022 (capture/see ``--path``). The output-writing commands
``selector export``, ``record export`` and ``visual diff`` opened the
``--output`` file with a bare ``open()`` (selector/record) or let
``visual.compare_images`` create the directory unguarded. When the parent
directory was missing or uncreatable they leaked a raw Python traceback to
stderr and — fatally for an agent — ignored the ``-j`` JSON contract, emitting
no error envelope at all.

The fix routes every ``--output`` write through
:func:`naturo.cli.core._common._ensure_output_dir` *before* opening the file,
mirroring #1022's option A: a normally-missing parent is auto-created, and a
genuinely uncreatable parent yields a clean ``INVALID_INPUT`` envelope (``-j``)
or a one-line ``Error:`` (otherwise) — never a raw traceback or ``[Errno 2]``.
"""
from __future__ import annotations

import json
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest
from click.testing import CliRunner

from naturo import recording as rec_mod
from naturo.cli import main, selector_cmd
from naturo.recording import ActionStep, Recording, save_recording


@pytest.fixture()
def runner():
    return CliRunner()


@pytest.fixture()
def tmp_selectors(tmp_path):
    """Patch SELECTORS_DIR so selector writes/reads stay in a temp dir."""
    with patch.object(selector_cmd, "SELECTORS_DIR", tmp_path):
        yield tmp_path


@pytest.fixture()
def tmp_recordings(tmp_path):
    """Patch RECORDINGS_DIR so recording reads stay in a temp dir."""
    with patch.object(rec_mod, "RECORDINGS_DIR", tmp_path):
        yield tmp_path


def _save_sample_recording() -> str:
    """Persist a small recording and return its id."""
    rec = Recording(
        name="Export Flow",
        recording_id="rec_20260401_120000",
        created_at="2026-04-01T12:00:00",
    )
    rec.steps = [ActionStep("click", {"x": 1, "y": 2}, 1000.0)]
    save_recording(rec)
    return rec.recording_id


def _assert_no_raw_traceback(result) -> None:
    """A handled error must never surface a Python traceback or raw OS errno."""
    combined = result.output + (str(result.exception) if result.exception else "")
    assert "Traceback (most recent call last)" not in result.output
    assert "[Errno 2]" not in combined
    assert "No such file or directory" not in combined


# ── selector export ───────────────────────────────────────────────────────────


class TestSelectorExportOutputDir:
    def test_missing_parent_is_auto_created(self, runner, tmp_selectors, tmp_path):
        runner.invoke(main, ["selector", "save", "notepad", "btn", "app://notepad/btn"])
        out = tmp_path / "missing_sub" / "sel.json"
        assert not out.parent.exists()

        result = runner.invoke(main, [
            "-j", "selector", "export", "notepad", "-o", str(out),
        ])

        assert result.exit_code == 0, result.output
        assert out.exists()
        data = json.loads(result.output)
        assert data["success"] is True
        assert data["path"] == str(out)

    def test_uncreatable_parent_yields_invalid_input_envelope(
        self, runner, tmp_selectors, tmp_path,
    ):
        runner.invoke(main, ["selector", "save", "notepad", "btn", "app://notepad/btn"])
        blocker = tmp_path / "afile"
        blocker.write_text("not a directory")
        out = blocker / "sub" / "sel.json"  # parent path traverses a file

        result = runner.invoke(main, [
            "-j", "selector", "export", "notepad", "-o", str(out),
        ])

        assert result.exit_code == 1
        _assert_no_raw_traceback(result)
        data = json.loads(result.output)
        assert data["error"]["code"] == "INVALID_INPUT"
        assert not out.exists()

    def test_uncreatable_parent_plain_text_error(
        self, runner, tmp_selectors, tmp_path,
    ):
        runner.invoke(main, ["selector", "save", "notepad", "btn", "app://notepad/btn"])
        blocker = tmp_path / "afile"
        blocker.write_text("not a directory")
        out = blocker / "sub" / "sel.json"

        result = runner.invoke(main, [
            "selector", "export", "notepad", "-o", str(out),
        ])

        assert result.exit_code == 1
        _assert_no_raw_traceback(result)
        assert "Error:" in result.output


# ── record export ─────────────────────────────────────────────────────────────


class TestRecordExportOutputDir:
    def test_missing_parent_is_auto_created(self, runner, tmp_recordings, tmp_path):
        _save_sample_recording()
        out = tmp_path / "missing_sub" / "script.json"
        assert not out.parent.exists()

        result = runner.invoke(main, [
            "-j", "record", "export", "rec_20260401_120000",
            "--format", "json", "-o", str(out),
        ])

        assert result.exit_code == 0, result.output
        assert out.exists()
        data = json.loads(result.output)
        assert data["success"] is True
        assert data["path"] == str(out)

    def test_uncreatable_parent_yields_invalid_input_envelope(
        self, runner, tmp_recordings, tmp_path,
    ):
        _save_sample_recording()
        blocker = tmp_path / "afile"
        blocker.write_text("not a directory")
        out = blocker / "sub" / "script.json"

        result = runner.invoke(main, [
            "-j", "record", "export", "rec_20260401_120000",
            "--format", "json", "-o", str(out),
        ])

        assert result.exit_code == 1
        _assert_no_raw_traceback(result)
        data = json.loads(result.output)
        assert data["error"]["code"] == "INVALID_INPUT"
        assert not out.exists()


# ── visual diff ───────────────────────────────────────────────────────────────


class TestVisualDiffOutputDir:
    """``visual diff`` pre-validates the ``-o`` parent before comparing.

    ``compare_images`` is patched so the test exercises only the CLI-layer
    directory handling and does not require the imaging dependencies.
    """

    @pytest.fixture()
    def images(self, tmp_path):
        img1 = tmp_path / "a.png"
        img2 = tmp_path / "b.png"
        img1.write_bytes(b"\x89PNG\r\n\x1a\n")
        img2.write_bytes(b"\x89PNG\r\n\x1a\n")
        return str(img1), str(img2)

    def test_missing_parent_is_auto_created(self, runner, tmp_path, images):
        img1, img2 = images
        out = tmp_path / "missing_sub" / "diff.png"
        fake = MagicMock()
        fake.to_dict.return_value = {"match": True, "similarity": 1.0}

        with patch("naturo.cli.visual_cmd.compare_images", return_value=fake) as cmp_mock:
            result = runner.invoke(main, [
                "-j", "visual", "diff", img1, img2, "-o", str(out),
            ])

        assert result.exit_code == 0, result.output
        assert out.parent.is_dir()
        cmp_mock.assert_called_once()

    def test_uncreatable_parent_yields_invalid_input_envelope(
        self, runner, tmp_path, images,
    ):
        img1, img2 = images
        blocker = tmp_path / "afile"
        blocker.write_text("not a directory")
        out = blocker / "sub" / "diff.png"

        with patch("naturo.cli.visual_cmd.compare_images") as cmp_mock:
            result = runner.invoke(main, [
                "-j", "visual", "diff", img1, img2, "-o", str(out),
            ])

        assert result.exit_code == 1
        _assert_no_raw_traceback(result)
        data = json.loads(result.output)
        assert data["error"]["code"] == "INVALID_INPUT"
        cmp_mock.assert_not_called()  # fail fast, before the comparison runs
