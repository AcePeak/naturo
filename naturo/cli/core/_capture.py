"""Capture command — screenshot capture with optional element/region crop."""
from __future__ import annotations

import click

import naturo.cli.core._common as _common
from naturo.cli._jsonio import json_dumps


@click.command("capture")
@click.option("--app", help="Target application (name or partial match)")
@click.option("--pid", type=int, default=None, help="Process ID")
@click.option("--window", "window_title", default=None, help="Window title pattern (substring match)")
@click.option("--window-title", "window_title", default=None, hidden=True, help="")
@click.option("--hwnd", type=int, default=None, help="Window handle (HWND)")
@click.option("--screen", "-s", type=int, default=0, help="Screen/monitor index")
@click.option("--path", "-p", "-o", default=None, help="Output file path (default: capture.<format>)")
@click.option("--format", "fmt", type=click.Choice(["png", "jpg", "bmp"]), default="png", help="Image format (default: png)")
@click.option("--element", "-e", "--ref", "element_ref", default=None,
              help="Crop to element ref (eN) from most recent snapshot, e.g. --element e5 or --ref e5")
@click.option("--region", default=None, metavar="X,Y,W,H",
              help="Crop to region: x,y,width,height (e.g. --region 100,50,400,300)")
@click.option("--padding", type=int, default=0,
              help="Extra padding (px) added around --element or --region crop")
@click.option("--snapshot/--no-snapshot", "store_snapshot", default=True, help="Store result in snapshot (default: on)")
@click.option("--session", default=None, envvar="NATURO_SESSION",
              help="Snapshot session for isolation (default: NATURO_SESSION env or 'default')")
@click.option("--json", "-j", "json_output", is_flag=True, help="JSON output")
@click.option("--app-id", "app_id", default=None,
              help='Stable app/window ID from "naturo app list" output (e.g. a1)')
