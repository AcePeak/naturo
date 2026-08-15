"""Universal, self-maintaining ``-j`` success-envelope guard (issue #1142).

Why this file exists
--------------------
For years QA found the *same* defect one subcommand at a time: a ``-j``/``--json``
**success** response that omitted the top-level ``success`` key every other command
carries (#865 ``see``, #1054 ``get``/``set``, #977/#1141 ``visual compare``/``diff``,
#876 ``selector``/``record list`` …). Each was filed and fixed individually, and a
sibling in the very same file surfaced the next cycle.

``tests/test_json_envelope_contract.py`` already guards the ``@collection_read``
list-style commands. This module is the *universal* companion demanded by #1142: it
introspects the **entire** live Click command tree, enumerates **every** subcommand
that can emit ``-j`` output, and forces each into exactly one of two buckets:

* **DRIVEN** — the command's success path is invoked hermetically (empty on-disk
  stores, a mocked browser page, or pure computation — no DLL, desktop, or network)
  and the emitted JSON is asserted to carry a top-level *boolean* ``success``.
* **REQUIRES_LIVE_ENV** — an explicit, reviewed allow-list of commands whose success
  path genuinely cannot run in CI (needs the native ``naturo_core.dll`` + a live
  desktop window, a live CDP browser, Excel COM, a subprocess/network action, or
  pre-seeded mutable state). Every entry carries a reason. These commands were still
  **statically audited** for the envelope during the #1142 sweep; they are simply not
  *runtime*-driven here.

The self-maintaining hinge is :func:`test_every_json_command_is_classified`: a NEW
``-j`` subcommand that is in *neither* bucket fails CI on day one. The author must
either wire a hermetic driver (which then asserts the envelope) or consciously
allow-list it with a reason — the exclusion is visible and bounded, never silent.
"""

from __future__ import annotations

import json
import shutil
import tempfile
from pathlib import Path
from typing import Callable, Iterator, Optional
from unittest.mock import MagicMock, patch

import click
import pytest
from click.testing import CliRunner

from naturo.cli import main


# ── Tree walk ─────────────────────────────────────────────────────────────────

def _walk(group: click.Group, prefix: tuple[str, ...] = ()) -> Iterator[tuple[tuple[str, ...], click.Command]]:
    """Yield ``(path, command)`` for every leaf command under ``group``."""
    for name, command in group.commands.items():
        path = prefix + (name,)
        if isinstance(command, click.Group):
            yield from _walk(command, path)
        else:
            yield path, command


def _emits_json(command: click.Command) -> bool:
    """True when the command declares a ``-j``/``--json`` (``json_output``) flag."""
    return any(getattr(p, "name", None) == "json_output" for p in command.params)


def _all_json_commands() -> dict[tuple[str, ...], click.Command]:
    """Every leaf command in the live tree that can emit ``-j`` output."""
    return {path: cmd for path, cmd in _walk(main) if _emits_json(cmd)}


# ── DRIVEN: commands whose success path we invoke hermetically ────────────────
#
# Each driver returns the parsed JSON payload of the command's ``-j`` output. The
# shared assertion below then requires a top-level boolean ``success``.

_STORE_ROOTS: dict[tuple[str, ...], tuple[str, str]] = {
    # path                      (module, attribute holding the on-disk store root)
    ("selector", "list"): ("naturo.cli.selector_cmd", "SELECTORS_DIR"),
    ("visual", "list"): ("naturo.visual", "BASELINES_DIR"),
    ("record", "list"): ("naturo.recording", "RECORDINGS_DIR"),
}

# Pure-computation / read-only commands whose non-exception path is their success
# path and needs no isolation to run deterministically in CI. ``doctor``/``info``
# legitimately emit ``success: false`` on a host that fails a required check — the
# contract is the *presence of a top-level boolean* ``success``, which they satisfy.
_COMPUTE_READS: tuple[tuple[str, ...], ...] = (
    ("config", "show"),
    ("snapshot", "list"),
    ("snapshot", "sessions"),
    ("list", "screens"),
    ("mcp", "tools"),
    ("doctor",),
    ("info",),
    ("browser", "stealth-flags"),
    ("browser", "profiles"),
)

