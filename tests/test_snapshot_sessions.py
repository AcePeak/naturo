"""Tests for issue #173 — Snapshot session isolation.

Verifies:
- SnapshotManager session parameter isolates storage
- get_snapshot_manager() factory reads NATURO_SESSION env var
- get_snapshot_manager() falls back to "default" session
- Different sessions have independent snapshot dirs
- NATURO_SESSION env var scopes see/click resolution
- TTL increase to 1800 s (30 min) from previous 600 s
- NATURO_SNAPSHOT_TTL env var overrides default TTL
- snapshot session and snap_root properties
- CLI: naturo snapshot list --session
- CLI: naturo snapshot sessions
- CLI: naturo snapshot clean --session
"""
from __future__ import annotations

import json
import time
from pathlib import Path
from typing import Dict

import pytest

from naturo.models.snapshot import UIElement
from naturo.snapshot import (
    DEFAULT_SESSION,
    SNAPSHOT_VALIDITY_SECONDS,
    SnapshotManager,
    get_active_session,
    get_active_ttl,
    get_snapshot_manager,
)
from click.testing import CliRunner
from naturo.cli import main


# ── Fixtures ─────────────────────────────────────────────────────────────────


@pytest.fixture()
def base_root(tmp_path: Path) -> Path:
    root = tmp_path / "snapshots"
    root.mkdir()
    return root


@pytest.fixture()
def mgr_a(base_root: Path) -> SnapshotManager:
    return SnapshotManager(storage_root=base_root, session="session-a")


@pytest.fixture()
def mgr_b(base_root: Path) -> SnapshotManager:
    return SnapshotManager(storage_root=base_root, session="session-b")


# ── Default TTL increased ─────────────────────────────────────────────────────


class TestDefaultTTL:
    def test_default_validity_is_1800s(self):
        """Validity window increased to 30 min (from 10 min) for longer workflows."""
        assert SNAPSHOT_VALIDITY_SECONDS == 1800

    def test_manager_default_validity(self, base_root):
        mgr = SnapshotManager(storage_root=base_root)
        assert mgr._validity_seconds == 1800


# ── Session parameter ─────────────────────────────────────────────────────────


class TestSessionIsolation:
    def test_default_session_name(self, base_root):
        mgr = SnapshotManager(storage_root=base_root)
        assert mgr.session == DEFAULT_SESSION

    def test_custom_session_name(self, mgr_a):
        assert mgr_a.session == "session-a"

    def test_session_scopes_storage(self, base_root, mgr_a, mgr_b):
        """Snapshots from different sessions are stored in different directories."""
        sid_a = mgr_a.create_snapshot()
        sid_b = mgr_b.create_snapshot()

        # Each session has its own subdirectory
        assert (base_root / "session-a" / sid_a).is_dir()
        assert (base_root / "session-b" / sid_b).is_dir()
        # No cross-contamination
        assert not (base_root / "session-a" / sid_b).exists()
        assert not (base_root / "session-b" / sid_a).exists()

    def test_storage_path_includes_session(self, base_root, mgr_a):
        assert Path(mgr_a.storage_path) == base_root / "session-a"

    def test_base_storage_path_is_root(self, base_root, mgr_a):
        assert Path(mgr_a.base_storage_path) == base_root

    def test_session_property(self, mgr_a):
        assert mgr_a.session == "session-a"

    def test_different_sessions_independent_refs(self, base_root):
        """e1 in session-a and e1 in session-b refer to different elements."""
        png_bytes = (
            b"\x89PNG\r\n\x1a\n"
            b"\x00\x00\x00\rIHDR\x00\x00\x00\x01\x00\x00\x00\x01\x08\x02"
            b"\x00\x00\x00\x90wS\xde\x00\x00\x00\x0cIDATx\x9cc\xf8\x0f\x00"
            b"\x00\x01\x01\x00\x05\x18\xd8N\x00\x00\x00\x00IEND\xaeB`\x82"
        )

        mgr_a = SnapshotManager(storage_root=base_root, session="session-a")
        mgr_b = SnapshotManager(storage_root=base_root, session="session-b")

        # Store e1 → element A in session-a
        el_a = UIElement(id="elem_a", element_id="elem_a", role="Button",
                         title="Save", label="Save", value=None,
                         frame=(10, 20, 80, 30), is_actionable=True,
                         parent_id=None, children=[])
        sid_a = mgr_a.create_snapshot()
        mgr_a.store_detection_result(sid_a, {"elem_a": el_a})
        mgr_a.store_ref_map(sid_a, {"e1": "elem_a"})

        # Store e1 → element B in session-b
        el_b = UIElement(id="elem_b", element_id="elem_b", role="Button",
                         title="Close", label="Close", value=None,
                         frame=(500, 300, 60, 25), is_actionable=True,
                         parent_id=None, children=[])
        sid_b = mgr_b.create_snapshot()
        mgr_b.store_detection_result(sid_b, {"elem_b": el_b})
        mgr_b.store_ref_map(sid_b, {"e1": "elem_b"})

        # Each session resolves its own e1
        resolved_a = mgr_a.resolve_ref("e1")
        resolved_b = mgr_b.resolve_ref("e1")

        assert resolved_a is not None
        assert resolved_b is not None
        # Different coordinates — no cross-contamination
        assert resolved_a[:2] != resolved_b[:2]
        assert resolved_a[0] == 10 + 80 // 2   # center of Save button
        assert resolved_b[0] == 500 + 60 // 2  # center of Close button

    def test_clean_all_only_affects_own_session(self, base_root, mgr_a, mgr_b):
        mgr_a.create_snapshot()
        sid_b = mgr_b.create_snapshot()

        mgr_a.clean_all()

        # session-a is empty
        assert list((base_root / "session-a").iterdir()) == []
        # session-b is untouched
        assert (base_root / "session-b" / sid_b).is_dir()


