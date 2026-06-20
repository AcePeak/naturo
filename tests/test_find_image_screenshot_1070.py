"""Tests for ``naturo find --image --screenshot`` offline matching (#1070) and
template-vs-haystack error attribution (#1067).

#1070: ``--image --screenshot <file>`` must match against the supplied
screenshot, not silently discard the flag and capture the live screen (which
returns confidently-wrong coordinates at ``score 1.0``).

#1067: a template file that exists but cannot be decoded must be attributed to
the template (``INVALID_TEMPLATE``), never mis-reported as a haystack capture
failure (``CAPTURE_FAILED``).

All tests drive the CLI with a mocked capture backend and in-memory images, so
they need neither a desktop session nor the native core DLL — they run on every
CI platform.
"""
from __future__ import annotations

import json

import pytest

# Pillow backs the matcher; skip the whole module where it is unavailable.
pytest.importorskip("PIL")

from click.testing import CliRunner  # noqa: E402
from PIL import Image  # noqa: E402
from unittest.mock import MagicMock, patch  # noqa: E402

from naturo.cli.core import find_cmd  # noqa: E402


def _distinctive_patch(width: int = 24, height: int = 18) -> Image.Image:
    """A patch with strong internal contrast so NCC is well conditioned."""
    patch = Image.new("L", (width, height), 0)
    px = patch.load()
    for y in range(height):
        for x in range(width):
            px[x, y] = 255 if (x // 4 + y // 4) % 2 == 0 else 0
    return patch


def _haystack_with_patch(
    size: tuple[int, int], patch: Image.Image, at: tuple[int, int], background: int = 128,
) -> Image.Image:
    """Build a haystack with ``patch`` pasted at ``at`` over a lightly textured
    background (so the background carries no spurious high-contrast match)."""
    width, height = size
    base = Image.new("L", size, background)
    px = base.load()
    for y in range(height):
        for x in range(width):
            px[x, y] = (background + (x + y) % 7) % 256
    base.paste(patch, at)
    return base


def _backend_capturing(image: Image.Image) -> MagicMock:
    """A backend whose live capture would write ``image`` — used to prove the
    offline path never reaches it."""
    backend = MagicMock()

    def _capture_screen(screen_index: int = 0, output_path: str = "capture.png"):
        image.save(output_path)
        return MagicMock(path=output_path, width=image.width, height=image.height)

    backend.capture_screen.side_effect = _capture_screen
    backend.list_monitors.return_value = [MagicMock(x=0, y=0)]
    return backend


@pytest.fixture
def runner() -> CliRunner:
    return CliRunner()


class TestScreenshotOfflineMatching:
    """--screenshot is honored as the haystack (#1070)."""

    def test_screenshot_is_haystack_not_live_capture(self, runner, tmp_path) -> None:
        patch_img = _distinctive_patch()
        # The screenshot contains the template at a known offset.
        shot = _haystack_with_patch((320, 240), patch_img, at=(60, 90))
        shot_file = tmp_path / "shot.png"
        shot.save(shot_file)
        template_file = tmp_path / "tmpl.png"
        patch_img.save(template_file)

        # The live screen would contain the template at a DIFFERENT offset; if the
        # flag were ignored we would get those coordinates instead.
        live = _haystack_with_patch((320, 240), patch_img, at=(200, 30))
        backend = _backend_capturing(live)

        with patch("naturo.cli.core._common._platform_supports_gui", return_value=True), \
             patch("naturo.cli.core._common._get_backend", return_value=backend):
            result = runner.invoke(
                find_cmd,
                ["--image", str(template_file), "--screenshot", str(shot_file), "--json"],
            )

        assert result.exit_code == 0, result.output
        payload = json.loads(result.output)
        assert payload["count"] == 1
        assert payload["coordinate_frame"] == "screenshot"
        el = payload["elements"][0]
        # Coordinates come from the screenshot (60,90), not the live screen (200,30).
        assert abs(el["x"] - 60) <= 2
        assert abs(el["y"] - 90) <= 2
        backend.capture_screen.assert_not_called()
        backend.capture_window.assert_not_called()

    def test_black_screenshot_yields_no_match(self, runner, tmp_path) -> None:
        """The exact #1070 repro: an all-black screenshot cannot contain the
        template, so the count is 0 — proving the live screen is not captured."""
        patch_img = _distinctive_patch()
        black = Image.new("L", (320, 240), 0)
        black_file = tmp_path / "black.png"
        black.save(black_file)
        template_file = tmp_path / "tmpl.png"
        patch_img.save(template_file)

        # The live screen DOES contain the template; if --screenshot were ignored
        # we would falsely match it at score 1.0.
        live = _haystack_with_patch((320, 240), patch_img, at=(100, 80))
        backend = _backend_capturing(live)

        with patch("naturo.cli.core._common._platform_supports_gui", return_value=True), \
             patch("naturo.cli.core._common._get_backend", return_value=backend):
            result = runner.invoke(
                find_cmd,
                ["--image", str(template_file), "--screenshot", str(black_file),
                 "--threshold", "0.95", "--json"],
            )

        assert result.exit_code == 0, result.output
        payload = json.loads(result.output)
        assert payload["count"] == 0
        backend.capture_screen.assert_not_called()

    def test_screenshot_rejects_window_targeting_flags(self, runner, tmp_path) -> None:
        template_file = tmp_path / "tmpl.png"
        _distinctive_patch().save(template_file)
        shot_file = tmp_path / "shot.png"
        Image.new("L", (50, 50), 128).save(shot_file)

        result = runner.invoke(
            find_cmd,
            ["--image", str(template_file), "--screenshot", str(shot_file),
             "--hwnd", "12345", "--json"],
        )
        assert result.exit_code == 1
        assert json.loads(result.output)["error"]["code"] == "INVALID_INPUT"

    def test_screenshot_file_not_found(self, runner, tmp_path) -> None:
        template_file = tmp_path / "tmpl.png"
        _distinctive_patch().save(template_file)

        result = runner.invoke(
            find_cmd,
            ["--image", str(template_file), "--screenshot",
             str(tmp_path / "missing.png"), "--json"],
        )
        assert result.exit_code == 1
        assert json.loads(result.output)["error"]["code"] == "FILE_NOT_FOUND"

    def test_undecodable_screenshot_attributed_to_screenshot(self, runner, tmp_path) -> None:
        template_file = tmp_path / "tmpl.png"
        _distinctive_patch().save(template_file)
        bad_shot = tmp_path / "shot.png"
        bad_shot.write_text("not an image", encoding="utf-8")

        with patch("naturo.cli.core._common._platform_supports_gui", return_value=True):
            result = runner.invoke(
                find_cmd,
                ["--image", str(template_file), "--screenshot", str(bad_shot), "--json"],
            )
        assert result.exit_code == 1
        assert json.loads(result.output)["error"]["code"] == "INVALID_SCREENSHOT"


class TestTemplateErrorAttribution:
    """A bad template is attributed to the template, not the haystack (#1067)."""

    def test_bad_template_is_invalid_template_not_capture_failed(self, runner, tmp_path) -> None:
        # Template exists but is not a decodable image.
        bad_template = tmp_path / "notimg.txt.png"
        bad_template.write_text("not an image", encoding="utf-8")

        # Live capture succeeds (writes a valid haystack), so the only fault is
        # the template — it must NOT be reported as CAPTURE_FAILED.
        live = _haystack_with_patch((100, 100), _distinctive_patch(), at=(10, 10))
        backend = _backend_capturing(live)

        with patch("naturo.cli.core._common._platform_supports_gui", return_value=True), \
             patch("naturo.cli.core._common._get_backend", return_value=backend):
            result = runner.invoke(
                find_cmd, ["--image", str(bad_template), "--json"],
            )
        assert result.exit_code == 1
        assert json.loads(result.output)["error"]["code"] == "INVALID_TEMPLATE"

    def test_live_path_reports_screen_coordinate_frame(self, runner, tmp_path) -> None:
        """Sanity: the live-capture path is unchanged and labels its frame
        ``screen``."""
        patch_img = _distinctive_patch()
        live = _haystack_with_patch((320, 240), patch_img, at=(100, 80))
        template_file = tmp_path / "tmpl.png"
        patch_img.save(template_file)
        backend = _backend_capturing(live)

        with patch("naturo.cli.core._common._platform_supports_gui", return_value=True), \
             patch("naturo.cli.core._common._get_backend", return_value=backend):
            result = runner.invoke(find_cmd, ["--image", str(template_file), "--json"])

        assert result.exit_code == 0, result.output
        payload = json.loads(result.output)
        assert payload["coordinate_frame"] == "screen"
        assert payload["count"] == 1
        backend.capture_screen.assert_called_once()
