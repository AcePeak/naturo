"""Tests for visual regression testing engine and CLI."""
from __future__ import annotations

import json
from pathlib import Path
from unittest.mock import patch

import pytest
from click.testing import CliRunner

try:
    from PIL import Image
    _HAS_PIL = True
except ImportError:
    _HAS_PIL = False

from naturo.cli import main
from naturo import visual as visual_mod


pytestmark = pytest.mark.skipif(not _HAS_PIL, reason="Pillow not installed")


@pytest.fixture()
def runner():
    return CliRunner()


@pytest.fixture()
def tmp_dirs(tmp_path):
    """Patch baseline and report dirs."""
    bd = tmp_path / "baselines"
    rd = tmp_path / "reports"
    bd.mkdir()
    rd.mkdir()
    with patch.object(visual_mod, "BASELINES_DIR", bd), \
         patch.object(visual_mod, "REPORTS_DIR", rd):
        yield bd, rd


@pytest.fixture()
def red_image(tmp_path) -> Path:
    """Create a solid red 100x100 PNG."""
    p = tmp_path / "red.png"
    Image.new("RGB", (100, 100), (255, 0, 0)).save(p)
    return p


@pytest.fixture()
def blue_image(tmp_path) -> Path:
    """Create a solid blue 100x100 PNG."""
    p = tmp_path / "blue.png"
    Image.new("RGB", (100, 100), (0, 0, 255)).save(p)
    return p


@pytest.fixture()
def red_copy(tmp_path) -> Path:
    """Create another solid red 100x100 PNG (identical to red_image)."""
    p = tmp_path / "red_copy.png"
    Image.new("RGB", (100, 100), (255, 0, 0)).save(p)
    return p


@pytest.fixture()
def slightly_different(tmp_path) -> Path:
    """Create a mostly-red image with a few different pixels."""
    img = Image.new("RGB", (100, 100), (255, 0, 0))
    for x in range(5):
        for y in range(5):
            img.putpixel((x, y), (0, 255, 0))  # 25 green pixels out of 10000
    p = tmp_path / "slight.png"
    img.save(p)
    return p


# ── Engine tests ─────────────────────────────────────────────────────────────


class TestSaveBaseline:
    def test_save_creates_files(self, tmp_dirs, red_image):
        bd, _ = tmp_dirs
        path = visual_mod.save_baseline(red_image, "test_screen", bd)
        assert path.exists()
        assert (bd / "test_screen.png").exists()
        assert (bd / "test_screen.json").exists()

    def test_save_metadata(self, tmp_dirs, red_image):
        bd, _ = tmp_dirs
        visual_mod.save_baseline(red_image, "test_screen", bd)
        meta = json.loads((bd / "test_screen.json").read_text())
        assert meta["name"] == "test_screen"
        assert meta["size"] == [100, 100]

    def test_save_not_found(self, tmp_dirs):
        bd, _ = tmp_dirs
        with pytest.raises(FileNotFoundError):
            visual_mod.save_baseline("/nonexistent.png", "test", bd)


class TestListBaselines:
    def test_list_empty(self, tmp_dirs):
        bd, _ = tmp_dirs
        assert visual_mod.list_baselines(bd) == []

    def test_list_returns_saved(self, tmp_dirs, red_image):
        bd, _ = tmp_dirs
        visual_mod.save_baseline(red_image, "screen1", bd)
        visual_mod.save_baseline(red_image, "screen2", bd)
        result = visual_mod.list_baselines(bd)
        assert len(result) == 2
        names = {r["name"] for r in result}
        assert names == {"screen1", "screen2"}


class TestDeleteBaseline:
    def test_delete_existing(self, tmp_dirs, red_image):
        bd, _ = tmp_dirs
        visual_mod.save_baseline(red_image, "test", bd)
        assert visual_mod.delete_baseline("test", bd) is True
        assert not (bd / "test.png").exists()
        assert not (bd / "test.json").exists()

    def test_delete_nonexistent(self, tmp_dirs):
        bd, _ = tmp_dirs
        assert visual_mod.delete_baseline("nope", bd) is False


