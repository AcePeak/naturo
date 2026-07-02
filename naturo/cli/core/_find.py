"""Find command — search for UI elements matching a query."""
from __future__ import annotations

from naturo.cli._jsonio import json_dumps
from typing import Any, NoReturn

import click

import naturo.cli.core._common as _common

# (#1144 / #809 §4) File extensions that mark a bare query as an image-template
# path for strategy auto-detection. Lower-cased; compared case-insensitively.
_IMAGE_QUERY_EXTENSIONS = frozenset(
    {".png", ".jpg", ".jpeg", ".bmp", ".gif", ".tif", ".tiff", ".webp"}
)


def _detect_query_strategy(query: str) -> str | None:
    """Infer the find strategy from a bare query's shape (#1144, #809 §4).

    The unified find engine is a *universal locator*: a positional (or
    ``-q/--query``) value should reach the right strategy without the caller
    spelling out ``--image``/``--selector``. This classifies only the
    *unambiguous* shapes from the #809 table; everything else falls through to
    the default UIA tree search so a normal name query is never hijacked.

    Args:
        query: The raw query string (positional arg or ``--query`` value).

    Returns:
        ``"selector"`` for a unified-selector path (an ``app://…`` URI or an
        ``@app/name`` saved-selector ref), ``"image"`` for a template-image file
        path (extension in :data:`_IMAGE_QUERY_EXTENSIONS`), or ``None`` for an
        ordinary text/role query.
    """
    import os

    q = query.strip()
    # Only ``app://`` URIs and ``@name`` refs auto-route to the selector engine
    # (per the #809 table). The ``//`` shorthand is deliberately excluded: it is
    # far likelier to be a literal text fragment than the ``app://``/``@`` forms,
    # so it stays a text query unless passed via the explicit --selector flag.
    if q.startswith("app://") or q.startswith("@"):
        return "selector"
    if os.path.splitext(q)[1].lower() in _IMAGE_QUERY_EXTENSIONS:
        return "image"
    return None


@click.command("find")
@click.argument("query", required=False, default=None)
@click.option("--query", "-q", "query_opt", default=None,
              help="Search query (alternative to positional arg; survives shell glob expansion)")
@click.option("--all", "find_all", is_flag=True,
              help="Find all elements (equivalent to query \"*\"). Safe from shell glob expansion.")
@click.option("--role", help="Filter by element role (e.g., Button, Edit)")
@click.option("--actionable", is_flag=True, help="Only show actionable elements")
@click.option("--depth", "-d", type=int, default=20, help="Maximum tree depth (default 20; use lower values for performance)")
@click.option("--limit", type=int, default=50, help="Maximum number of results")
@click.option("--ai", is_flag=True, help="Use AI vision to find element by natural language")
@click.option("--image", "image_template", type=click.Path(), default=None,
              help="Locate a template image (PNG/JPG) on the target window or screen "
                   "via normalized cross-correlation (no UIA tree needed)")
@click.option("--threshold", type=float, default=0.9, show_default=True,
              help="Minimum match score in [0.0, 1.0] for --image (higher is stricter)")
@click.option("--selector", default=None,
              help="Resolve a unified selector path to an element (the strategy "
                   "click/type use). "
                   'URI: app://notepad.exe/Button[@name="Save"]. '
                   'Short: //Edit[@name="Search"] (any app, descendant search). '
                   "Saved: @app/name. App names are flexible: chrome, chrome.exe, Chrome.")
@click.option("--ocr", is_flag=True,
              help="Find on-screen text by OCR (for Canvas/game/custom-drawn "
                   "controls UIA can't see). The positional QUERY is the text to "
                   "locate; returns bounding boxes. Requires 'pip install naturo[ocr]'.")
@click.option("--screenshot", type=click.Path(), default=None,
              help="Match against this existing screenshot instead of capturing "
                   "live (for --ai and --image modes). With --image the screenshot "
                   "is the search haystack and reported coordinates are "
                   "screenshot-relative; window-targeting flags do not apply.")
@click.option("--app", default=None, help="Target app window")
@click.option("--app-id", "app_id", default=None,
              help='Stable app/window ID from "naturo app list" output (e.g. a1)')
@click.option("--window", "window_title", default=None,
              help="Window title pattern (substring match)")
@click.option("--hwnd", default=None, type=int, help="Window handle (HWND)")
@click.option("--pid", default=None, type=int, help="Process ID")
@click.option("--json", "-j", "json_output", is_flag=True, help="JSON output")
@click.option(
    "--backend", "--method", "-b", "-m",
    type=click.Choice(["uia", "msaa", "ia2", "jab", "cdp", "win32", "win32hybrid", "auto", "hybrid"]),
    default="auto",
    help="Accessibility backend / interaction method: auto (default: tries all), uia, msaa (legacy apps), ia2 (Firefox/Thunderbird), jab (Java/Swing), cdp (Chrome/Electron web content), win32 (VB6/ActiveX), hybrid (per-node backend selection)",
)
@click.option("--provider", "ai_provider",
              type=click.Choice(["auto", "anthropic", "openai", "ollama"]),
              default="auto", help="AI provider for --ai mode (auto, anthropic, openai, ollama)")
@click.option("--model", "ai_model", default=None, envvar="NATURO_AI_MODEL",
              help="AI model name override (e.g. claude-sonnet-4-20250514, gpt-4o)")
@click.option("--api-key", "ai_api_key", default=None,
              help="AI provider API key (overrides env var)")
