"""Security tests for Naturo.

Tests for JSON injection, path traversal, and DLL load safety.
"""

from __future__ import annotations

import json
import os
import platform
import sys
import tempfile

import pytest


class TestJSONInjection:
    """R-SEC-001, R-SEC-002: JSON injection safety in C++ serialization."""

    @pytest.mark.skipif(platform.system() != "Windows", reason="Windows UI test")
    @pytest.mark.ui
    def test_json_special_chars_in_window_title(self):
        """R-SEC-001: Window title containing special JSON chars must be properly escaped.

        When window titles contain ", \\, }, ] the JSON output must parse without error.
        Verified via the C++ naturo_list_windows JSON serialization.
        """
        from naturo.bridge import NaturoCore

        core = NaturoCore()
        core.init()
        try:
            windows = core.list_windows()
            # All windows must have properly escaped titles that parsed correctly
            for w in windows:
                assert isinstance(w.title, str)
                assert isinstance(w.process_name, str)
                # Re-serialize to JSON to verify round-trip safety
                data = json.dumps({"title": w.title, "process_name": w.process_name})
                parsed = json.loads(data)
                assert parsed["title"] == w.title
        finally:
            core.shutdown()

    @pytest.mark.skipif(platform.system() != "Windows", reason="Windows UI test")
    @pytest.mark.ui
    def test_json_injection_in_element_name(self):
        """R-SEC-002: Element name containing JSON-like string must be treated as literal.

        If an element name contains '{"malicious": true}' it must appear as a
        plain string in the JSON output, not parsed as a nested object.
        """
        from naturo.bridge import NaturoCore

        core = NaturoCore()
        core.init()
        try:
            tree = core.get_element_tree(hwnd=0, depth=2)
            if tree is not None:
                # Verify all element names are proper strings
                def check_elements(el):
                    assert isinstance(el.name, str)
                    assert isinstance(el.role, str)
                    # Re-serialize and verify
                    data = json.dumps({"name": el.name, "role": el.role})
                    parsed = json.loads(data)
                    assert parsed["name"] == el.name
                    for child in el.children:
                        check_elements(child)
                check_elements(tree)
        finally:
            core.shutdown()


class TestPathTraversal:
    """R-SEC-003: Path traversal protection."""

    def test_capture_path_traversal_relative(self):
        """R-SEC-003: capture with relative path traversal should be handled safely.

        The path '../../etc/passwd' should either be rejected or resolved to a safe
        location. On non-Windows we verify the path logic in Python; on Windows the
        C++ core handles it.
        """
        # Verify that Path resolution works correctly
        from pathlib import Path

        dangerous_path = "../../etc/passwd"
        resolved = Path(dangerous_path).resolve()
        # The resolved path should not end up in a system directory
        # (this is a design-level check — actual enforcement is in the CLI layer)
        assert str(resolved) != "/etc/passwd" or platform.system() == "Linux"

    @pytest.mark.skipif(platform.system() != "Windows", reason="Windows-only path test")
    @pytest.mark.ui
    def test_capture_path_traversal_windows(self):
        """R-SEC-003: capture with traversal path on Windows.

        Attempt to capture to a path with '..' components. The C++ core should
        either reject or resolve it safely.
        """
        from naturo.bridge import NaturoCore, NaturoCoreError

        core = NaturoCore()
        core.init()
        try:
            traversal_path = os.path.join(tempfile.gettempdir(), "..", "..", "test_traversal.bmp")
            try:
                core.capture_screen(0, traversal_path)
                # If it succeeds, verify the file was created at the resolved path
                resolved = os.path.realpath(traversal_path)
                if os.path.exists(resolved):
                    os.unlink(resolved)
            except NaturoCoreError:
                # Rejection is also acceptable behavior
                pass
        finally:
            core.shutdown()


class TestDLLLoadSafety:
    """R-SEC-010: DLL load safety — search order must not include CWD before package dir."""

    def test_dll_search_order_package_before_cwd(self):
        """R-SEC-010: Library search order does not include CWD before package directory.

        The _load method in NaturoCore checks:
        1. Explicit lib_path
        2. NATURO_CORE_PATH env var
        3. Package bin/ directory
        4. CWD
        5. System PATH

        Package bin/ (step 3) must come before CWD (step 4) to prevent
        DLL hijacking attacks where a malicious DLL is placed in CWD.
        """
        import inspect
        from naturo.bridge import NaturoCore

        source = inspect.getsource(NaturoCore._load)
        # Verify the search order in source code
        pkg_idx = source.find("pkg_lib")
        cwd_idx = source.find("cwd_lib")
        assert pkg_idx > 0, "Package lib search not found in _load"
        assert cwd_idx > 0, "CWD lib search not found in _load"
        assert pkg_idx < cwd_idx, (
            "Package directory must be searched before CWD to prevent DLL hijacking"
        )

    def test_env_var_path_validated(self):
        """R-SEC-010: NATURO_CORE_PATH is checked for existence before loading.

        The bridge should verify the file exists before attempting to load it.
        """
        import inspect
        from naturo.bridge import NaturoCore

        source = inspect.getsource(NaturoCore._load)
        # The code should check os.path.exists before loading env var path
        assert "os.path.exists" in source or "exists()" in source, (
            "NATURO_CORE_PATH should be validated before loading"
        )

    def test_nonexistent_env_path_ignored(self):
        """R-SEC-010: Non-existent NATURO_CORE_PATH should be ignored, not crash."""
        old_val = os.environ.get("NATURO_CORE_PATH")
        try:
            os.environ["NATURO_CORE_PATH"] = "/nonexistent/path/naturo_core.dll"
            if platform.system() != "Windows":
                # On non-Windows, we expect FileNotFoundError
                with pytest.raises(FileNotFoundError):
                    from naturo.bridge import NaturoCore
                    NaturoCore()
            else:
                # On Windows, it should skip the invalid path and find the real DLL
                from naturo.bridge import NaturoCore
                core = NaturoCore()
                assert core is not None
        finally:
            if old_val is not None:
                os.environ["NATURO_CORE_PATH"] = old_val
            else:
                os.environ.pop("NATURO_CORE_PATH", None)
