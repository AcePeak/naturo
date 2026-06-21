"""Visual regression testing engine.

Captures baseline screenshots, compares against current state,
generates diff images and reports for detecting UI changes.
"""
from __future__ import annotations

import json
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path
from typing import Optional

try:
    from PIL import Image, ImageChops, ImageDraw
    _HAS_PIL = True
except ImportError:
    _HAS_PIL = False


BASELINES_DIR = Path.home() / ".naturo" / "visual" / "baselines"
REPORTS_DIR = Path.home() / ".naturo" / "visual" / "reports"


def _require_pil() -> None:
    if not _HAS_PIL:
        raise ImportError(
            "Pillow is required for visual regression testing. "
            "Install with: pip install naturo[visual] or pip install Pillow"
        )


def _ensure_dir(d: Path) -> Path:
    d.mkdir(parents=True, exist_ok=True)
    return d


@dataclass
class ComparisonResult:
    """Result of comparing two images."""
    name: str
    match: bool
    similarity: float  # 0.0 to 1.0
    threshold: float
    baseline_path: str
    current_path: str
    diff_path: Optional[str] = None
    diff_pixels: int = 0
    total_pixels: int = 0
    dimensions_match: bool = True
    baseline_size: tuple = (0, 0)
    current_size: tuple = (0, 0)

    def to_dict(self) -> dict:
        return {
            "name": self.name,
            "match": self.match,
            "similarity": round(self.similarity, 4),
            "threshold": self.threshold,
            "baseline_path": self.baseline_path,
            "current_path": self.current_path,
            "diff_path": self.diff_path,
            "diff_pixels": self.diff_pixels,
            "total_pixels": self.total_pixels,
            "diff_percentage": round(
                (self.diff_pixels / self.total_pixels * 100) if self.total_pixels > 0 else 0, 2
            ),
            "dimensions_match": self.dimensions_match,
            "baseline_size": list(self.baseline_size),
            "current_size": list(self.current_size),
        }


@dataclass
class VisualReport:
    """A visual regression test report."""
    name: str
    created_at: str
    results: list[ComparisonResult] = field(default_factory=list)
    passed: int = 0
    failed: int = 0

    def add_result(self, result: ComparisonResult) -> None:
        self.results.append(result)
        if result.match:
            self.passed += 1
        else:
            self.failed += 1

    @property
    def all_passed(self) -> bool:
        return self.failed == 0

    def to_dict(self) -> dict:
        return {
            "name": self.name,
            "created_at": self.created_at,
            "passed": self.passed,
            "failed": self.failed,
            "all_passed": self.all_passed,
            "results": [r.to_dict() for r in self.results],
        }


def save_baseline(
    image_path: str | Path,
    name: str,
    directory: Optional[Path] = None,
) -> Path:
    """Save an image as a visual baseline.

    Args:
        image_path: Path to the screenshot to use as baseline.
        name: Friendly name for the baseline (e.g., "login_screen").
        directory: Custom baselines directory. Uses default if None.

    Returns:
        Path to the saved baseline image.
    """
    _require_pil()
    src = Path(image_path)
    if not src.exists():
        raise FileNotFoundError(f"Image not found: {image_path}")

    d = _ensure_dir(directory or BASELINES_DIR)
    dest = d / f"{name}.png"

    img = Image.open(src)
    img.save(dest, "PNG")

    # Save metadata
    meta = {
        "name": name,
        "created_at": datetime.now().isoformat(),
        "size": list(img.size),
        "source": str(src),
    }
    meta_path = d / f"{name}.json"
    with open(meta_path, "w", encoding="utf-8") as f:
        json.dump(meta, f, indent=2)

    return dest


def list_baselines(directory: Optional[Path] = None) -> list[dict]:
    """List all saved baselines.

    Returns:
        List of baseline metadata dictionaries.
    """
    d = directory or BASELINES_DIR
    if not d.exists():
        return []

    results = []
    for meta_path in sorted(d.glob("*.json")):
        try:
            with open(meta_path, "r", encoding="utf-8") as f:
                meta = json.load(f)
            img_path = d / f"{meta['name']}.png"
            meta["exists"] = img_path.exists()
            results.append(meta)
        except (json.JSONDecodeError, KeyError):
            continue
    return results


