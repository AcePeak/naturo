"""Tests for the worktree-integrity import guard (#971).

The guard fails loudly when an imported ``naturo`` resolves to a package
outside the *active* worktree root — the silent-failure hazard from #969 where
a stale editable install (egg-link/``.pth``) shadows the checkout under test
with a sibling worktree's pre-#720 code, producing confident false verdicts.

The guard is opt-in via the ``NATURO_EXPECTED_ROOT`` environment variable so it
is a no-op for ordinary pip installs (which legitimately live in site-packages
outside any worktree) and only enforced by the agent harness, which sets the
variable to the checkout it is running from.
"""

from __future__ import annotations

import subprocess
import sys
from pathlib import Path

import pytest

from naturo._worktree_guard import (
    WORKTREE_ENV_VAR,
    WorktreeMismatchError,
    check_worktree_integrity,
)
from naturo.errors import ErrorCode, NaturoError


def test_noop_when_no_expected_root(tmp_path, monkeypatch):
    """With the env var unset and no explicit root, the guard does nothing.

    This is the ordinary-install path — naturo lives in site-packages, far from
    any worktree, and must never raise just for being imported.
    """
    monkeypatch.delenv(WORKTREE_ENV_VAR, raising=False)
    # A package_file that is clearly outside any plausible root: must not raise.
    check_worktree_integrity(package_file=str(tmp_path / "elsewhere" / "naturo" / "__init__.py"))


def test_passes_when_package_under_expected_root(tmp_path):
    """No error when the package resolves under the expected worktree root."""
    root = tmp_path / "naturo-qa"
    pkg = root / "naturo" / "__init__.py"
    pkg.parent.mkdir(parents=True)
    pkg.write_text("", encoding="utf-8")
    # Should not raise.
    check_worktree_integrity(expected_root=str(root), package_file=str(pkg))


def test_raises_when_package_outside_expected_root(tmp_path):
    """The core deliverable: a sibling-worktree import fails loudly."""
    expected = tmp_path / "naturo-qa"
    sibling = tmp_path / "naturo-qa-mariana"
    pkg = sibling / "naturo" / "__init__.py"
    pkg.parent.mkdir(parents=True)
    pkg.write_text("", encoding="utf-8")
    expected.mkdir()

    with pytest.raises(WorktreeMismatchError) as excinfo:
        check_worktree_integrity(expected_root=str(expected), package_file=str(pkg))

    err = excinfo.value
    # Loud: names both the resolved package path and the expected root.
    assert str(pkg.resolve()) in err.message
    assert str(expected.resolve()) in err.message
    # Structured: a NaturoError carrying the dedicated code.
    assert isinstance(err, NaturoError)
    assert err.code == ErrorCode.WORKTREE_MISMATCH
    assert err.suggested_action  # actionable hint present


def test_env_var_supplies_expected_root(tmp_path, monkeypatch):
    """The env var is read when no explicit root is passed."""
    expected = tmp_path / "naturo-qa"
    sibling = tmp_path / "stale"
    pkg = sibling / "naturo" / "__init__.py"
    pkg.parent.mkdir(parents=True)
    pkg.write_text("", encoding="utf-8")
    expected.mkdir()
    monkeypatch.setenv(WORKTREE_ENV_VAR, str(expected))

    with pytest.raises(WorktreeMismatchError):
        check_worktree_integrity(package_file=str(pkg))


def test_explicit_root_overrides_env(tmp_path, monkeypatch):
    """An explicit expected_root takes precedence over the env var."""
    root = tmp_path / "naturo-qa"
    pkg = root / "naturo" / "__init__.py"
    pkg.parent.mkdir(parents=True)
    pkg.write_text("", encoding="utf-8")
    # Env points elsewhere, but the explicit (correct) root wins → no raise.
    monkeypatch.setenv(WORKTREE_ENV_VAR, str(tmp_path / "somewhere-else"))
    check_worktree_integrity(expected_root=str(root), package_file=str(pkg))


def test_blank_env_var_is_treated_as_unset(tmp_path, monkeypatch):
    """A whitespace-only env var must not enable an unsatisfiable guard."""
    monkeypatch.setenv(WORKTREE_ENV_VAR, "   ")
    check_worktree_integrity(package_file=str(tmp_path / "naturo" / "__init__.py"))


def test_root_equal_to_package_dir_passes(tmp_path):
    """resolve() normalisation: trailing-slash / dot segments still match."""
    root = tmp_path / "naturo-qa"
    pkg = root / "naturo" / "__init__.py"
    pkg.parent.mkdir(parents=True)
    pkg.write_text("", encoding="utf-8")
    messy_root = str(root) + "/./"
    check_worktree_integrity(expected_root=messy_root, package_file=str(pkg))


def test_import_time_guard_fires_in_subprocess(tmp_path):
    """End-to-end: `import naturo` aborts when the env var points elsewhere.

    This proves the real deliverable — `python -m naturo` / `import naturo`
    refuses to run stale sibling code — without needing a second worktree.
    """
    env = {
        **_clean_env(),
        WORKTREE_ENV_VAR: str(tmp_path / "definitely-not-this-checkout"),
    }
    proc = subprocess.run(
        [sys.executable, "-c", "import naturo"],
        capture_output=True,
        text=True,
        env=env,
    )
    assert proc.returncode != 0, "import naturo should fail loudly under a mismatched root"
    assert "WORKTREE_MISMATCH" in proc.stderr or "worktree" in proc.stderr.lower()


def test_import_time_guard_silent_without_env(tmp_path):
    """Control: `import naturo` succeeds when the env var is unset."""
    proc = subprocess.run(
        [sys.executable, "-c", "import naturo"],
        capture_output=True,
        text=True,
        env=_clean_env(),
    )
    assert proc.returncode == 0, proc.stderr


def _clean_env():
    """A copy of the current environment with the guard var removed.

    Keeps PATH/PYTHONPATH so the subprocess imports the same naturo as the
    test session, but ensures the guard starts from a known (unset) state.
    """
    import os

    env = dict(os.environ)
    env.pop(WORKTREE_ENV_VAR, None)
    return env
