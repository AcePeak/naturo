"""Tests for naturo.backends.linux — LinuxBackend stub."""
from __future__ import annotations

from unittest.mock import patch

import pytest

from naturo.backends.linux import LinuxBackend


@pytest.fixture
def backend():
    return LinuxBackend()


class TestLinuxBackendProperties:
    """Tests for LinuxBackend properties and display server detection."""

    def test_platform_name(self, backend):
        assert backend.platform_name == "linux"

    def test_capabilities_structure(self, backend):
        caps = backend.capabilities
        assert caps["platform"] == "linux"
        assert caps["input_modes"] == ["normal"]
        assert caps["accessibility"] == ["atspi"]
        assert isinstance(caps["extensions"], list)
        assert "display_server" in caps

    @patch.dict("os.environ", {"WAYLAND_DISPLAY": "wayland-0"}, clear=False)
    def test_detect_wayland(self, backend):
        assert backend._detect_display_server() == "wayland"

    @patch.dict("os.environ", {"DISPLAY": ":0"}, clear=False)
    def test_detect_x11(self):
        import os
        # Ensure WAYLAND_DISPLAY is not set for this test
        env = os.environ.copy()
        env.pop("WAYLAND_DISPLAY", None)
        with patch.dict("os.environ", env, clear=True):
            b = LinuxBackend()
            assert b._detect_display_server() == "x11"

    @patch.dict("os.environ", {}, clear=True)
    def test_detect_headless(self):
        b = LinuxBackend()
        assert b._detect_display_server() == "headless"


class TestLinuxBackendNotImplemented:
    """All automation methods must raise NotImplementedError."""

    _METHODS_WITH_ARGS = [
        ("list_monitors", []),
        ("capture_screen", []),
        ("capture_window", []),
        ("list_windows", []),
        ("focus_window", []),
        ("close_window", []),
        ("minimize_window", []),
        ("maximize_window", []),
        ("move_window", []),
        ("resize_window", []),
        ("set_bounds", []),
        ("restore_window", []),
        ("find_element", []),
        ("get_element_tree", []),
        ("click", []),
        ("type_text", []),
        ("press_key", []),
        ("hotkey", []),
        ("scroll", []),
        ("drag", []),
        ("move_mouse", []),
        ("clipboard_get", []),
        ("clipboard_set", []),
        ("clipboard_clear", []),
        ("list_apps", []),
        ("launch_app", []),
        ("quit_app", []),
        ("open_uri", []),
        ("get_element_value", []),
    ]

    @pytest.mark.parametrize("method_name,args", _METHODS_WITH_ARGS, ids=[m[0] for m in _METHODS_WITH_ARGS])
    def test_method_raises_not_implemented(self, backend, method_name, args):
        method = getattr(backend, method_name)
        with pytest.raises(NotImplementedError, match="Linux desktop automation is not yet supported"):
            method(*args)