# Script runner (#42): driven with a trivial inline program so the ``-j`` success
# envelope is asserted hermetically — it spawns a subprocess interpreter (the
# resolver's system Python), needs no desktop or native DLL. Maps path -> args.
_SCRIPT_DRIVEN: dict[tuple[str, ...], list[str]] = {
    ("run",): ["-c", "pass"],
}

# Browser commands are driven against a mocked CDP page (no Chrome needed), exactly
# as ``tests/test_browser_cmd.py`` does. Maps path -> extra positional args.
_BROWSER_DRIVEN: dict[tuple[str, ...], list[str]] = {
    ("browser", "navigate"): ["https://example.com"],
    ("browser", "url"): [],
    ("browser", "title"): [],
    ("browser", "eval"): ["1+1"],
    ("browser", "tabs"): [],
    ("browser", "tab"): ["tab-1"],
    ("browser", "scroll"): ["--to-top"],
    ("browser", "find"): ["#x"],
    ("browser", "text"): ["#x"],
    ("browser", "attr"): ["#x", "href"],
    ("browser", "html"): ["#x"],
    ("browser", "click"): ["#x"],
    ("browser", "type"): ["#x", "hello"],
    ("browser", "select"): ["#x", "v"],
    ("browser", "hover"): ["#x"],
    ("browser", "frames"): [],
    ("browser", "frame-eval"): ["f", "1+1"],
    ("browser", "frame-find"): ["f", "#x"],
    ("browser", "wait"): ["#x"],
    ("browser", "wait-navigation"): [],
    ("browser", "wait-url"): ["/x"],
    ("browser", "wait-function"): ["ready"],
    ("browser", "wait-network-idle"): [],
    ("browser", "screenshot"): [],
    ("browser", "close"): [],
}


def _make_mock_page() -> MagicMock:
    """A MagicMock BrowserPage with JSON-serialisable returns for every accessor."""
    page = MagicMock()
    page.url = "https://example.com"
    page.title = "Example Domain"
    page.evaluate.return_value = "result"
    page.tabs.return_value = [{"id": "tab-1", "title": "T", "url": "https://one.com"}]
    page.frames.return_value = [
        {"id": "main", "name": "", "url": "https://example.com", "parentId": "", "depth": 0},
    ]
    page.wait_for_navigation.return_value = "https://example.com/next"
    page.wait_for_url.return_value = "https://example.com/x"
    page.wait_for_function.return_value = True
    page.screenshot.return_value = "screenshot.png"

    element = MagicMock()
    element.tag_name = "div"
    element.text = "hello"
    element.value = "v"
    element.attr.return_value = "https://example.com"
    element.inner_html = "<span>inner</span>"
    element.outer_html = "<div><span>outer</span></div>"
    page.find.return_value = element
    page.find_all.return_value = [element]

    frame = MagicMock()
    frame.evaluate.return_value = "frame-result"
    frame.find.return_value = element
    frame.find_all.return_value = [element]
    page.frame.return_value = frame
    return page


def _drive_store_read(path: tuple[str, ...], monkeypatch: pytest.MonkeyPatch,
                      tmp: Path) -> dict:
    module_name, attribute = _STORE_ROOTS[path]
    module = __import__(module_name, fromlist=[attribute])
    monkeypatch.setattr(module, attribute, tmp / "store")
    result = CliRunner().invoke(main, [*path, "-j"])
    assert result.exit_code == 0, result.output
    return json.loads(result.output)


def _drive_compute(path: tuple[str, ...]) -> dict:
    result = CliRunner().invoke(main, [*path, "-j"])
    # doctor/info may exit 1 on an unhealthy host; both still emit the envelope.
    assert result.exit_code in (0, 1), result.output
    return json.loads(result.output)


def _drive_browser(path: tuple[str, ...]) -> dict:
    args = [*path, *_BROWSER_DRIVEN[path], "-j"]
    with patch("naturo.cli.browser_cmd._get_page", return_value=_make_mock_page()):
        result = CliRunner().invoke(main, args, catch_exceptions=False)
    assert result.exit_code == 0, result.output
    return json.loads(result.output)


def _drive_script(path: tuple[str, ...]) -> dict:
    args = [*path, *_SCRIPT_DRIVEN[path], "-j"]
    result = CliRunner().invoke(main, args)
    assert result.exit_code == 0, result.output
    return json.loads(result.output)


