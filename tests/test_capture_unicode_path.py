"""Unit tests for the bridge-level Unicode output-path guard (#777).

The bundled ``naturo_core`` native library writes BMP files. Older builds use
narrow-string file I/O that cannot open paths containing non-ASCII characters
(for example a Chinese Windows username in ``%TEMP%``), returning a
``File I/O error``. ``NaturoCore`` guards against this by routing non-ASCII
output paths through an ASCII-only temporary file and then moving the result to
the requested destination.

These tests exercise that routing logic directly with a fake native call, so
they require neither the native library nor a real display and run on every
platform.
"""

from __future__ import annotations

import os

import pytest

from naturo.bridge._core import NaturoCore
from naturo.bridge._errors import NaturoCoreError


def _make_core() -> NaturoCore:
    """Build a NaturoCore without loading the native library.

    ``_capture_to_path`` does not touch ``self._lib``, so bypassing
    ``__init__`` lets the routing logic be tested without the DLL present.
    """
    return object.__new__(NaturoCore)


def test_ascii_path_passes_straight_to_native(tmp_path):
    """An ASCII path is handed to the native call unchanged (no staging)."""
    core = _make_core()
    dest = str(tmp_path / "shot.bmp")
    calls = []

    def fake_native(path_bytes: bytes) -> int:
        calls.append(path_bytes)
        with open(path_bytes.decode("utf-8"), "wb") as handle:
            handle.write(b"BMP")
        return 0

    result = core._capture_to_path(fake_native, dest, "capture_screen")

    assert result == dest
    assert calls == [dest.encode("utf-8")]
    assert os.path.exists(dest)


def test_unicode_path_routes_through_ascii_temp(tmp_path):
    """A non-ASCII path is captured to an ASCII temp file, then moved."""
    core = _make_core()
    unicode_dir = tmp_path / "naturo_测试_中文"
    unicode_dir.mkdir()
    dest = str(unicode_dir / "截图.bmp")
    seen = []

    def fake_native(path_bytes: bytes) -> int:
        path = path_bytes.decode("utf-8")
        seen.append(path)
        with open(path, "wb") as handle:
            handle.write(b"PIXELDATA")
        return 0

    result = core._capture_to_path(fake_native, dest, "capture_screen")

    assert result == dest
    # The native layer only ever saw an ASCII-only staging path.
    assert len(seen) == 1
    assert seen[0].isascii()
    assert seen[0] != dest
    # The captured bytes ended up at the requested Unicode destination.
    assert os.path.exists(dest)
    with open(dest, "rb") as handle:
        assert handle.read() == b"PIXELDATA"
    # The staging file was cleaned up.
    assert not os.path.exists(seen[0])


def test_unicode_path_overwrites_existing_destination(tmp_path):
    """Re-capturing to an existing Unicode path overwrites it (no error)."""
    core = _make_core()
    unicode_dir = tmp_path / "中文_目录"
    unicode_dir.mkdir()
    dest = str(unicode_dir / "截图.bmp")
    with open(dest, "wb") as handle:
        handle.write(b"OLD")

    def fake_native(path_bytes: bytes) -> int:
        with open(path_bytes.decode("utf-8"), "wb") as handle:
            handle.write(b"NEW")
        return 0

    core._capture_to_path(fake_native, dest, "capture_screen")

    with open(dest, "rb") as handle:
        assert handle.read() == b"NEW"


def test_native_error_on_ascii_path_raises(tmp_path):
    """A non-zero native status on an ASCII path raises NaturoCoreError."""
    core = _make_core()
    dest = str(tmp_path / "shot.bmp")

    with pytest.raises(NaturoCoreError):
        core._capture_to_path(lambda _: -3, dest, "capture_screen")


def test_native_error_on_unicode_path_raises_and_cleans_up(tmp_path):
    """A native failure on a Unicode path raises and leaves no staging file."""
    core = _make_core()
    dest = str(tmp_path / "中文.bmp")
    seen = []

    def fake_native(path_bytes: bytes) -> int:
        seen.append(path_bytes.decode("utf-8"))
        return -3

    with pytest.raises(NaturoCoreError):
        core._capture_to_path(fake_native, dest, "capture_screen")

    assert not os.path.exists(dest)
    assert seen and not os.path.exists(seen[0])


def test_none_path_raises():
    """A None output path raises NaturoCoreError without invoking native."""
    core = _make_core()

    with pytest.raises(NaturoCoreError):
        core._capture_to_path(lambda _: 0, None, "capture_screen")