def delete_baseline(name: str, directory: Optional[Path] = None) -> bool:
    """Delete a baseline image and its metadata."""
    d = directory or BASELINES_DIR
    img_path = d / f"{name}.png"
    meta_path = d / f"{name}.json"
    deleted = False
    if img_path.exists():
        img_path.unlink()
        deleted = True
    if meta_path.exists():
        meta_path.unlink()
        deleted = True
    return deleted


def update_baseline(
    image_path: str | Path,
    name: str,
    directory: Optional[Path] = None,
) -> Path:
    """Update an existing baseline with a new screenshot.

    Args:
        image_path: Path to the new screenshot.
        name: Baseline name to update.
        directory: Custom baselines directory. Uses default if None.

    Returns:
        Path to the updated baseline image.

    Raises:
        FileNotFoundError: If the baseline does not exist.
    """
    _require_pil()
    d = directory or BASELINES_DIR
    existing = d / f"{name}.png"
    if not existing.exists():
        raise FileNotFoundError(f"Baseline not found: {name}")

    return save_baseline(image_path, name, directory)


def _apply_ignore_regions(
    img: "Image.Image",
    regions: list[tuple[int, int, int, int]],
    fill: tuple[int, int, int] = (128, 128, 128),
) -> "Image.Image":
    """Mask regions of an image with a solid fill color.

    Args:
        img: PIL Image to mask.
        regions: List of (x, y, width, height) tuples to mask.
        fill: RGB fill color for masked regions.

    Returns:
        New image with masked regions.
    """
    masked = img.copy()
    draw = ImageDraw.Draw(masked)
    for x, y, w, h in regions:
        draw.rectangle([x, y, x + w, y + h], fill=fill)
    return masked


def compare_images(
    baseline_path: str | Path,
    current_path: str | Path,
    name: str = "comparison",
    threshold: float = 0.95,
    diff_output: Optional[str | Path] = None,
    highlight_color: tuple = (255, 0, 0),
    ignore_regions: Optional[list[tuple[int, int, int, int]]] = None,
) -> ComparisonResult:
    """Compare two images and generate a diff.

    Args:
        baseline_path: Path to the baseline image.
        current_path: Path to the current screenshot.
        name: Name for this comparison.
        threshold: Similarity threshold (0.0-1.0). Above = pass, below = fail.
        diff_output: Path to save the diff image. None = don't save.
        highlight_color: RGB color for highlighting differences.
        ignore_regions: List of (x, y, width, height) tuples to mask before comparison.

    Returns:
        ComparisonResult with similarity score and diff information.
    """
    _require_pil()

    baseline = Image.open(baseline_path).convert("RGB")
    current = Image.open(current_path).convert("RGB")

    if ignore_regions:
        baseline = _apply_ignore_regions(baseline, ignore_regions)
        current = _apply_ignore_regions(current, ignore_regions)

    dimensions_match = baseline.size == current.size

    if not dimensions_match:
        # Resize current to baseline size for comparison
        current_resized = current.resize(baseline.size, Image.LANCZOS)
    else:
        current_resized = current

    # Pixel-level diff
    diff = ImageChops.difference(baseline, current_resized)
    diff_data = diff.get_flattened_data() if hasattr(diff, 'get_flattened_data') else diff.getdata()

    # Count differing pixels (with tolerance for anti-aliasing)
    tolerance = 10  # per-channel tolerance
    diff_pixels = 0
    for pixel in diff_data:
        if any(c > tolerance for c in pixel):
            diff_pixels += 1

    total_pixels = baseline.size[0] * baseline.size[1]
    similarity = 1.0 - (diff_pixels / total_pixels) if total_pixels > 0 else 1.0

    # Generate diff image
    diff_path = None
    if diff_output:
        diff_img = _generate_diff_image(baseline, current_resized, tolerance, highlight_color)
        diff_path_obj = Path(diff_output)
        _ensure_dir(diff_path_obj.parent)
        diff_img.save(diff_path_obj, "PNG")
        diff_path = str(diff_path_obj)

    return ComparisonResult(
        name=name,
        match=similarity >= threshold,
        similarity=similarity,
        threshold=threshold,
        baseline_path=str(baseline_path),
        current_path=str(current_path),
        diff_path=diff_path,
        diff_pixels=diff_pixels,
        total_pixels=total_pixels,
        dimensions_match=dimensions_match,
        baseline_size=baseline.size,
        current_size=current.size,
    )


