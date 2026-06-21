"""#1141: ``visual`` comparison-result commands must carry the ``-j`` success envelope.

``visual compare -j`` / ``visual diff -j`` historically emitted a **bare result
object** on success (``result.to_dict()`` with no top-level ``"success"`` key),
while their error paths and every sibling ``visual`` subcommand already use the
standard ``{"success": true, ...}`` / ``{"success": false, "error": {...}}``
envelope. A programmatic consumer could not branch on ``success`` for these
commands.

This is the direct missed sibling of #977 (which fixed ``visual list`` /
``selector show``). Rather than fix only the two commands named in #1141, this
module sweeps the **whole visual comparison-result family** so the next QA round
cannot file the same defect against ``report`` / ``suite`` — the per-subcommand
drip the #1142 umbrella exists to stop:

* ``visual compare -j``  (#1141)
* ``visual diff -j``     (#1141)
* ``visual report -j``   (same-file sibling: emitted ``report.to_dict()`` bare)
* ``visual suite -j``    (same-file sibling: emitted ``report.to_dict()`` bare)

The success envelope means *the operation completed* — a visual **mismatch** is a
valid result (``match: false`` / ``all_passed: false``) reported with
``success: true`` and the existing ``exit 1`` PASS/FAIL semantics preserved, not
an error. These are pure CLI/JSON tests with no DLL, desktop session, or input
simulation required.

The temp directories use :func:`tempfile.mkdtemp` rather than the ``tmp_path``
fixture: the shared pytest temp base on the agent host is contended by concurrent
loop cycles and its numbered-dir scan intermittently raises ``WinError 5``, so
``mkdtemp`` (which creates an isolated directory without scanning that base) keeps
the test deterministic on both the agent host and CI (matching the approach in
``tests/test_json_envelope_contract.py``).
"""

from __future__ import annotations

import json
import shutil
import tempfile
from pathlib import Path
from typing import Iterator

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
def runner() -> CliRunner:
    return CliRunner()


@pytest.fixture()
def workdir() -> Iterator[Path]:
    """Yield a fresh, isolated working directory (see module docstring)."""
    path = Path(tempfile.mkdtemp(prefix="naturo-visual-envelope-1141-"))
    try:
        yield path
    finally:
        shutil.rmtree(path, ignore_errors=True)


@pytest.fixture()
def stores(workdir, monkeypatch) -> Path:
    """Point the baseline/report stores at isolated temp dirs."""
    bd = workdir / "baselines"
    rd = workdir / "reports"
    bd.mkdir()
    rd.mkdir()
    monkeypatch.setattr(visual_mod, "BASELINES_DIR", bd)
    monkeypatch.setattr(visual_mod, "REPORTS_DIR", rd)
    return bd


def _png(path: Path, color: tuple[int, int, int]) -> Path:
    Image.new("RGB", (100, 100), color).save(path)
    return path


@pytest.fixture()
def red_image(workdir) -> Path:
    return _png(workdir / "red.png", (255, 0, 0))


@pytest.fixture()
def red_copy(workdir) -> Path:
    return _png(workdir / "red_copy.png", (255, 0, 0))


@pytest.fixture()
def blue_image(workdir) -> Path:
    return _png(workdir / "blue.png", (0, 0, 255))


# ── visual compare -j ─────────────────────────────────────────────────────────


class TestCompareEnvelope:
    def test_match_success_has_envelope(self, runner, stores, red_image, red_copy):
        """A matching compare emits success=true alongside the result fields."""
        runner.invoke(main, ["visual", "baseline", "s1", "--from", str(red_image)])
        result = runner.invoke(
            main, ["visual", "compare", "s1", "--current", str(red_copy), "--json"]
        )
        assert result.exit_code == 0, result.output
        data = json.loads(result.output)
        assert data["success"] is True
        # Existing result fields are preserved (backward-compatible).
        assert data["match"] is True
        assert data["similarity"] == 1.0

    def test_mismatch_still_success_true_with_exit_1(
        self, runner, stores, red_image, blue_image
    ):
        """A mismatch is a valid result: success=true, match=false, exit 1."""
        runner.invoke(main, ["visual", "baseline", "s1", "--from", str(red_image)])
        result = runner.invoke(
            main, ["visual", "compare", "s1", "--current", str(blue_image), "--json"]
        )
        assert result.exit_code == 1
        data = json.loads(result.output)
        assert data["success"] is True
        assert data["match"] is False

    def test_error_path_envelope_unchanged(self, runner, stores, red_image):
        """The error path keeps success=false (no regression)."""
        result = runner.invoke(
            main, ["visual", "compare", "missing", "--current", str(red_image), "--json"]
        )
        assert result.exit_code == 1
        data = json.loads(result.output)
        assert data["success"] is False
        assert "error" in data


# ── visual diff -j ────────────────────────────────────────────────────────────


class TestDiffEnvelope:
    def test_match_success_has_envelope(self, runner, red_image, red_copy):
        result = runner.invoke(
            main, ["visual", "diff", str(red_image), str(red_copy), "--json"]
        )
        assert result.exit_code == 0, result.output
        data = json.loads(result.output)
        assert data["success"] is True
        assert data["match"] is True

    def test_mismatch_has_envelope(self, runner, red_image, blue_image):
        result = runner.invoke(
            main, ["visual", "diff", str(red_image), str(blue_image), "--json"]
        )
        assert result.exit_code == 0, result.output
        data = json.loads(result.output)
        assert data["success"] is True
        assert data["match"] is False


# ── visual report -j ──────────────────────────────────────────────────────────


class TestReportEnvelope:
    def test_report_success_has_envelope(self, runner, stores, red_image, workdir):
        runner.invoke(main, ["visual", "baseline", "s1", "--from", str(red_image)])
        current_dir = workdir / "current"
        current_dir.mkdir()
        _png(current_dir / "s1.png", (255, 0, 0))
        result = runner.invoke(
            main, ["visual", "report", "--current-dir", str(current_dir), "--json"]
        )
        assert result.exit_code == 0, result.output
        data = json.loads(result.output)
        assert data["success"] is True
        assert data["all_passed"] is True


# ── visual suite -j ───────────────────────────────────────────────────────────


class TestSuiteEnvelope:
    def test_suite_success_has_envelope(self, runner, stores, red_image, red_copy, workdir):
        runner.invoke(main, ["visual", "baseline", "s1", "--from", str(red_image)])
        suite_file = workdir / "suite.json"
        suite_file.write_text(
            json.dumps({"name": "S", "tests": [{"name": "s1", "current": str(red_copy)}]})
        )
        result = runner.invoke(main, ["visual", "suite", str(suite_file), "--json"])
        assert result.exit_code == 0, result.output
        data = json.loads(result.output)
        assert data["success"] is True
        assert data["all_passed"] is True
