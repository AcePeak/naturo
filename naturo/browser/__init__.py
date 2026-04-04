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
from naturo.browser._captcha import (
    CaptchaManager,
    CaptchaSolver,
    CaptchaError,
    ManualSolver,
    TokenInjectionSolver,
)
from naturo.browser._launcher import (
    ChromeProcess,
    find_chrome,
    launch_chrome,
    list_profiles,
)
from naturo.browser._frame import BrowserFrame

__all__ = [
    "BrowserPage",
    "BrowserElement",
    "BrowserFrame",
    "SelectorType",
    "ParsedSelector",
    "parse_selector",
    "CaptchaManager",
    "CaptchaSolver",
    "CaptchaError",
    "ManualSolver",
    "TokenInjectionSolver",
    "ChromeProcess",
    "find_chrome",
    "launch_chrome",
    "list_profiles",
]