# The full set of runtime-driven commands (used by the classification check).
_DRIVEN: frozenset[tuple[str, ...]] = frozenset(
    set(_STORE_ROOTS)
    | set(_COMPUTE_READS)
    | set(_BROWSER_DRIVEN)
    | set(_SCRIPT_DRIVEN)
)


# ── REQUIRES_LIVE_ENV: explicit, reviewed exclusions ──────────────────────────
#
# Each command's success path needs a real resource CI does not have. All were
# statically audited for the top-level ``success`` envelope during the #1142 sweep;
# they are excluded from *runtime* driving only, with the reason recorded here. To
# un-exclude one, move it into a DRIVEN bucket above (and it will then be asserted).

_REASON_DESKTOP = "needs naturo_core.dll + a live desktop window/UIA backend"
_REASON_BROWSER = "needs a live CDP browser connection"
_REASON_EXCEL = "needs Excel via COM automation"
_REASON_SIDE_EFFECT = "mutating / subprocess / network / interactive action, or needs pre-seeded state or a live target arg"
_REASON_HOOK = "needs naturo_core.dll with the MinHook Win32 hook engine (in-process API hooking)"

REQUIRES_LIVE_ENV: dict[tuple[str, ...], str] = {
    # Desktop automation — native DLL + a real window.
    ("capture",): _REASON_DESKTOP,
    ("see",): _REASON_DESKTOP,
    ("find",): _REASON_DESKTOP,
    ("get",): _REASON_DESKTOP,
    ("set",): _REASON_DESKTOP,
    ("click",): _REASON_DESKTOP,
    ("type",): _REASON_DESKTOP,
    ("press",): _REASON_DESKTOP,
    ("hotkey",): _REASON_DESKTOP,
    ("scroll",): _REASON_DESKTOP,
    ("drag",): _REASON_DESKTOP,
    ("move",): _REASON_DESKTOP,
    ("highlight",): _REASON_DESKTOP,
    ("menu-inspect",): _REASON_DESKTOP,
    ("wait",): _REASON_DESKTOP,
    ("diff",): _REASON_DESKTOP,
    ("list", "windows"): _REASON_DESKTOP,
    ("list", "apps"): _REASON_DESKTOP,
    ("list", "permissions"): _REASON_DESKTOP,
    ("app", "close"): _REASON_DESKTOP,
    ("app", "find"): _REASON_DESKTOP,
    ("app", "focus"): _REASON_DESKTOP,
    ("app", "hide"): _REASON_DESKTOP,
    ("app", "inspect"): _REASON_DESKTOP,
    ("app", "launch"): _REASON_DESKTOP,
    ("app", "list"): _REASON_DESKTOP,
    ("app", "maximize"): _REASON_DESKTOP,
    ("app", "minimize"): _REASON_DESKTOP,
    ("app", "move"): _REASON_DESKTOP,
    ("app", "quit"): _REASON_DESKTOP,
    ("app", "relaunch"): _REASON_DESKTOP,
    ("app", "restore"): _REASON_DESKTOP,
    ("app", "switch"): _REASON_DESKTOP,
    ("app", "unhide"): _REASON_DESKTOP,
    ("app", "windows"): _REASON_DESKTOP,
    ("window", "close"): _REASON_DESKTOP,
    ("window", "focus"): _REASON_DESKTOP,
    ("window", "list"): _REASON_DESKTOP,
    ("window", "maximize"): _REASON_DESKTOP,
    ("window", "minimize"): _REASON_DESKTOP,
    ("window", "move"): _REASON_DESKTOP,
    ("window", "resize"): _REASON_DESKTOP,
    ("window", "restore"): _REASON_DESKTOP,
    ("window", "set-bounds"): _REASON_DESKTOP,
    ("clipboard", "clear"): _REASON_DESKTOP,
    ("clipboard", "get"): _REASON_DESKTOP,
    ("clipboard", "info"): _REASON_DESKTOP,
    ("clipboard", "set"): _REASON_DESKTOP,
    ("dialog", "accept"): _REASON_DESKTOP,
    ("dialog", "click-button"): _REASON_DESKTOP,
    ("dialog", "detect"): _REASON_DESKTOP,
    ("dialog", "dismiss"): _REASON_DESKTOP,
    ("dialog", "type"): _REASON_DESKTOP,
    ("taskbar", "click"): _REASON_DESKTOP,
    ("taskbar", "list"): _REASON_DESKTOP,
    ("tray", "click"): _REASON_DESKTOP,
    ("tray", "list"): _REASON_DESKTOP,
    ("desktop", "close"): _REASON_DESKTOP,
    ("desktop", "create"): _REASON_DESKTOP,
    ("desktop", "list"): _REASON_DESKTOP,
    ("desktop", "move-window"): _REASON_DESKTOP,
    ("desktop", "switch"): _REASON_DESKTOP,
    # Live CDP browser.
    ("browser", "launch"): _REASON_BROWSER,
    ("browser", "captcha-detect"): _REASON_BROWSER,
    ("browser", "captcha-solve"): _REASON_BROWSER,
    ("browser", "download"): _REASON_BROWSER,
    ("browser", "intercept"): _REASON_BROWSER,
    ("browser", "requests"): _REASON_BROWSER,
    ("browser", "stealth"): _REASON_BROWSER,
    ("browser", "stealth-check"): _REASON_BROWSER,
    # Excel COM.
    ("excel", "create-chart"): _REASON_EXCEL,
    ("excel", "info"): _REASON_EXCEL,
    ("excel", "list-sheets"): _REASON_EXCEL,
    ("excel", "open"): _REASON_EXCEL,
    ("excel", "read"): _REASON_EXCEL,
    ("excel", "run-macro"): _REASON_EXCEL,
    ("excel", "write"): _REASON_EXCEL,
    # Win32 API hooking (#40) — success path drives the native hook engine.
    ("hook", "install"): _REASON_HOOK,
    ("hook", "list"): _REASON_HOOK,
    ("hook", "monitor"): _REASON_HOOK,
    ("hook", "remove"): _REASON_HOOK,
    # Side-effecting / stateful / arg-required success paths.
    ("config", "clear"): _REASON_SIDE_EFFECT,
    ("config", "setup", "anthropic"): _REASON_SIDE_EFFECT,
    ("mcp", "install"): _REASON_SIDE_EFFECT,
    ("mcp", "start"): _REASON_SIDE_EFFECT,
    ("selector", "save"): _REASON_SIDE_EFFECT,
    ("selector", "load"): _REASON_SIDE_EFFECT,
    ("selector", "delete"): _REASON_SIDE_EFFECT,
    ("selector", "clear"): _REASON_SIDE_EFFECT,
    ("selector", "import"): _REASON_SIDE_EFFECT,
    ("selector", "export"): _REASON_SIDE_EFFECT,
    ("selector", "show"): _REASON_SIDE_EFFECT,
    ("selector", "test"): _REASON_DESKTOP,
    ("record", "start"): _REASON_SIDE_EFFECT,
    ("record", "stop"): _REASON_SIDE_EFFECT,
    ("record", "play"): _REASON_DESKTOP,
    ("record", "delete"): _REASON_SIDE_EFFECT,
    ("record", "show"): _REASON_SIDE_EFFECT,
    ("record", "export"): _REASON_SIDE_EFFECT,
    ("snapshot", "clean"): _REASON_SIDE_EFFECT,
    ("visual", "baseline"): _REASON_SIDE_EFFECT,
    ("visual", "compare"): _REASON_SIDE_EFFECT,
    ("visual", "diff"): _REASON_SIDE_EFFECT,
    ("visual", "delete"): _REASON_SIDE_EFFECT,
    ("visual", "report"): _REASON_SIDE_EFFECT,
    ("visual", "suite"): _REASON_SIDE_EFFECT,
    ("visual", "update"): _REASON_SIDE_EFFECT,
    ("visual", "update-all"): _REASON_SIDE_EFFECT,
}