class TestCompareImages:
    def test_identical_images(self, red_image, red_copy):
        result = visual_mod.compare_images(red_image, red_copy, threshold=0.95)
        assert result.match is True
        assert result.similarity == 1.0
        assert result.diff_pixels == 0

    def test_completely_different(self, red_image, blue_image):
        result = visual_mod.compare_images(red_image, blue_image, threshold=0.95)
        assert result.match is False
        assert result.similarity < 0.1
        assert result.diff_pixels == 10000

    def test_slightly_different_passes(self, red_image, slightly_different):
        result = visual_mod.compare_images(red_image, slightly_different, threshold=0.95)
        assert result.match is True  # 25/10000 = 0.25% diff
        assert result.similarity > 0.99

    def test_diff_image_generated(self, red_image, blue_image, tmp_path):
        diff_out = tmp_path / "diff.png"
        result = visual_mod.compare_images(
            red_image, blue_image, diff_output=str(diff_out),
        )
        assert diff_out.exists()
        assert result.diff_path == str(diff_out)
        # Diff image is 3x wide (side-by-side)
        diff_img = Image.open(diff_out)
        assert diff_img.size == (300, 100)

    def test_different_dimensions(self, red_image, tmp_path):
        small = tmp_path / "small.png"
        Image.new("RGB", (50, 50), (255, 0, 0)).save(small)
        result = visual_mod.compare_images(red_image, small)
        assert result.dimensions_match is False
        assert result.match is True  # same color, just resized

    def test_threshold_configurable(self, red_image, slightly_different):
        # Very strict threshold — 25/10000 diff = 99.75% similar, fails at 99.9%
        result = visual_mod.compare_images(
            red_image, slightly_different, threshold=0.999,
        )
        assert result.match is False
        assert result.similarity > 0.99
        # Relaxed threshold — passes
        result2 = visual_mod.compare_images(
            red_image, slightly_different, threshold=0.99,
        )
        assert result2.match is True


class TestCompareWithBaseline:
    def test_compare_against_baseline(self, tmp_dirs, red_image, red_copy):
        bd, rd = tmp_dirs
        visual_mod.save_baseline(red_image, "test", bd)
        result = visual_mod.compare_with_baseline(
            red_copy, "test", baselines_dir=bd, reports_dir=rd,
        )
        assert result.match is True

    def test_baseline_not_found(self, tmp_dirs, red_image):
        bd, rd = tmp_dirs
        with pytest.raises(FileNotFoundError):
            visual_mod.compare_with_baseline(
                red_image, "nonexistent", baselines_dir=bd, reports_dir=rd,
            )


class TestSSIM:
    def test_identical_ssim(self, red_image, red_copy):
        img1 = Image.open(red_image)
        img2 = Image.open(red_copy)
        ssim = visual_mod.compute_ssim(img1, img2)
        assert ssim > 0.99

    def test_different_ssim(self, red_image, blue_image):
        img1 = Image.open(red_image)
        img2 = Image.open(blue_image)
        ssim = visual_mod.compute_ssim(img1, img2)
        assert ssim < 0.99  # different images have lower SSIM


class TestHTMLReport:
    def test_generate_report(self, tmp_dirs, red_image, blue_image):
        bd, rd = tmp_dirs
        result = visual_mod.compare_images(red_image, blue_image, name="test")
        report = visual_mod.VisualReport(
            name="Test Report",
            created_at="2026-04-01T12:00:00",
        )
        report.add_result(result)
        html_path = visual_mod.generate_html_report(report, rd / "report.html")
        assert html_path.exists()
        content = html_path.read_text()
        assert "Test Report" in content
        assert "FAILED" in content
        assert "test" in content


# ── CLI tests ────────────────────────────────────────────────────────────────