def find_cmd(query: str | None, query_opt: str | None, find_all: bool, role: str | None,
             actionable: bool, depth: int, limit: int, ai: bool,
             image_template: str | None, threshold: float, selector: str | None,
             ocr: bool, ai_provider: str, ai_model: str | None, ai_api_key: str | None,
             screenshot: str | None, app: str | None, app_id: str | None,
             window_title: str | None, hwnd: int | None, pid: int | None,
             json_output: bool, backend: str) -> None:
    """Search for UI elements matching a query.

    Supports fuzzy name matching, role filtering, and combined queries.
    Use --ai for natural language element finding powered by AI vision.
    Use --ocr to locate on-screen text the accessibility tree cannot see
    (Canvas/game/custom-drawn controls); requires 'pip install naturo[ocr]'.
    Use --backend msaa for legacy applications that lack UIA support.
    Use --backend ia2 for IA2-enabled apps (Firefox, Thunderbird, LibreOffice).

    \b
    Strategy auto-detection: a bare query routes itself by shape, so you can skip
    the explicit flag —
        app://… or @app/name    -> selector resolution (same as --selector)
        path ending .png/.jpg/… -> image template match (same as --image)
        anything else           -> UIA tree search
    Explicit --image/--selector/--ai always take precedence.

    \b
    Examples:
        naturo find "Save"                      # fuzzy name search
        naturo find "Button:Save"               # role + name
        naturo find "role:Edit"                  # by role only
        naturo find --all --actionable           # all actionable elements
        naturo find --all --role Button          # all buttons
        naturo find "the save button" --ai       # AI vision search
        naturo find "Save" --app "Notepad"              # search in specific app
        naturo find "search field" --ai --app "Chrome"  # AI + specific app
        naturo find "OK" --backend msaa          # MSAA for legacy apps
        naturo find submit.png                   # auto-detected image template match
        naturo find --image icon.png --app Notepad --all  # all matches in app
        naturo find 'app://notepad.exe/Edit'     # auto-detected selector resolution
        naturo find @notepad/save-btn            # auto-detected saved selector (@app/name)
        naturo find --selector '//Button[@name="Save"]'   # resolve a selector path
        naturo find --ocr "Start" --app game.exe          # OCR text on a window
        naturo find --ocr "Score" --screenshot shot.png   # OCR text in a saved image
    """
    # (#752) Auto-detect app ID pattern (a1, a2, ...) in --app flag
    from naturo.cli.options import maybe_promote_app_to_app_id
    app, app_id = maybe_promote_app_to_app_id(app, app_id)

    # (#593) Resolve --app-id to hwnd before any other logic.
    # An explicit --app-id takes precedence over a raw --hwnd value.
    if app_id is not None:
        from naturo.app_ids import get_app_id_map
        id_map = get_app_id_map()
        entry = id_map.resolve(app_id)
        if entry is None:
            msg = f'App ID "{app_id}" not found or expired. Run "naturo app list" to refresh.'
            if json_output:
                click.echo(_common._json_error_str("APP_ID_NOT_FOUND", msg))
            else:
                click.echo(f"Error: {msg}", err=True)
            raise SystemExit(1)
        hwnd = entry.handle

    # (#1173) Validate --limit up front, before any strategy dispatch and before
    # the platform/GUI gate. --limit feeds every find strategy — the tree/image
    # paths pass it as a counter-based ``max_results`` (a non-positive value
    # collapses the set to empty) and the selector path uses a literal ``[:limit]``
    # slice (a negative value slices from the end → a non-empty but silently-wrong
    # set). Both are silent-misleading-results, so reject ``--limit < 1`` here with
    # the same INVALID_INPUT envelope its siblings --depth/--threshold use. Placing
    # it before the GUI gate keeps the bad-input → error-code contract platform-
    # invariant (same code on headless CI as on a Windows desktop).
    if limit < 1:
        msg = f"--limit must be a positive integer, got {limit}"
        if json_output:
            click.echo(_common._json_error_str("INVALID_INPUT", msg))
        else:
            click.echo(f"Error: {msg}", err=True)
        raise SystemExit(1)

    # (#1144 / #809 §4) Strategy auto-detection — when the caller gives a bare
    # query and no explicit strategy flag, infer the locator strategy from the
    # query's shape so `naturo find button.png` and `naturo find app://…` reach
    # the image and selector engines without --image/--selector. Explicit
    # --image/--selector/--ai always win (we only run when none is set), and an
    # ordinary text/role query stays on the default tree-search path. The
    # detected query is moved into the matching strategy flag so the existing
    # dispatch (and its conflict checks) handle it unchanged.
    _auto_query = query if query is not None else query_opt
    if (selector is None and image_template is None and not ai and not ocr
            and not find_all and _auto_query is not None):
        detected = _detect_query_strategy(_auto_query)
        if detected == "selector":
            selector = _auto_query
            query = query_opt = None
        elif detected == "image":
            image_template = _auto_query
            query = query_opt = None

    # Selector resolution mode — resolve a saved/inline selector path to an
    # element (the third unified-find strategy, #1061 / #809).  Dispatched
    # before query resolution since --selector carries its own target path, not
    # a text query.
    if selector is not None:
        conflict = None
        if ai:
            conflict = "--selector and --ai are mutually exclusive; choose one find strategy."
        elif image_template is not None:
            conflict = "--selector and --image are mutually exclusive; choose one find strategy."
        elif ocr:
            conflict = "--selector and --ocr are mutually exclusive; choose one find strategy."
        elif query is not None or query_opt is not None:
            conflict = ("--selector takes no text query; it resolves a selector path, "
                        "not a named element.")
        if conflict is not None:
            if json_output:
                click.echo(_common._json_error_str("INVALID_INPUT", conflict))
            else:
                click.echo(f"Error: {conflict}", err=True)
            raise SystemExit(1)
        _find_with_selector(
            selector, find_all,
            app=app, window_title=window_title, hwnd=hwnd, pid=pid,
            depth=depth, method=backend,
            limit=limit, json_output=json_output,
        )
        return

    # Image template matching mode — locate a picture on the window/screen.
    # Dispatched before query resolution since --image needs no text query
    # (and reuses --all to mean "every occurrence").
    if image_template is not None:
        if ai:
            msg = "--image and --ai are mutually exclusive; choose one find strategy."
            if json_output:
                click.echo(_common._json_error_str("INVALID_INPUT", msg))
            else:
                click.echo(f"Error: {msg}", err=True)
            raise SystemExit(1)
        if ocr:
            msg = "--image and --ocr are mutually exclusive; choose one find strategy."
            if json_output:
                click.echo(_common._json_error_str("INVALID_INPUT", msg))
            else:
                click.echo(f"Error: {msg}", err=True)
            raise SystemExit(1)
        if query is not None or query_opt is not None:
            msg = ("--image takes no text query; it locates a template image, "
                   "not a named element.")
            if json_output:
                click.echo(_common._json_error_str("INVALID_INPUT", msg))
            else:
                click.echo(f"Error: {msg}", err=True)
            raise SystemExit(1)
        _find_with_image(
            image_template, threshold, find_all,
            app=app, window_title=window_title, hwnd=hwnd, pid=pid,
            screenshot=screenshot, limit=limit, json_output=json_output,
        )
        return

    # (#1193) Treat an empty / whitespace-only query the same as a missing one.
    # Left as-is, "" / "   " falls through to the search layer, which normalizes
    # it to the "*" wildcard and matches *every* element with success:true — the
    # silent-wrong class QA guards against (an unpopulated `naturo find "$VAR"`
    # would dump the whole tree as a "success"). Selector- and image-mode already
    # reject empty input (INVALID_SELECTOR / FILE_NOT_FOUND); this aligns the
    # default text path with them and with the argument-omitted path. Callers
    # that want every element opt in explicitly via --all (or narrow with
    # --role/--actionable, which keep the match-all intent below).
    if query is not None and not query.strip():
        query = None
    if query_opt is not None and not query_opt.strip():
        query_opt = None
    # OCR text-finding mode — recognise on-screen text and return the bounding
    # boxes of regions matching the query (#1060).  Dispatched before query
    # resolution because, like --image, it owns its own targeting and treats
    # --all as "every match" rather than a wildcard text query.
    if ocr:
        if ai:
            msg = "--ocr and --ai are mutually exclusive; choose one find strategy."
            if json_output:
                click.echo(_common._json_error_str("INVALID_INPUT", msg))
            else:
                click.echo(f"Error: {msg}", err=True)
            raise SystemExit(1)
        ocr_query = query if query is not None else query_opt
        if ocr_query is None or not ocr_query.strip():
            msg = ("--ocr needs the text to find. Provide it as the positional "
                   "QUERY or via --query/-q (e.g. naturo find --ocr \"Start\").")
            if json_output:
                click.echo(_common._json_error_str("INVALID_INPUT", msg))
            else:
                click.echo(f"Error: {msg}", err=True)
            raise SystemExit(1)
        _find_with_ocr(
            ocr_query, find_all,
            app=app, window_title=window_title, hwnd=hwnd, pid=pid,
            screenshot=screenshot, limit=limit, json_output=json_output,
        )
        return

    # Resolve query: --all flag → wildcard, --query option → override positional
    if find_all:
        query = "*"
    elif query_opt is not None:
        query = query_opt
    # else: query is the positional arg (may be None)

    if query is None:
        # When --actionable or --role is set, treat a missing or empty query as a
        # wildcard — the explicit filter already narrows the match-all intent.
        if actionable or role:
            query = "*"
        else:
            msg = ("Missing or empty argument 'QUERY'. Provide a non-empty query "
                   "as a positional arg or --query/-q option, or use --all to "
                   "match every element.")
            if json_output:
                click.echo(_common._json_error_str("INVALID_INPUT", msg))
            else:
                click.echo(f"Error: {msg}", err=True)
            raise SystemExit(1)

    # Auto-enable AI mode when --provider or --model is explicitly set (#287)
    if not ai and (ai_provider != "auto" or ai_model is not None or ai_api_key is not None):
        ai = True

    # AI vision mode — natural language element finding
    if ai:
        # AI vision operates on a screenshot, not the UIA tree, so window-handle
        # targeting does not apply.  Reject it explicitly rather than silently
        # ignoring the flags — use --app to scope the captured app instead.
        if window_title is not None or hwnd is not None or pid is not None:
            msg = ("--window/--hwnd/--pid are not supported with --ai "
                   "(vision mode operates on a screenshot); use --app to scope "
                   "the target application.")
            if json_output:
                click.echo(_common._json_error_str("INVALID_INPUT", msg))
            else:
                click.echo(f"Error: {msg}", err=True)
            raise SystemExit(1)
        _find_with_ai(query, ai_provider, screenshot, app, json_output,
                      model=ai_model, api_key=ai_api_key)
        return

    # Validate --depth range (find supports deeper traversal than see)
    if depth < 1 or depth > 50:
        msg = f"--depth must be between 1 and 50, got {depth}"
        if json_output:
            click.echo(_common._json_error_str("INVALID_INPUT", msg))
        else:
            click.echo(f"Error: {msg}", err=True)
        raise SystemExit(1)

    if not _common._platform_supports_gui():
        msg = _common._platform_error_msg("UI inspection")
        if json_output:
            click.echo(_common._json_error_str("PLATFORM_ERROR", msg))
        else:
            click.echo(f"Error: {msg}", err=True)
        raise SystemExit(1)

    try:
        be = _common._get_backend(json_output)
        tree = be.get_element_tree(app=app, window_title=window_title, hwnd=hwnd,
                                   pid=pid, depth=depth, backend=backend)
        if tree is None:
            msg = "No window found or UI tree is empty."
            if json_output:
                click.echo(_common._json_error_str("WINDOW_NOT_FOUND", msg))
            else:
                click.echo(f"Error: {msg}", err=True)
            raise SystemExit(1)

        from naturo.search import search_elements
        # Convert backend ElementInfo tree to bridge ElementInfo for search
        from naturo.bridge import ElementInfo as BridgeElementInfo

        def to_bridge(el: Any) -> BridgeElementInfo:
            """Convert backend ElementInfo to bridge ElementInfo."""
            return BridgeElementInfo(
                id=el.id,
                role=el.role,
                name=el.name,
                value=el.value,
                x=el.x,
                y=el.y,
                width=el.width,
                height=el.height,
                children=[to_bridge(c) for c in el.children],
                parent_id=el.properties.get("parent_id"),
                keyboard_shortcut=el.properties.get("keyboard_shortcut"),
            )

        bridge_tree = to_bridge(tree)
        results = search_elements(
            bridge_tree,
            query,
            role_filter=role,
            actionable_only=actionable,
            max_results=limit,
        )

        # (#369) Store snapshot with refs so users can `naturo click e3` after find
        from naturo.snapshot import get_snapshot_manager
        from naturo.models.snapshot import UIElement

        mgr = get_snapshot_manager()
        snapshot_id = mgr.create_snapshot()

        # (#456) Use stable hash-based refs (same as `see` command)
        from naturo.refs import assign_stable_refs

        _element_id_to_ref: dict[int, str] = {}
        ui_map, ref_map = assign_stable_refs(
            bridge_tree, UIElement, element_obj_to_ref=_element_id_to_ref,
        )
        mgr.store_detection_result(snapshot_id, ui_map)
        mgr.store_ref_map(snapshot_id, ref_map)

        # (#1184) Build the reusable unified ``app://…`` selector for each
        # result so ``find`` output round-trips into ``selector save`` /
        # ``find <selector>`` / ``click --selector`` without falling back to
        # ``see``.  Uses the SAME SelectorBuilder + element-dict shape +
        # app-default as ``see`` (_see.py), and the ancestor chain threaded
        # through SearchResult, so ``find`` and ``see`` emit an identical
        # selector for the same node.
        import re as _re_mod

        from naturo.selector import SelectorBuilder

        _sel_builder = SelectorBuilder()
        _selector_app = app or "*"

        def _el_to_selector_dict(el: Any) -> dict[str, str]:
            """Convert an ElementInfo to a dict for SelectorBuilder (#1184)."""
            raw_id = str(el.id) if el.id else ""
            aid = raw_id if raw_id and not _re_mod.fullmatch(r"e\d+", raw_id) else ""
            return {
                "role": el.role or "*",
                "name": el.name or "",
                "automationid": aid,
            }

        def _build_result_selector(r: Any) -> str:
            """Build the unified selector for a SearchResult (#1184)."""
            ancestors_dicts = [_el_to_selector_dict(a) for a in r.ancestors]
            return _sel_builder.build_uri(
                _el_to_selector_dict(r.element), ancestors_dicts, app=_selector_app)

        if json_output:
            data = [
                {
                    "ref": _element_id_to_ref.get(id(r.element), r.element.id),
                    "id": r.element.id,
                    "role": r.element.role,
                    "name": r.element.name,
                    "value": r.element.value,
                    "x": r.element.x,
                    "y": r.element.y,
                    "width": r.element.width,
                    "height": r.element.height,
                    "selector": _build_result_selector(r),
                    "breadcrumb": r.breadcrumb_str,
                    "keyboard_shortcut": r.element.keyboard_shortcut,
                }
                for r in results
            ]
            click.echo(json_dumps({
                "success": True,
                "elements": data,
                "count": len(data),
                "snapshot_id": snapshot_id,
            }, indent=2))
        else:
            if not results:
                click.echo(f"No elements found matching: {query}")
                return

            for i, r in enumerate(results):
                el = r.element
                ref = _element_id_to_ref.get(id(el), "?")
                name_str = f' "{el.name}"' if el.name else ""
                pos_str = f"({el.x},{el.y} {el.width}x{el.height})"
                shortcut = f" [{el.keyboard_shortcut}]" if el.keyboard_shortcut else ""
                click.echo(f"  {ref}. [{el.role}]{name_str} {pos_str}{shortcut}")
                click.echo(f"     {r.breadcrumb_str}")
                # (#1184) Show the reusable unified selector so the human
                # output is also discover-then-save friendly, not just JSON.
                click.echo(f"     selector: {_build_result_selector(r)}")

            click.echo(f"\n{len(results)} element(s) found.")
            click.echo(f"Snapshot: {snapshot_id}")
            click.echo("Tip: use 'naturo click e<N>' to interact with a found element.")

    except _common.WindowNotFoundError as e:
        # (#1047) The backend raises WindowNotFoundError (message "Window not
        # found: <target>") rather than returning None, so the not-found path
        # never reaches the ``tree is None`` branch above.  Classify it as a
        # recoverable WINDOW_NOT_FOUND with remediation guidance — matching the
        # envelope its siblings (see/menu-inspect/highlight) emit for the same
        # condition — instead of flattening it into an unrecoverable
        # UNKNOWN_ERROR via the broad handler below.
        if json_output:
            click.echo(_common._json_error_str("WINDOW_NOT_FOUND", str(e)))
        else:
            click.echo(f"Error: {e}", err=True)
        raise SystemExit(1)
    except Exception as e:
        if json_output:
            click.echo(_common._json_error_str("UNKNOWN_ERROR", str(e)))
        else:
            click.echo(f"Error: {e}", err=True)
        raise SystemExit(1)