# ── Fixtures ──────────────────────────────────────────────────────────────────

@pytest.fixture()
def store_tmp() -> Iterator[Path]:
    """A fresh, empty temp directory for a command's on-disk store.

    Uses :func:`tempfile.mkdtemp` (not ``tmp_path``) for the same reason as the
    sibling contract test: the shared pytest temp base is contended on the agent
    host and its numbered-dir scan intermittently raises ``WinError 5``.
    """
    path = Path(tempfile.mkdtemp(prefix="naturo-envelope-sweep-"))
    try:
        yield path
    finally:
        shutil.rmtree(path, ignore_errors=True)


# ── 1. The self-maintaining classification hinge ──────────────────────────────

def test_every_json_command_is_classified() -> None:
    """Every ``-j`` subcommand is either DRIVEN or explicitly allow-listed.

    This is what ends the per-subcommand drip: a newly added ``-j`` command that
    is in neither bucket fails here, forcing its author to wire a hermetic driver
    (which then asserts the envelope) or record an explicit exclusion reason.
    """
    all_json = set(_all_json_commands())
    classified = _DRIVEN | set(REQUIRES_LIVE_ENV)

    unclassified = all_json - classified
    assert not unclassified, (
        "New -j subcommand(s) not covered by the envelope sweep: "
        + ", ".join(" ".join(p) for p in sorted(unclassified))
        + ". Add a hermetic driver in _DRIVEN (so the top-level `success` envelope "
        "is asserted) or an explicit REQUIRES_LIVE_ENV entry with a reason."
    )

    # Guard against rot in the constants themselves: no phantom paths, no overlap.
    phantom = classified - all_json
    assert not phantom, (
        "Envelope-sweep constants reference commands that no longer emit -j: "
        + ", ".join(" ".join(p) for p in sorted(phantom))
    )
    overlap = _DRIVEN & set(REQUIRES_LIVE_ENV)
    assert not overlap, (
        "Commands both driven and allow-listed: "
        + ", ".join(" ".join(p) for p in sorted(overlap))
    )


