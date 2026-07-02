"""Tests for ``naturo click --image`` template-match targeting (#1059).

``click --image template.png`` locates the template on the target window/screen
(reusing the ``find --image`` matching core) and clicks the center of the best
match — the ``naturo click --image`` shortcut from the unified-find-engine scope
(#809).

Image matching is pure computation, so these tests resolve the click coordinates
deterministically against in-memory fixtures with the capture backend mocked, and
assert the resolved coordinates by mocking the click backend's ``click`` call —
no real input injection and no desktop session, so they run on every CI platform.
"""
from __future__ import annotations

import json

import pytest

# Pillow backs the matcher; skip the whole module where it is unavailable.
pytest.importorskip("PIL")

from click.testing import CliRunner  # noqa: E402
from PIL import Image  # noqa: E402
from unittest.mock import MagicMock, patch  # noqa: E402

from naturo.cli.interaction._click import click_cmd  # noqa: E402


def _distinctive_patch(width: int = 24, height: int = 18) -> Image.Image:
    """A patch with strong internal contrast so NCC is well conditioned."""
    patch_img = Image.new("L", (width, height), 0)
    px = patch_img.load()
    for y in range(height):
        for x in range(width):
            px[x, y] = 255 if (x // 4 + y // 4) % 2 == 0 else 0
    return patch_img


def _haystack_with_patch(
    size: tuple[int, int], patch_img: Image.Image, at: tuple[int, int], background: int = 128,
) -> Image.Image:
    """Build a haystack with ``patch_img`` pasted at ``at`` over a lightly textured
    background (so the background carries no spurious high-contrast match)."""
    width, height = size
    base = Image.new("L", size, background)
    px = base.load()
    for y in range(height):
        for x in range(width):
            px[x, y] = (background + (x + y) % 7) % 256
    base.paste(patch_img, at)
    return base


def _backend(capture_image: Image.Image) -> MagicMock:
    """A backend whose live capture writes ``capture_image`` and whose ``click``
    records the resolved coordinates."""
    backend = MagicMock()

    def _capture_screen(screen_index: int = 0, output_path: str = "capture.png"):
        capture_image.save(output_path)
        return MagicMock(path=output_path)

    def _capture_window(hwnd: int, output_path: str = "capture.png"):
        capture_image.save(output_path)
        return MagicMock(path=output_path)

    backend.capture_screen.side_effect = _capture_screen
    backend.capture_window.side_effect = _capture_window
    backend.list_monitors.return_value = [MagicMock(x=0, y=0)]
    backend.click.return_value = None
    backend.focus_window.return_value = None
    backend._resolve_hwnd.return_value = 4242
    backend._resolve_hwnds.return_value = [4242]
    backend._is_afh_window.return_value = False
    backend._is_winui_window.return_value = False
    return backend


def _patches(backend: MagicMock):
    """Patch every host-dependent call on the click --image path so the result
    reflects the code, not the runner's desktop state."""
    return [
        patch("naturo.cli.core._common._platform_supports_gui", return_value=True),
        patch("naturo.cli.core._common._get_backend", return_value=backend),
        patch("naturo.cli.interaction._common._get_backend", return_value=backend),
        patch("naturo.cli.interaction._common._resolve_app_id",
              return_value=(None, None, None)),
        patch("naturo.cli.interaction._common._auto_route", return_value={}),
    ]


def _invoke(runner: CliRunner, backend: MagicMock, args: list[str]):
    ctx = _patches(backend)
    with ctx[0], ctx[1], ctx[2], ctx[3], ctx[4]:
        return runner.invoke(click_cmd, args, catch_exceptions=False)


@pytest.fixture
def runner() -> CliRunner:
    return CliRunner()


class TestClickImageHappyPath:
    """--image resolves to the match center and clicks it (live capture)."""

    def test_clicks_center_of_match(self, runner, tmp_path) -> None:
        patch_img = _distinctive_patch()  # 24x18
        screen = _haystack_with_patch((320, 240), patch_img, at=(60, 90))
        template_file = tmp_path / "tmpl.png"
        patch_img.save(template_file)
        backend = _backend(screen)

        result = _invoke(runner, backend, ["--image", str(template_file)])

        assert result.exit_code == 0, result.output
        backend.click.assert_called_once()
        kwargs = backend.click.call_args.kwargs
        # Center of the match: top-left (60,90) + half of (24,18) = (72,99).
        assert abs(kwargs["x"] - 72) <= 2
        assert abs(kwargs["y"] - 99) <= 2
        assert kwargs["button"] == "left"
        assert kwargs["double"] is False

    def test_json_reports_template_and_score(self, runner, tmp_path) -> None:
        patch_img = _distinctive_patch()
        screen = _haystack_with_patch((320, 240), patch_img, at=(40, 50))
        template_file = tmp_path / "tmpl.png"
        patch_img.save(template_file)
        backend = _backend(screen)

        result = _invoke(runner, backend, ["--image", str(template_file), "--json"])

        assert result.exit_code == 0, result.output
        payload = json.loads(result.output)
        assert payload["success"] is True
        match = payload["data"]["image_match"]
        assert match["template"] == "tmpl.png"
        assert match["score"] >= 0.9

    def test_double_and_right_flags_flow_through(self, runner, tmp_path) -> None:
        patch_img = _distinctive_patch()
        screen = _haystack_with_patch((320, 240), patch_img, at=(60, 90))
        template_file = tmp_path / "tmpl.png"
        patch_img.save(template_file)
        backend = _backend(screen)

        result = _invoke(
            runner, backend,
            ["--image", str(template_file), "--double", "--right"],
        )

        assert result.exit_code == 0, result.output
        kwargs = backend.click.call_args.kwargs
        assert kwargs["double"] is True
        assert kwargs["button"] == "right"


class TestClickImageErrors:
    """Failures are attributed to their own registered error codes, and no click
    is dispatched (prefer a false negative over clicking the wrong place)."""

    def test_no_match_is_element_not_found(self, runner, tmp_path) -> None:
        patch_img = _distinctive_patch()
        # The screen is uniform black: the template cannot be present.
        black = Image.new("L", (320, 240), 0)
        template_file = tmp_path / "tmpl.png"
        patch_img.save(template_file)
        backend = _backend(black)

        result = _invoke(
            runner, backend,
            ["--image", str(template_file), "--threshold", "0.95", "--json"],
        )

        assert result.exit_code == 1, result.output
        error = json.loads(result.output)["error"]
        assert error["code"] == "ELEMENT_NOT_FOUND"
        assert error["category"] == "automation"
        backend.click.assert_not_called()

    def test_missing_template_file_is_file_not_found(self, runner, tmp_path) -> None:
        backend = _backend(Image.new("L", (100, 100), 128))

        result = _invoke(
            runner, backend,
            ["--image", str(tmp_path / "nope.png"), "--json"],
        )

        assert result.exit_code == 1, result.output
        assert json.loads(result.output)["error"]["code"] == "FILE_NOT_FOUND"
        backend.click.assert_not_called()

    def test_undecodable_template_is_invalid_template(self, runner, tmp_path) -> None:
        """A bad template carries the registered INVALID_TEMPLATE code with its
        proper (non-degraded) category — locks the #1059 error-code registration."""
        bad_template = tmp_path / "bad.png"
        bad_template.write_text("not an image", encoding="utf-8")
        backend = _backend(_haystack_with_patch((100, 100), _distinctive_patch(), at=(10, 10)))

        result = _invoke(runner, backend, ["--image", str(bad_template), "--json"])

        assert result.exit_code == 1, result.output
        error = json.loads(result.output)["error"]
        assert error["code"] == "INVALID_TEMPLATE"
        assert error["category"] == "validation"
        backend.click.assert_not_called()

    def test_bad_threshold_is_invalid_input(self, runner, tmp_path) -> None:
        template_file = tmp_path / "tmpl.png"
        _distinctive_patch().save(template_file)
        backend = _backend(Image.new("L", (100, 100), 128))

        result = _invoke(
            runner, backend,
            ["--image", str(template_file), "--threshold", "1.5", "--json"],
        )

        assert result.exit_code == 1, result.output
        assert json.loads(result.output)["error"]["code"] == "INVALID_INPUT"
        backend.click.assert_not_called()

    @pytest.mark.parametrize(
        "extra",
        [
            ["--coords", "10", "20"],
            ["--id", "button_ok"],
            ["--on", "Save"],
            ["some text query"],
        ],
    )
    def test_image_is_mutually_exclusive_with_other_targets(
        self, runner, tmp_path, extra,
    ) -> None:
        template_file = tmp_path / "tmpl.png"
        _distinctive_patch().save(template_file)
        backend = _backend(Image.new("L", (100, 100), 128))

        result = _invoke(
            runner, backend,
            ["--image", str(template_file), "--json", *extra],
        )

        assert result.exit_code == 1, result.output
        assert json.loads(result.output)["error"]["code"] == "INVALID_INPUT"
        backend.click.assert_not_called()
