"""Tests for ``naturo find --ocr`` OCR text finding (#1060, part of #809).

``naturo find --ocr "text"`` recognises on-screen text via the optional RapidOCR
engine and returns the bounding boxes of regions matching the query — so naturo
can target Canvas / game / custom-drawn controls the accessibility tree cannot
see. When the optional ``naturo[ocr]`` extra is absent the command must emit a
recoverable ``OCR_NOT_AVAILABLE`` error with the install hint, never fail opaquely.

These tests inject a fake OCR engine / patch the engine loader and the capture
backend, so they need neither the RapidOCR dependency, a desktop session, nor the
native core DLL — they run on every CI platform.
"""
from __future__ import annotations

import json
import sys

import pytest

# Pillow backs the haystack-dimension read; skip the whole module where absent.
pytest.importorskip("PIL")

from click.testing import CliRunner  # noqa: E402
from PIL import Image  # noqa: E402
from unittest.mock import MagicMock, patch  # noqa: E402

from naturo.cli.core import find_cmd  # noqa: E402
from naturo.errors import ErrorCategory, ErrorCode, category_for_code  # noqa: E402
from naturo.ocr_match import (  # noqa: E402
    OCRNotAvailableError,
    TextMatch,
    find_text,
    load_engine,
)


def _detection(text: str, box: list[list[int]], score: float) -> list:
    """Build one RapidOCR-shaped detection ``[box, text, score]``."""
    return [box, text, score]


def _quad(x: int, y: int, w: int, h: int) -> list[list[int]]:
    """Four corner points (clockwise from top-left) for an axis-aligned box."""
    return [[x, y], [x + w, y], [x + w, y + h], [x, y + h]]


# ── 1. The recognition → coordinate logic (engine injected) ──────────────────


class TestFindTextLogic:
    """``find_text`` converts detections to matches without the real engine."""

    def test_substring_match_is_case_insensitive(self) -> None:
        def engine(_path):
            return (
                [
                    _detection("Start Game", _quad(10, 20, 50, 18), 0.97),
                    _detection("Quit", _quad(10, 60, 30, 18), 0.90),
                ],
                0.01,
            )

        matches = find_text("shot.png", "start", find_all=True, engine=engine)
        assert len(matches) == 1
        m = matches[0]
        assert m.text == "Start Game"
        assert (m.x, m.y, m.width, m.height) == (10, 20, 50, 18)
        assert m.score == pytest.approx(0.97)

    def test_results_sorted_by_descending_confidence(self) -> None:
        def engine(_path):
            return (
                [
                    _detection("score: 10", _quad(0, 0, 40, 12), 0.70),
                    _detection("score: 20", _quad(0, 30, 40, 12), 0.95),
                ],
                0.01,
            )

        matches = find_text("shot.png", "score", find_all=True, engine=engine)
        assert [round(m.score, 2) for m in matches] == [0.95, 0.70]

    def test_find_all_false_returns_single_best(self) -> None:
        def engine(_path):
            return (
                [
                    _detection("score: 10", _quad(0, 0, 40, 12), 0.70),
                    _detection("score: 20", _quad(0, 30, 40, 12), 0.95),
                ],
                0.01,
            )

        matches = find_text("shot.png", "score", find_all=False, engine=engine)
        assert len(matches) == 1
        assert matches[0].score == pytest.approx(0.95)

    def test_no_text_detected_returns_empty(self) -> None:
        # RapidOCR yields ``(None, elapse)`` when it finds no text at all.
        matches = find_text("shot.png", "x", engine=lambda _p: (None, 0.0))
        assert matches == []

    def test_no_match_returns_empty(self) -> None:
        def engine(_path):
            return ([_detection("Hello", _quad(0, 0, 30, 12), 0.9)], 0.01)

        assert find_text("shot.png", "absent", find_all=True, engine=engine) == []

    def test_max_results_truncates(self) -> None:
        def engine(_path):
            return (
                [_detection(f"item {i}", _quad(0, i * 10, 30, 8), 0.9) for i in range(5)],
                0.01,
            )

        matches = find_text("shot.png", "item", find_all=True, max_results=2, engine=engine)
        assert len(matches) == 2


class TestLoadEngine:
    """``load_engine`` fails clearly when the optional extra is missing."""

    def test_missing_rapidocr_raises_ocr_not_available(self, monkeypatch) -> None:
        # Force ``import rapidocr_onnxruntime`` to fail regardless of whether the
        # extra happens to be installed in the test environment.
        monkeypatch.setitem(sys.modules, "rapidocr_onnxruntime", None)
        with pytest.raises(OCRNotAvailableError) as excinfo:
            load_engine()
        assert "naturo[ocr]" in str(excinfo.value)


# ── 2. Error taxonomy ────────────────────────────────────────────────────────


class TestErrorTaxonomy:
    """The new codes are registered with the right category."""

    def test_ocr_not_available_is_configuration(self) -> None:
        assert category_for_code(ErrorCode.OCR_NOT_AVAILABLE) == ErrorCategory.CONFIGURATION

    def test_ocr_failed_is_automation(self) -> None:
        assert category_for_code(ErrorCode.OCR_FAILED) == ErrorCategory.AUTOMATION


# ── 3. CLI dispatch and validation ───────────────────────────────────────────


@pytest.fixture
def runner() -> CliRunner:
    return CliRunner()


@pytest.fixture
def screenshot(tmp_path):
    path = tmp_path / "shot.png"
    Image.new("RGB", (200, 100), "white").save(path)
    return str(path)