def _window_origin(target_hwnd: int | None) -> tuple[int, int]:
    """Return the screen-space top-left of a captured window.

    ``capture_window`` produces a window-relative image (origin 0,0); adding
    this offset converts match coordinates back to screen-absolute coordinates
    so the results are directly clickable.

    Args:
        target_hwnd: Window handle, or 0/None for the foreground window.

    Returns:
        ``(left, top)`` in screen pixels; ``(0, 0)`` when the rect cannot be
        queried (e.g. non-Windows) so coordinates stay window-relative rather
        than failing.
    """
    import platform as _plat
    if _plat.system() != "Windows":
        return 0, 0
    try:
        import ctypes
        import ctypes.wintypes as wt
        handle = target_hwnd or ctypes.windll.user32.GetForegroundWindow()  # type: ignore[attr-defined]
        rect = wt.RECT()
        if handle and ctypes.windll.user32.GetWindowRect(handle, ctypes.byref(rect)):  # type: ignore[attr-defined]
            return rect.left, rect.top
    except Exception as exc:
        _common.logger.debug("Window rect lookup failed for hwnd %s: %s", target_hwnd, exc)
    return 0, 0


def _monitor_origin(backend: Any, screen_index: int) -> tuple[int, int]:
    """Return the virtual-desktop top-left of a captured monitor.

    Args:
        backend: The active platform backend.
        screen_index: Zero-based monitor index.

    Returns:
        ``(x, y)`` in virtual-desktop pixels; ``(0, 0)`` when monitor geometry
        is unavailable.
    """
    try:
        monitors = backend.list_monitors()
        if 0 <= screen_index < len(monitors):
            mon = monitors[screen_index]
            return int(mon.x), int(mon.y)
    except Exception as exc:
        _common.logger.debug("Monitor origin lookup failed for screen %s: %s", screen_index, exc)
    return 0, 0


