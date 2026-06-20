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
import os
import shutil
import socket
import subprocess
import tempfile
import time
from contextlib import contextmanager
from pathlib import Path
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


def test_image_captcha_click_offset_equivalence(
    browser_page: BrowserPage, fixtures_server: str
) -> None:
    """Reproduce the Chaojiying coordinate-click captcha solve via naturo.

    Mirrors the migration guide's "Image Recognition Captcha" section: the
    *Before* code screenshots the captcha image, submits it to a solver
    (Chaojiying / ddddocr) which returns pixel coordinates *relative to the
    captcha image element*, then drives
    ``ActionChains.move_to_element_with_offset(img, x, y).click()`` for each
    returned point. The *After* surface is
    :meth:`BrowserElement.click` with ``offset_x`` / ``offset_y``.

    Driven against ``captcha-image.html`` -- a deterministic 3x3 grid of 80px
    cells (4px gap) whose target is the centre cell (index 4) -- a solver
    coordinate must land on the exact cell, proving the click honours the
    element-relative offset rather than silently defaulting to the element
    centre. Per naturo's never-lie contract (SOUL.md) precision is proven
    *both ways*: a deliberately wrong offset selects the wrong cell and does
    NOT pass, and only the correct offset flips the page's own ``data-passed``
    flag to ``true``.

    Because the target *is* the grid centre, the negative leg is essential: an
    offset-ignoring click would hit the centre cell and spuriously pass, so the
    wrong-offset click landing on cell 0 (the grid's top-left) is what actually
    proves the offset is respected.
    """
    browser_page.navigate(f"{fixtures_server}/captcha-image.html")
    grid = browser_page.find("#captcha-grid")

    # Cell geometry: 80px cells separated by a 4px gap, so each column/row
    # advances by 84px. Cell N's centre, measured from the grid's top-left
    # corner (the origin _get_click_point uses for offsets), is
    # (col * 84 + 40, row * 84 + 40) with col = N % 3, row = N // 3.
    def cell_center(index: int) -> tuple[int, int]:
        col, row = index % 3, index // 3
        return (col * 84 + 40, row * 84 + 40)

    # never-lie (precision, negative leg): a wrong solver coordinate must land on
    # the wrong cell. If the click ignored the offset it would hit the grid
    # centre -- which happens to be the target cell -- and spuriously pass.
    # Cell 0's centre (the grid's top-left) proves the offset is honoured.
    wrong_x, wrong_y = cell_center(0)
    grid.click(offset_x=wrong_x, offset_y=wrong_y)
    assert browser_page.find(".captcha-cell.selected").attr("data-index") == "0"
    assert browser_page.find("#captcha-status").attr("data-passed") == "false"

    # Before: ActionChains.move_to_element_with_offset(img, x, y).click()
    #  ->  After: find(captcha).click(offset_x=x, offset_y=y) at the solver coord.
    target = int(grid.attr("data-target") or "")
    target_x, target_y = cell_center(target)
    grid.click(offset_x=target_x, offset_y=target_y)

    # never-lie: the page's own pass flag flips only because the precise target
    # cell was hit -- the same authoritative signal the Before code checks after
    # clicking the solver-returned coordinate.
    assert browser_page.find(".captcha-cell.selected").attr("data-index") == str(target)
    assert browser_page.find("#captcha-status").attr("data-passed") == "true"
    assert browser_page.find("#captcha-status").text == "Captcha passed."


