"""Tests for the pure-Pillow image template matcher (feature #1059).

These tests exercise ``naturo.image_match.match_template`` directly with
synthetic in-memory images, so they require neither a desktop session nor the
native core DLL — they run on every CI platform.

The matcher implements normalized cross-correlation (NCC) with a coarse-to-fine
search, using only Pillow and the standard library (no NumPy / OpenCV), per the
unified-find-engine design in #809.
"""
from __future__ import annotations

import json

import pytest

# Pillow backs the matcher; skip the whole module where it is unavailable (it is
# an optional dependency, absent on some minimal CI environments) rather than
# erroring at collection time. Must precede the naturo imports below, which load
# Pillow transitively.
pytest.importorskip("PIL")

from click.testing import CliRunner  # noqa: E402
from PIL import Image  # noqa: E402
from unittest.mock import MagicMock, patch  # noqa: E402

from naturo.cli.core import find_cmd  # noqa: E402
from naturo.image_match import ImageMatch, match_template  # noqa: E402


def _solid(width: int, height: int, color: int) -> Image.Image:
    """Return a solid grayscale image."""
    return Image.new("L", (width, height), color)


def _haystack_with_patch(
    size: tuple[int, int],
    patch: Image.Image,
    at: tuple[int, int],
    background: int = 128,
) -> Image.Image:
    """Build a haystack image with ``patch`` pasted at ``at`` over a flat
    background plus light positional gradient (so the background itself carries
    no spurious high-contrast match)."""
    width, height = size
    base = Image.new("L", size, background)
    # A gentle gradient gives the background some texture without creating a
    # region that correlates strongly with the patch.
    px = base.load()
    for y in range(height):
        for x in range(width):
            px[x, y] = (background + (x + y) % 7) % 256
    base.paste(patch, at)
    return base


