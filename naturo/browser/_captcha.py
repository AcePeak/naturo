"""Captcha detection and solving architecture.

Provides a pluggable captcha handling system with detection via JavaScript
and two built-in solver strategies:

- :class:`ManualSolver` — polls for a user-supplied solution.
- :class:`TokenInjectionSolver` — injects a pre-obtained token from an
  external solving service (e.g. 2Captcha, Anti-Captcha).

Usage::

    from naturo.browser import BrowserPage
    from naturo.browser._captcha import CaptchaManager, ManualSolver

    page = BrowserPage(port=9222)
    manager = CaptchaManager(page)
    captchas = manager.detect()
    for c in captchas:
        print(c["type"], c["sitekey"])

    # Solve with a token from an external service
    from naturo.browser._captcha import TokenInjectionSolver
    solver = TokenInjectionSolver(token="03AGdBq24...")
    result = manager.solve(solver=solver)
"""

from __future__ import annotations

import abc
import logging
import time
from typing import Any, Dict, List, Optional

logger = logging.getLogger(__name__)


# ── Detection JavaScript ─────────────────────────────────────────────────────

_DETECT_CAPTCHA_JS = r"""
(() => {
    const results = [];

    // reCAPTCHA v2 (checkbox or invisible)
    const recaptchaV2 = document.querySelector('.g-recaptcha');
    if (recaptchaV2) {
        results.push({
            type: 'recaptcha-v2',
            sitekey: recaptchaV2.getAttribute('data-sitekey') || '',
            element: 'div.g-recaptcha',
            visible: recaptchaV2.offsetParent !== null,
        });
    }

    // reCAPTCHA v2 via iframe
    const recaptchaIframes = document.querySelectorAll(
        'iframe[src*="recaptcha"], iframe[src*="google.com/recaptcha"]'
    );
    if (recaptchaIframes.length > 0 && !recaptchaV2) {
        const src = recaptchaIframes[0].src || '';
        const keyMatch = src.match(/[?&]k=([^&]+)/);
        results.push({
            type: 'recaptcha-v2',
            sitekey: keyMatch ? keyMatch[1] : '',
            element: 'iframe[src*="recaptcha"]',
            visible: true,
        });
    }

    // reCAPTCHA v3 (invisible, loaded via script)
    if (typeof grecaptcha !== 'undefined' && !recaptchaV2 && recaptchaIframes.length === 0) {
        // v3 is script-only, try to find sitekey from the script tag
        const scripts = document.querySelectorAll('script[src*="recaptcha"]');
        let sitekey = '';
        for (const s of scripts) {
            const m = s.src.match(/render=([^&]+)/);
            if (m) { sitekey = m[1]; break; }
        }
        results.push({
            type: 'recaptcha-v3',
            sitekey: sitekey,
            element: 'script[src*="recaptcha"]',
            visible: false,
        });
    }

    // hCaptcha
    const hcaptcha = document.querySelector('.h-captcha');
    if (hcaptcha) {
        results.push({
            type: 'hcaptcha',
            sitekey: hcaptcha.getAttribute('data-sitekey') || '',
            element: 'div.h-captcha',
            visible: hcaptcha.offsetParent !== null,
        });
    }

    // hCaptcha via iframe
    const hcaptchaIframes = document.querySelectorAll(
        'iframe[src*="hcaptcha.com"]'
    );
    if (hcaptchaIframes.length > 0 && !hcaptcha) {
        results.push({
            type: 'hcaptcha',
            sitekey: '',
            element: 'iframe[src*="hcaptcha.com"]',
            visible: true,
        });
    }

    // Cloudflare Turnstile
    const turnstile = document.querySelector('.cf-turnstile');
    if (turnstile) {
        results.push({
            type: 'turnstile',
            sitekey: turnstile.getAttribute('data-sitekey') || '',
            element: 'div.cf-turnstile',
            visible: turnstile.offsetParent !== null,
        });
    }

    // Turnstile via iframe
    const turnstileIframes = document.querySelectorAll(
        'iframe[src*="challenges.cloudflare.com"]'
    );
    if (turnstileIframes.length > 0 && !turnstile) {
        results.push({
            type: 'turnstile',
            sitekey: '',
            element: 'iframe[src*="challenges.cloudflare.com"]',
            visible: true,
        });
    }

    // Generic captcha iframes (fallback)
    if (results.length === 0) {
        const captchaIframes = document.querySelectorAll(
            'iframe[src*="captcha"], iframe[title*="captcha" i]'
        );
        for (const iframe of captchaIframes) {
            results.push({
                type: 'generic-iframe',
                sitekey: '',
                element: `iframe[src="${iframe.src}"]`,
                visible: iframe.offsetParent !== null,
            });
        }
    }

    return results;
})()
"""