class _ImageMatchError(Exception):
    """Internal carrier for an image-matching failure with its own error code.

    Lets the shared matching core (:func:`_resolve_image_matches`) attribute each
    distinct failure source to its own code/message (#1067/#1070) while leaving
    each caller — ``find --image`` and ``click --image`` (#1059) — to render the
    error in its command's house style (a plain ``_json_error_str`` code for
    ``find`` vs. the structured ``_json_err`` envelope for ``click``).

    Attributes:
        code: The attributing error-code string (a registered ``ErrorCode``).
        message: The human-readable error message.
    """

    def __init__(self, code: str, message: str) -> None:
        super().__init__(message)
        self.code = code
        self.message = message


def _resolve_image_matches(
    template_path: str,
    threshold: float,
    find_all: bool,
    *,
    app: str | None,
    window_title: str | None,
    hwnd: int | None,
    pid: int | None,
    screenshot: str | None,
    limit: int,
    json_output: bool,
) -> tuple[list[Any], int, int, int | None, int, int]:
    """Load a template, acquire the haystack, and run NCC template matching.

    Shared core behind ``naturo find --image`` and ``naturo click --image``
    (#1059) so both commands resolve a template to coordinates identically — same
    capture precedence, same threshold semantics, and the same per-source error
    attribution (#1067/#1070). The caller owns rendering: matches are returned
    rather than printed, and every failure is raised as :class:`_ImageMatchError`
    carrying the error code instead of being emitted directly.

    The haystack is, in order of precedence:

    * the image at ``screenshot`` when given (offline/deterministic matching for
      replay and headless pipelines — coordinates are relative to the
      screenshot's top-left, origin ``(0, 0)``);
    * a specific window when any of app/window/hwnd/pid is given;
    * otherwise the primary screen.

    Args:
        template_path: Path to the template image (PNG/JPG).
        threshold: Minimum match score in ``[0.0, 1.0]``.
        find_all: When True, return every non-overlapping match; otherwise the
            single best.
        app: Target app name/partial match.
        window_title: Target window title substring.
        hwnd: Target window handle.
        pid: Target process ID.
        screenshot: Optional path to an existing screenshot to match against
            instead of capturing live. Incompatible with the window-targeting
            flags (app/window/hwnd/pid), which are rejected rather than silently
            ignored (#1070), since the screenshot is the haystack.
        limit: Maximum number of matches to return.
        json_output: Forwarded to backend acquisition so a headless-session
            error is rendered in the caller's chosen format.

    Returns:
        ``(matches, origin_x, origin_y, target_hwnd, haystack_width,
        haystack_height)`` where ``matches`` are
        :class:`~naturo.image_match.Match` objects in haystack coordinates and
        ``(origin_x, origin_y)`` is the offset to add for screen-absolute
        coordinates.

    Raises:
        _ImageMatchError: On invalid threshold, missing/undecodable template or
            screenshot, a missing Pillow dependency, a GUI-less platform (live
            path only), window-not-found, or a live-capture fault — each with its
            own attributing code.
        SystemExit: Propagated from backend acquisition when no interactive
            desktop session exists (live path only).
    """
    import os

    if not (0.0 <= threshold <= 1.0):
        raise _ImageMatchError(
            "INVALID_INPUT",
            f"--threshold must be between 0.0 and 1.0, got {threshold}",
        )

    if not os.path.exists(template_path):
        raise _ImageMatchError(
            "FILE_NOT_FOUND", f"Template image not found: {template_path}",
        )

    try:
        from PIL import Image
    except ImportError as e:  # pragma: no cover - exercised only without Pillow
        raise _ImageMatchError(
            "MISSING_DEPENDENCY",
            f"Pillow is required for --image matching: {e}. "
            "Install it with 'pip install naturo[annotate]'.",
        )

    from naturo.image_match import match_template

    # Offline mode (#1070): when --screenshot is given the screenshot IS the
    # search haystack, so the window-targeting flags do not apply. Reject the
    # combination explicitly rather than silently ignoring it (the convention
    # the --ai path already follows) — silently discarding --screenshot and
    # matching the live screen returns confidently-wrong coordinates. Offline
    # matching needs no live capture, so it is also exempt from the GUI-platform
    # requirement that the live-capture path enforces (it runs headless).
    if screenshot is not None:
        if hwnd or app or window_title or pid:
            raise _ImageMatchError(
                "INVALID_INPUT",
                "--screenshot matches against the supplied image, so "
                "--app/--window/--hwnd/--pid do not apply; drop those flags to "
                "match the screenshot, or drop --screenshot to capture a live "
                "window.",
            )
        if not os.path.exists(screenshot):
            raise _ImageMatchError(
                "FILE_NOT_FOUND", f"Screenshot file not found: {screenshot}",
            )
    elif not _common._platform_supports_gui():
        raise _ImageMatchError(
            "PLATFORM_ERROR", _common._platform_error_msg("Image matching"),
        )

    # Load the template once, in its own try, so a template that exists but
    # cannot be decoded is attributed to the template — never mis-reported as a
    # haystack capture/load failure (#1067).
    try:
        with Image.open(template_path) as tmpl_src:
            template = tmpl_src.copy()
    except Exception as e:
        raise _ImageMatchError(
            "INVALID_TEMPLATE",
            f"Template image could not be loaded: {template_path} ({e})",
        )

    # Acquire the haystack: the supplied screenshot (offline) or a live capture.
    target_hwnd = hwnd
    if screenshot is not None:
        try:
            with Image.open(screenshot) as hay_src:
                haystack = hay_src.copy()
        except Exception as e:
            raise _ImageMatchError(
                "INVALID_SCREENSHOT",
                f"Screenshot could not be loaded: {screenshot} ({e})",
            )
        # Matches are located within the supplied screenshot, so coordinates are
        # relative to its top-left rather than screen-absolute.
        origin_x, origin_y = 0, 0
        target_hwnd = None
    else:
        backend = _common._get_backend(json_output)
        targeted = bool(hwnd or app or window_title or pid)

        import tempfile
        fd, capture_path = tempfile.mkstemp(suffix=".png")
        os.close(fd)
        try:
            if targeted:
                if not target_hwnd and hasattr(backend, "_resolve_hwnd"):
                    target_hwnd = backend._resolve_hwnd(
                        app=app, window_title=window_title, pid=pid)
                if not target_hwnd:
                    target = app or window_title or (f"pid={pid}" if pid else "target")
                    raise _ImageMatchError(
                        "WINDOW_NOT_FOUND", f"Window not found: {target}")
                backend.capture_window(hwnd=target_hwnd, output_path=capture_path)
                origin_x, origin_y = _window_origin(target_hwnd)
            else:
                backend.capture_screen(screen_index=0, output_path=capture_path)
                origin_x, origin_y = _monitor_origin(backend, 0)

            with Image.open(capture_path) as hay_src:
                haystack = hay_src.copy()
        except _ImageMatchError:
            raise
        except Exception as e:
            raise _ImageMatchError("CAPTURE_FAILED", f"Screen capture failed: {e}")
        finally:
            try:
                os.remove(capture_path)
            except OSError:
                pass

    try:
        matches = match_template(
            haystack, template, threshold=threshold, find_all=find_all, max_results=limit,
        )
    except ValueError as e:
        raise _ImageMatchError("INVALID_INPUT", str(e))

    return matches, origin_x, origin_y, target_hwnd, haystack.width, haystack.height


