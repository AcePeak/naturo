"""Before/After migration equivalence tests for the browser subcommand (#766).

``docs/MIGRATION_FROM_RPA_SCRIPTS.md`` promises that real DrissionPage/Selenium
client patterns can be reproduced 1:1 with naturo's browser API. This module
proves that promise end-to-end: it drives the documented *After* surface
(:class:`naturo.browser.BrowserPage`) against the deterministic, fully-offline
fixtures from #1073 and asserts the *Before* (old-library) behaviour is
faithfully reproduced -- same element counts, same extracted text, same
post-action page state.

These tests launch a real headless Chrome via CDP, so they are marked
``@pytest.mark.desktop`` and skipped on the headless Linux/macOS CI matrix
(which runs ``-m "not desktop"``). They remain collectable everywhere: all
Chrome interaction is confined to fixtures, so ``--collect-only`` needs no
browser.

Each launch is isolated in its own throwaway ``user_data_dir`` on a free port,
so concurrent desktop runs (e.g. Dev + QA) never share a Chrome profile.
"""

from __future__ import annotations

import json
import shutil
import socket
import subprocess
import tempfile
from contextlib import contextmanager
from typing import Iterator

import pytest

from naturo.browser import BrowserPage, launch_chrome

pytestmark = pytest.mark.desktop


def _free_tcp_port() -> int:
    """Return a currently-free loopback TCP port for the CDP endpoint."""
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as sock:
        sock.bind(("127.0.0.1", 0))
        return int(sock.getsockname()[1])


@contextmanager
def _headless_chrome_page() -> Iterator[BrowserPage]:
    """Yield a headless Chrome connected via CDP, isolated in a temp profile.

    Each browser runs on its own free port with a throwaway ``user_data_dir``
    so it never touches the real Chrome profile and concurrent desktop runs
    (e.g. Dev + QA) never share a profile. The process and its temp directory
    are fully torn down on exit.

    Yields:
        A connected :class:`BrowserPage`.
    """
    user_data_dir = tempfile.mkdtemp(prefix="naturo_migration_")
    port = _free_tcp_port()
    chrome = launch_chrome(
        port=port,
        headless=True,
        user_data_dir=user_data_dir,
        timeout=30.0,
    )
    page = BrowserPage(port=port)
    try:
        yield page
    finally:
        page.close()
        chrome.terminate()
        try:
            chrome.wait(timeout=10)
        except subprocess.TimeoutExpired:
            chrome.kill()
        shutil.rmtree(user_data_dir, ignore_errors=True)


@pytest.fixture(scope="module")
def browser_page() -> Iterator[BrowserPage]:
    """A headless Chrome shared across the module's read-only equivalence tests.

    Launched once per module; safe to share because these tests only navigate
    and read. Tests that install connection-wide CDP state (e.g. network
    interception) must use :func:`isolated_browser_page` instead.

    Yields:
        A connected :class:`BrowserPage`.
    """
    with _headless_chrome_page() as page:
        yield page


@pytest.fixture
def isolated_browser_page() -> Iterator[BrowserPage]:
    """A throwaway headless Chrome for tests that mutate connection-wide state.

    Network request interception installs a CDP ``Fetch`` rule that persists for
    the lifetime of the connection, so the mocking test runs against its own
    browser rather than the module-shared :func:`browser_page` -- otherwise the
    rule would leak into sibling tests and pause their matching requests.

    Yields:
        A connected :class:`BrowserPage`.
    """
    with _headless_chrome_page() as page:
        yield page


def test_element_finding_equivalence(
    browser_page: BrowserPage, fixtures_server: str
) -> None:
    """Reproduce the DrissionPage element-dictionary scrape via naturo.

    Mirrors the migration guide's "Element Finding" section: the *Before*
    code reads ``page.ele(sel).text``, iterates ``page.eles(sel)``, and pulls
    ``ele.attr(name)``; the *After* code uses ``find``/``find_all``/``attr``.
    Driven against ``basic.html``, the two must agree on element counts, text,
    and attribute values.
    """
    browser_page.navigate(f"{fixtures_server}/basic.html")

    # Before: page.eles("...nav-link...")  ->  After: page.find_all(".nav-link")
    links = browser_page.find_all(".nav-link")
    assert [el.text for el in links] == ["Documentation", "Guide", "API"]

    # Before: page.ele("#intro").text  ->  After: page.find("#intro").text
    assert browser_page.find("#intro").text == (
        "A deterministic page for element finding and text extraction."
    )

    # Before: ele.attr("data-count")  ->  After: page.find(...).attr(...)
    assert browser_page.find("#item-count").attr("data-count") == "2"

    # Section bodies extracted in document order (the multi-element scrape loop).
    sections = browser_page.find_all(".section-title")
    assert [el.text for el in sections] == ["Section One", "Section Two"]


