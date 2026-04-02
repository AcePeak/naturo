"""Anti-detection stealth patches for browser automation.

Applies Chrome launch flags and runtime JavaScript patches to reduce
bot fingerprinting. Based on common detection vectors checked by
anti-bot services (e.g. ``navigator.webdriver``, missing plugins,
headless indicators).

Usage (programmatic)::

    from naturo.browser._stealth import STEALTH_FLAGS, apply_stealth_patches
    from naturo.browser import BrowserPage

    # Launch Chrome with stealth flags (pass to _launcher.launch_chrome)
    proc = launch_chrome(extra_args=STEALTH_FLAGS)

    # Then apply runtime JS patches
    page = BrowserPage(port=proc.port)
    apply_stealth_patches(page)

Usage (CLI)::

    naturo browser stealth              # Apply to running browser
    naturo browser stealth-flags        # Print flags for manual launch
"""

from __future__ import annotations

import logging
from typing import List

logger = logging.getLogger(__name__)

# ── Chrome launch flags ──────────────────────────────────────────────────────

STEALTH_FLAGS: List[str] = [
    "--disable-blink-features=AutomationControlled",
    "--disable-infobars",
    "--disable-extensions",
    "--disable-default-apps",
    "--disable-popup-blocking",
    "--window-size=1920,1080",
    "--start-maximized",
]
"""Chrome flags that reduce automation fingerprinting."""

# ── Runtime JavaScript patches ───────────────────────────────────────────────
#
# Each patch is a JS snippet injected via Page.addScriptToEvaluateOnNewDocument
# so it executes before any page script.  The patches are idempotent and safe
# to re-apply.

_PATCH_WEBDRIVER = """
Object.defineProperty(navigator, 'webdriver', {
    get: () => undefined,
    configurable: true,
});
"""

_PATCH_PLUGINS = """
Object.defineProperty(navigator, 'plugins', {
    get: () => {
        const plugins = [
            {name: 'Chrome PDF Plugin', filename: 'internal-pdf-viewer', description: 'Portable Document Format'},
            {name: 'Chrome PDF Viewer', filename: 'mhjfbmdgcfjbbpaeojofohoefgiehjai', description: ''},
            {name: 'Native Client', filename: 'internal-nacl-plugin', description: ''},
        ];
        plugins.length = 3;
        return plugins;
    },
    configurable: true,
});
"""

_PATCH_LANGUAGES = """
Object.defineProperty(navigator, 'languages', {
    get: () => ['en-US', 'en'],
    configurable: true,
});
"""

_PATCH_PERMISSIONS = """
if (typeof Notification !== 'undefined') {
    const origQuery = window.Notification && window.Notification.permission;
    Object.defineProperty(Notification, 'permission', {
        get: () => 'default',
        configurable: true,
    });
}
"""

_PATCH_CHROME_RUNTIME = """
if (!window.chrome) { window.chrome = {}; }
if (!window.chrome.runtime) {
    window.chrome.runtime = {
        connect: function() {},
        sendMessage: function() {},
    };
}
"""

_PATCH_WEBGL_VENDOR = """
(function() {
    const getParameter = WebGLRenderingContext.prototype.getParameter;
    WebGLRenderingContext.prototype.getParameter = function(parameter) {
        if (parameter === 37445) return 'Intel Inc.';
        if (parameter === 37446) return 'Intel Iris OpenGL Engine';
        return getParameter.call(this, parameter);
    };
})();
"""

ALL_PATCHES: List[str] = [
    _PATCH_WEBDRIVER,
    _PATCH_PLUGINS,
    _PATCH_LANGUAGES,
    _PATCH_PERMISSIONS,
    _PATCH_CHROME_RUNTIME,
    _PATCH_WEBGL_VENDOR,
]
"""All stealth JavaScript patches in application order."""


def apply_stealth_patches(page) -> int:
    """Inject stealth patches into a BrowserPage.

    Uses ``Page.addScriptToEvaluateOnNewDocument`` so patches persist
    across navigations. Also evaluates each patch immediately in the
    current page context.

    Args:
        page: A :class:`~naturo.browser.BrowserPage` instance.

    Returns:
        Number of patches applied.
    """
    count = 0
    for patch_js in ALL_PATCHES:
        try:
            # Register for future navigations
            page._cdp.send(
                "Page.addScriptToEvaluateOnNewDocument",
                {"source": patch_js},
            )
            # Apply to current page immediately
            page._cdp.evaluate(patch_js)
            count += 1
        except Exception as exc:
            logger.warning("Failed to apply stealth patch: %s", exc)
    logger.info("Applied %d/%d stealth patches", count, len(ALL_PATCHES))
    return count
