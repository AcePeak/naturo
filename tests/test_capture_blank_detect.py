"""Blank-frame detection for the GPU-window capture fallback.

PrintWindow (the native window capture) fails destructively on GPU-composited
windows (Chromium/Electron, DirectComposition skins): it returns a flat blank
frame *and* blanks the live window until it repaints. capture_window detects the
blank result and re-captures non-destructively from the screen. This tests the
pure detector (`_image_is_blank`) — no Windows/DLL needed.
"""
from __future__ import annotations

import tempfile
import os
from unittest.mock import MagicMock

from PIL import Image

from naturo.backends.windows._capture import CaptureMixin


def _save(img: Image.Image) -> str:
    fd, path = tempfile.mkstemp(suffix=".png")
    os.close(fd)
    img.save(path, "PNG")
    return path


def test_uniform_white_is_blank():
    path = _save(Image.new("RGB", (400, 300), (255, 255, 255)))
    try:
        assert CaptureMixin._image_is_blank(path) is True
    finally:
        os.remove(path)


def test_uniform_black_is_blank():
    path = _save(Image.new("RGB", (400, 300), (0, 0, 0)))
    try:
        assert CaptureMixin._image_is_blank(path) is True
    finally:
        os.remove(path)


def test_near_uniform_within_tolerance_is_blank():
    # A couple of stray off-by-few pixels must not defeat blank detection.
    img = Image.new("RGB", (400, 300), (255, 255, 255))
    img.putpixel((0, 0), (252, 253, 251))
    path = _save(img)
    try:
        assert CaptureMixin._image_is_blank(path) is True
    finally:
        os.remove(path)


def test_real_content_is_not_blank():
    # Two clearly different regions -> real content, must NOT be flagged blank.
    img = Image.new("RGB", (400, 300), (255, 255, 255))
    for y in range(150):
        for x in range(400):
            img.putpixel((x, y), (10, 40, 200))  # a solid blue band
    path = _save(img)
    try:
        assert CaptureMixin._image_is_blank(path) is False
    finally:
        os.remove(path)


def test_gradient_is_not_blank():
    img = Image.new("RGB", (256, 64))
    for x in range(256):
        for y in range(64):
            img.putpixel((x, y), (x, x, x))
    path = _save(img)
    try:
        assert CaptureMixin._image_is_blank(path) is False
    finally:
        os.remove(path)


# ── WGC ultimate-fallback dispatch ──────────────────────────────────────────
# When PrintWindow AND the screen-region heal both come back blank (a GPU/
# DirectComposition surface GDI cannot read), capture_window must fall back to
# WGC (Windows.Graphics.Capture). Pure dispatch test — all Windows/DLL calls mocked.


def _capture_backend(**attrs) -> MagicMock:
    obj = MagicMock()
    core = MagicMock()
    obj._ensure_core.return_value = core
    obj._core = core
    for k, v in attrs.items():
        setattr(obj, k, v)
    return obj


def test_wgc_fires_when_all_gdi_paths_blank():
    obj = _capture_backend()
    obj._window_is_unoccluded_onscreen.return_value = False  # skip visibility-first
    obj._window_is_minimized.return_value = False
    obj._image_is_blank.return_value = True                  # PrintWindow + heal both blank
    obj._capture_window_via_screen.return_value = (100, 200, "png")
    obj._convert_bmp.return_value = (100, 200, "png")

    CaptureMixin.capture_window(obj, hwnd=1234, output_path="out.png",
                               raise_if_occluded=False)

    obj._ensure_core.return_value.capture_window.assert_called()       # PrintWindow tried
    obj._ensure_core.return_value.capture_window_wgc.assert_called_once()  # WGC rescue fired


def test_wgc_not_used_when_capture_is_not_blank():
    obj = _capture_backend()
    obj._window_is_unoccluded_onscreen.return_value = True   # visibility-first succeeds
    obj._capture_window_via_screen.return_value = (100, 200, "png")

    CaptureMixin.capture_window(obj, hwnd=1234, output_path="out.png")

    obj._ensure_core.return_value.capture_window_wgc.assert_not_called()
