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