# ── Solver ABC ────────────────────────────────────────────────────────────────


class CaptchaSolver(abc.ABC):
    """Abstract base class for captcha solvers.

    Subclasses must implement :meth:`solve` which returns a solution token
    string (the value to inject into the response textarea).
    """

    @abc.abstractmethod
    def solve(self, captcha_info: Dict[str, Any], page: Any) -> str:
        """Solve a captcha and return the response token.

        Args:
            captcha_info: Detection result dict with keys ``type``,
                ``sitekey``, ``element``, ``visible``.
            page: The :class:`BrowserPage` instance for JS evaluation.

        Returns:
            The captcha response token string.

        Raises:
            CaptchaError: If the captcha cannot be solved.
        """


class CaptchaError(Exception):
    """Raised when captcha detection or solving fails."""


# ── Built-in Solvers ──────────────────────────────────────────────────────────


class ManualSolver(CaptchaSolver):
    """Solver that polls for a user-supplied solution.

    The user must solve the captcha manually (e.g. in a visible browser
    window) and the solver polls the response textarea until it is filled
    or the timeout expires.

    Args:
        timeout: Maximum seconds to wait for a manual solution.
        poll_interval: Seconds between polls.
    """

    def __init__(self, timeout: float = 120.0, poll_interval: float = 2.0):
        self.timeout = timeout
        self.poll_interval = poll_interval

    def solve(self, captcha_info: Dict[str, Any], page: Any) -> str:
        """Poll the captcha response textarea until filled or timeout.

        Args:
            captcha_info: Detection result dict.
            page: BrowserPage instance.

        Returns:
            The response token string.

        Raises:
            CaptchaError: If timeout expires without a solution.
        """
        captcha_type = captcha_info.get("type", "")

        # Build the JS expression to check for a response
        check_js = _response_check_js(captcha_type)

        deadline = time.monotonic() + self.timeout
        while time.monotonic() < deadline:
            result = page.evaluate(check_js)
            if result and isinstance(result, str) and len(result) > 10:
                logger.info("Manual captcha solution detected (%d chars)", len(result))
                return result
            time.sleep(self.poll_interval)

        raise CaptchaError(
            f"Timeout after {self.timeout}s waiting for manual captcha solution"
        )


class TokenInjectionSolver(CaptchaSolver):
    """Solver that injects a pre-obtained token.

    Use this when you have already obtained a captcha solution token from
    an external service (e.g. 2Captcha, Anti-Captcha, CapMonster).

    Args:
        token: The pre-obtained captcha response token.
    """

    def __init__(self, token: str):
        if not token:
            raise ValueError("Token must not be empty")
        self.token = token

    def solve(self, captcha_info: Dict[str, Any], page: Any) -> str:
        """Inject the token into the captcha response textarea.

        Args:
            captcha_info: Detection result dict.
            page: BrowserPage instance.

        Returns:
            The injected token string.
        """
        captcha_type = captcha_info.get("type", "")
        inject_js = _inject_token_js(captcha_type, self.token)
        page.evaluate(inject_js)
        logger.info("Injected captcha token for %s (%d chars)", captcha_type, len(self.token))
        return self.token


# ── CaptchaManager ────────────────────────────────────────────────────────────