def capture(app: str | None, pid: int | None, window_title: str | None, hwnd: int | None,
            screen: int, path: str | None, fmt: str, store_snapshot: bool, session: str | None,
            element_ref: str | None, region: str | None, padding: int, json_output: bool,
            app_id: str | None) -> None:
    """Capture a live screenshot, optionally cropped to an element or region.

    Captures the screen or a specific window and saves to a file.
    Use --hwnd to capture a specific window, or --screen to select a monitor.
    The screenshot is automatically stored in a snapshot (use --no-snapshot to skip).
    Output format is PNG by default (matching Peekaboo).

    Use --element eN (or --ref eN) to crop to a specific element from the last 'naturo see' snapshot.
    Use --region X,Y,W,H to crop to arbitrary coordinates.
    Use --padding N to add N pixels of padding around the crop area.

    \b
    Examples:
        naturo capture                                  # full screen
        naturo capture --element e5                     # crop to element e5
        naturo capture --ref e5 --padding 20            # with 20px padding
        naturo capture --region 100,50,400,300          # crop to region
        naturo capture --app feishu --element e12       # element in specific app
        naturo capture --pid 51764                      # capture by process ID
        naturo capture --app-id a1 --element e12        # element by app ID
        naturo capture -o output.png                    # save to output.png
    """
    # (#752) Auto-detect app ID pattern (a1, a2, ...) in --app flag
    from naturo.cli.options import maybe_promote_app_to_app_id
    app, app_id = maybe_promote_app_to_app_id(app, app_id)

    # (#361) Resolve --app-id to app/hwnd before any other logic
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
        # (#573) Use hwnd for precise targeting.  Do NOT set app
        # to process_name — it may be a full path that breaks fuzzy matching.
        hwnd = entry.handle

    if not _common._platform_supports_gui():
        msg = _common._platform_error_msg("Screen capture")
        if json_output:
            click.echo(_common._json_error_str("PLATFORM_ERROR", msg))
        else:
            click.echo(f"Error: {msg}", err=True)
        raise SystemExit(1)

    # Resolve output path: use --path if given, else timestamped name
    if path is None:
        from datetime import datetime
        timestamp = datetime.now().strftime("%Y%m%d-%H%M%S")
        app_label = (app or window_title or "screen").lower().replace(" ", "-")
        path = f"naturo-{app_label}-{timestamp}.{fmt}"

    # (#1022) Auto-create the parent directory so a missing folder doesn't
    # surface as a raw [Errno 2] mislabeled as a capture failure.
    _common._ensure_output_dir(path, json_output)

    try:
        backend = _common._get_backend(json_output)
        if hwnd or app or window_title or pid:
            # Resolve app/window_title/pid to hwnd if needed
            target_hwnd = hwnd
            if not target_hwnd and hasattr(backend, '_resolve_hwnd'):
                target_hwnd = backend._resolve_hwnd(app=app, window_title=window_title, pid=pid)
            # (#843) When targeting an app/pid, capture the main window plus
            # any popup/menu windows owned by the same process.  When a direct
            # --hwnd is given, capture only that single window.
            if target_hwnd and not hwnd and hasattr(backend, 'capture_app_windows'):
                result = backend.capture_app_windows(main_hwnd=target_hwnd, output_path=path)
            else:
                result = backend.capture_window(hwnd=target_hwnd or 0, output_path=path)
        else:
            # Validate screen index against available monitors
            if screen < 0:
                msg = f"--screen must be >= 0, got {screen}"
                if json_output:
                    click.echo(_common._json_error_str("INVALID_INPUT", msg))
                else:
                    click.echo(f"Error: {msg}", err=True)
                raise SystemExit(1)
            try:
                monitors = backend.list_monitors()
                if monitors and screen >= len(monitors):
                    msg = f"Screen index {screen} out of range (0-{len(monitors) - 1}). Use 'naturo list screens' to see available monitors."
                    if json_output:
                        click.echo(_common._json_error_str("INVALID_INPUT", msg))
                    else:
                        click.echo(f"Error: {msg}", err=True)
                    raise SystemExit(1)
            except NotImplementedError:
                pass  # Non-Windows: skip validation, let backend handle it
            result = backend.capture_screen(screen_index=screen, output_path=path)

        # ── Element / region crop (issue #160) ───────────────────────────────
        crop_box = None  # (left, top, right, bottom) in image coordinates
        # The user's raw --region request (x, y, w, h), kept so an off-screen
        # error can echo what the user typed rather than the clamped PIL box
        # (issue #1050).  None for the --element path.
        requested_region: tuple[int, int, int, int] | None = None

        # Track whether the capture is window-relative (for element crop offset)
        _is_window_capture = bool(hwnd or app or window_title or pid)

        if element_ref:
            # Resolve eN ref → bounds from most recent snapshot
            from naturo.snapshot import get_snapshot_manager
            _mgr = get_snapshot_manager(session=session)
            resolved = _mgr.resolve_ref(element_ref, app_name=app)
            if resolved is None:
                msg = (
                    f"Element ref '{element_ref}' not found in recent snapshots. "
                    "Run 'naturo see' first to create a snapshot."
                )
                if json_output:
                    click.echo(_common._json_error_str(
                        "STALE_SNAPSHOT_CACHE", msg, context={"ref": element_ref}))
                else:
                    click.echo(f"Error: {msg}", err=True)
                raise SystemExit(1)
            cx, cy, _snap_id = resolved
            el_result = _mgr.resolve_ref_element(element_ref, app_name=app)
            if el_result:
                element, snap_id = el_result
                ex, ey, ew, eh = element.frame

                # Check for zero-size bounds (cannot crop)
                if ew <= 0 or eh <= 0:
                    msg = (
                        f"Element {element_ref} (role={element.role!r} name={element.name!r}) "
                        f"has zero-size bounds ({ew}x{eh}) at ({ex},{ey}) and cannot be cropped. "
                        "This element may be off-screen, hidden, or in a virtualized container."
                    )
                    if json_output:
                        click.echo(_common._json_error_str("ZERO_SIZE_ELEMENT", msg))
                    else:
                        click.echo(f"Error: {msg}", err=True)
                    raise SystemExit(1)

                # When capturing a specific window (--app/--hwnd), the
                # screenshot is window-relative (origin 0,0) but element
                # coords from the snapshot are screen-absolute.  Subtract
                # the window origin so the crop aligns with the image.
                win_offset_x, win_offset_y = 0, 0
                if _is_window_capture:
                    # Try 1: query current window rect via Win32 API
                    try:
                        import platform as _plat
                        _cap_hwnd = target_hwnd if target_hwnd else 0
                        if _cap_hwnd and _plat.system() == "Windows":
                            import ctypes
                            import ctypes.wintypes as wt
                            rect = wt.RECT()
                            if ctypes.windll.user32.GetWindowRect(  # type: ignore[attr-defined]
                                _cap_hwnd, ctypes.byref(rect)
                            ):
                                win_offset_x = rect.left
                                win_offset_y = rect.top
                    except Exception as exc:
                        _common.logger.debug("Window rect lookup failed for hwnd %s: %s", _cap_hwnd, exc)
                    # Try 2: fall back to snapshot window_bounds
                    if win_offset_x == 0 and win_offset_y == 0:
                        try:
                            snap_data = _mgr.get_snapshot(snap_id)
                            if snap_data.window_bounds:
                                win_offset_x = snap_data.window_bounds[0]
                                win_offset_y = snap_data.window_bounds[1]
                        except Exception:
                            pass  # Best-effort; absolute coords as last resort

                crop_box = (
                    max(0, ex - win_offset_x - padding),
                    max(0, ey - win_offset_y - padding),
                    ex - win_offset_x + ew + padding,
                    ey - win_offset_y + eh + padding,
                )
        elif region:
            # Parse X,Y,W,H
            try:
                parts = [int(v.strip()) for v in region.split(",")]
                if len(parts) != 4:
                    raise ValueError("need 4 values")
                rx, ry, rw, rh = parts
                requested_region = (rx, ry, rw, rh)
                crop_box = (
                    max(0, rx - padding),
                    max(0, ry - padding),
                    rx + rw + padding,
                    ry + rh + padding,
                )
            except (ValueError, TypeError) as exc:
                msg = f"--region must be X,Y,W,H (e.g. 100,50,400,300): {exc}"
                if json_output:
                    click.echo(_common._json_error_str("INVALID_INPUT", msg))
                else:
                    click.echo(f"Error: {msg}", err=True)
                raise SystemExit(1)

        # Apply crop if requested
        if crop_box is not None:
            try:
                from PIL import Image as _PILImage
                img = _PILImage.open(result.path)
                # Clamp to image bounds
                iw, ih = img.size
                left = max(0, crop_box[0])
                top = max(0, crop_box[1])
                right = min(iw, crop_box[2])
                bottom = min(ih, crop_box[3])
                if right <= left or bottom <= top:
                    # Echo the user's *requested* region, not the clamped PIL
                    # crop box — the clamped (left, top, right, bottom) reads
                    # like an X,Y,W,H the user never typed (issue #1050).
                    if requested_region is not None:
                        rx, ry, rw, rh = requested_region
                        if rw <= 0 or rh <= 0:
                            msg = (
                                f"Crop region X,Y,W,H ({rx},{ry},{rw},{rh}) has "
                                "non-positive width/height; W and H must both be > 0."
                            )
                        else:
                            msg = (
                                f"Crop region X,Y,W,H ({rx},{ry},{rw},{rh}) is entirely "
                                f"outside the captured image bounds ({iw}x{ih}). "
                                "Reduce X/Y or W/H so the region overlaps the screen."
                            )
                        context = {
                            "requested_region": [rx, ry, rw, rh],
                            "image_size": [iw, ih],
                        }
                    else:
                        # --element path: the resolved bounds fall outside the
                        # captured image after the window-origin offset.
                        msg = (
                            f"Crop bounds fall entirely outside the captured image "
                            f"bounds ({iw}x{ih}); the element may be off-screen."
                        )
                        context = {
                            "clamped_crop_box": [left, top, right, bottom],
                            "image_size": [iw, ih],
                        }
                    if json_output:
                        click.echo(
                            _common._json_error_str("INVALID_INPUT", msg, context=context)
                        )
                    else:
                        click.echo(f"Error: {msg}", err=True)
                    raise SystemExit(1)
                cropped = img.crop((left, top, right, bottom))
                cropped.save(result.path)
                # Update result dimensions (best-effort via dataclass copy)
                from dataclasses import replace as _dc_replace
                result = _dc_replace(result, width=right - left, height=bottom - top)
            except ImportError:
                msg = "Pillow required for --element/--region crop. Install: pip install naturo[annotate]"
                if json_output:
                    click.echo(_common._json_error_str("MISSING_DEPENDENCY", msg))
                else:
                    click.echo(f"Error: {msg}", err=True)
                raise SystemExit(1)

        snapshot_id = None
        if store_snapshot:
            from naturo.snapshot import get_snapshot_manager
            mgr = get_snapshot_manager(session=session)
            snapshot_id = mgr.create_snapshot()
            metadata = {
                "window_handle": hwnd,
                "application_name": app,
                "window_title": window_title,
            }
            mgr.store_screenshot(snapshot_id, result.path, metadata)

        if json_output:
            out: dict = {
                "success": True,
                "path": result.path,
                "width": result.width,
                "height": result.height,
                "format": result.format,
                "scale_factor": result.scale_factor,
                "dpi": result.dpi,
            }
            if crop_box is not None:
                out["cropped"] = True
                out["crop_source"] = "element" if element_ref else "region"
            if snapshot_id:
                out["snapshot_id"] = snapshot_id
            click.echo(json_dumps(out))
        else:
            import os
            full_path = os.path.abspath(result.path)
            crop_note = ""
            if element_ref:
                crop_note = f" [cropped to {element_ref}]"
            elif region:
                crop_note = f" [cropped to {region}]"
            click.echo(f"Saved: {full_path} ({result.width}x{result.height}){crop_note}")
    except _common.WindowNotFoundError as e:
        if json_output:
            click.echo(_common._json_error_str("WINDOW_NOT_FOUND", str(e)))
        else:
            click.echo(f"Error: {e}", err=True)
        raise SystemExit(1)
    except Exception as e:
        if json_output:
            click.echo(_common._json_error_str("CAPTURE_ERROR", str(e)))
        else:
            click.echo(f"Error: {e}", err=True)
        raise SystemExit(1)