def _find_with_image(
    template_path: str,
    threshold: float,
    find_all: bool,
    *,
    app: str | None,
    window_title: str | None,
    hwnd: int | None,
    pid: int | None,
    screenshot: str | None,
    limit: int,
    json_output: bool,
) -> None:
    """Locate a template image on the target window, screen, or screenshot.

    Backs ``naturo find --image``.  The haystack is, in order of precedence:

    * the image at ``screenshot`` when given (offline/deterministic matching for
      replay, headless pipelines, and regression fixtures — coordinates are
      reported relative to the screenshot's top-left, origin ``(0, 0)``);
    * a specific window when any of app/window/hwnd/pid is given;
    * otherwise the primary screen.

    It runs normalized cross-correlation and reports matches as snapshot
    elements with stable ``eN`` refs so they can be acted on with
    ``naturo click eN``.

    Each distinct failure source carries its own error code rather than
    inheriting a sibling's (#1067/#1070 error attribution): a template file that
    cannot be decoded → ``INVALID_TEMPLATE`` (never the haystack's
    ``CAPTURE_FAILED``); a missing screenshot → ``FILE_NOT_FOUND``; a screenshot
    that cannot be decoded → ``INVALID_SCREENSHOT``; a live-capture fault →
    ``CAPTURE_FAILED``.

    Args:
        template_path: Path to the template image (PNG/JPG).
        threshold: Minimum match score in ``[0.0, 1.0]``.
        find_all: When True, report every non-overlapping match; otherwise the
            single best.
        app: Target app name/partial match.
        window_title: Target window title substring.
        hwnd: Target window handle.
        pid: Target process ID.
        screenshot: Optional path to an existing screenshot to match against
            instead of capturing live.  Incompatible with the window-targeting
            flags (app/window/hwnd/pid), which the function rejects rather than
            silently ignoring (#1070), since the screenshot is the haystack.
        limit: Maximum number of matches to return.
        json_output: Whether to emit JSON.

    Raises:
        SystemExit: With status 1 on invalid input, missing/undecodable file,
            platform without GUI support, window-not-found, or capture failure.
    """
    import os

    def _emit(code: str, message: str) -> NoReturn:
        if json_output:
            click.echo(_common._json_error_str(code, message))
        else:
            click.echo(f"Error: {message}", err=True)
        raise SystemExit(1)

    try:
        matches, origin_x, origin_y, target_hwnd, haystack_width, haystack_height = (
            _resolve_image_matches(
                template_path, threshold, find_all,
                app=app, window_title=window_title, hwnd=hwnd, pid=pid,
                screenshot=screenshot, limit=limit, json_output=json_output,
            )
        )
    except _ImageMatchError as exc:
        _emit(exc.code, exc.message)

    # Register matches as snapshot elements so `naturo click eN` works, mirroring
    # the ref bookkeeping the text-search path uses.
    from naturo.bridge import ElementInfo as BridgeElementInfo
    from naturo.snapshot import get_snapshot_manager
    from naturo.models.snapshot import UIElement
    from naturo.refs import assign_stable_refs

    template_name = os.path.basename(template_path)
    children = [
        BridgeElementInfo(
            id=str(i),
            role="Image",
            name=template_name,
            value=f"{m.score:.4f}",
            x=origin_x + m.x,
            y=origin_y + m.y,
            width=m.width,
            height=m.height,
            parent_id="0",
            hwnd=target_hwnd or 0,
        )
        for i, m in enumerate(matches, start=1)
    ]
    root = BridgeElementInfo(
        id="0",
        role="Pane",
        name="image-match",
        value=None,
        x=origin_x,
        y=origin_y,
        width=haystack_width,
        height=haystack_height,
        children=children,
        hwnd=target_hwnd or 0,
    )

    mgr = get_snapshot_manager()
    snapshot_id = mgr.create_snapshot()
    element_id_to_ref: dict[int, str] = {}
    ui_map, ref_map = assign_stable_refs(root, UIElement, element_obj_to_ref=element_id_to_ref)
    mgr.store_detection_result(snapshot_id, ui_map)
    mgr.store_ref_map(snapshot_id, ref_map)

    if json_output:
        data = [
            {
                "ref": element_id_to_ref.get(id(child), child.id),
                "role": child.role,
                "name": child.name,
                "x": child.x,
                "y": child.y,
                "width": child.width,
                "height": child.height,
                "center_x": child.x + child.width // 2,
                "center_y": child.y + child.height // 2,
                "score": round(m.score, 4),
            }
            for child, m in zip(children, matches)
        ]
        click.echo(json_dumps({
            "success": True,
            "elements": data,
            "count": len(data),
            "snapshot_id": snapshot_id,
            "coordinate_frame": "screenshot" if screenshot is not None else "screen",
        }, indent=2))
    else:
        if not matches:
            click.echo(f"No match for template '{template_name}' (threshold {threshold}).")
            return
        for child, m in zip(children, matches):
            ref = element_id_to_ref.get(id(child), "?")
            click.echo(
                f"  {ref}. [Image] \"{template_name}\" "
                f"({child.x},{child.y} {child.width}x{child.height}) score={m.score:.3f}"
            )
        click.echo(f"\n{len(matches)} match(es) found.")
        click.echo(f"Snapshot: {snapshot_id}")
        if screenshot is not None:
            click.echo("Coordinates are relative to the supplied screenshot "
                       "(not screen-absolute).")
        click.echo("Tip: use 'naturo click e<N>' to interact with a match.")