def test_form_interaction_equivalence(
    browser_page: BrowserPage, fixtures_server: str
) -> None:
    """Reproduce the Dianping click/input/wait/read pattern via naturo.

    Mirrors the migration guide's "Element Interaction" section: type into
    fields, choose a dropdown option, submit, wait for the result, and read it
    back. Per naturo's never-lie contract (SOUL.md), every action is verified
    against the resulting page state rather than trusted on return.
    """
    browser_page.navigate(f"{fixtures_server}/form.html")

    # Before: ele.input("alice")  ->  After: find(...).type("alice", clear_first=True)
    browser_page.find("#username").type("alice", clear_first=True)
    assert browser_page.find("#username").value == "alice"

    browser_page.find("#bio").type("Automation engineer", clear_first=True)
    assert browser_page.find("#bio").value == "Automation engineer"

    # Before: dropdown selection  ->  After: find("#country").select("cn")
    browser_page.find("#country").select("cn")
    assert browser_page.find("#country").value == "cn"

    # Before: ele.click() then a hand-written polling loop
    #  ->  After: click() + wait_for(state="visible")
    browser_page.find("#submit-button").click()
    browser_page.wait_for("#form-status", state="visible", timeout=5.0)

    # never-lie: the submit handler must have actually run and mutated the page.
    status = browser_page.find("#form-status")
    assert status.text == "Submitted: alice"
    assert status.attr("data-submitted") == "true"


def test_iframe_switching_equivalence(
    browser_page: BrowserPage, fixtures_server: str
) -> None:
    """Reproduce the Selenium ``switch_to.frame`` captcha/login flow via naturo.

    Mirrors the migration guide's "iframe Handling" section: the *Before* code
    chains ``driver.switch_to.frame(...)`` to reach an element nested two iframe
    levels deep, then fills and submits a form inside it. The *After* surface is
    the scoped :meth:`BrowserPage.frame` / :meth:`BrowserFrame.frame` objects.

    Driven against ``iframe-nested.html`` (top -> ``frame-level1`` ->
    ``frame-level2`` -> ``#deep-form``), this proves both that frame scoping
    resolves the deeply-nested element *and* — per naturo's never-lie contract
    (SOUL.md) — that a frame-scoped ``click`` actually lands on its target and
    fires the form submit, rather than silently missing because the element's
    frame-relative coordinates were dispatched in the top document (#1080).
    """
    browser_page.navigate(f"{fixtures_server}/iframe-nested.html")

    # Before: driver.switch_to.frame(level1); driver.switch_to.frame(level2)
    #  ->  After: page.frame(name=...).frame(name=...)
    level2 = browser_page.frame(name="frame-level1").frame(name="frame-level2")

    # The nested frame's own content is reachable through the scoped object.
    assert level2.find("#level2-heading").text == "Level 2 frame"

    # Before: ele.input(...)  ->  After: frame.find(...).type(...)
    level2.find("#deep-input").type("nested-ok", clear_first=True)
    assert level2.find("#deep-input").value == "nested-ok"

    # Before: ele.click() inside the switched frame
    #  ->  After: frame.find(...).click(). This is the #1080 regression guard:
    # the click point must be resolved in top-document coordinates so the event
    # lands inside the (doubly-nested) iframe instead of the top-level page.
    level2.find("#deep-submit").click()

    # never-lie: the in-frame submit handler must have actually run.
    deep_status = level2.find("#deep-status")
    assert deep_status.text == "Submitted: nested-ok"
    assert deep_status.attr("data-submitted") == "true"


def test_infinite_scroll_scraping_equivalence(
    browser_page: BrowserPage, fixtures_server: str
) -> None:
    """Reproduce the Xiaohongshu infinite-scroll scrape loop via naturo.

    Mirrors the migration guide's "Data Scraping with Infinite Scroll" pattern
    (the real DrissionPage Xiaohongshu brand-keyword project): the *Before*
    code loops ``page.eles(note)``, dedups each card by a stable id, and calls
    ``page.scroll.down(1000)`` until the feed stops growing. The *After*
    surface is :meth:`BrowserPage.find_all` + :meth:`BrowserPage.scroll_to_bottom`
    with ``attr``-keyed dedup.

    Driven against ``infinite-scroll.html`` -- a feed that lazily appends six
    cards each time a scroll nears the bottom, up to a fixed total of 30 -- the
    scrape loop must collect every card exactly once, in document order, and
    terminate on its own when the feed is exhausted (rather than over- or
    under-counting). Per naturo's never-lie contract (SOUL.md) the scrape's own
    tally is cross-checked against the page's authoritative ``data-loaded``
    counter.
    """
    browser_page.navigate(f"{fixtures_server}/infinite-scroll.html")

    # Lazy feed: only the first batch exists before any scroll happens.
    assert len(browser_page.find_all(".note-card")) == 6
    assert browser_page.find("#status").attr("data-loaded") == "6"

    # Before: for _ in range(80): eles = page.eles(note); dedup; scroll.down(1000)
    #  ->  After: find_all + attr-keyed dedup + scroll, terminating when a
    # scroll loads no new cards instead of relying on a fixed iteration cap.
    # scroll_to_bottom (vs a fixed scroll_by step) deterministically crosses the
    # feed's lazy-load threshold on every call, so each scroll appends exactly
    # one batch -- the page grows the document as it loads, which a fixed-pixel
    # step can undershoot.
    seen_indices: list[str] = []
    seen: set[str] = set()
    for _ in range(40):  # generous safety cap; real exit is "no new cards".
        for card in browser_page.find_all(".note-card"):
            index = card.attr("data-index")
            assert index is not None  # every fixture card carries a stable id
            if index not in seen:
                seen.add(index)
                seen_indices.append(index)
        if len(seen) >= 30:
            break
        # The scroll event handler appends the next batch asynchronously, so
        # wait for the feed to actually grow before re-scraping. A timeout here
        # means the feed is exhausted -> the scrape loop is done.
        before = len(seen)
        browser_page.scroll_to_bottom()
        try:
            browser_page.wait_for_function(
                f"document.querySelectorAll('.note-card').length > {before}",
                timeout=3.0,
            )
        except TimeoutError:
            break

    # Equivalence: every one of the 30 cards scraped exactly once, in document
    # order -- the same deduplicated set the DrissionPage scroll loop yields.
    assert seen_indices == [str(i) for i in range(30)]
    # never-lie: the scrape's tally agrees with the page's own load counter.
    assert browser_page.find("#status").attr("data-loaded") == "30"


