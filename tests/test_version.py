"""Test version consistency."""
from __future__ import annotations

import sys
from naturo.version import __version__


def test_version_is_string():
    """T340: Version is a valid semver string."""
    assert isinstance(__version__, str)


def test_version_format():
    """T341: Version format is X.Y.Z (3 numeric parts)."""
    parts = __version__.split(".")
    assert len(parts) == 3
    for part in parts:
        assert part.isdigit()


def test_version_matches_cmake():
    """T343: CMakeLists.txt project version matches Python version."""
    import re
    from pathlib import Path

    cmake_file = Path(__file__).parent.parent / "core" / "CMakeLists.txt"
    if not cmake_file.exists():
        return  # skip in installed package

    text = cmake_file.read_text()
    m = re.search(r'project\(naturo_core\s+VERSION\s+(\S+)', text)
    assert m is not None, "Could not find project VERSION in CMakeLists.txt"
    assert m.group(1) == __version__, (
        f"CMakeLists.txt version {m.group(1)} != Python version {__version__}"
    )


def test_version_matches_version_cpp():
    """T344: version.cpp NATURO_VERSION matches Python version."""
    import re
    from pathlib import Path

    version_cpp = Path(__file__).parent.parent / "core" / "src" / "version.cpp"
    if not version_cpp.exists():
        return  # skip in installed package

    text = version_cpp.read_text()
    m = re.search(r'NATURO_VERSION\s*=\s*"([^"]+)"', text)
    assert m is not None, "Could not find NATURO_VERSION in version.cpp"
    assert m.group(1) == __version__, (
        f"version.cpp version {m.group(1)} != Python version {__version__}"
    )


def test_version_matches_pyproject():
    """T342: Version matches pyproject.toml."""
    from pathlib import Path

    pyproject = Path(__file__).parent.parent / "pyproject.toml"
    if not pyproject.exists():
        return  # skip in installed package

    if sys.version_info >= (3, 11):
        import tomllib
    else:
        try:
            import tomli as tomllib
        except ImportError:
            import re
            # Fallback: parse version from pyproject.toml with regex
            text = pyproject.read_text()
            m = re.search(r'^version\s*=\s*"([^"]+)"', text, re.MULTILINE)
            assert m is not None, "Could not find version in pyproject.toml"
            assert m.group(1) == __version__
            return

    with open(pyproject, "rb") as f:
        data = tomllib.load(f)
    assert data["project"]["version"] == __version__