def _find_with_ocr(
    text: str,
    find_all: bool,
    *,
    app: str | None,
    window_title: str | None,
    hwnd: int | None,
    pid: int | None,
    screenshot: str | None,
    limit: int,
    json_output: bool,
) -> None:
    """Locate on-screen text by OCR (naturo find --ocr).

    Recognises text on the target window, screen, or a supplied screenshot via
    the optional RapidOCR engine and reports each region whose text matches
    ``text`` as a snapshot element with a stable ``eN`` ref, so matches can be
    acted on with ``naturo click eN`` — the contract the text/image/selector
    strategies share.

    The haystack is, in order of precedence:

    * the image at ``screenshot`` when given (offline/deterministic matching —
      coordinates are relative to the screenshot's top-left, origin ``(0, 0)``);
    * a specific window when any of app/window/hwnd/pid is given;
    * otherwise the primary screen.

    Each distinct failure source carries its own error code: a missing OCR engine
    → ``OCR_NOT_AVAILABLE`` (recoverable, with the install hint); a
    ``--screenshot`` combined with window-targeting flags → ``INVALID_INPUT``; a
    missing screenshot → ``FILE_NOT_FOUND``; a live-capture fault →
    ``CAPTURE_FAILED``; an OCR engine fault → ``OCR_FAILED``.

    Validation that does not depend on a live desktop (the ``--screenshot``
    conflict and existence checks) runs *before* the GUI-platform gate so a given
    bad input yields the same error code on every OS (#1072), and the offline
    ``--screenshot`` path is exempt from the gate entirely.

    Args:
        text: The text to locate (case-insensitive substring match).
        find_all: When True, report every matching region; otherwise the single
            highest-confidence match.
        app: Target app name/partial match.
        window_title: Target window title substring.
        hwnd: Target window handle.
        pid: Target process ID.
        screenshot: Optional path to an existing screenshot to OCR instead of
            capturing live. Incompatible with the window-targeting flags
            (app/window/hwnd/pid), which are rejected rather than silently
            ignored, since the screenshot is the haystack.
        limit: Maximum number of matches to return.
        json_output: Whether to emit JSON.

    Raises:
        SystemExit: With status 1 on any of the failure sources above or on a
            platform without GUI support (live path only).
    """
    import os

    def _emit(code: str, message: str) -> NoReturn:
        if json_output:
            click.echo(_common._json_error_str(code, message))
        else:
            click.echo(f"Error: {message}", err=True)
        raise SystemExit(1)

    # Offline-input validation first, so the bad-input → code contract is the same
    # on every OS; the offline path needs no live capture and skips the GUI gate.
    if screenshot is not None:
        if hwnd or app or window_title or pid:
            _emit(
                "INVALID_INPUT",
                "--screenshot matches against the supplied image, so "
                "--app/--window/--hwnd/--pid do not apply; drop those flags to "
                "OCR the screenshot, or drop --screenshot to capture a live window.",
            )
        if not os.path.exists(screenshot):
            _emit("FILE_NOT_FOUND", f"Screenshot file not found: {screenshot}")
    elif not _common._platform_supports_gui():
        _emit("PLATFORM_ERROR", _common._platform_error_msg("OCR text finding"))

    # Acquire the haystack image path and its coordinate origin. The supplied
    # screenshot is used directly (origin 0,0); otherwise a live window/screen
    # capture is written to a temp file that is removed once OCR has read it.
    from naturo.ocr_match import OCRNotAvailableError, find_text

    target_hwnd = hwnd
    temp_path: str | None = None
    if screenshot is not None:
        haystack_path = screenshot
        origin_x, origin_y = 0, 0
        target_hwnd = None
    else:
        backend = _common._get_backend(json_output)
        targeted = bool(hwnd or app or window_title or pid)
        import tempfile
        fd, temp_path = tempfile.mkstemp(suffix=".png")
        os.close(fd)
        try:
            if targeted:
                if not target_hwnd and hasattr(backend, "_resolve_hwnd"):
                    target_hwnd = backend._resolve_hwnd(
                        app=app, window_title=window_title, pid=pid)
                if not target_hwnd:
                    target = app or window_title or (f"pid={pid}" if pid else "target")
                    _cleanup_temp(temp_path)
                    _emit("WINDOW_NOT_FOUND", f"Window not found: {target}")
                backend.capture_window(hwnd=target_hwnd, output_path=temp_path)
                origin_x, origin_y = _window_origin(target_hwnd)
            else:
                backend.capture_screen(screen_index=0, output_path=temp_path)
                origin_x, origin_y = _monitor_origin(backend, 0)
        except SystemExit:
            raise
        except Exception as e:
            _cleanup_temp(temp_path)
            _emit("CAPTURE_FAILED", f"Screen capture failed: {e}")
        haystack_path = temp_path

    # Read haystack dimensions for the snapshot root (best-effort).
    haystack_width, haystack_height = 0, 0
    try:
        from PIL import Image
        with Image.open(haystack_path) as hay:
            haystack_width, haystack_height = hay.width, hay.height
    except Exception as exc:
        _common.logger.debug("Haystack dimension read failed for %s: %s",
                             haystack_path, exc)

    try:
        matches = find_text(haystack_path, text, find_all=find_all, max_results=limit)
    except OCRNotAvailableError as exc:
        _emit("OCR_NOT_AVAILABLE", str(exc))
    except Exception as exc:
        _emit("OCR_FAILED", f"OCR text recognition failed: {exc}")
    finally:
        # Remove the temp capture once OCR has read it (no-op for --screenshot).
        _cleanup_temp(temp_path)

    # Register matches as snapshot elements so `naturo click eN` works, mirroring
    # the image strategy's ref bookkeeping.
    from naturo.bridge import ElementInfo as BridgeElementInfo
    from naturo.snapshot import get_snapshot_manager
    from naturo.models.snapshot import UIElement
    from naturo.refs import assign_stable_refs

    children = [
        BridgeElementInfo(
            id=str(i),
            role="Text",
            name=m.text,
            value=f"{m.score:.4f}",
            x=origin_x + m.x,
            y=origin_y + m.y,
            width=m.width,
            height=m.height,
            parent_id="0",
            hwnd=target_hwnd or 0,
        )
        for i, m in enumerate(matches, start=1)
    ]
    root = BridgeElementInfo(
        id="0",
        role="Pane",
        name="ocr-match",
        value=None,
        x=origin_x,
        y=origin_y,
        width=haystack_width,
        height=haystack_height,
        children=children,
        hwnd=target_hwnd or 0,
    )

    mgr = get_snapshot_manager()
    snapshot_id = mgr.create_snapshot()
    element_id_to_ref: dict[int, str] = {}
    ui_map, ref_map = assign_stable_refs(root, UIElement, element_obj_to_ref=element_id_to_ref)
    mgr.store_detection_result(snapshot_id, ui_map)
    mgr.store_ref_map(snapshot_id, ref_map)

    if json_output:
        data = [
            {
                "ref": element_id_to_ref.get(id(child), child.id),
                "role": child.role,
                "text": child.name,
                "x": child.x,
                "y": child.y,
                "width": child.width,
                "height": child.height,
                "center_x": child.x + child.width // 2,
                "center_y": child.y + child.height // 2,
                "score": round(m.score, 4),
            }
            for child, m in zip(children, matches)
        ]
        click.echo(json_dumps({
            "success": True,
            "elements": data,
            "count": len(data),
            "snapshot_id": snapshot_id,
            "coordinate_frame": "screenshot" if screenshot is not None else "screen",
        }, indent=2))
    else:
        if not matches:
            click.echo(f"No on-screen text matching: {text}")
            return
        for child, m in zip(children, matches):
            ref = element_id_to_ref.get(id(child), "?")
            click.echo(
                f"  {ref}. [Text] \"{child.name}\" "
                f"({child.x},{child.y} {child.width}x{child.height}) score={m.score:.3f}"
            )
        click.echo(f"\n{len(matches)} match(es) found.")
        click.echo(f"Snapshot: {snapshot_id}")
        if screenshot is not None:
            click.echo("Coordinates are relative to the supplied screenshot "
                       "(not screen-absolute).")
        click.echo("Tip: use 'naturo click e<N>' to interact with a match.")