class CaptchaManager:
    """Detect and solve captchas on a browser page.

    Args:
        page: The :class:`BrowserPage` instance to operate on.
    """

    def __init__(self, page: Any):
        self._page = page

    def detect(self) -> List[Dict[str, Any]]:
        """Detect captchas on the current page.

        Returns:
            List of captcha info dicts, each with keys ``type``,
            ``sitekey``, ``element``, ``visible``. Empty list if
            no captchas are found.
        """
        try:
            result = self._page.evaluate(_DETECT_CAPTCHA_JS)
        except Exception as exc:
            logger.warning("Captcha detection failed: %s", exc)
            return []

        if not isinstance(result, list):
            return []
        return result

    def solve(
        self,
        solver: CaptchaSolver,
        captcha_info: Optional[Dict[str, Any]] = None,
    ) -> str:
        """Solve a captcha using the given solver.

        If *captcha_info* is not provided, auto-detects the first captcha
        on the page.

        Args:
            solver: The solver strategy to use.
            captcha_info: Specific captcha to solve (from :meth:`detect`).

        Returns:
            The captcha response token string.

        Raises:
            CaptchaError: If no captcha is found or solving fails.
        """
        if captcha_info is None:
            detected = self.detect()
            if not detected:
                raise CaptchaError("No captcha detected on the page")
            captcha_info = detected[0]

        logger.info(
            "Solving %s captcha (sitekey=%s)",
            captcha_info.get("type"),
            captcha_info.get("sitekey", "")[:20],
        )
        return solver.solve(captcha_info, self._page)


# ── JS helpers ────────────────────────────────────────────────────────────────


def _response_check_js(captcha_type: str) -> str:
    """Return JS to check if a captcha response token is available.

    Args:
        captcha_type: The captcha type string from detection.

    Returns:
        JavaScript expression that returns the token string or empty string.
    """
    if captcha_type.startswith("recaptcha"):
        return (
            "(typeof grecaptcha !== 'undefined' && "
            "grecaptcha.getResponse && grecaptcha.getResponse()) || "
            "document.querySelector('#g-recaptcha-response')?.value || ''"
        )
    if captcha_type == "hcaptcha":
        return (
            "(typeof hcaptcha !== 'undefined' && "
            "hcaptcha.getResponse && hcaptcha.getResponse()) || "
            "document.querySelector('[name=\"h-captcha-response\"]')?.value || ''"
        )
    if captcha_type == "turnstile":
        return (
            "(typeof turnstile !== 'undefined' && "
            "turnstile.getResponse && turnstile.getResponse()) || "
            "document.querySelector('[name=\"cf-turnstile-response\"]')?.value || ''"
        )
    # Generic fallback
    return (
        "document.querySelector('textarea[name*=\"captcha-response\"]')?.value || ''"
    )


def _inject_token_js(captcha_type: str, token: str) -> str:
    """Return JS to inject a token into the captcha response field.

    Args:
        captcha_type: The captcha type string from detection.
        token: The token to inject.

    Returns:
        JavaScript expression that injects the token.
    """
    # Escape token for JS string literal
    safe_token = token.replace("\\", "\\\\").replace("'", "\\'").replace("\n", "\\n")

    if captcha_type.startswith("recaptcha"):
        return (
            f"(() => {{"
            f"  const ta = document.querySelector('#g-recaptcha-response');"
            f"  if (ta) {{ ta.style.display = ''; ta.value = '{safe_token}'; }}"
            f"  if (typeof grecaptcha !== 'undefined' && grecaptcha.getResponse) {{"
            f"    // Trigger callback if available"
            f"    const cb = document.querySelector('.g-recaptcha')?.getAttribute('data-callback');"
            f"    if (cb && typeof window[cb] === 'function') window[cb]('{safe_token}');"
            f"  }}"
            f"}})()"
        )
    if captcha_type == "hcaptcha":
        return (
            f"(() => {{"
            f"  const ta = document.querySelector('[name=\"h-captcha-response\"]');"
            f"  if (ta) {{ ta.value = '{safe_token}'; }}"
            f"  if (typeof hcaptcha !== 'undefined' && hcaptcha.getResponse) {{"
            f"    const cb = document.querySelector('.h-captcha')?.getAttribute('data-callback');"
            f"    if (cb && typeof window[cb] === 'function') window[cb]('{safe_token}');"
            f"  }}"
            f"}})()"
        )
    if captcha_type == "turnstile":
        return (
            f"(() => {{"
            f"  const ta = document.querySelector('[name=\"cf-turnstile-response\"]');"
            f"  if (ta) {{ ta.value = '{safe_token}'; }}"
            f"  const cb = document.querySelector('.cf-turnstile')?.getAttribute('data-callback');"
            f"  if (cb && typeof window[cb] === 'function') window[cb]('{safe_token}');"
            f"}})()"
        )
    # Generic fallback
    return (
        f"(() => {{"
        f"  const ta = document.querySelector('textarea[name*=\"captcha-response\"]');"
        f"  if (ta) ta.value = '{safe_token}';"
        f"}})()"
    )
