"""Tests for naturo/detect/probes.py — framework detection and probe logic.

All tests mock _get_process_dlls so no Windows APIs are required.
"""
from __future__ import annotations

from unittest.mock import patch

import pytest

from naturo.detect.models import (
    FrameworkType,
    InteractionMethodType,
    ProbeStatus,
)
from naturo.detect import probes


# ── DLL signature set invariants ────────────────────────────────────────────

class TestDLLSignatureSets:
    """Verify that DLL signature sets are well-formed."""

    @pytest.mark.parametrize("name,dlls", [
        ("ELECTRON", probes._ELECTRON_DLLS),
        ("CEF", probes._CEF_DLLS),
        ("CHROME", probes._CHROME_DLLS),
        ("WPF", probes._WPF_DLLS),
        ("WINFORMS", probes._WINFORMS_DLLS),
        ("QT", probes._QT_DLLS),
        ("JAVA", probes._JAVA_DLLS),
        ("JAB", probes._JAB_DLLS),
        ("GTK", probes._GTK_DLLS),
        ("UWP", probes._UWP_DLLS),
    ])
    def test_dll_sets_non_empty(self, name, dlls):
        assert len(dlls) > 0, f"{name} DLL set is empty"

    @pytest.mark.parametrize("name,dlls", [
        ("ELECTRON", probes._ELECTRON_DLLS),
        ("CEF", probes._CEF_DLLS),
        ("CHROME", probes._CHROME_DLLS),
        ("WPF", probes._WPF_DLLS),
        ("WINFORMS", probes._WINFORMS_DLLS),
        ("QT", probes._QT_DLLS),
        ("JAVA", probes._JAVA_DLLS),
        ("JAB", probes._JAB_DLLS),
        ("GTK", probes._GTK_DLLS),
        ("UWP", probes._UWP_DLLS),
    ])
    def test_dll_names_lowercase(self, name, dlls):
        for dll in dlls:
            assert dll == dll.lower(), f"{name}: {dll} is not lowercase"

    def test_uwp_exes_lowercase(self):
        for exe in probes._UWP_EXES:
            assert exe == exe.lower()

    def test_uwp_known_apps_lowercase(self):
        for app in probes._UWP_KNOWN_APPS:
            assert app == app.lower()


# ── detect_frameworks_from_dlls — exe-name heuristics (no DLLs) ─────────────

class TestDetectFrameworksExeHeuristics:
    """When _get_process_dlls returns empty (non-Windows), exe name is used."""

    @patch.object(probes, "_get_process_dlls", return_value=set())
    def test_electron_exe(self, _mock):
        result = probes.detect_frameworks_from_dlls(1234, "C:\\Apps\\electron.exe")
        assert len(result) == 1
        assert result[0].framework_type == FrameworkType.ELECTRON

    @patch.object(probes, "_get_process_dlls", return_value=set())
    def test_chrome_exe(self, _mock):
        result = probes.detect_frameworks_from_dlls(1234, "C:\\Chrome\\chrome.exe")
        assert result[0].framework_type == FrameworkType.CHROME

    @patch.object(probes, "_get_process_dlls", return_value=set())
    def test_chromium_exe(self, _mock):
        result = probes.detect_frameworks_from_dlls(1234, "/usr/bin/chromium-browser")
        assert result[0].framework_type == FrameworkType.CHROME

    @patch.object(probes, "_get_process_dlls", return_value=set())
    def test_java_exe(self, _mock):
        result = probes.detect_frameworks_from_dlls(1234, "C:\\Java\\bin\\java.exe")
        assert result[0].framework_type == FrameworkType.JAVA_SWING

    @patch.object(probes, "_get_process_dlls", return_value=set())
    def test_javaw_exe(self, _mock):
        result = probes.detect_frameworks_from_dlls(1234, "C:\\Java\\bin\\javaw.exe")
        assert result[0].framework_type == FrameworkType.JAVA_SWING

    @patch.object(probes, "_get_process_dlls", return_value=set())
    def test_uwp_known_app(self, _mock):
        result = probes.detect_frameworks_from_dlls(1234, "C:\\WindowsApps\\Calculator.exe")
        assert result[0].framework_type == FrameworkType.UWP

    @patch.object(probes, "_get_process_dlls", return_value=set())
    def test_uwp_afh_exe(self, _mock):
        result = probes.detect_frameworks_from_dlls(1234, "ApplicationFrameHost.exe")
        assert result[0].framework_type == FrameworkType.UWP

    @patch.object(probes, "_get_process_dlls", return_value=set())
    def test_uwp_windowsapps_path(self, _mock):
        result = probes.detect_frameworks_from_dlls(
            1234, "C:\\Program Files\\WindowsApps\\SomeApp.exe"
        )
        assert result[0].framework_type == FrameworkType.UWP

    @patch.object(probes, "_get_process_dlls", return_value=set())
    def test_unknown_exe_non_windows(self, _mock):
        """Unknown exe on non-Windows returns UNKNOWN framework."""
        with patch.object(probes.platform, "system", return_value="Linux"):
            result = probes.detect_frameworks_from_dlls(1234, "someapp")
        assert result[0].framework_type == FrameworkType.UNKNOWN

    @patch.object(probes, "_get_process_dlls", return_value=set())
    def test_unknown_exe_windows(self, _mock):
        """Unknown exe on Windows returns WIN32 framework."""
        with patch.object(probes.platform, "system", return_value="Windows"):
            result = probes.detect_frameworks_from_dlls(1234, "someapp.exe")
        assert result[0].framework_type == FrameworkType.WIN32