def compare_with_baseline(
    current_path: str | Path,
    name: str,
    threshold: float = 0.95,
    baselines_dir: Optional[Path] = None,
    reports_dir: Optional[Path] = None,
    ignore_regions: Optional[list[tuple[int, int, int, int]]] = None,
) -> ComparisonResult:
    """Compare a screenshot against its saved baseline.

    Args:
        current_path: Path to the current screenshot.
        name: Baseline name to compare against.
        threshold: Similarity threshold (0.0-1.0).
        baselines_dir: Custom baselines directory.
        reports_dir: Custom reports directory for diff images.
        ignore_regions: List of (x, y, width, height) tuples to mask before comparison.

    Returns:
        ComparisonResult with match/similarity data.

    Raises:
        FileNotFoundError: If baseline doesn't exist.
    """
    bd = baselines_dir or BASELINES_DIR
    baseline_path = bd / f"{name}.png"
    if not baseline_path.exists():
        raise FileNotFoundError(f"Baseline not found: {name}")

    rd = _ensure_dir(reports_dir or REPORTS_DIR)
    diff_output = rd / f"{name}_diff.png"

    return compare_images(
        baseline_path=baseline_path,
        current_path=current_path,
        name=name,
        threshold=threshold,
        diff_output=diff_output,
        ignore_regions=ignore_regions,
    )


def _generate_diff_image(
    baseline: "Image.Image",
    current: "Image.Image",
    tolerance: int = 10,
    highlight_color: tuple = (255, 0, 0),
) -> "Image.Image":
    """Generate a side-by-side diff image with differences highlighted.

    Layout: [baseline | diff overlay | current]
    """
    w, h = baseline.size
    canvas = Image.new("RGB", (w * 3, h), (255, 255, 255))

    # Left: baseline
    canvas.paste(baseline, (0, 0))

    # Middle: diff overlay on dimmed baseline
    overlay = baseline.copy()
    overlay = Image.blend(overlay, Image.new("RGB", (w, h), (200, 200, 200)), 0.5)
    diff = ImageChops.difference(baseline, current)
    draw = ImageDraw.Draw(overlay)

    diff_data = diff.get_flattened_data() if hasattr(diff, 'get_flattened_data') else diff.getdata()
    for i, pixel in enumerate(diff_data):
        if any(c > tolerance for c in pixel):
            x = i % w
            y = i // w
            draw.point((x, y), fill=highlight_color)

    canvas.paste(overlay, (w, 0))

    # Right: current
    canvas.paste(current, (w * 2, 0))

    return canvas