def test_hover_reveal_menu_equivalence(
    browser_page: BrowserPage, fixtures_server: str
) -> None:
    """Reproduce the DrissionPage ``ele.hover().click()`` reveal-then-click via naturo.

    Mirrors the migration guide's "Hover" / "Dropdown" sections: the *Before*
    DrissionPage code calls ``ele.hover().click()`` on a control whose menu items
    only exist once the trigger is hovered (the upload-video / playlist-select
    pattern). The *After* surface is :meth:`BrowserElement.hover` followed by
    :meth:`BrowserElement.click`.

    Driven against ``hover-menu.html`` -- a CSS ``:hover`` dropdown that is
    ``display:none`` until ``#menu-trigger`` is hovered -- naturo must dispatch a
    real mouse-move that activates the CSS hover state, reveal the menu, and then
    click an item inside it. Per naturo's never-lie contract (SOUL.md) the reveal
    is proven *both ways*: while the menu is hidden a click cannot reach an item
    (no selection happens), and only after the hover dispatch makes the dropdown
    visible does the click land and fire the selection handler. The negative leg
    is essential -- it proves the ``hover()`` is genuinely required, not that the
    item was clickable all along.
    """
    browser_page.navigate(f"{fixtures_server}/hover-menu.html")

    # Before hover: the dropdown is display:none and nothing is selected.
    assert (
        browser_page.evaluate(
            "getComputedStyle(document.getElementById('menu-dropdown')).display"
        )
        == "none"
    )
    assert browser_page.find("#menu-status").attr("data-selected") == ""

    # never-lie (negative leg): a click while the menu is hidden cannot reach the
    # item -- the hidden item has no layout box, so the click lands nowhere and
    # the selection handler never fires. This proves the hover is required.
    browser_page.find("#menu-item-settings").click()
    assert browser_page.find("#menu-status").attr("data-selected") == ""

    # Before: ele.hover()  ->  After: find("#menu-trigger").hover() dispatches a
    # real CDP mouseMoved that activates the CSS :hover and reveals the dropdown.
    browser_page.find("#menu-trigger").hover()
    browser_page.wait_for_function(
        "getComputedStyle(document.getElementById('menu-dropdown')).display === 'block'",
        timeout=3.0,
    )

    # Before: .click() on the now-visible item  ->  After: find(item).click().
    browser_page.find("#menu-item-settings").click()

    # never-lie: the click landed on the revealed item and the selection handler
    # actually ran -- the same authoritative page state the Before code reads back.
    status = browser_page.find("#menu-status")
    assert status.attr("data-selected") == "menu-item-settings"
    assert status.text == "Selected: Settings"


def _wait_for_tab(page: BrowserPage, url_substring: str, timeout: float = 8.0) -> str:
    """Poll ``page.tabs()`` until a tab whose URL contains *url_substring* appears.

    A ``window.open`` target registers with the browser asynchronously, slightly
    after the click handler that triggered it returns, so the new tab is not
    guaranteed to be enumerable on the first ``tabs()`` call. This polls until it
    is, mirroring the *Before* code's ``len(browser.get_tabs()) > old_count``
    guard loop.

    Args:
        page: The connected browser page to enumerate tabs on.
        url_substring: Substring the target tab's URL must contain.
        timeout: Maximum seconds to wait before failing.

    Returns:
        The ``id`` of the first matching tab.

    Raises:
        AssertionError: If no matching tab appears within *timeout*.
    """
    deadline = time.monotonic() + timeout
    while time.monotonic() < deadline:
        for tab in page.tabs():
            if url_substring in tab["url"]:
                return tab["id"]
        time.sleep(0.05)
    raise AssertionError(
        f"No tab matching {url_substring!r} appeared within {timeout}s; "
        f"open tabs: {[t['url'] for t in page.tabs()]}"
    )


def test_tab_management_equivalence(
    isolated_browser_page: BrowserPage, fixtures_server: str
) -> None:
    """Reproduce the DrissionPage multi-tab publishing flow via naturo.

    Mirrors the migration guide's "Tab Management" section: the *Before*
    DrissionPage code records ``len(browser.get_tabs())``, performs an action
    that spawns a new tab via ``window.open``, detects the tab count growing, and
    grabs ``browser.latest_tab`` to drive the new context. The *After* surface is
    :meth:`BrowserPage.tabs` + :meth:`BrowserPage.switch_tab`.

    Driven against ``tabs.html`` -- whose buttons each ``window.open`` another
    fixture into a named browsing context -- naturo must enumerate every spawned
    tab, switch the active connection to a chosen one, and drive content inside
    it. Per naturo's never-lie contract (SOUL.md) the flow is cross-checked two
    ways: the opener page's own ``data-opened`` counter must advance once per
    real click (proving the click landed, not just that a tab appeared), and the
    switched-to tab's content must be readable/writable through the same page
    object (proving ``switch_tab`` truly rebound the CDP connection).

    This test uses :func:`isolated_browser_page` because opening tabs and
    ``switch_tab`` mutate connection-wide target state that must not leak into the
    module-shared read-only browser.
    """
    page = isolated_browser_page
    page.navigate(f"{fixtures_server}/tabs.html")

    # Before: old_tab_count = len(browser.get_tabs())  -> only the opener exists.
    initial_tabs = page.tabs()
    assert len(initial_tabs) == 1
    assert page.find("#tab-status").attr("data-opened") == "0"

    # Before: an action opens a new tab -> After: a real click spawns window.open.
    # never-lie: wait on the page's own counter so we know the click handler ran
    # (not merely that some tab materialised), then confirm the tab enumerates.
    page.find("#open-basic").click()
    page.wait_for_function(
        "document.getElementById('tab-status').getAttribute('data-opened') === '1'",
        timeout=5.0,
    )
    basic_tab_id = _wait_for_tab(page, "basic.html")
    assert len(page.tabs()) == 2  # Before: len(get_tabs()) > old_tab_count

    # A second spawned tab -> the count grows deterministically, one per click.
    page.find("#open-form").click()
    page.wait_for_function(
        "document.getElementById('tab-status').getAttribute('data-opened') === '2'",
        timeout=5.0,
    )
    form_tab_id = _wait_for_tab(page, "form.html")
    assert len(page.tabs()) == 3
    assert page.find("#tab-status").text == "Opened 2 tab(s)."

    # Before: new_tab = browser.latest_tab  -> After: switch_tab to the spawned
    # tab and read its content through the now-rebound connection.
    page.switch_tab(basic_tab_id)
    assert page.find("#intro").text == (
        "A deterministic page for element finding and text extraction."
    )

    # never-lie: switching to another tab and *writing* into it proves the CDP
    # connection genuinely rebound -- a stale connection would type into the old
    # document (or fail to find the field) instead of mutating the form tab.
    page.switch_tab(form_tab_id)
    page.find("#username").type("carol", clear_first=True)
    assert page.find("#username").value == "carol"