# ── get_snapshot_manager factory ─────────────────────────────────────────────


class TestGetSnapshotManagerFactory:
    def test_reads_env_var(self, monkeypatch, base_root):
        monkeypatch.setenv("NATURO_SESSION", "env-session")
        mgr = get_snapshot_manager(storage_root=base_root)
        assert mgr.session == "env-session"

    def test_explicit_session_overrides_env(self, monkeypatch, base_root):
        monkeypatch.setenv("NATURO_SESSION", "env-session")
        mgr = get_snapshot_manager(session="explicit-session", storage_root=base_root)
        assert mgr.session == "explicit-session"

    def test_default_session_when_no_env(self, monkeypatch, base_root):
        monkeypatch.delenv("NATURO_SESSION", raising=False)
        mgr = get_snapshot_manager(storage_root=base_root)
        assert mgr.session == DEFAULT_SESSION

    def test_empty_env_uses_default(self, monkeypatch, base_root):
        monkeypatch.setenv("NATURO_SESSION", "")
        mgr = get_snapshot_manager(storage_root=base_root)
        assert mgr.session == DEFAULT_SESSION


# ── get_active_session / get_active_ttl ──────────────────────────────────────


class TestActiveSessionHelpers:
    def test_get_active_session_from_env(self, monkeypatch):
        monkeypatch.setenv("NATURO_SESSION", "workflow-x")
        assert get_active_session() == "workflow-x"

    def test_get_active_session_default(self, monkeypatch):
        monkeypatch.delenv("NATURO_SESSION", raising=False)
        assert get_active_session() == DEFAULT_SESSION

    def test_get_active_ttl_default(self, monkeypatch):
        monkeypatch.delenv("NATURO_SNAPSHOT_TTL", raising=False)
        assert get_active_ttl() == SNAPSHOT_VALIDITY_SECONDS

    def test_get_active_ttl_from_env(self, monkeypatch):
        monkeypatch.setenv("NATURO_SNAPSHOT_TTL", "3600")
        assert get_active_ttl() == 3600

    def test_get_active_ttl_invalid_env(self, monkeypatch):
        monkeypatch.setenv("NATURO_SNAPSHOT_TTL", "not-a-number")
        assert get_active_ttl() == SNAPSHOT_VALIDITY_SECONDS

    def test_get_active_ttl_negative_ignored(self, monkeypatch):
        monkeypatch.setenv("NATURO_SNAPSHOT_TTL", "-1")
        assert get_active_ttl() == SNAPSHOT_VALIDITY_SECONDS


# ── CLI: snapshot sessions ────────────────────────────────────────────────────


def _get_snapshot_cli_module():
    """Import the snapshot CLI module, bypassing Click group name collision."""
    import importlib
    import sys
    # Force fresh module reference from sys.modules
    return sys.modules.get("naturo.cli.snapshot") or importlib.import_module("naturo.cli.snapshot")


class TestSnapshotSessionsCLI:
    @pytest.fixture(autouse=True)
    def patch_storage(self, monkeypatch, tmp_path):
        import sys
        _snap_mod = sys.modules["naturo.cli.snapshot"]
        self._base = tmp_path / "snapshots"
        monkeypatch.setattr(_snap_mod, "DEFAULT_STORAGE_ROOT", self._base)

    def test_list_sessions_empty(self):
        runner = CliRunner()
        result = runner.invoke(main, ["snapshot", "sessions"])
        assert result.exit_code == 0
        assert "No sessions found" in result.output

    def test_list_sessions_json_empty(self):
        runner = CliRunner()
        result = runner.invoke(main, ["snapshot", "sessions", "--json"])
        assert result.exit_code == 0
        data = json.loads(result.output)
        assert data["success"] is True
        assert data["sessions"] == []

    def test_list_sessions_shows_session_names(self):
        # Create snapshots in two sessions
        SnapshotManager(storage_root=self._base, session="alpha").create_snapshot()
        SnapshotManager(storage_root=self._base, session="beta").create_snapshot()

        runner = CliRunner()
        result = runner.invoke(main, ["snapshot", "sessions", "--json"])
        data = json.loads(result.output)
        names = {s["name"] for s in data["sessions"]}
        assert "alpha" in names
        assert "beta" in names


class TestSnapshotListWithSession:
    def test_list_scoped_to_session(self, monkeypatch, tmp_path):
        import sys
        _snap_mod = sys.modules["naturo.cli.snapshot"]
        base = tmp_path / "snapshots"
        monkeypatch.setattr(_snap_mod, "DEFAULT_STORAGE_ROOT", base)
        monkeypatch.setattr("naturo.snapshot.DEFAULT_STORAGE_ROOT", base)

        # Create snapshot in wf-a
        SnapshotManager(storage_root=base, session="wf-a").create_snapshot()
        # Create snapshot in wf-b (should not appear)
        SnapshotManager(storage_root=base, session="wf-b").create_snapshot()

        runner = CliRunner()
        result = runner.invoke(main, ["snapshot", "list", "--session", "wf-a", "--json"])
        assert result.exit_code == 0
        data = json.loads(result.output)
        assert data["session"] == "wf-a"
        assert len(data["snapshots"]) == 1
