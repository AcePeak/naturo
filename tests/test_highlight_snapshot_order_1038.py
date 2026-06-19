"""Regression tests for #1038 — highlight reads newest snapshot, not oldest.

``naturo.snapshot.SnapshotManager.list_snapshots()`` returns snapshots
**newest-first** (``infos.sort(..., reverse=True)``), so index ``0`` is the
most recent and index ``-1`` is the oldest.  ``highlight_elements_uia`` must
select the newest snapshot in both its annotate and live-overlay paths.

Before the fix it used ``snaps[-1]`` (the oldest snapshot), which typically
has no stored screenshot — causing ``highlight --annotate`` to always fail
with ``NO_SNAPSHOT`` even right after a successful ``see``.  These tests are
mock-based and CI-safe (no DLL / desktop required).
"""
from __future__ import annotations

from unittest.mock import MagicMock, patch

from naturo.bridge import _highlight


def _snapshot_info(snapshot_id: str) -> MagicMock:
    """Build a minimal ``SnapshotInfo``-like stub exposing only ``.id``."""
    info = MagicMock()
    info.id = snapshot_id
    return info


def _make_manager() -> MagicMock:
    """Manager whose newest snapshot has a screenshot and the oldest does not.

    ``list_snapshots()`` returns newest-first, mirroring the real
    implementation: ``["new", "old"]``.
    """
    newest = MagicMock()
    newest.ui_map = {"e1": MagicMock()}
    newest.screenshot_path = "C:/snaps/new/raw.png"

    oldest = MagicMock()
    oldest.ui_map = None
    oldest.screenshot_path = None  # the symptom: oldest never has a screenshot

    mgr = MagicMock()
    mgr.list_snapshots.return_value = [_snapshot_info("new"), _snapshot_info("old")]
    mgr.get_snapshot.side_effect = lambda sid: {"new": newest, "old": oldest}[sid]
    return mgr


def test_annotate_uses_newest_snapshot() -> None:
    """Annotate mode must read the newest snapshot (``snaps[0]``), not oldest."""
    mgr = _make_manager()
    with patch("naturo.snapshot.get_snapshot_manager", return_value=mgr), \
            patch("naturo.annotate.highlight_annotate", return_value="out.png") as mock_ann:
        result = _highlight.highlight_elements_uia(
            backend=MagicMock(),
            app="notepad",
            annotate_path="out.png",
        )

    assert result == "out.png"
    mgr.get_snapshot.assert_called_once_with("new")
    # The newest snapshot's screenshot must be the one annotated.
    assert mock_ann.call_args.kwargs["screenshot_path"] == "C:/snaps/new/raw.png"


def test_live_overlay_uses_newest_snapshot() -> None:
    """Live-overlay mode must also resolve the newest snapshot (``snaps[0]``)."""
    mgr = _make_manager()
    backend = MagicMock()
    backend.get_element_tree.return_value = None
    with patch("naturo.snapshot.get_snapshot_manager", return_value=mgr), \
            patch.object(_highlight.platform, "system", return_value="Windows"), \
            patch.object(_highlight, "_draw_gdi_overlay"):
        _highlight.highlight_elements_uia(
            backend=backend,
            app="notepad",
            duration=0.0,
        )

    mgr.get_snapshot.assert_called_once_with("new")
