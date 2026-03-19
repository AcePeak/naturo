"""Version consistency tests.

Verifies that version numbers are consistent across Python package and native DLL.
"""

from __future__ import annotations

import platform

import pytest

from naturo.version import __version__


@pytest.mark.skipif(platform.system() != "Windows", reason="DLL version check requires Windows")
def test_python_version_matches_dll_version():
    """R-DEV-005: Python version must match DLL version (naturo_core.naturo_version()).

    The Python package version (__version__) must be identical to the version
    string returned by the native library's naturo_version() function.
    """
    from naturo.bridge import NaturoCore

    core = NaturoCore()
    dll_version = core.version()
    assert dll_version == __version__, (
        f"Version mismatch: Python={__version__}, DLL={dll_version}"
    )