# ── detect_frameworks_from_dlls — DLL-based detection ────────────────────────

class TestDetectFrameworksDLLBased:
    """When _get_process_dlls returns actual DLL names."""

    @patch.object(probes, "_get_process_dlls")
    def test_electron_from_dlls(self, mock_dlls):
        mock_dlls.return_value = {"electron.exe", "libcef.dll", "chrome_elf.dll", "node.dll"}
        result = probes.detect_frameworks_from_dlls(1234, "slack.exe")
        types = {f.framework_type for f in result}
        assert FrameworkType.ELECTRON in types

    @patch.object(probes, "_get_process_dlls")
    def test_cef_with_chrome_dll(self, mock_dlls):
        """libcef.dll + chrome.dll = Chrome, not Electron or CEF."""
        mock_dlls.return_value = {"libcef.dll", "chrome.dll"}
        result = probes.detect_frameworks_from_dlls(1234, "someapp.exe")
        types = {f.framework_type for f in result}
        assert FrameworkType.CHROME in types
        # libcef.dll alone triggers Electron detection (it's in _ELECTRON_DLLS)
        # but with chrome.dll present, CEF check is skipped
        assert FrameworkType.CEF not in types

    @patch.object(probes, "_get_process_dlls")
    def test_chrome_browser_from_dll(self, mock_dlls):
        mock_dlls.return_value = {"chrome.dll", "chrome_elf.dll"}
        result = probes.detect_frameworks_from_dlls(1234, "chrome.exe")
        types = {f.framework_type for f in result}
        assert FrameworkType.CHROME in types

    @patch.object(probes, "_get_process_dlls")
    def test_wpf_from_dlls(self, mock_dlls):
        mock_dlls.return_value = {"presentationframework.dll", "presentationcore.dll"}
        result = probes.detect_frameworks_from_dlls(1234, "myapp.exe")
        types = {f.framework_type for f in result}
        assert FrameworkType.WPF in types

    @patch.object(probes, "_get_process_dlls")
    def test_winforms_from_dlls(self, mock_dlls):
        mock_dlls.return_value = {"system.windows.forms.dll", "mscorlib.dll"}
        result = probes.detect_frameworks_from_dlls(1234, "myapp.exe")
        types = {f.framework_type for f in result}
        assert FrameworkType.WINFORMS in types

    @patch.object(probes, "_get_process_dlls")
    def test_qt5_from_dlls(self, mock_dlls):
        mock_dlls.return_value = {"qt5core.dll", "qt5widgets.dll"}
        result = probes.detect_frameworks_from_dlls(1234, "creator.exe")
        types = {f.framework_type for f in result}
        assert FrameworkType.QT in types
        qt_fw = [f for f in result if f.framework_type == FrameworkType.QT][0]
        assert "5" in qt_fw.version

    @patch.object(probes, "_get_process_dlls")
    def test_qt6_from_dlls(self, mock_dlls):
        mock_dlls.return_value = {"qt6core.dll"}
        result = probes.detect_frameworks_from_dlls(1234, "app.exe")
        qt_fw = [f for f in result if f.framework_type == FrameworkType.QT][0]
        assert "6" in qt_fw.version

    @patch.object(probes, "_get_process_dlls")
    def test_java_from_dlls(self, mock_dlls):
        mock_dlls.return_value = {"jvm.dll", "java.dll"}
        result = probes.detect_frameworks_from_dlls(1234, "idea.exe")
        types = {f.framework_type for f in result}
        assert FrameworkType.JAVA_SWING in types

    @patch.object(probes, "_get_process_dlls")
    def test_gtk_from_dlls(self, mock_dlls):
        mock_dlls.return_value = {"libgtk-3-0.dll", "libglib.dll"}
        result = probes.detect_frameworks_from_dlls(1234, "gimp.exe")
        types = {f.framework_type for f in result}
        assert FrameworkType.GTK in types

    @patch.object(probes, "_get_process_dlls")
    def test_uwp_from_dlls(self, mock_dlls):
        mock_dlls.return_value = {"windows.ui.xaml.dll", "combase.dll"}
        result = probes.detect_frameworks_from_dlls(1234, "calculator.exe")
        types = {f.framework_type for f in result}
        assert FrameworkType.UWP in types

    @patch.object(probes, "_get_process_dlls")
    def test_winui3_from_dlls(self, mock_dlls):
        mock_dlls.return_value = {"microsoft.ui.xaml.dll", "vcruntime140.dll"}
        result = probes.detect_frameworks_from_dlls(1234, "notepad.exe")
        types = {f.framework_type for f in result}
        assert FrameworkType.UWP in types

    @patch.object(probes, "_get_process_dlls")
    def test_win32_fallback(self, mock_dlls):
        """Unknown DLLs on Windows fall back to WIN32."""
        mock_dlls.return_value = {"kernel32.dll", "user32.dll", "mylib.dll"}
        with patch.object(probes.platform, "system", return_value="Windows"):
            result = probes.detect_frameworks_from_dlls(1234, "app.exe")
        assert result[0].framework_type == FrameworkType.WIN32

    @patch.object(probes, "_get_process_dlls")
    def test_multiple_frameworks_detected(self, mock_dlls):
        """A process can match multiple frameworks (e.g. WPF + UWP)."""
        mock_dlls.return_value = {
            "presentationframework.dll", "windows.ui.xaml.dll",
        }
        result = probes.detect_frameworks_from_dlls(1234, "hybrid.exe")
        types = {f.framework_type for f in result}
        assert FrameworkType.WPF in types
        assert FrameworkType.UWP in types

    @patch.object(probes, "_get_process_dlls")
    def test_dll_signatures_are_sorted(self, mock_dlls):
        """Detected DLL signatures should be sorted alphabetically."""
        mock_dlls.return_value = {"presentationcore.dll", "presentationframework.dll", "wpfgfx_v0400.dll"}
        result = probes.detect_frameworks_from_dlls(1234, "app.exe")
        wpf = [f for f in result if f.framework_type == FrameworkType.WPF][0]
        assert wpf.dll_signatures == sorted(wpf.dll_signatures)


