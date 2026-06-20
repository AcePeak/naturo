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

import shutil
import socket
import subprocess
import tempfile
from typing import Iterator

import pytest

from naturo.browser import BrowserPage, launch_chrome

pytestmark = pytest.mark.desktop


def _free_tcp_port() -> int:
    """Return a currently-free loopback TCP port for the CDP endpoint."""
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as sock:
        sock.bind(("127.0.0.1", 0))
        return int(sock.getsockname()[1])


@pytest.fixture(scope="module")
def browser_page() -> Iterator[BrowserPage]:
    """A headless Chrome connected via CDP, isolated in a temp profile.

    Launched once per module on a free port with a throwaway
    ``user_data_dir`` so it never touches the real Chrome profile, and is
    fully torn down afterwards.

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
