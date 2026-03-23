"""Tests for _check_desktop_session SSH-into-RDP detection (fixes #113, #183).

Verifies that the desktop session check correctly distinguishes between:
- Console/RDP sessions (interactive desktop — OK)
- SSH sessions to a machine with active RDP (no desktop access — error)
- Pure headless/service sessions (no desktop — error)
- Task Scheduler /it sessions with no SESSIONNAME but active desktop (OK)
"""

import pytest
from unittest.mock import patch, MagicMock
import subprocess


# Import conditionally — the function only does work on Windows but
# we test the logic by mocking platform.system().
from naturo.cli.interaction import (
    _check_desktop_session,
    _is_current_session_interactive,
)
from naturo.errors import NoDesktopSessionError

# Shorthand for patching the WTS interactive check used when SESSIONNAME is empty.
_PATCH_WTS = "naturo.cli.interaction._is_current_session_interactive"


class TestCheckDesktopSession:
    """Tests for the desktop session detection logic."""

    def test_non_windows_always_passes(self):
        """Non-Windows platforms skip the check entirely."""
        with patch("platform.system", return_value="Darwin"):
            _check_desktop_session()  # Should not raise

    def test_console_session_passes(self):
        """SESSIONNAME=Console indicates physical desktop — should pass."""
        with patch("platform.system", return_value="Windows"), \
             patch.dict("os.environ", {"SESSIONNAME": "Console"}):
            _check_desktop_session()  # Should not raise

    def test_rdp_session_passes(self):
        """SESSIONNAME starting with RDP-Tcp indicates RDP desktop — should pass."""
        with patch("platform.system", return_value="Windows"), \
             patch.dict("os.environ", {"SESSIONNAME": "RDP-Tcp#0"}):
            _check_desktop_session()  # Should not raise

    def test_services_session_raises(self):
        """SESSIONNAME=Services indicates a service session — should raise."""
        with patch("platform.system", return_value="Windows"), \
             patch.dict("os.environ", {"SESSIONNAME": "Services"}):
            with pytest.raises(NoDesktopSessionError):
                _check_desktop_session()

    def test_empty_sessionname_no_explorer_raises(self):
        """Empty SESSIONNAME + WTS non-interactive + no explorer = headless."""
        mock_result = MagicMock()
        mock_result.stdout = "INFO: No tasks are running which match the specified criteria."
        with patch("platform.system", return_value="Windows"), \
             patch.dict("os.environ", {"SESSIONNAME": ""}, clear=False), \
             patch(_PATCH_WTS, return_value=False), \
             patch("subprocess.run", return_value=mock_result):
            with pytest.raises(NoDesktopSessionError):
                _check_desktop_session()

    def test_empty_sessionname_with_explorer_raises_ssh_error(self):
        """Empty SESSIONNAME + WTS non-interactive + explorer = SSH scenario.

        This is the key scenario from #113: SSH session cannot interact
        with the desktop even though explorer.exe is running.
        """
        mock_result = MagicMock()
        mock_result.stdout = '"explorer.exe","27552","Console","1","294,880 K"'
        with patch("platform.system", return_value="Windows"), \
             patch.dict("os.environ", {"SESSIONNAME": ""}, clear=False), \
             patch(_PATCH_WTS, return_value=False), \
             patch("subprocess.run", return_value=mock_result):
            with pytest.raises(NoDesktopSessionError) as exc_info:
                _check_desktop_session()
            # Verify the error message mentions SSH scenario
            assert "SSH" in str(exc_info.value) or "ssh" in str(exc_info.value).lower()

    def test_unset_sessionname_with_explorer_raises(self):
        """Completely unset SESSIONNAME + WTS non-interactive + explorer = SSH."""
        mock_result = MagicMock()
        mock_result.stdout = '"explorer.exe","1234","Console","1","100,000 K"'
        env = {"PATH": "/usr/bin"}  # SESSIONNAME not present
        with patch("platform.system", return_value="Windows"), \
             patch.dict("os.environ", env, clear=True), \
             patch(_PATCH_WTS, return_value=False), \
             patch("subprocess.run", return_value=mock_result):
            with pytest.raises(NoDesktopSessionError):
                _check_desktop_session()

    def test_unknown_session_type_passes(self):
        """Unknown SESSIONNAME values (Citrix, VNC, etc.) should pass through."""
        with patch("platform.system", return_value="Windows"), \
             patch.dict("os.environ", {"SESSIONNAME": "ICA-tcp#7"}):
            _check_desktop_session()  # Should not raise

    def test_tasklist_failure_still_raises(self):
        """If tasklist and WTS both fail, empty SESSIONNAME should still raise."""
        with patch("platform.system", return_value="Windows"), \
             patch.dict("os.environ", {"SESSIONNAME": ""}, clear=False), \
             patch(_PATCH_WTS, return_value=False), \
             patch("subprocess.run", side_effect=subprocess.TimeoutExpired("tasklist", 5)):
            with pytest.raises(NoDesktopSessionError):
                _check_desktop_session()

    def test_schtasks_interactive_session_passes(self):
        """Empty SESSIONNAME but WTS confirms active desktop session — schtasks /it.

        This is the key scenario from #183: Task Scheduler /it tasks run
        in the interactive session but do NOT set SESSIONNAME.  The WTS
        check should detect the active session and allow through.
        """
        with patch("platform.system", return_value="Windows"), \
             patch.dict("os.environ", {"SESSIONNAME": ""}, clear=False), \
             patch(_PATCH_WTS, return_value=True):
            _check_desktop_session()  # Should not raise

    def test_unset_sessionname_wts_interactive_passes(self):
        """Completely unset SESSIONNAME but WTS interactive — should pass."""
        env = {"PATH": "/usr/bin"}
        with patch("platform.system", return_value="Windows"), \
             patch.dict("os.environ", env, clear=True), \
             patch(_PATCH_WTS, return_value=True):
            _check_desktop_session()  # Should not raise


class TestIsCurrentSessionInteractive:
    """Tests for the WTS-based interactive session detection."""

    def test_non_windows_returns_false(self):
        """On non-Windows (no ctypes.windll), should safely return False."""
        # _is_current_session_interactive uses ctypes.windll which only
        # exists on Windows.  On macOS/Linux it raises AttributeError
        # which the function catches and returns False.
        import platform
        if platform.system() == "Windows":
            pytest.skip("This test validates non-Windows fallback behavior")
        result = _is_current_session_interactive()
        assert result is False

    @pytest.mark.skipif(
        __import__("platform").system() != "Windows",
        reason="WTS API only available on Windows",
    )
    def test_returns_bool(self):
        """On Windows, the function should return a boolean."""
        result = _is_current_session_interactive()
        assert isinstance(result, bool)