# ── probe_ia2 ────────────────────────────────────────────────────────────────

class TestProbeIA2:
    """IA2 probe uses exe-name heuristic only."""

    def test_firefox_detected(self):
        with patch.object(probes.platform, "system", return_value="Windows"):
            # Use forward slashes — os.path.basename works on both platforms
            result = probes.probe_ia2(1234, "C:/Firefox/firefox.exe")
        assert result is not None
        assert result.method == InteractionMethodType.IA2
        assert result.status == ProbeStatus.AVAILABLE

    def test_thunderbird_detected(self):
        with patch.object(probes.platform, "system", return_value="Windows"):
            result = probes.probe_ia2(1234, "C:/Thunderbird/thunderbird.exe")
        assert result is not None
        assert result.method == InteractionMethodType.IA2

    def test_libreoffice_detected(self):
        with patch.object(probes.platform, "system", return_value="Windows"):
            result = probes.probe_ia2(1234, "/usr/lib/libreoffice/soffice.exe")
        assert result is not None
        assert result.method == InteractionMethodType.IA2

    def test_soffice_bin_detected(self):
        with patch.object(probes.platform, "system", return_value="Windows"):
            result = probes.probe_ia2(1234, "/usr/lib/libreoffice/soffice.bin")
        assert result is not None
        assert result.method == InteractionMethodType.IA2

    def test_non_ia2_app_returns_none(self):
        with patch.object(probes.platform, "system", return_value="Windows"):
            result = probes.probe_ia2(1234, "notepad.exe")
        assert result is None

    def test_non_windows_returns_none(self):
        with patch.object(probes.platform, "system", return_value="Linux"):
            result = probes.probe_ia2(1234, "firefox.exe")
        assert result is None


