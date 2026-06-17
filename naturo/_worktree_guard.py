"""Fail loudly when imported ``naturo`` resolves outside the active worktree.

Background (#971, companion to the environment-only #969): an editable install
(egg-link / ``.pth``) can resolve ``import naturo`` to a *sibling* worktree —
for example ``naturo-qa-mariana`` holding pre-#720 stale code — instead of the
checkout the harness is running from. When that happens, runtime verification
probes silently validate the wrong source and emit confident *false* verdicts
(the false FAIL at #963). Fixing the install itself touches another agent's
worktree and is human-only (#969); this module is the code-only loud-failure
guard that makes the hazard impossible to miss in the meantime and permanently
after.

The guard is **opt-in**: it does nothing unless ``NATURO_EXPECTED_ROOT`` is set
(or an explicit root is passed). Ordinary pip installs legitimately live in
``site-packages`` outside any worktree, so enabling it unconditionally would
break every normal user. The agent harness sets the variable to the worktree it
is verifying; then ``import naturo`` / ``python -m naturo`` refuses to run if a
different checkout's code was loaded.
"""

from __future__ import annotations

import os
from pathlib import Path

from naturo.errors import WorktreeMismatchError

#: Environment variable naming the worktree root the imported package must be under.
WORKTREE_ENV_VAR = "NATURO_EXPECTED_ROOT"


def _is_under(child: Path, ancestor: Path) -> bool:
    """Return True if ``child`` is ``ancestor`` or lives beneath it.

    Uses ``relative_to`` rather than ``Path.is_relative_to`` so the check
    behaves identically on Python 3.9, where the latter does not exist.
    """
    try:
        child.relative_to(ancestor)
    except ValueError:
        return False
    return True


def check_worktree_integrity(
    expected_root: str | os.PathLike[str] | None = None,
    package_file: str | None = None,
) -> None:
    """Assert the imported ``naturo`` package lives under the expected worktree.

    Args:
        expected_root: The worktree root the package must be under. When ``None``
            (the default), the value of the ``NATURO_EXPECTED_ROOT`` environment
            variable is used; if that is also unset or blank the guard is a
            no-op and returns immediately.
        package_file: Path to the imported package's ``__init__.py``. Defaults to
            this module's own location (``naturo/_worktree_guard.py``), which
            resolves to the same package directory as ``naturo.__file__`` without
            importing the partially-initialised top-level package. Exposed for
            testing.

    Raises:
        WorktreeMismatchError: If an expected root is configured and the resolved
            package path is not under it. The message names both the resolved
            package path and the expected root so the mismatch is obvious.
    """
    root_value = expected_root if expected_root is not None else os.environ.get(WORKTREE_ENV_VAR)
    if root_value is None or not str(root_value).strip():
        return

    expected = Path(root_value).expanduser().resolve()

    if package_file is not None:
        package_path = Path(package_file)
    else:
        # ``naturo/_worktree_guard.py`` -> the file whose presence we vouch for.
        package_path = Path(__file__).with_name("__init__.py")
    package_path = package_path.resolve()

    if _is_under(package_path, expected):
        return

    raise WorktreeMismatchError(
        f"Imported naturo resolves to {package_path}, which is not under the "
        f"expected worktree root {expected} (set via {WORKTREE_ENV_VAR}). "
        f"A stale editable install is shadowing the checkout under test; "
        f"runtime verification would silently validate the wrong code.",
        context={
            "resolved_package": str(package_path),
            "expected_root": str(expected),
            "env_var": WORKTREE_ENV_VAR,
        },
    )