def _cleanup_temp(path: str | None) -> None:
    """Remove a temporary capture file, ignoring a missing/locked file.

    Args:
        path: Path to the temp file, or None when no temp capture was made.
    """
    if not path:
        return
    try:
        import os
        os.remove(path)
    except OSError:
        pass


def _find_with_selector(
    selector_str: str,
    find_all: bool,
    *,
    app: str | None,
    window_title: str | None,
    hwnd: int | None,
    pid: int | None,
    depth: int,
    method: str,
    limit: int,
    json_output: bool,
) -> None:
    """Resolve a unified selector path to element(s) (naturo find --selector).

    Mirrors the click/type family's ``_resolve_selector_target`` so the
    ``--selector`` flag resolves the SAME way across commands — same selector
    grammar, ``@named`` dereferencing, app-name normalization, and
    ``SelectorResolver`` — then reports the match(es) as snapshot elements with
    stable ``eN`` refs (the contract the text and image strategies share), so
    they can be acted on with ``naturo click eN``.

    Each distinct failure source carries its own error code (#1047/#1067 error
    attribution): a bad ``@name`` ref → ``SELECTOR_REF_ERROR``, a malformed
    selector → ``INVALID_SELECTOR``, a missing window → ``WINDOW_NOT_FOUND``, a
    tree-fetch fault → ``TREE_ERROR``, and a no-match → ``SELECTOR_NOT_FOUND``.

    Args:
        selector_str: Selector path (URI / XML / ``//`` shorthand / ``@named``).
        find_all: When True, return every exact match; otherwise the single best
            (with the resolver's relaxed/fuzzy fallback).
        app: Target app name/partial match (overridden by the selector's app
            when not given explicitly).
        window_title: Target window title substring.
        hwnd: Target window handle.
        pid: Target process ID.
        depth: Maximum tree depth to traverse (the ``--depth`` option).
        method: Accessibility backend to use (the ``--backend``/``--method``
            option, e.g. ``"auto"``/``"uia"``/``"msaa"``). Forwarded to
            ``get_element_tree`` so the selector path resolves over the SAME
            tree the text-query path does — without it the fetch silently fell
            to the backend's ``"uia"`` default (UIA only, no hybrid fallback),
            and selectors over WinUI/XAML apps matched nothing (#1169).
        limit: Maximum number of matches to return.
        json_output: Whether to emit JSON.

    Raises:
        SystemExit: With status 1 on any of the failure sources above or on a
            platform without GUI support.
    """
    from naturo.selector import (
        parse, SelectorParseError, SelectorResolver, normalize_app_name,
    )

    def _emit_error(code: str, message: str) -> None:
        if json_output:
            click.echo(_common._json_error_str(code, message))
        else:
            click.echo(f"Error: {message}", err=True)
        raise SystemExit(1)

    # Dereference a saved @name selector to its stored path (#105), matching the
    # click family's behavior exactly.
    if selector_str.startswith("@"):
        from naturo.cli.selector_cmd import resolve_named_selector
        try:
            selector_str = resolve_named_selector(selector_str)
        except (KeyError, ValueError) as exc:
            _emit_error("SELECTOR_REF_ERROR", str(exc))

    try:
        ast = parse(selector_str)
    except SelectorParseError as exc:
        _emit_error("INVALID_SELECTOR", f"Invalid selector: {exc}")

    # The selector's app scopes the search when no explicit --app was given.
    if ast.app and ast.app != "*" and not app:
        app = normalize_app_name(ast.app)

    if not _common._platform_supports_gui():
        _emit_error("PLATFORM_ERROR", _common._platform_error_msg("Selector resolution"))

    backend = _common._get_backend(json_output)

    # An emitted wildcard-host selector (app://*/Window[@name="…"]/…) with no
    # explicit window target resolves across all top-level windows so the
    # selector see/find emit round-trips straight back into find --selector
    # (#1190) — the same behavior the click family uses, kept in lock-step via
    # the shared _common helper, which returns None for every other selector
    # shape so the normal single-window path (below) is unchanged.
    forest = None
    if (ast.app == "*" and app is None and window_title is None
            and hwnd is None and pid is None):
        from naturo.cli.interaction._common import _resolve_wildcard_host_forest
        forest = _resolve_wildcard_host_forest(
            backend, ast, depth=depth, method=method,
        )

    if forest is not None:
        tree_dict = forest
    else:
        try:
            tree = backend.get_element_tree(
                app=app, window_title=window_title, hwnd=hwnd, pid=pid,
                depth=depth, backend=method,
            )
        except _common.WindowNotFoundError as exc:
            _emit_error("WINDOW_NOT_FOUND", str(exc))
        except Exception as exc:
            _emit_error("TREE_ERROR", f"Failed to get UI tree for selector resolution: {exc}")

        if tree is None:
            _emit_error(
                "WINDOW_NOT_FOUND",
                "No window found for selector resolution. Check that the target "
                "application is running and visible.",
            )

        # Reuse the click family's ElementInfo→dict conversion so both commands
        # feed the resolver an identically-shaped tree (no semantic drift).
        from naturo.cli.interaction._common import _elementinfo_to_dict
        tree_dict = [_elementinfo_to_dict(tree)]

    resolver = SelectorResolver()
    if find_all:
        resolved = [r.element for r in resolver.resolve_all(ast, tree_dict)][:limit]
    else:
        result = resolver.resolve(ast, tree_dict)
        resolved = [result.element] if result is not None else []

    if not resolved:
        _emit_error("SELECTOR_NOT_FOUND", f"Selector matched no elements: {selector_str}")

    from naturo.bridge import ElementInfo as BridgeElementInfo
    from naturo.snapshot import get_snapshot_manager
    from naturo.models.snapshot import UIElement
    from naturo.refs import assign_stable_refs

    children = [
        BridgeElementInfo(
            id=str(i),
            role=el.get("role", ""),
            name=el.get("name", ""),
            value=el.get("value", "") or None,
            x=el.get("x", 0),
            y=el.get("y", 0),
            width=el.get("width", 0),
            height=el.get("height", 0),
            parent_id="0",
            hwnd=hwnd or 0,
        )
        for i, el in enumerate(resolved, start=1)
    ]
    root = BridgeElementInfo(
        id="0",
        role="Pane",
        name="selector-match",
        value=None,
        x=0,
        y=0,
        width=0,
        height=0,
        children=children,
        hwnd=hwnd or 0,
    )

    mgr = get_snapshot_manager()
    snapshot_id = mgr.create_snapshot()
    element_id_to_ref: dict[int, str] = {}
    ui_map, ref_map = assign_stable_refs(root, UIElement, element_obj_to_ref=element_id_to_ref)
    mgr.store_detection_result(snapshot_id, ui_map)
    mgr.store_ref_map(snapshot_id, ref_map)

    if json_output:
        data = [
            {
                "ref": element_id_to_ref.get(id(child), child.id),
                "role": child.role,
                "name": child.name,
                "value": child.value,
                "x": child.x,
                "y": child.y,
                "width": child.width,
                "height": child.height,
                "center_x": child.x + child.width // 2,
                "center_y": child.y + child.height // 2,
            }
            for child in children
        ]
        click.echo(json_dumps({
            "success": True,
            "elements": data,
            "count": len(data),
            "snapshot_id": snapshot_id,
        }, indent=2))
    else:
        for child in children:
            ref = element_id_to_ref.get(id(child), "?")
            name_str = f' "{child.name}"' if child.name else ""
            pos_str = f"({child.x},{child.y} {child.width}x{child.height})"
            click.echo(f"  {ref}. [{child.role}]{name_str} {pos_str}")
        click.echo(f"\n{len(children)} element(s) found.")
        click.echo(f"Snapshot: {snapshot_id}")
        click.echo("Tip: use 'naturo click e<N>' to interact with a resolved element.")