# ── probe_vision ─────────────────────────────────────────────────────────────

class TestProbeVision:
    """Vision probe is always available."""

    def test_always_returns_method(self):
        result = probes.probe_vision(1234, "anything.exe")
        assert result is not None
        assert result.method == InteractionMethodType.VISION
        assert result.status == ProbeStatus.FALLBACK
        assert result.confidence == 0.5

    def test_has_click_capability(self):
        result = probes.probe_vision(1234, "app.exe")
        assert "click" in result.capabilities

    def test_has_screenshot_capability(self):
        result = probes.probe_vision(1234, "app.exe")
        assert "screenshot" in result.capabilities

    def test_works_on_any_platform(self):
        """Vision probe has no platform gate."""
        with patch.object(probes.platform, "system", return_value="Linux"):
            result = probes.probe_vision(1234, "app")
        assert result is not None
        assert result.method == InteractionMethodType.VISION


# ── probe_jab ────────────────────────────────────────────────────────────────

class TestProbeJAB:
    """JAB probe requires Java DLLs."""

    @patch.object(probes, "_get_process_dlls")
    def test_java_with_jab_available(self, mock_dlls):
        mock_dlls.return_value = {"jvm.dll", "windowsaccessbridge-64.dll"}
        with patch.object(probes.platform, "system", return_value="Windows"):
            result = probes.probe_jab(1234, "idea.exe")
        assert result is not None
        assert result.method == InteractionMethodType.JAB
        assert result.status == ProbeStatus.AVAILABLE

    @patch.object(probes, "_get_process_dlls")
    def test_java_without_jab(self, mock_dlls):
        mock_dlls.return_value = {"jvm.dll", "java.dll"}
        with patch.object(probes.platform, "system", return_value="Windows"):
            result = probes.probe_jab(1234, "myapp.exe")
        assert result is not None
        assert result.method == InteractionMethodType.JAB
        assert result.status == ProbeStatus.UNAVAILABLE
        assert "jabswitch" in result.metadata.get("note", "")

    @patch.object(probes, "_get_process_dlls")
    def test_non_java_app(self, mock_dlls):
        mock_dlls.return_value = {"user32.dll", "kernel32.dll"}
        with patch.object(probes.platform, "system", return_value="Windows"):
            result = probes.probe_jab(1234, "notepad.exe")
        assert result is None

    def test_non_windows_returns_none(self):
        with patch.object(probes.platform, "system", return_value="Linux"):
            result = probes.probe_jab(1234, "idea")
        assert result is None


# ── probe_cdp / probe_uia / probe_msaa — platform-gated ─────────────────────

class TestPlatformGatedProbes:
    """CDP, UIA, and MSAA probes return None on non-Windows."""

    def test_cdp_non_windows(self):
        with patch.object(probes.platform, "system", return_value="Linux"):
            assert probes.probe_cdp(1234, "chrome.exe") is None

    def test_uia_non_windows(self):
        with patch.object(probes.platform, "system", return_value="Linux"):
            assert probes.probe_uia(1234, "notepad.exe") is None

    def test_msaa_non_windows(self):
        with patch.object(probes.platform, "system", return_value="Linux"):
            assert probes.probe_msaa(1234, "notepad.exe") is None


# ── _get_process_dlls — non-Windows returns empty ───────────────────────────

class TestGetProcessDLLs:
    """_get_process_dlls returns empty set on non-Windows."""

    def test_returns_empty_on_linux(self):
        with patch.object(probes.platform, "system", return_value="Linux"):
            assert probes._get_process_dlls(1234) == set()


# ── _find_main_window / _find_window_by_process_name — non-Windows ──────────

class TestHelperFunctionsNonWindows:

    def test_find_main_window_non_windows(self):
        with patch.object(probes.platform, "system", return_value="Linux"):
            assert probes._find_main_window(1234) is None

    def test_find_window_by_process_name_non_windows(self):
        with patch.object(probes.platform, "system", return_value="Linux"):
            assert probes._find_window_by_process_name(1234, "app.exe") is None

    def test_find_afh_content_children_non_windows(self):
        with patch.object(probes.platform, "system", return_value="Linux"):
            assert probes._find_afh_content_children(12345) == []
