"""``naturo browser`` CLI subcommands, split from the monolithic ``browser_cmd.py``.

Each module attaches its commands to the shared ``browser`` Click group defined in
``naturo.cli.browser_cmd`` and uses that module's canonical ``_get_page`` helper:

- ``navigation`` — navigate, url, title, scroll, eval, close, tabs, tab
- ``elements`` — find, click, type, select, text, attr, html, hover
- ``frames`` — frames, frame-eval, frame-find
- ``waits`` — wait, wait-navigation, wait-url, wait-function, wait-network-idle
- ``network`` — requests, intercept
- ``visual`` — screenshot
- ``stealth`` — stealth, stealth-flags, stealth-check
- ``lifecycle`` — launch, profiles, download
- ``captcha`` — captcha-detect, captcha-solve
"""