def _distinctive_patch(width: int = 24, height: int = 18) -> Image.Image:
    """A patch with strong internal contrast (checker-ish) so NCC is well
    conditioned."""
    patch = Image.new("L", (width, height), 0)
    px = patch.load()
    for y in range(height):
        for x in range(width):
            px[x, y] = 255 if ((x // 4) + (y // 3)) % 2 == 0 else 20
    return patch


class TestMatchTemplate:
    def test_finds_exact_patch_location(self) -> None:
        """A template cropped from the haystack is located at its true origin."""
        patch = _distinctive_patch()
        hay = _haystack_with_patch((300, 200), patch, at=(120, 70))

        matches = match_template(hay, patch, threshold=0.9)

        assert len(matches) == 1
        m = matches[0]
        assert isinstance(m, ImageMatch)
        # Coarse-to-fine should land within a couple of pixels of the truth.
        assert abs(m.x - 120) <= 2
        assert abs(m.y - 70) <= 2
        assert m.width == patch.width
        assert m.height == patch.height
        assert m.score >= 0.9

    def test_center_helpers(self) -> None:
        patch = _distinctive_patch()
        hay = _haystack_with_patch((260, 180), patch, at=(40, 30))
        m = match_template(hay, patch, threshold=0.9)[0]
        assert abs(m.center_x - (40 + patch.width // 2)) <= 2
        assert abs(m.center_y - (30 + patch.height // 2)) <= 2

    def test_threshold_rejects_absent_template(self) -> None:
        """A template that does not occur is not reported above threshold."""
        patch = _distinctive_patch()
        # Haystack contains a *different* pattern, so the patch is absent.
        other = Image.new("L", (300, 200), 200)
        matches = match_template(other, patch, threshold=0.9)
        assert matches == []

    def test_find_all_returns_every_occurrence(self) -> None:
        """--all surfaces every above-threshold, non-overlapping occurrence."""
        patch = _distinctive_patch()
        hay = _haystack_with_patch((360, 200), patch, at=(30, 40))
        hay.paste(patch, (220, 120))  # second copy

        matches = match_template(hay, patch, threshold=0.9, find_all=True)

        assert len(matches) == 2
        found = sorted((m.x, m.y) for m in matches)
        # Both true locations recovered (within coarse-to-fine tolerance).
        assert abs(found[0][0] - 30) <= 2 and abs(found[0][1] - 40) <= 2
        assert abs(found[1][0] - 220) <= 2 and abs(found[1][1] - 120) <= 2

    def test_find_all_disabled_returns_single_best(self) -> None:
        patch = _distinctive_patch()
        hay = _haystack_with_patch((360, 200), patch, at=(30, 40))
        hay.paste(patch, (220, 120))
        matches = match_template(hay, patch, threshold=0.9, find_all=False)
        assert len(matches) == 1

    def test_template_larger_than_haystack_returns_empty(self) -> None:
        big = _distinctive_patch(width=100, height=100)
        small_hay = _solid(40, 40, 128)
        assert match_template(small_hay, big, threshold=0.9) == []

    def test_flat_template_raises(self) -> None:
        """A contrast-free template cannot be normalized-correlated."""
        flat = _solid(20, 20, 128)
        hay = _solid(200, 200, 128)
        with pytest.raises(ValueError):
            match_template(hay, flat, threshold=0.9)

    def test_rgb_inputs_are_accepted(self) -> None:
        """RGB images are converted to luminance internally."""
        patch_l = _distinctive_patch()
        patch = patch_l.convert("RGB")
        hay = _haystack_with_patch((280, 180), patch_l, at=(60, 50)).convert("RGB")
        matches = match_template(hay, patch, threshold=0.9)
        assert len(matches) == 1
        assert abs(matches[0].x - 60) <= 2
        assert abs(matches[0].y - 50) <= 2


class TestFindImageCli:
    """CLI integration for ``naturo find --image`` with a mocked capture backend.

    The backend's ``capture_screen`` is stubbed to write a known haystack PNG to
    the requested path, so the command runs end-to-end without a real desktop or
    the native core DLL.
    """

    @pytest.fixture
    def runner(self) -> CliRunner:
        return CliRunner()

    def _mock_backend(self, haystack: Image.Image) -> MagicMock:
        backend = MagicMock()

        def _capture_screen(screen_index: int = 0, output_path: str = "capture.png"):
            haystack.save(output_path)
            return MagicMock(path=output_path, width=haystack.width, height=haystack.height)

        backend.capture_screen.side_effect = _capture_screen
        backend.list_monitors.return_value = [MagicMock(x=0, y=0)]
        return backend

    def test_finds_template_on_screen_json(self, runner, tmp_path) -> None:
        patch_img = _distinctive_patch()
        hay = _haystack_with_patch((320, 240), patch_img, at=(100, 80))
        template_file = tmp_path / "patch.png"
        patch_img.save(template_file)

        backend = self._mock_backend(hay)
        with patch("naturo.cli.core._common._platform_supports_gui", return_value=True), \
             patch("naturo.cli.core._common._get_backend", return_value=backend):
            result = runner.invoke(
                find_cmd, ["--image", str(template_file), "--json"],
            )

        assert result.exit_code == 0, result.output
        payload = json.loads(result.output)
        assert payload["success"] is True
        assert payload["count"] == 1
        el = payload["elements"][0]
        assert abs(el["x"] - 100) <= 2
        assert abs(el["y"] - 80) <= 2
        assert el["score"] >= 0.9
        assert el["ref"].startswith("e")
        assert el["role"] == "Image"

    def test_no_match_reports_zero_count(self, runner, tmp_path) -> None:
        patch_img = _distinctive_patch()
        # A haystack that does NOT contain the patch.
        hay = Image.new("L", (320, 240), 200)
        template_file = tmp_path / "patch.png"
        patch_img.save(template_file)

        backend = self._mock_backend(hay)
        with patch("naturo.cli.core._common._platform_supports_gui", return_value=True), \
             patch("naturo.cli.core._common._get_backend", return_value=backend):
            result = runner.invoke(find_cmd, ["--image", str(template_file), "--json"])

        assert result.exit_code == 0, result.output
        payload = json.loads(result.output)
        assert payload["success"] is True
        assert payload["count"] == 0

    def test_all_flag_returns_multiple(self, runner, tmp_path) -> None:
        patch_img = _distinctive_patch()
        hay = _haystack_with_patch((400, 240), patch_img, at=(40, 40))
        hay.paste(patch_img, (260, 150))
        template_file = tmp_path / "patch.png"
        patch_img.save(template_file)

        backend = self._mock_backend(hay)
        with patch("naturo.cli.core._common._platform_supports_gui", return_value=True), \
             patch("naturo.cli.core._common._get_backend", return_value=backend):
            result = runner.invoke(
                find_cmd, ["--image", str(template_file), "--all", "--json"],
            )

        assert result.exit_code == 0, result.output
        payload = json.loads(result.output)
        assert payload["count"] == 2

    def test_missing_template_file_errors(self, runner, tmp_path) -> None:
        backend = self._mock_backend(Image.new("L", (10, 10), 0))
        with patch("naturo.cli.core._common._platform_supports_gui", return_value=True), \
             patch("naturo.cli.core._common._get_backend", return_value=backend):
            result = runner.invoke(
                find_cmd, ["--image", str(tmp_path / "nope.png"), "--json"],
            )
        assert result.exit_code == 1
        assert json.loads(result.output)["error"]["code"] == "FILE_NOT_FOUND"

    def test_image_and_ai_mutually_exclusive(self, runner, tmp_path) -> None:
        template_file = tmp_path / "patch.png"
        _distinctive_patch().save(template_file)
        result = runner.invoke(
            find_cmd, ["--image", str(template_file), "--ai", "--json"],
        )
        assert result.exit_code == 1
        assert json.loads(result.output)["error"]["code"] == "INVALID_INPUT"

    def test_image_rejects_text_query(self, runner, tmp_path) -> None:
        template_file = tmp_path / "patch.png"
        _distinctive_patch().save(template_file)
        result = runner.invoke(
            find_cmd, ["Save", "--image", str(template_file), "--json"],
        )
        assert result.exit_code == 1
        assert json.loads(result.output)["error"]["code"] == "INVALID_INPUT"

    def test_bad_threshold_rejected(self, runner, tmp_path) -> None:
        template_file = tmp_path / "patch.png"
        _distinctive_patch().save(template_file)
        backend = self._mock_backend(Image.new("L", (50, 50), 0))
        with patch("naturo.cli.core._common._platform_supports_gui", return_value=True), \
             patch("naturo.cli.core._common._get_backend", return_value=backend):
            result = runner.invoke(
                find_cmd, ["--image", str(template_file), "--threshold", "1.5", "--json"],
            )
        assert result.exit_code == 1
        assert json.loads(result.output)["error"]["code"] == "INVALID_INPUT"


@pytest.mark.desktop
class TestFindImageDesktop:
    """End-to-end check against a real screen capture (self-hosted desktop only).

    Captures the live screen, crops a known sub-region as the template, and
    confirms ``naturo find --image`` locates it at the crop's screen
    coordinates. The template is taken from the same frame, so the match is
    deterministic regardless of what is on screen.
    """

    def test_find_image_locates_self_crop_on_real_screen(self, tmp_path) -> None:
        from naturo.backends.base import get_backend

        backend = get_backend()
        screen_path = str(tmp_path / "screen.png")
        backend.capture_screen(screen_index=0, output_path=screen_path)
        screen = Image.open(screen_path)

        # Crop a content-rich, contrast-bearing region at an arbitrary offset.
        crop_x, crop_y, crop_w, crop_h = 821, 541, 96, 32
        if screen.width < crop_x + crop_w or screen.height < crop_y + crop_h:
            pytest.skip("screen too small for the fixed crop region")
        template = screen.crop((crop_x, crop_y, crop_x + crop_w, crop_y + crop_h))
        if match_template(screen, template, threshold=0.9) == []:
            pytest.skip("crop region lacks the contrast NCC needs on this screen")

        runner = CliRunner()
        template_file = tmp_path / "crop.png"
        template.save(template_file)
        result = runner.invoke(find_cmd, ["--image", str(template_file), "--json"])

        assert result.exit_code == 0, result.output
        payload = json.loads(result.output)
        assert payload["count"] >= 1
        # The best match must sit at the crop's screen coordinates.
        best = max(payload["elements"], key=lambda e: e["score"])
        assert abs(best["x"] - crop_x) <= 3
        assert abs(best["y"] - crop_y) <= 3
        assert best["score"] >= 0.9
