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
    naturo browser stealth-check        # Verify patches are working
"""

from __future__ import annotations

import logging
from typing import Dict, List

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


# ── Stealth verification ────────────────────────────────────────────────────

_CHECK_JS = """
(function() {
    var results = {};

    // 1. navigator.webdriver should be undefined (not true)
    results.webdriver = (navigator.webdriver === undefined || navigator.webdriver === false);

    // 2. navigator.plugins should have entries
    results.plugins = (navigator.plugins && navigator.plugins.length > 0);

    // 3. navigator.languages should be populated
    results.languages = (navigator.languages && navigator.languages.length > 0);

    // 4. chrome.runtime should exist
    results.chrome_runtime = !!(window.chrome && window.chrome.runtime);

    // 5. WebGL vendor should not be empty/default
    try {
        var canvas = document.createElement('canvas');
        var gl = canvas.getContext('webgl');
        if (gl) {
            var debugInfo = gl.getExtension('WEBGL_debug_renderer_info');
            if (debugInfo) {
                var vendor = gl.getParameter(debugInfo.UNMASKED_VENDOR_WEBGL);
                results.webgl_vendor = (vendor && vendor.length > 0);
            } else {
                results.webgl_vendor = true;  // No debug info = not detectable
            }
        } else {
            results.webgl_vendor = true;  // No WebGL = not detectable
        }
    } catch(e) {
        results.webgl_vendor = true;  // Error = not detectable
    }

    // 6. Notification.permission should not expose automation
    try {
        results.permissions = (typeof Notification === 'undefined'
                               || Notification.permission !== 'denied');
    } catch(e) {
        results.permissions = true;
    }

    return results;
})()
"""


def check_stealth(page) -> Dict[str, bool]:
    """Run stealth verification checks against a BrowserPage.

    Evaluates JavaScript checks for the 6 detection vectors that
    :func:`apply_stealth_patches` addresses. Each check returns True
    if the browser appears non-automated for that vector.

    Args:
        page: A :class:`~naturo.browser.BrowserPage` instance.

    Returns:
        Dict mapping check name to pass/fail boolean.  Keys:
        ``webdriver``, ``plugins``, ``languages``, ``chrome_runtime``,
        ``webgl_vendor``, ``permissions``.
    """
    result = page._cdp.evaluate(_CHECK_JS)
    if not isinstance(result, dict):
        raise RuntimeError(f"Stealth check returned unexpected type: {type(result)}")
    return result