def test_file_download_equivalence(
    isolated_browser_page: BrowserPage,
    fixtures_server: str,
    fixtures_dir: Path,
) -> None:
    """Reproduce the DrissionPage download-prefs + filesystem-poll pattern via naturo.

    Mirrors the migration guide's "File Download" section: the *Before* code
    sets ``co.set_pref("download.default_directory", dir)`` (plus
    ``download.prompt_for_download = False``), clicks the export link, then
    spins ``while not os.path.exists(expected_file): time.sleep(1)`` until the
    file lands. The *After* surface is :meth:`BrowserPage.set_download_dir`
    followed by :meth:`BrowserPage.wait_for_download`, exactly as the guide
    documents (``download.path`` / ``download.name``).

    Driven against ``download.html`` -- whose ``#download-link`` anchor carries
    ``download="report.txt"`` and points at the deterministic 42-byte
    ``download-payload.txt`` -- naturo must route the download to the configured
    directory and block until it completes. Per naturo's never-lie contract
    (SOUL.md) the equivalence is proven on the *bytes that landed on disk*: the
    downloaded file's content must be byte-for-byte the served payload (the same
    content/size check the Before code performs after polling), proving a real,
    completed download rather than a partial ``.crdownload`` or a placeholder.

    This test uses :func:`isolated_browser_page` because
    ``Browser.setDownloadBehavior`` installs connection-wide download state that
    must not leak into the module-shared read-only browser.
    """
    page = isolated_browser_page
    # A throwaway download directory (matching this module's tempfile.mkdtemp
    # style for browser temp dirs, so concurrent desktop runs never collide).
    download_dir = tempfile.mkdtemp(prefix="naturo_download_")
    try:
        # Before: co.set_pref("download.default_directory", dir) + prompt suppression
        #  ->  After: page.set_download_dir(dir).
        page.set_download_dir(download_dir)

        page.navigate(f"{fixtures_server}/download.html")

        # never-lie (precondition): nothing has been saved yet, so a passing
        # assertion below can only come from a download this test triggered.
        assert os.listdir(download_dir) == []

        # Before: click the export link, then `while not os.path.exists(f): sleep(1)`
        #  ->  After: click() + wait_for_download() polling until no partial remains.
        page.find("#download-link").click()
        result = page.wait_for_download(timeout=20.0)

        # The anchor's download="report.txt" attribute names the saved file.
        assert result.name == "report.txt"
        assert os.path.basename(result.path) == "report.txt"
        assert os.path.isfile(result.path)

        # never-lie: the bytes on disk are exactly the served payload -- the same
        # content/size equivalence the Before code verifies after its poll loop,
        # proving the download completed rather than leaving a partial file.
        served = (fixtures_dir / "download-payload.txt").read_bytes()
        downloaded = Path(result.path).read_bytes()
        assert downloaded == served
        assert result.size == len(served) == 42
    finally:
        shutil.rmtree(download_dir, ignore_errors=True)