class TestVisualCLI:
    def test_baseline_command(self, runner, tmp_dirs, red_image):
        result = runner.invoke(main, [
            "visual", "baseline", "screen1", "--from", str(red_image),
        ])
        assert result.exit_code == 0
        assert "Baseline saved" in result.output

    def test_list_command(self, runner, tmp_dirs, red_image):
        runner.invoke(main, ["visual", "baseline", "s1", "--from", str(red_image)])
        result = runner.invoke(main, ["visual", "list"])
        assert result.exit_code == 0
        assert "s1" in result.output

    def test_list_empty(self, runner, tmp_dirs):
        result = runner.invoke(main, ["visual", "list"])
        assert result.exit_code == 0
        assert "No baselines" in result.output

    def test_compare_pass(self, runner, tmp_dirs, red_image, red_copy):
        runner.invoke(main, ["visual", "baseline", "s1", "--from", str(red_image)])
        result = runner.invoke(main, [
            "visual", "compare", "s1", "--current", str(red_copy),
        ])
        assert result.exit_code == 0
        assert "PASS" in result.output

    def test_compare_fail(self, runner, tmp_dirs, red_image, blue_image):
        runner.invoke(main, ["visual", "baseline", "s1", "--from", str(red_image)])
        result = runner.invoke(main, [
            "visual", "compare", "s1", "--current", str(blue_image),
        ])
        assert result.exit_code != 0
        assert "FAIL" in result.output

    def test_compare_json(self, runner, tmp_dirs, red_image, red_copy):
        runner.invoke(main, ["visual", "baseline", "s1", "--from", str(red_image)])
        result = runner.invoke(main, [
            "visual", "compare", "s1", "--current", str(red_copy), "--json",
        ])
        assert result.exit_code == 0
        data = json.loads(result.output)
        assert data["match"] is True
        assert data["similarity"] == 1.0

    def test_diff_command(self, runner, red_image, blue_image, tmp_path):
        diff_out = str(tmp_path / "diff.png")
        result = runner.invoke(main, [
            "visual", "diff", str(red_image), str(blue_image), "-o", diff_out,
        ])
        assert result.exit_code == 0
        assert "DIFFER" in result.output
        assert Path(diff_out).exists()

    def test_delete_command(self, runner, tmp_dirs, red_image):
        runner.invoke(main, ["visual", "baseline", "s1", "--from", str(red_image)])
        result = runner.invoke(main, ["visual", "delete", "s1", "--force"])
        assert result.exit_code == 0
        assert "Deleted" in result.output

    def test_help(self, runner):
        result = runner.invoke(main, ["visual", "--help"])
        assert result.exit_code == 0
        assert "baseline" in result.output
        assert "compare" in result.output
        assert "diff" in result.output
        assert "report" in result.output


# ── Enterprise feature tests ────────────────────────────────────────────────


class TestIgnoreRegions:
    def test_ignore_region_masks_difference(self, red_image, tmp_path):
        """A blue patch in a masked region should not cause a diff."""
        # Create image with blue patch at (0,0)-(10,10)
        patched = tmp_path / "patched.png"
        img = Image.new("RGB", (100, 100), (255, 0, 0))
        for x in range(10):
            for y in range(10):
                img.putpixel((x, y), (0, 0, 255))
        img.save(patched)

        # Without masking: should detect difference (100/10000 = 1% diff)
        result = visual_mod.compare_images(red_image, patched, threshold=0.999)
        assert result.match is False

        # With masking over the blue patch: should pass
        result2 = visual_mod.compare_images(
            red_image, patched, threshold=0.999,
            ignore_regions=[(0, 0, 10, 10)],
        )
        assert result2.match is True
        assert result2.similarity == 1.0

    def test_ignore_multiple_regions(self, red_image, tmp_path):
        """Multiple ignore regions mask independently."""
        patched = tmp_path / "multi.png"
        img = Image.new("RGB", (100, 100), (255, 0, 0))
        # Two blue patches
        for x in range(5):
            for y in range(5):
                img.putpixel((x, y), (0, 0, 255))
                img.putpixel((90 + x, 90 + y), (0, 0, 255))
        img.save(patched)

        result = visual_mod.compare_images(
            red_image, patched, threshold=0.99,
            ignore_regions=[(0, 0, 5, 5), (90, 90, 10, 10)],
        )
        assert result.match is True


class TestUpdateBaseline:
    def test_update_existing(self, tmp_dirs, red_image, blue_image):
        bd, _ = tmp_dirs
        visual_mod.save_baseline(red_image, "test_screen", bd)
        path = visual_mod.update_baseline(blue_image, "test_screen", bd)
        assert path.exists()
        # Verify it's now the blue image
        img = Image.open(path)
        assert img.getpixel((50, 50)) == (0, 0, 255)

    def test_update_nonexistent_raises(self, tmp_dirs, red_image):
        bd, _ = tmp_dirs
        with pytest.raises(FileNotFoundError):
            visual_mod.update_baseline(red_image, "nonexistent", bd)