def generate_html_report(report: VisualReport, output_path: str | Path) -> Path:
    """Generate an HTML report for visual regression results.

    Args:
        report: VisualReport with comparison results.
        output_path: Path to save the HTML file.

    Returns:
        Path to the generated HTML report.
    """
    path = Path(output_path)
    _ensure_dir(path.parent)

    status_color = "#2ecc71" if report.all_passed else "#e74c3c"
    status_text = "PASSED" if report.all_passed else "FAILED"

    rows = []
    for r in report.results:
        color = "#2ecc71" if r.match else "#e74c3c"
        status = "PASS" if r.match else "FAIL"
        diff_link = f'<a href="{r.diff_path}">View Diff</a>' if r.diff_path else "N/A"
        rows.append(f"""
        <tr>
            <td>{r.name}</td>
            <td style="color:{color};font-weight:bold">{status}</td>
            <td>{r.similarity:.1%}</td>
            <td>{r.threshold:.1%}</td>
            <td>{r.diff_pixels:,} / {r.total_pixels:,} ({r.to_dict()['diff_percentage']:.2f}%)</td>
            <td>{'Yes' if r.dimensions_match else f'No ({r.baseline_size} vs {r.current_size})'}</td>
            <td>{diff_link}</td>
        </tr>""")

    html = f"""<!DOCTYPE html>
<html>
<head>
    <title>Visual Regression Report — {report.name}</title>
    <style>
        body {{ font-family: -apple-system, BlinkMacSystemFont, sans-serif; margin: 2em; }}
        h1 {{ color: #333; }}
        .status {{ display: inline-block; padding: 4px 12px; border-radius: 4px;
                   color: white; background: {status_color}; font-weight: bold; }}
        table {{ border-collapse: collapse; width: 100%; margin-top: 1em; }}
        th, td {{ border: 1px solid #ddd; padding: 8px 12px; text-align: left; }}
        th {{ background: #f5f5f5; }}
        tr:hover {{ background: #f9f9f9; }}
        .summary {{ margin: 1em 0; color: #666; }}
    </style>
</head>
<body>
    <h1>Visual Regression Report</h1>
    <p><strong>Name:</strong> {report.name}</p>
    <p><strong>Date:</strong> {report.created_at}</p>
    <p><strong>Status:</strong> <span class="status">{status_text}</span></p>
    <p class="summary">{report.passed} passed, {report.failed} failed out of {len(report.results)} comparisons</p>
    <table>
        <tr>
            <th>Name</th><th>Status</th><th>Similarity</th><th>Threshold</th>
            <th>Diff Pixels</th><th>Dimensions</th><th>Diff Image</th>
        </tr>
        {''.join(rows)}
    </table>
</body>
</html>"""

    with open(path, "w", encoding="utf-8") as f:
        f.write(html)
    return path


def compute_ssim(
    img1: "Image.Image",
    img2: "Image.Image",
    window_size: int = 8,
) -> float:
    """Compute Structural Similarity Index (SSIM) between two images.

    Simplified SSIM implementation using only Pillow (no scipy/numpy dependency).
    Computes mean SSIM over non-overlapping blocks.

    Args:
        img1: First image (PIL Image, RGB).
        img2: Second image (PIL Image, RGB, same size as img1).
        window_size: Block size for local SSIM computation.

    Returns:
        SSIM value between -1.0 and 1.0 (1.0 = identical).
    """
    if img1.size != img2.size:
        img2 = img2.resize(img1.size, Image.LANCZOS)

    # Convert to grayscale
    g1 = img1.convert("L")
    g2 = img2.convert("L")
    w, h = g1.size
    _gd = lambda img: img.get_flattened_data() if hasattr(img, 'get_flattened_data') else img.getdata()  # noqa: E731
    d1 = list(_gd(g1))
    d2 = list(_gd(g2))

    C1 = (0.01 * 255) ** 2
    C2 = (0.03 * 255) ** 2

    ssim_sum = 0.0
    count = 0

    for by in range(0, h - window_size + 1, window_size):
        for bx in range(0, w - window_size + 1, window_size):
            block1 = []
            block2 = []
            for dy in range(window_size):
                for dx in range(window_size):
                    idx = (by + dy) * w + (bx + dx)
                    block1.append(d1[idx])
                    block2.append(d2[idx])

            n = len(block1)
            mu1 = sum(block1) / n
            mu2 = sum(block2) / n
            var1 = sum((x - mu1) ** 2 for x in block1) / n
            var2 = sum((x - mu2) ** 2 for x in block2) / n
            cov = sum((block1[i] - mu1) * (block2[i] - mu2) for i in range(n)) / n

            num = (2 * mu1 * mu2 + C1) * (2 * cov + C2)
            den = (mu1 ** 2 + mu2 ** 2 + C1) * (var1 + var2 + C2)
            ssim_sum += num / den if den != 0 else 1.0
            count += 1

    return ssim_sum / count if count > 0 else 1.0


@dataclass
class SuiteTest:
    """A single test case in a visual regression suite."""
    name: str
    current: str
    threshold: Optional[float] = None
    ignore_regions: Optional[list[tuple[int, int, int, int]]] = None