def test_xpath_scoped_card_scrape_equivalence(
    browser_page: BrowserPage, fixtures_server: str
) -> None:
    """Reproduce the rpa-client-lingkehudong (小红书) per-card xpath scrape via naturo.

    Mirrors the migration guide / #763 Phase-1 target: the DrissionPage *Before*
    code enumerates feed cards and reads each card's OWN field with a relative
    xpath scoped to that card::

        items = page.eles("xpath://div[contains(@class,'note-item')]")
        for item in items:
            title = item.ele("xpath:.//span").text

    The *After* surface is :meth:`BrowserPage.find_all` for the card list and the
    element-scoped :meth:`BrowserElement.find` / :meth:`BrowserElement.find_all`
    for each card's children. Driven against ``xhs-feed.html`` (four
    ``.note-item`` cards, each with a distinct title + author span), naturo must
    reproduce the scrape exactly: the same card count and, per card, that card's
    own title text.

    never-lie (SOUL.md): the scoping is proven, not assumed. A relative
    ``xpath:.//span`` resolved against the whole document (the pre-#1063 bug)
    would return the *first* card's title for *every* card, so the scrape would
    confidently report four identical titles. The assertion therefore pins the
    four distinct, per-card titles in document order — which only holds if
    ``item.find(...)`` genuinely confines the search to that card's subtree.
    """
    browser_page.navigate(f"{fixtures_server}/xhs-feed.html")

    # Before: page.eles("xpath://div[contains(@class,'note-item')]")
    #  ->  After: page.find_all("xpath://div[contains(@class,'note-item')]").
    cards = browser_page.find_all("xpath://div[contains(@class,'note-item')]")
    assert len(cards) == 4

    # Before: for item in items: title = item.ele("xpath:.//span").text
    #  ->  After: card.find("xpath:.//span").text, scoped to each card. The first
    # span in each card is its title, so the relative xpath must return that
    # card's own title -- distinct per card, in document order.
    titles = [card.find("xpath:.//span").text for card in cards]
    assert titles == [
        "城市夜景手机摄影技巧",
        "十分钟快手早餐合集",
        "通勤穿搭分享",
        "阳台多肉养护笔记",
    ]
    # never-lie: every scraped title is distinct -- a document-scoped (unscoped)
    # xpath would collapse all four to the first card's title.
    assert len(set(titles)) == 4

    # Scoped find_all: each card exposes exactly its own two spans (title,
    # author), not the feed's eight, proving the array form is scoped too.
    first_card_spans = cards[0].find_all("xpath:.//span")
    assert [span.text for span in first_card_spans] == [
        "城市夜景手机摄影技巧",
        "@aurora",
    ]

    # A scoped CSS read resolves against the same card subtree as the xpath read.
    assert cards[2].find(".note-author").text == "@mina"


def test_scroll_equivalence(
    browser_page: BrowserPage, fixtures_server: str
) -> None:
    """Reproduce the DrissionPage scroll-by-pixels / scroll-into-view pattern via naturo.

    Mirrors the migration guide's "Scroll" section / DrissionPage API mapping:
    the *Before* code calls ``page.scroll.down(1000)`` to advance a feed (the
    Xiaohongshu/Dianping scroll loops that motivate #763) and
    ``ele.scroll.to_see()`` to bring an off-screen control into view before
    acting on it. The *After* surface is :meth:`BrowserPage.scroll_by` and
    :meth:`BrowserPage.scroll_to_element`.

    Driven against ``scroll.html`` -- a page far taller than the viewport with a
    ``#target`` row parked ~2000px below the fold -- naturo must genuinely move
    the viewport. Per naturo's never-lie contract (SOUL.md) the movement is
    proven on the page's own scroll state, both ways: the page opens at the top
    (``scrollY`` 0, target below the fold), ``scroll_by`` advances ``scrollY`` by
    the requested pixels, and ``scroll_to_element`` brings the previously
    off-screen target into the viewport and centres it. A "scroll" that silently
    left the viewport in place would fail every assertion -- ``scrollY`` and the
    target's viewport-relative rect are the live, authoritative scroll position,
    so they cannot report movement that did not happen.
    """
    browser_page.navigate(f"{fixtures_server}/scroll.html")

    def scroll_y() -> int:
        return int(browser_page.evaluate("Math.round(window.scrollY)"))

    def target_top() -> float:
        # The target's top edge, in viewport-relative CSS pixels (negative ->
        # scrolled past it, >= innerHeight -> still below the fold).
        return float(
            browser_page.evaluate(
                "document.getElementById('target').getBoundingClientRect().top"
            )
        )

    viewport_height = int(browser_page.evaluate("window.innerHeight"))

    # never-lie (precondition): the page opens at the top and the target is parked
    # below the fold, so any later "in view" assertion can only come from a real
    # scroll this test performed.
    assert scroll_y() == 0
    assert browser_page.find("#top-marker").text == "top"
    assert target_top() > viewport_height  # target is below the visible viewport

    # Before: page.scroll.down(1000)  ->  After: page.scroll_by(1000).
    # never-lie: the viewport genuinely advanced by the requested pixels; a silent
    # no-op would leave scrollY at 0.
    browser_page.scroll_by(1000)
    assert abs(scroll_y() - 1000) <= 2

    # Before: ele.scroll.to_see()  ->  After: page.scroll_to_element("#target").
    # never-lie: the previously off-screen target is now within the viewport and
    # centred (scroll_into_view uses block:'center'), proving the scroll landed on
    # the element rather than a top-aligned nudge or no-op.
    browser_page.scroll_to_element("#target")
    top_after = target_top()
    assert 0 <= top_after < viewport_height  # target is now visible
    # Centred, not merely top-aligned: block:'center' leaves clear space above the
    # target (a block:'start' scroll would put its top at ~0). The fixture's
    # trailing spacer guarantees there is room to centre.
    assert top_after >= viewport_height * 0.2


