"""Offline acceptance for the browser migration fixtures (#1062, part of #766).

These deterministic static pages stand in for real-world sites so the
before/after migration matrix (#766/#1063) can run fully offline, with no
external sites and no flakiness. This module proves three contract properties
for every fixture, on every OS, with no browser and no native DLL:

  1. **It loads over HTTP** from a local server (the same way #1063 serves it
     to Chrome) — a ``200`` with the right content type.
  2. **It exercises the feature its #766 row needs** — asserted via required
     structural markers, so a fixture cannot silently regress into an empty
     page that "loads" but tests nothing.
  3. **It is fully offline** — no ``http(s)://`` resource references, so the
     matrix never depends on a network or an external site.

These checks are pure-stdlib and CI-safe (Linux/macOS included): they do not
launch Chrome or touch the native core. Driving the fixtures through a real
browser is #1063's job.
"""

from __future__ import annotations

import json
import urllib.request
from pathlib import Path

import pytest

# fixture filename -> structural markers proving it exercises its feature.
# Each marker is a substring that MUST appear in the served page; if a fixture
# is gutted, the matching test fails loudly instead of silently passing.
FIXTURE_MARKERS: dict[str, list[str]] = {
    # Element finding + text extraction.
    "basic.html": ['id="main-heading"', 'class="nav-link"', 'id="intro"'],
    # Form filling, dropdown selection, file upload, submit.
    "form.html": [
        'id="signup-form"',
        'method="post"',
        'name="username"',
        "<textarea",
        "<select",
        'type="file"',
        'type="submit"',
    ],
    # Scraping loop + scroll: JS appends note cards as the feed scrolls.
    "infinite-scroll.html": ['id="feed"', "note-card", 'addEventListener("scroll"'],
    # Slider captcha: draggable handle validated against a target offset.
    "captcha-slider.html": [
        'id="slider-track"',
        'id="slider-handle"',
        'id="slider-status"',
    ],
    # Image captcha: click-to-verify grid with a known target cell.
    "captcha-image.html": ['id="captcha-grid"', "captcha-cell", "data-target"],
    # iframe switching: 2-level nested frames ending in a form.
    "iframe-nested.html": ['id="frame-level1"', "iframe-level1.html"],
    "iframe-level1.html": ['id="frame-level2"', "iframe-level2.html"],
    "iframe-level2.html": ['id="deep-input"', "<form"],
    # Network interception: page fetches JSON via XHR/fetch and renders it.
    "api-dashboard.html": ['id="api-output"', "api-data.json", "fetch("],
    "api-data.json": ['"orders"'],
    # Anti-detection: reads navigator.webdriver and automation markers.
    "stealth-check.html": [
        "navigator.webdriver",
        'id="webdriver-result"',
        'id="stealth-summary"',
    ],
    # Hover interaction: submenu revealed on hover.
    "hover-menu.html": ['id="menu-trigger"', 'id="menu-dropdown"', ":hover"],
    # Tab management: links open new windows.
    "tabs.html": ["window.open(", 'class="open-tab"'],
    # Download management: anchor triggers a file download.
    "download.html": ['id="download-link"', "download="],
}

ALL_FIXTURES = sorted(FIXTURE_MARKERS)
HTML_FIXTURES = [name for name in ALL_FIXTURES if name.endswith(".html")]

# The 11 top-level pages the #766 fixture table requires (excludes the nested
# iframe children and the XHR JSON endpoint, which are supporting files).
REQUIRED_766_FIXTURES = {
    "basic.html",
    "form.html",
    "infinite-scroll.html",
    "captcha-slider.html",
    "captcha-image.html",
    "iframe-nested.html",
    "api-dashboard.html",
    "stealth-check.html",
    "hover-menu.html",
    "tabs.html",
    "download.html",
}


@pytest.mark.parametrize("name", ALL_FIXTURES)
def test_fixture_loads_and_exercises_feature(name: str, fixtures_server: str) -> None:
    """Each fixture serves a 200 with the right type and its feature markers."""
    url = f"{fixtures_server}/{name}"
    with urllib.request.urlopen(url, timeout=10) as response:  # noqa: S310 - loopback
        assert response.status == 200
        content_type = response.headers.get_content_type()
        body = response.read().decode("utf-8")

    if name.endswith(".json"):
        assert content_type == "application/json", f"{name}: got {content_type}"
        json.loads(body)  # must be valid, parseable JSON
    else:
        assert content_type == "text/html", f"{name}: got {content_type}"

    for marker in FIXTURE_MARKERS[name]:
        assert marker in body, f"{name} missing required marker: {marker!r}"


@pytest.mark.parametrize("name", HTML_FIXTURES)
def test_fixture_is_fully_offline(name: str, fixtures_dir: Path) -> None:
    """No fixture may reference an external resource (#1062: 'No external sites')."""
    text = (fixtures_dir / name).read_text(encoding="utf-8").lower()
    for forbidden in ("http://", "https://", 'src="//', "src='//"):
        assert forbidden not in text, (
            f"{name} references an external resource ({forbidden!r}); fixtures "
            "must load fully offline so the migration matrix is deterministic."
        )


def test_all_766_fixtures_present(fixtures_dir: Path) -> None:
    """Every page named in the #766 fixture table exists on disk."""
    present = {path.name for path in fixtures_dir.glob("*.html")}
    missing = REQUIRED_766_FIXTURES - present
    assert not missing, f"missing #766 fixtures: {sorted(missing)}"
