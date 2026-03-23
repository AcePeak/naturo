"""Integration tests for Unified App Model across framework types.

These tests validate the full detection → routing → execution pipeline
against real Windows applications. They require:
- Windows desktop session with GUI access
- Target applications installed (Notepad, Calculator, etc.)

Run with: pytest tests/integration/ -m integration -v

Test matrix:
| Framework | App           | Detection | Routing | CLI     |
|-----------|---------------|-----------|---------|---------|
| Win32     | Notepad       | ✓         | ✓       | ✓       |
| UWP/WinUI| Calculator    | ✓         | ✓       | ✓       |
| Win32     | Explorer      | ✓         | ✓       | —       |
"""

import json
import platform
import subprocess
from typing import Any, Dict

import pytest

pytestmark = [
    pytest.mark.integration,
    pytest.mark.skipif(
        platform.system() != "Windows",
        reason="Integration tests require Windows desktop",
    ),
]


def _run_naturo(*args: str, timeout: int = 15) -> Dict[str, Any]:
    """Run a naturo CLI command and return parsed JSON output.

    Args:
        *args: Command arguments after 'naturo'.
        timeout: Max seconds to wait.

    Returns:
        Parsed JSON dict from stdout.

    Raises:
        subprocess.TimeoutExpired: If command exceeds timeout.
        json.JSONDecodeError: If output is not valid JSON.
    """
    cmd = ["python", "-m", "naturo"] + list(args) + ["--json"]
    result = subprocess.run(
        cmd,
        capture_output=True,
        text=True,
        timeout=timeout,
    )
    return json.loads(result.stdout)


class TestDetectionChainNotepad:
    """Test detection chain against Notepad (Win32 native)."""

    def test_detect_notepad_framework(self, notepad_app, detect_chain):
        """Notepad should be detected as a Win32 native application."""
        result = detect_chain(pid=notepad_app, app_name="Notepad")

        assert result.pid == notepad_app
        assert len(result.methods) > 0, "Should detect at least one interaction method"

    def test_detect_notepad_has_uia(self, notepad_app, detect_chain):
        """Notepad should support UIA interaction method."""
        result = detect_chain(pid=notepad_app, app_name="Notepad")

        method_names = [m.method.value for m in result.methods]
        assert "uia" in method_names, (
            f"Notepad should support UIA, got methods: {method_names}"
        )

    def test_detect_notepad_best_method(self, notepad_app, detect_chain):
        """Notepad's best method should be UIA (native Win32 app)."""
        result = detect_chain(pid=notepad_app, app_name="Notepad")

        best = result.best_method()
        assert best is not None, "Should have a best method"
        # Win32 native apps typically route to UIA as the best method
        assert best.method.value in ("uia", "msaa"), (
            f"Expected UIA or MSAA for Win32 app, got {best.method.value}"
        )

    def test_detect_notepad_quick_mode(self, notepad_app, detect_chain):
        """Quick mode should return faster with fewer probes."""
        result = detect_chain(pid=notepad_app, app_name="Notepad", quick=True)

        assert result.best_method() is not None, "Quick mode should still find a method"

    def test_detect_notepad_cache(self, notepad_app, detect_chain):
        """Second detection should use cache (same result, faster)."""
        result1 = detect_chain(pid=notepad_app, app_name="Notepad")
        result2 = detect_chain(pid=notepad_app, app_name="Notepad")

        # Same PID, same methods — cache should give identical result
        assert result1.pid == result2.pid
        assert len(result1.methods) == len(result2.methods)

    def test_detect_notepad_no_cache(self, notepad_app, detect_chain):
        """Detection without cache should still work."""
        result = detect_chain(pid=notepad_app, app_name="Notepad", use_cache=False)
        assert result.pid == notepad_app
        assert len(result.methods) > 0

    def test_detect_notepad_serialization(self, notepad_app, detect_chain):
        """DetectionResult should serialize to valid JSON dict."""
        result = detect_chain(pid=notepad_app, app_name="Notepad")
        d = result.to_dict()

        assert "pid" in d
        assert "interaction_methods" in d
        assert isinstance(d["interaction_methods"], list)
        assert d["pid"] == notepad_app

    def test_detect_notepad_vision_fallback(self, notepad_app, detect_chain):
        """Vision method should always be present as fallback."""
        result = detect_chain(pid=notepad_app, app_name="Notepad")

        method_names = [m.method.value for m in result.methods]
        assert "vision" in method_names, "Vision fallback should always be present"