def test_allow_list_entries_have_reasons() -> None:
    """Every exclusion is a conscious, documented choice."""
    for path, reason in REQUIRES_LIVE_ENV.items():
        assert isinstance(reason, str) and reason.strip(), (
            f"{' '.join(path)} is allow-listed without a reason."
        )


# ── 2. The actual envelope assertion for every DRIVEN command ──────────────────

def _assert_envelope(path: tuple[str, ...], payload: object) -> None:
    joined = " ".join(path)
    assert isinstance(payload, dict), (
        f"{joined} -j emitted a non-object ({type(payload).__name__}); the success "
        f"envelope must be a JSON object with a top-level `success` key."
    )
    assert "success" in payload, (
        f"{joined} -j success output is missing the top-level `success` key "
        f"(keys: {sorted(payload)}). Route it through success_envelope(...) or lead "
        f"with {{'success': True, ...}}."
    )
    assert isinstance(payload["success"], bool), (
        f"{joined} -j top-level `success` must be a JSON boolean, got "
        f"{type(payload['success']).__name__}."
    )


@pytest.mark.parametrize(
    "path", sorted(_STORE_ROOTS), ids=lambda p: " ".join(p),
)
def test_store_read_success_envelope(
    path: tuple[str, ...], store_tmp: Path, monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Store-backed reads emit the envelope against an empty, isolated store."""
    payload = _drive_store_read(path, monkeypatch, store_tmp)
    _assert_envelope(path, payload)
    assert payload["success"] is True


@pytest.mark.parametrize(
    "path", sorted(_COMPUTE_READS), ids=lambda p: " ".join(p),
)
def test_compute_read_success_envelope(path: tuple[str, ...]) -> None:
    """Pure read/compute commands emit a top-level boolean ``success``."""
    payload = _drive_compute(path)
    _assert_envelope(path, payload)


@pytest.mark.parametrize(
    "path", sorted(_BROWSER_DRIVEN), ids=lambda p: " ".join(p),
)
def test_browser_success_envelope(path: tuple[str, ...]) -> None:
    """Browser commands emit the envelope when driven against a mocked page."""
    payload = _drive_browser(path)
    _assert_envelope(path, payload)
    assert payload["success"] is True


@pytest.mark.parametrize(
    "path", sorted(_SCRIPT_DRIVEN), ids=lambda p: " ".join(p),
)
def test_script_runner_success_envelope(path: tuple[str, ...]) -> None:
    """`naturo run -c "pass" -j` emits a top-level ``success: true`` envelope."""
    payload = _drive_script(path)
    _assert_envelope(path, payload)
    assert payload["success"] is True