@dataclass
class Suite:
    """A visual regression test suite loaded from JSON.

    Suite JSON format::

        {
          "name": "Login Flow",
          "threshold": 0.95,
          "tests": [
            {"name": "login_screen", "current": "screenshots/login.png"},
            {"name": "dashboard", "current": "screenshots/dash.png",
             "threshold": 0.98, "ignore_regions": [[10, 5, 200, 30]]}
          ]
        }
    """
    name: str
    tests: list[SuiteTest]
    threshold: float = 0.95


def _validate_suite_threshold(value: object, context: str) -> float:
    """Validate a suite-sourced threshold is a real number in ``[0.0, 1.0]``.

    Similarity is a fraction in ``[0, 1]``, so a threshold outside that range
    silently breaks every comparison (``> 1.0`` fails identical images, ``< 0.0``
    passes everything). Rejecting it here keeps the JSON ``threshold`` field held
    to the same contract Click's ``FloatRange`` enforces on the ``--threshold``
    flag (#1149).

    Args:
        value: The threshold sourced from the suite JSON (any JSON type).
        context: Human-readable description of where the value came from, used
            in the error message (e.g. ``"suite threshold"``).

    Returns:
        The validated threshold as a float.

    Raises:
        ValueError: If the value is not a real number in ``[0.0, 1.0]``.
    """
    # ``bool`` is a subclass of ``int`` — reject ``true``/``false`` explicitly.
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        raise ValueError(
            f"{context} must be a number in the range 0.0-1.0, got: {value!r}"
        )
    if not 0.0 <= value <= 1.0:
        raise ValueError(
            f"{context} {float(value)} is not in the range 0.0<=x<=1.0"
        )
    return float(value)


def load_suite(path: str | Path) -> Suite:
    """Load a visual regression suite from a JSON file.

    Args:
        path: Path to the suite JSON file.

    Returns:
        Parsed Suite object.

    Raises:
        FileNotFoundError: If the suite file does not exist.
        ValueError: If the suite JSON is invalid (malformed structure or a
            threshold outside the documented ``[0.0, 1.0]`` range).
    """
    p = Path(path)
    if not p.exists():
        raise FileNotFoundError(f"Suite file not found: {path}")

    with open(p, "r", encoding="utf-8") as f:
        data = json.load(f)

    if "tests" not in data or not isinstance(data["tests"], list):
        raise ValueError("Suite JSON must contain a 'tests' array")

    suite_threshold = _validate_suite_threshold(
        data.get("threshold", 0.95), "suite threshold"
    )
    tests = []
    for t in data["tests"]:
        if "name" not in t or "current" not in t:
            raise ValueError("Each test must have 'name' and 'current' fields")
        test_threshold = t.get("threshold")
        if test_threshold is not None:
            test_threshold = _validate_suite_threshold(
                test_threshold, f"test {t['name']!r} threshold"
            )
        regions = None
        if "ignore_regions" in t:
            regions = [tuple(r) for r in t["ignore_regions"]]
        tests.append(SuiteTest(
            name=t["name"],
            current=t["current"],
            threshold=test_threshold,
            ignore_regions=regions,
        ))

    return Suite(
        name=data.get("name", p.stem),
        tests=tests,
        threshold=suite_threshold,
    )


def run_suite(
    suite: Suite,
    baselines_dir: Optional[Path] = None,
    reports_dir: Optional[Path] = None,
) -> VisualReport:
    """Run all tests in a visual regression suite.

    Args:
        suite: Parsed Suite object.
        baselines_dir: Custom baselines directory.
        reports_dir: Custom reports directory.

    Returns:
        VisualReport with all comparison results.
    """
    report = VisualReport(
        name=suite.name,
        created_at=datetime.now().isoformat(),
    )

    for test in suite.tests:
        threshold = test.threshold if test.threshold is not None else suite.threshold
        try:
            result = compare_with_baseline(
                current_path=test.current,
                name=test.name,
                threshold=threshold,
                baselines_dir=baselines_dir,
                reports_dir=reports_dir,
                ignore_regions=test.ignore_regions,
            )
            report.add_result(result)
        except FileNotFoundError:
            report.add_result(ComparisonResult(
                name=test.name,
                match=False,
                similarity=0.0,
                threshold=threshold,
                baseline_path="<not found>",
                current_path=test.current,
            ))

    return report
