"""Regression guard for the recognition headline doc (issue #982).

``docs/RECOGNITION.md`` is the published proof of naturo's multi-framework
recognition moat. A visitor must be able to read one document that (a) shows the
coverage matrix versus UIA-only rivals, (b) carries the honest #931 benchmark
numbers, and (c) gives a **copy-paste ``see`` / ``find`` / ``click`` example
against the owned Electron fixture** — no external app required (issue #982
acceptance). These tests pin those guarantees so the doc cannot silently drift
away from the acceptance criteria or reference CLI commands that do not exist.
"""

from __future__ import annotations

from pathlib import Path

from naturo.cli import main

_REPO_ROOT = Path(__file__).resolve().parent.parent
_DOC = _REPO_ROOT / "docs" / "RECOGNITION.md"
_README = _REPO_ROOT / "README.md"

#: Window title set by ``benchmarks/recognition/fixtures/electron/main.js``.
_FIXTURE_WINDOW_TITLE = "Naturo Electron Recognition Fixture"


def _doc_text() -> str:
    return _DOC.read_text(encoding="utf-8")


def test_recognition_doc_exists() -> None:
    """The headline recognition doc must exist (issue #982)."""
    assert _DOC.is_file(), "docs/RECOGNITION.md must exist (issue #982)"


def test_readme_links_recognition_doc_above_the_fold() -> None:
    """README must link the doc above the fold as the differentiator headline."""
    head = _README.read_text(encoding="utf-8").splitlines()[:40]
    assert any("docs/RECOGNITION.md" in line for line in head), (
        "README must link docs/RECOGNITION.md above the fold (issue #982)"
    )


def test_doc_has_capability_matrix_for_all_three_frameworks() -> None:
    """The coverage matrix must name Electron, Java and SAP rows."""
    text = _doc_text()
    assert "Capability matrix" in text
    for framework in ("Electron", "Java", "SAP"):
        assert framework in text, f"matrix must cover the {framework} framework"


def test_doc_carries_benchmark_numbers_without_fabrication() -> None:
    """The measured #931 results table and an honest-gap note must be present."""
    text = _doc_text()
    assert "Measured benchmark" in text
    # Honest about the frameworks that still cannot be measured live on the host
    # (SAP, and mature external Java apps) — the gaps section must persist so no
    # fabricated row can be slipped in for an unmeasured framework.
    assert "Documented gaps" in text
    assert "not available in this environment" in text or "not installed" in text


def test_doc_has_owned_fixture_copy_paste_example() -> None:
    """The Electron how-to must offer a runnable example on the OWNED fixture.

    Acceptance bullet (#982): "a copy-paste ``naturo see/find/click`` example
    against the owned fixture app." Earlier how-to text only targeted external
    apps (VS Code / DBeaver), which a reader cannot reproduce without installing
    them; the owned Electron fixture ships in-repo and needs no third-party app.
    """
    text = _doc_text()
    assert _FIXTURE_WINDOW_TITLE in text, (
        "the how-to must target the owned Electron fixture window so the "
        "example is reproducible without any external app (issue #982)"
    )
    for command in ("naturo see", "naturo find", "naturo click"):
        assert command in text, (
            f"the owned-fixture how-to must show a `{command}` example (#982)"
        )


def test_documented_commands_are_real_cli_commands() -> None:
    """The see/find/click commands the doc advertises must exist in the CLI."""
    for command in ("see", "find", "click"):
        assert command in main.commands, (
            f"docs/RECOGNITION.md references `naturo {command}`, which the CLI "
            f"must expose"
        )


def test_jab_row_carries_interim_regression_caveat() -> None:
    """The Java Access Bridge claims must flag the live regression (issue #1098).

    #1096 proved on a correctly-provisioned desktop (JDK 21 + JAB enabled) that
    naturo's JAB init never attaches, so the published ``+40 via jab`` headline
    and the ``Java Swing / SWT (JAB) ✅`` matrix cell do **not** currently
    reproduce. Per never-lie (SOUL.md), the doc must not assert that result
    while the shipped code cannot produce it. This pins an interim honesty
    caveat — explicitly tracking #1096 — so a future edit cannot silently
    re-assert the unreproducible number without first removing the caveat (i.e.
    after #1096 lands and ``test_jab_recognition_932.py`` is green again).
    """
    text = _doc_text()
    assert "#1096" in text, (
        "the JAB section must reference the tracking issue #1096 while the "
        "moat row is under repair (issue #1098)"
    )
    # A recognizable known-regression marker must accompany the JAB claims so
    # the public doc reads as 'under repair', not as a reproduced result.
    lowered = text.lower()
    assert "known regression" in lowered or "under repair" in lowered, (
        "the JAB row/matrix cell must be marked as a known regression / under "
        "repair while #1096 is open (issue #1098)"
    )