def _find_with_ai(
    query,
    provider_name,
    screenshot,
    app,
    json_output,
    *,
    model: str | None = None,
    api_key: str | None = None,
) -> None:
    """AI-powered element finding via naturo find --ai.

    Args:
        query: Natural language description of the element.
        provider_name: AI provider name.
        screenshot: Optional screenshot path.
        app: Optional target application window.
        json_output: Whether to output JSON.
        model: Optional AI model name override (from --model).
        api_key: Optional API key override (from --api-key).
    """
    try:
        from naturo.ai_find import ai_find_element
    except ImportError as e:
        msg = f"AI find dependencies not available: {e}"
        if json_output:
            click.echo(_common._json_error_str("MISSING_DEPENDENCY", msg))
        else:
            click.echo(f"Error: {msg}", err=True)
        raise SystemExit(1)

    # Validate screenshot path
    if screenshot and not __import__("os").path.exists(screenshot):
        msg = f"Screenshot file not found: {screenshot}"
        if json_output:
            click.echo(_common._json_error_str("FILE_NOT_FOUND", msg))
        else:
            click.echo(f"Error: {msg}", err=True)
        raise SystemExit(1)

    try:
        result = ai_find_element(
            query,
            provider_name=provider_name,
            window_title=app,
            screenshot_path=screenshot,
            model=model,
            api_key=api_key,
        )
    except Exception as e:
        msg = str(e)
        # Route through the canonical six-key error envelope (#884) so the
        # category / context / suggested_action / recoverable keys are populated,
        # not just code + message (#1179). Each branch uses a *registered* error
        # code so its category and recovery hint resolve automatically — the
        # generic branch uses AI_ANALYSIS_FAILED (category "ai") rather than the
        # old unregistered "AI_FIND_FAILED", which would degrade to "unknown".
        code = "AI_ANALYSIS_FAILED"
        if "unavailable" in msg.lower() or "api key" in msg.lower():
            code = "AI_PROVIDER_UNAVAILABLE"
        elif "capture" in msg.lower():
            code = "CAPTURE_FAILED"
        if json_output:
            click.echo(_common._json_error_str(code, msg))
        else:
            click.echo(f"Error: {msg}", err=True)
        raise SystemExit(1)

    if json_output:
        output = {
            "success": result.found,
            "description": result.description,
            "confidence": result.confidence,
            "method": result.method,
            "model": result.model,
            "tokens_used": result.tokens_used,
        }
        if result.ai_bounds:
            output["ai_bounds"] = result.ai_bounds
        if result.element:
            output["element"] = result.element
        if not result.found:
            output["error"] = {
                "code": "ELEMENT_NOT_FOUND",
                "message": f"AI could not locate: {query}",
            }
        click.echo(json_dumps(output, indent=2))
    else:
        if not result.found:
            click.echo(f"Element not found: {query}")
            if result.description:
                click.echo(f"  AI says: {result.description}")
            raise SystemExit(1)

        click.echo(f"Found: {result.description}")
        click.echo(f"  Confidence: {result.confidence:.0%}")
        click.echo(f"  Method: {result.method}")
        if result.ai_bounds:
            b = result.ai_bounds
            click.echo(f"  AI bounds: ({b.get('x', '?')}, {b.get('y', '?')}) "
                        f"{b.get('width', '?')}x{b.get('height', '?')}")
        if result.element:
            el = result.element
            click.echo(f"  UIA match: [{el.get('role', '')}] \"{el.get('name', '')}\"")
            eb = el.get("bounds", {})
            click.echo(f"  UIA bounds: ({eb.get('x', '?')}, {eb.get('y', '?')}) "
                        f"{eb.get('width', '?')}x{eb.get('height', '?')}")
            click.echo(f"  Match distance: {el.get('match_distance', '?')} px")
        click.echo(f"  [{result.model}, {result.tokens_used} tokens]", err=True)

    if not result.found:
        raise SystemExit(1)
