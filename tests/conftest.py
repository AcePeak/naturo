import pytest
import platform


def pytest_configure(config):
    """Register custom markers."""
    pass  # markers defined in pyproject.toml


def cli_stdout(result):
    """Extract stdout-only text from a Click CliRunner result.

    Click 8.x's ``result.output`` mixes stderr and stdout. Use
    ``result.stdout`` when available (Click ≥8.0) to avoid stderr
    warnings contaminating JSON output assertions.
    """
    return getattr(result, "stdout", result.output)


@pytest.fixture
def is_windows():
    return platform.system() == "Windows"


@pytest.fixture
def skip_if_not_windows():
    if platform.system() != "Windows":
        pytest.skip("Windows-only test")