class TestSuiteLoading:
    def test_load_valid_suite(self, tmp_path):
        suite_file = tmp_path / "suite.json"
        suite_file.write_text(json.dumps({
            "name": "Test Suite",
            "threshold": 0.98,
            "tests": [
                {"name": "screen1", "current": "shots/s1.png"},
                {"name": "screen2", "current": "shots/s2.png",
                 "threshold": 0.90, "ignore_regions": [[10, 5, 200, 30]]},
            ],
        }))
        suite = visual_mod.load_suite(suite_file)
        assert suite.name == "Test Suite"
        assert suite.threshold == 0.98
        assert len(suite.tests) == 2
        assert suite.tests[1].threshold == 0.90
        assert suite.tests[1].ignore_regions == [(10, 5, 200, 30)]

    def test_load_missing_file(self):
        with pytest.raises(FileNotFoundError):
            visual_mod.load_suite("/nonexistent.json")

    def test_load_missing_tests_key(self, tmp_path):
        suite_file = tmp_path / "bad.json"
        suite_file.write_text(json.dumps({"name": "Bad"}))
        with pytest.raises(ValueError, match="tests"):
            visual_mod.load_suite(suite_file)

    def test_load_missing_required_fields(self, tmp_path):
        suite_file = tmp_path / "bad2.json"
        suite_file.write_text(json.dumps({
            "tests": [{"name": "only_name"}],
        }))
        with pytest.raises(ValueError, match="current"):
            visual_mod.load_suite(suite_file)


class TestRunSuite:
    def test_run_suite_all_pass(self, tmp_dirs, red_image, red_copy):
        bd, rd = tmp_dirs
        visual_mod.save_baseline(red_image, "screen1", bd)

        suite = visual_mod.Suite(
            name="Test", threshold=0.95,
            tests=[visual_mod.SuiteTest(name="screen1", current=str(red_copy))],
        )
        report = visual_mod.run_suite(suite, baselines_dir=bd, reports_dir=rd)
        assert report.all_passed
        assert report.passed == 1

    def test_run_suite_missing_baseline(self, tmp_dirs, red_image):
        bd, rd = tmp_dirs
        suite = visual_mod.Suite(
            name="Test", threshold=0.95,
            tests=[visual_mod.SuiteTest(name="missing", current=str(red_image))],
        )
        report = visual_mod.run_suite(suite, baselines_dir=bd, reports_dir=rd)
        assert not report.all_passed
        assert report.failed == 1

    def test_suite_per_test_threshold(self, tmp_dirs, red_image, slightly_different):
        bd, rd = tmp_dirs
        visual_mod.save_baseline(red_image, "screen1", bd)

        suite = visual_mod.Suite(
            name="Test", threshold=1.0,  # strict global
            tests=[
                visual_mod.SuiteTest(
                    name="screen1",
                    current=str(slightly_different),
                    threshold=0.95,  # relaxed per-test
                ),
            ],
        )
        report = visual_mod.run_suite(suite, baselines_dir=bd, reports_dir=rd)
        assert report.all_passed  # per-test threshold wins

    def test_suite_with_ignore_regions(self, tmp_dirs, red_image, tmp_path):
        bd, rd = tmp_dirs
        visual_mod.save_baseline(red_image, "screen1", bd)

        # Create image with blue corner
        patched = tmp_path / "patched.png"
        img = Image.new("RGB", (100, 100), (255, 0, 0))
        for x in range(10):
            for y in range(10):
                img.putpixel((x, y), (0, 0, 255))
        img.save(patched)

        suite = visual_mod.Suite(
            name="Test", threshold=0.99,
            tests=[
                visual_mod.SuiteTest(
                    name="screen1",
                    current=str(patched),
                    ignore_regions=[(0, 0, 10, 10)],
                ),
            ],
        )
        report = visual_mod.run_suite(suite, baselines_dir=bd, reports_dir=rd)
        assert report.all_passed