def test_network_observe_equivalence(
    browser_page: BrowserPage, fixtures_server: str
) -> None:
    """Reproduce the Selenium performance-log XHR capture via naturo.

    Mirrors the migration guide's "Network Request Interception" section: the
    *Before* Selenium code enables ``goog:loggingPrefs`` and scrapes
    ``Network.responseReceived`` events out of the performance log to learn which
    API calls a page made; the *After* surface is
    :meth:`naturo.browser._network.NetworkMonitor.find_requests`.

    Driven against ``api-dashboard.html`` -- which fetches ``api-data.json`` via
    XHR and renders one ``.order-row`` per order -- naturo must both observe the
    captured request and (per the never-lie contract, SOUL.md) see the real
    response data flow into the DOM.

    Scope note: the migration guide also documents a ``page.listen`` /
    ``page.wait_for_response`` response-*body* streaming API that the shipped
    surface does not implement (filed as a doc/impl gap). The implemented and
    verified network surface is request observation here plus interception via
    ``mock_response`` (see :func:`test_network_mock_response_equivalence`).
    """
    browser_page.navigate(f"{fixtures_server}/api-dashboard.html")
    browser_page.wait_for_function(
        "document.getElementById('api-output').getAttribute('data-loaded') === 'true'",
        timeout=5.0,
    )

    # never-lie: the real on-disk response actually reached the DOM in order.
    rows = browser_page.find_all(".order-row")
    assert [row.text for row in rows] == [
        "1001: Wireless Mouse ($24.99)",
        "1002: Mechanical Keyboard ($89.5)",
        "1003: USB-C Hub ($41)",
    ]

    # Before: parse Network.responseReceived out of the perf log to find the XHR.
    #  ->  After: page.network.find_requests(pattern).
    matches = browser_page.network.find_requests("*api-data.json*")
    assert len(matches) == 1
    assert matches[0]["name"].endswith("/api-data.json")
    assert matches[0]["type"] == "fetch"


def test_network_mock_response_equivalence(
    isolated_browser_page: BrowserPage, fixtures_server: str
) -> None:
    """Reproduce Selenium's CDP ``Fetch.fulfillRequest`` mocking via naturo.

    Mirrors the request-interception promise from the other direction: rather
    than only observing traffic, the *Before* Selenium code registers a
    ``Fetch.enable`` + ``Fetch.fulfillRequest`` handler to feed a deterministic
    response body; the *After* surface is
    :meth:`naturo.browser._network.NetworkMonitor.mock_response`. The rule is
    installed *before* navigation so it is in place when ``api-dashboard.html``
    issues its XHR.

    never-lie: the assertion is the rendered DOM, proving the page consumed the
    mocked body instead of the on-disk ``api-data.json`` (which carries three
    different orders) -- a real intercept, not a silent passthrough.
    """
    page = isolated_browser_page
    mocked_body = json.dumps(
        {"orders": [{"id": 9001, "item": "Mocked Widget", "total": 7.5}]}
    )
    page.network.mock_response("*api-data.json*", body=mocked_body)

    page.navigate(f"{fixtures_server}/api-dashboard.html")
    page.wait_for_function(
        "document.getElementById('api-output').getAttribute('data-loaded') === 'true'",
        timeout=5.0,
    )

    # The on-disk fixture serves three orders; the mock replaced them entirely.
    rows = page.find_all(".order-row")
    assert [row.text for row in rows] == ["9001: Mocked Widget ($7.5)"]
    assert page.find("#api-status").text == "Loaded 1 orders."