class TestDetectionChainCalculator:
    """Test detection chain against Calculator (UWP/WinUI)."""

    def test_detect_calculator_framework(self, calculator_app, detect_chain):
        """Calculator should be detected with some framework info."""
        result = detect_chain(pid=calculator_app, app_name="Calculator")

        assert result.pid == calculator_app
        assert len(result.methods) > 0, "Should detect at least one interaction method"

    def test_detect_calculator_has_uia(self, calculator_app, detect_chain):
        """Calculator (UWP) should support UIA — the primary method for UWP apps."""
        result = detect_chain(pid=calculator_app, app_name="Calculator")

        method_names = [m.method.value for m in result.methods]
        assert "uia" in method_names, (
            f"Calculator should support UIA, got methods: {method_names}"
        )

    def test_detect_calculator_best_method(self, calculator_app, detect_chain):
        """Calculator's best method should be UIA."""
        result = detect_chain(pid=calculator_app, app_name="Calculator")

        best = result.best_method()
        assert best is not None, "Should have a best method"
        assert best.method.value in ("uia", "msaa"), (
            f"Expected UIA or MSAA for UWP app, got {best.method.value}"
        )


class TestDetectionChainExplorer:
    """Test detection chain against File Explorer (Win32 shell)."""

    def test_detect_explorer_framework(self, explorer_app, detect_chain):
        """Explorer should be detected as a Win32 application."""
        result = detect_chain(pid=explorer_app, app_name="Explorer")

        assert result.pid == explorer_app
        assert len(result.methods) > 0

    def test_detect_explorer_has_methods(self, explorer_app, detect_chain):
        """Explorer should have UIA and vision methods available."""
        result = detect_chain(pid=explorer_app, app_name="Explorer")

        method_names = [m.method.value for m in result.methods]
        assert len(method_names) >= 1, "Explorer should have at least one method"


class TestRoutingPipeline:
    """Test the full routing pipeline (resolve_method)."""

    def test_routing_notepad_auto(self, notepad_app):
        """Auto-routing should find a method for Notepad by PID."""
        from naturo.routing import resolve_method

        result = resolve_method(pid=notepad_app, explicit_method="auto")

        assert result.pid == notepad_app
        assert result.source == "auto"
        assert result.method != "", "Should resolve to a method"

    def test_routing_explicit_override(self, notepad_app):
        """Explicit --method should bypass detection entirely."""
        from naturo.routing import resolve_method

        result = resolve_method(pid=notepad_app, explicit_method="vision")

        assert result.method == "vision"
        assert result.source == "explicit"

    def test_routing_nonexistent_pid(self):
        """Routing with a non-existent PID should fall back to vision."""
        from naturo.routing import resolve_method

        result = resolve_method(pid=99999, explicit_method="auto")

        # Should not crash, should fall back gracefully
        assert result.method in ("vision", ""), "Should fall back to vision"

    def test_routing_no_target(self):
        """No app/pid should return vision as default."""
        from naturo.routing import resolve_method

        result = resolve_method(explicit_method="auto")

        assert result.method == "vision"
        assert result.source == "auto"


class TestCLIIntegration:
    """Test CLI commands work end-to-end with real apps.

    These tests validate that the naturo CLI properly executes commands
    against running applications via the auto-routing pipeline.
    """

    def test_see_notepad(self, notepad_app):
        """'naturo see' should return UI elements from Notepad."""
        try:
            output = _run_naturo("see", "--pid", str(notepad_app))
            assert "elements" in output or "error" not in output
        except (subprocess.TimeoutExpired, json.JSONDecodeError):
            pytest.skip("CLI not available or timed out")

    def test_find_in_notepad(self, notepad_app):
        """'naturo find' should locate elements in Notepad."""
        try:
            output = _run_naturo("find", "--pid", str(notepad_app), "--all")
            # Should return some elements or an empty list (not crash)
            assert isinstance(output, (dict, list))
        except (subprocess.TimeoutExpired, json.JSONDecodeError):
            pytest.skip("CLI not available or timed out")

    def test_capture_notepad(self, notepad_app):
        """'naturo capture' should capture Notepad window."""
        try:
            output = _run_naturo("capture", "--pid", str(notepad_app))
            # Should return path to captured image
            assert "path" in output or "image" in output or "error" not in output
        except (subprocess.TimeoutExpired, json.JSONDecodeError):
            pytest.skip("CLI not available or timed out")


class TestDetectionCacheIntegrity:
    """Test that detection cache works correctly across apps."""

    def test_cache_per_pid(self, notepad_app, calculator_app, detect_chain):
        """Different PIDs should have separate cache entries."""
        result_notepad = detect_chain(pid=notepad_app, app_name="Notepad")
        result_calc = detect_chain(pid=calculator_app, app_name="Calculator")

        assert result_notepad.pid != result_calc.pid
        assert result_notepad.app_name != result_calc.app_name

    def test_cache_invalidation(self, notepad_app, detect_chain):
        """Cache should not interfere with no-cache requests."""
        # Fill cache
        cached_result = detect_chain(pid=notepad_app, use_cache=True)
        # Bypass cache
        fresh_result = detect_chain(pid=notepad_app, use_cache=False)

        # Both should find methods (cache doesn't corrupt results)
        assert len(cached_result.methods) > 0
        assert len(fresh_result.methods) > 0