class TestEnterpriseCLI:
    def test_update_command(self, runner, tmp_dirs, red_image, blue_image):
        runner.invoke(main, ["visual", "baseline", "s1", "--from", str(red_image)])
        result = runner.invoke(main, [
            "visual", "update", "s1", "--from", str(blue_image),
        ])
        assert result.exit_code == 0
        assert "updated" in result.output.lower()

    def test_update_nonexistent(self, runner, tmp_dirs, red_image):
        result = runner.invoke(main, [
            "visual", "update", "nope", "--from", str(red_image),
        ])
        assert result.exit_code != 0

    def test_update_json(self, runner, tmp_dirs, red_image, blue_image):
        runner.invoke(main, ["visual", "baseline", "s1", "--from", str(red_image)])
        result = runner.invoke(main, [
            "visual", "update", "s1", "--from", str(blue_image), "--json",
        ])
        assert result.exit_code == 0
        data = json.loads(result.output)
        assert data["success"] is True

    def test_update_all_command(self, runner, tmp_dirs, red_image, blue_image):
        bd, _ = tmp_dirs
        runner.invoke(main, ["visual", "baseline", "red", "--from", str(red_image)])
        # Create dir with updated screenshot
        update_dir = bd.parent / "updates"
        update_dir.mkdir()
        Image.new("RGB", (100, 100), (0, 255, 0)).save(update_dir / "red.png")
        Image.new("RGB", (100, 100), (0, 255, 0)).save(update_dir / "unknown.png")

        result = runner.invoke(main, [
            "visual", "update-all", "--from-dir", str(update_dir),
        ])
        assert result.exit_code == 0
        assert "Updated: red" in result.output
        assert "Skipped: unknown" in result.output

    def test_compare_with_ignore_region(self, runner, tmp_dirs, red_image, tmp_path):
        runner.invoke(main, ["visual", "baseline", "s1", "--from", str(red_image)])
        # Create image with blue corner
        patched = tmp_path / "patched.png"
        img = Image.new("RGB", (100, 100), (255, 0, 0))
        for x in range(10):
            for y in range(10):
                img.putpixel((x, y), (0, 0, 255))
        img.save(patched)

        # Fails without masking (100/10000 = 1% diff, similarity=0.99)
        result = runner.invoke(main, [
            "visual", "compare", "s1", "--current", str(patched),
            "--threshold", "0.999",
        ])
        assert result.exit_code != 0

        # Passes with masking
        result2 = runner.invoke(main, [
            "visual", "compare", "s1", "--current", str(patched),
            "--threshold", "0.999", "--ignore-region", "0,0,10,10",
        ])
        assert result2.exit_code == 0

    def test_suite_command(self, runner, tmp_dirs, red_image, red_copy, tmp_path):
        runner.invoke(main, ["visual", "baseline", "s1", "--from", str(red_image)])
        suite_file = tmp_path / "suite.json"
        suite_file.write_text(json.dumps({
            "name": "CI Suite",
            "tests": [
                {"name": "s1", "current": str(red_copy)},
            ],
        }))
        result = runner.invoke(main, ["visual", "suite", str(suite_file)])
        assert result.exit_code == 0
        assert "PASS" in result.output
        assert "1 passed" in result.output

    def test_suite_json_output(self, runner, tmp_dirs, red_image, red_copy, tmp_path):
        runner.invoke(main, ["visual", "baseline", "s1", "--from", str(red_image)])
        suite_file = tmp_path / "suite.json"
        suite_file.write_text(json.dumps({
            "name": "CI Suite",
            "tests": [
                {"name": "s1", "current": str(red_copy)},
            ],
        }))
        result = runner.invoke(main, ["visual", "suite", str(suite_file), "--json"])
        assert result.exit_code == 0
        data = json.loads(result.output)
        assert data["all_passed"] is True

    def test_suite_with_html_report(self, runner, tmp_dirs, red_image, red_copy, tmp_path):
        runner.invoke(main, ["visual", "baseline", "s1", "--from", str(red_image)])
        suite_file = tmp_path / "suite.json"
        suite_file.write_text(json.dumps({
            "name": "CI Suite",
            "tests": [{"name": "s1", "current": str(red_copy)}],
        }))
        report_path = tmp_path / "report.html"
        result = runner.invoke(main, [
            "visual", "suite", str(suite_file), "-o", str(report_path),
        ])
        assert result.exit_code == 0
        assert report_path.exists()

    def test_help_includes_new_commands(self, runner):
        result = runner.invoke(main, ["visual", "--help"])
        assert result.exit_code == 0
        assert "update" in result.output
        assert "suite" in result.output
