"""Browser automation package for naturo.

Provides high-level browser automation via Chrome DevTools Protocol (CDP).
Built on top of :mod:`naturo.cdp` — extends it with a user-friendly
``BrowserPage`` / ``BrowserElement`` API.

Usage::

    from naturo.browser import BrowserPage

    page = BrowserPage(port=9222)
    page.navigate("https://example.com")
    page.find("#search").type("hello")
    page.find("button.submit").click()
    print(page.title)
    page.close()

Or as context manager::

    with BrowserPage(port=9222) as page:
        page.navigate("https://example.com")
        items = page.find_all("css:.item")
        for item in items:
            print(item.text)
"""

from naturo.browser._page import BrowserPage
from naturo.browser._element import BrowserElement
from naturo.browser._selectors import (
    SelectorType,
    ParsedSelector,
    parse_selector,
)

__all__ = [
    "BrowserPage",
    "BrowserElement",
    "SelectorType",
    "ParsedSelector",
    "parse_selector",
]