def test_javascript_execution_equivalence(
    browser_page: BrowserPage, fixtures_server: str
) -> None:
    """Reproduce the Selenium/DrissionPage ``execute_script`` patterns via naturo.

    Mirrors the migration guide's "JavaScript Execution" section. The *Before*
    code reaches for ``execute_script`` to read page state
    (``return document.readyState``), count elements
    (``document.querySelectorAll(sel).length``), mutate style
    (``document.body.style.zoom='0.85'`` via DrissionPage ``run_js_loaded``) and
    reload the page (``execute_script('location.reload()')``). The *After*
    surface is :meth:`BrowserPage.evaluate`, exactly as the guide documents
    (``page.evaluate(...)`` / ``naturo browser eval``).

    Driven against ``basic.html`` (3 ``.nav-link`` anchors, 2 ``.section-title``
    headings), each ``evaluate`` call must return the real in-page value -- a
    string for ``readyState``, an int for an element count, the assigned string
    for a style mutation that actually sticks on the node -- and after a
    JS-triggered ``location.reload()`` the page must come back intact, proving
    the reload genuinely round-tripped rather than the call being a no-op.

    Scope note (never-lie): the guide's JS-*click* fallback in this same section
    (``naturo browser click "#x" --js`` / ``page.find("#x").click(js=True)``) is
    **not** implemented, so it is deliberately not asserted here; that
    doc-vs-code gap is tracked separately in #1106 rather than papered over.
    """
    browser_page.navigate(f"{fixtures_server}/basic.html")

    # Before: execute_script('return document.readyState')  ->  After: page.evaluate(...).
    # A loaded page reports the string "complete".
    assert browser_page.evaluate("document.readyState") == "complete"

    # Before: execute_script("document.querySelectorAll('.item').length")
    #  ->  After: page.evaluate(...). A primitive number returns as an int.
    assert browser_page.evaluate("document.querySelectorAll('.nav-link').length") == 3
    assert (
        browser_page.evaluate("document.querySelectorAll('.section-title').length") == 2
    )

    # Before: run_js_loaded("document.body.style.zoom='0.85'")  ->  After: page.evaluate(...).
    # The assignment expression returns the assigned value, and reading it back
    # proves the script actually ran in the page (not a swallowed no-op).
    assert browser_page.evaluate("document.body.style.zoom='0.85'") == "0.85"
    assert browser_page.evaluate("document.body.style.zoom") == "0.85"

    # Before: execute_script('location.reload()') + implicitly_wait + readyState check
    #  ->  After: page.evaluate('location.reload()'). reload() returns undefined
    # (-> None); polling readyState (the documented implicitly_wait analogue,
    # robust across the brief navigation window) confirms the reload completed
    # and the page came back whole -- the 3 nav links are present again.
    assert browser_page.evaluate("location.reload()") is None
    browser_page.wait_for_function(
        "document.readyState === 'complete'"
        " && document.querySelectorAll('.nav-link').length === 3",
        timeout=10.0,
    )
    assert browser_page.evaluate("document.readyState") == "complete"
    assert browser_page.evaluate("document.querySelectorAll('.nav-link').length") == 3