class TestOcrCliValidation:
    """Input/strategy validation is platform-invariant and self-attributing."""

    def test_engine_absent_yields_recoverable_ocr_not_available(
        self, runner, screenshot
    ) -> None:
        # Offline --screenshot path needs no GUI gate, so this runs on every OS.
        with patch(
            "naturo.ocr_match.load_engine",
            side_effect=OCRNotAvailableError("install naturo[ocr]"),
        ):
            result = runner.invoke(
                find_cmd, ["--ocr", "Start", "--screenshot", screenshot, "--json"]
            )
        assert result.exit_code == 1
        err = json.loads(result.output)["error"]
        assert err["code"] == "OCR_NOT_AVAILABLE"
        assert err["category"] == "configuration"
        assert err["recoverable"] is True
        assert err["suggested_action"]

    def test_missing_text_is_invalid_input(self, runner, screenshot) -> None:
        result = runner.invoke(find_cmd, ["--ocr", "--screenshot", screenshot, "--json"])
        assert result.exit_code == 1
        assert json.loads(result.output)["error"]["code"] == "INVALID_INPUT"

    def test_screenshot_rejects_window_targeting_flags(self, runner, screenshot) -> None:
        result = runner.invoke(
            find_cmd,
            ["--ocr", "Start", "--screenshot", screenshot, "--hwnd", "123", "--json"],
        )
        assert result.exit_code == 1
        assert json.loads(result.output)["error"]["code"] == "INVALID_INPUT"

    def test_missing_screenshot_is_file_not_found(self, runner, tmp_path) -> None:
        result = runner.invoke(
            find_cmd,
            ["--ocr", "Start", "--screenshot", str(tmp_path / "nope.png"), "--json"],
        )
        assert result.exit_code == 1
        assert json.loads(result.output)["error"]["code"] == "FILE_NOT_FOUND"

    @pytest.mark.parametrize(
        "extra_flag,template_needed",
        [(["--ai"], False), (["--image"], True), (["--selector", "//Button"], False)],
    )
    def test_mutually_exclusive_strategies(
        self, runner, screenshot, extra_flag, template_needed
    ) -> None:
        args = ["--ocr", "Start", "--json"]
        if template_needed:
            args = ["--ocr", "--image", screenshot, "--json"]
        else:
            args += extra_flag
        result = runner.invoke(find_cmd, args)
        assert result.exit_code == 1
        assert json.loads(result.output)["error"]["code"] == "INVALID_INPUT"


class TestOcrCliResults:
    """Successful OCR builds the snapshot envelope with the right coordinates."""

    def test_offline_screenshot_envelope(self, runner, screenshot) -> None:
        def fake(path, text, *, find_all=False, max_results=50):
            return [TextMatch(text="Start Game", x=10, y=20, width=50, height=18, score=0.97)]

        with patch("naturo.ocr_match.find_text", side_effect=fake):
            result = runner.invoke(
                find_cmd, ["--ocr", "start", "--screenshot", screenshot, "--json"]
            )
        assert result.exit_code == 0, result.output
        payload = json.loads(result.output)
        assert payload["success"] is True
        assert payload["count"] == 1
        assert payload["coordinate_frame"] == "screenshot"
        el = payload["elements"][0]
        assert el["text"] == "Start Game"
        # Screenshot-relative coordinates: no window/monitor origin added.
        assert (el["x"], el["y"]) == (10, 20)
        assert el["center_x"] == 10 + 50 // 2
        assert el["ref"]  # a stable eN ref for `naturo click`

    def test_live_capture_adds_monitor_origin(self, runner) -> None:
        """The live path is screen-absolute: the monitor origin is added to the
        match coordinates (the contract the --image path shares)."""

        def fake(path, text, *, find_all=False, max_results=50):
            return [TextMatch(text="Score", x=5, y=5, width=40, height=12, score=0.88)]

        backend = MagicMock()

        def _capture_screen(screen_index: int = 0, output_path: str = "c.png"):
            Image.new("RGB", (300, 200), "white").save(output_path)

        backend.capture_screen.side_effect = _capture_screen
        backend.list_monitors.return_value = [MagicMock(x=1000, y=500)]

        with patch("naturo.cli.core._common._platform_supports_gui", return_value=True), \
             patch("naturo.cli.core._common._get_backend", return_value=backend), \
             patch("naturo.ocr_match.find_text", side_effect=fake):
            result = runner.invoke(find_cmd, ["--ocr", "score", "--json"])

        assert result.exit_code == 0, result.output
        payload = json.loads(result.output)
        assert payload["coordinate_frame"] == "screen"
        el = payload["elements"][0]
        assert (el["x"], el["y"]) == (1005, 505)

    def test_no_match_is_success_with_zero_count(self, runner, screenshot) -> None:
        with patch("naturo.ocr_match.find_text", return_value=[]):
            result = runner.invoke(
                find_cmd, ["--ocr", "absent", "--screenshot", screenshot, "--json"]
            )
        assert result.exit_code == 0, result.output
        payload = json.loads(result.output)
        assert payload["success"] is True
        assert payload["count"] == 0

    def test_engine_fault_is_ocr_failed(self, runner, screenshot) -> None:
        with patch("naturo.ocr_match.find_text", side_effect=RuntimeError("boom")):
            result = runner.invoke(
                find_cmd, ["--ocr", "x", "--screenshot", screenshot, "--json"]
            )
        assert result.exit_code == 1
        err = json.loads(result.output)["error"]
        assert err["code"] == "OCR_FAILED"
        assert err["category"] == "automation"
