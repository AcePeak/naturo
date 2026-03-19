"""Test backend abstraction layer."""
import platform
import pytest
from naturo.backends.base import Backend, get_backend, WindowInfo, ElementInfo, CaptureResult


def test_window_info_dataclass():
    w = WindowInfo(handle=12345, title="Test", process_name="test.exe",
                   pid=1234, x=0, y=0, width=800, height=600,
                   is_visible=True, is_minimized=False)
    assert w.title == "Test"
    assert w.handle == 12345


def test_element_info_dataclass():
    e = ElementInfo(id="E1", role="Button", name="OK", value=None,
                    x=100, y=200, width=80, height=30, children=[], properties={})
    assert e.role == "Button"


def test_capture_result_dataclass():
    c = CaptureResult(path="/tmp/test.png", width=1920, height=1080, format="png")
    assert c.width == 1920


def test_get_backend_returns_correct_platform():
    backend = get_backend()
    system = platform.system().lower()
    if system == "windows":
        assert backend.platform_name == "windows"
    elif system == "darwin":
        assert backend.platform_name == "macos"
    elif system == "linux":
        assert backend.platform_name == "linux"


def test_backend_has_capabilities():
    backend = get_backend()
    caps = backend.capabilities
    assert "platform" in caps
    assert "input_modes" in caps
    assert "accessibility" in caps
    assert "extensions" in caps


def test_backend_methods_not_implemented():
    """Phase 2+ methods should still raise NotImplementedError."""
    backend = get_backend()
    with pytest.raises(NotImplementedError):
        backend.click()
    with pytest.raises(NotImplementedError):
        backend.type_text("hello")
    with pytest.raises(NotImplementedError):
        backend.press_key("enter")


def test_windows_backend_capabilities():
    """Windows backend should advertise advanced input modes."""
    if platform.system() != "Windows":
        pytest.skip("Windows only")
    from naturo.backends.windows import WindowsBackend
    b = WindowsBackend()
    assert "hardware" in b.capabilities["input_modes"]
    assert "hook" in b.capabilities["input_modes"]
    assert "uia" in b.capabilities["accessibility"]
    assert "excel" in b.capabilities["extensions"]


def test_macos_backend_capabilities():
    if platform.system() != "Darwin":
        pytest.skip("macOS only")
    from naturo.backends.macos import MacOSBackend
    b = MacOSBackend()
    assert b.platform_name == "macos"
    assert "ax" in b.capabilities["accessibility"]


def test_linux_backend_display_server():
    if platform.system() != "Linux":
        pytest.skip("Linux only")
    from naturo.backends.linux import LinuxBackend
    b = LinuxBackend()
    assert b.capabilities["display_server"] in ("x11", "wayland", "headless")
