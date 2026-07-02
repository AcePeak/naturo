"""Error-envelope contract tests for #877.

``naturo -j get eN`` / ``set eN value`` previously returned an error envelope
with ``code: "UNKNOWN_ERROR"`` and **no** ``suggested_action`` when the element
ref was absent from the snapshot cache. Both are contract violations: the
failure mode is fully known (the message names the fix), yet machine consumers
could not dispatch on ``error.code`` nor read a recovery hint.

These tests pin the fix: the dedicated :class:`StaleSnapshotCacheError` carries
the semantic ``STALE_SNAPSHOT_CACHE`` code plus a ``suggested_action``, the raise
sites in ``get``/``set`` use it, and the JSON envelope surfaces both fields.
"""

import json
from unittest.mock import MagicMock, patch

import pytest

from naturo.cli.error_helpers import json_error, json_error_from_exception
from naturo.cli.values import _set
from naturo.errors import ErrorCode, StaleSnapshotCacheError


class TestStaleSnapshotCacheError:
    """The dedicated error type carries a semantic code and recovery hint."""

    def test_has_semantic_code_not_unknown(self):
        err = StaleSnapshotCacheError("e1")
        assert err.code == ErrorCode.STALE_SNAPSHOT_CACHE
        assert err.code == "STALE_SNAPSHOT_CACHE"
        assert err.code != "UNKNOWN_ERROR"

    def test_carries_suggested_action_and_is_recoverable(self):
        err = StaleSnapshotCacheError("e1")
        assert err.suggested_action
        assert "naturo see" in err.suggested_action
        assert err.is_recoverable is True

    def test_message_names_the_ref_and_fix(self):
        err = StaleSnapshotCacheError("e47")
        assert "e47" in err.message
        assert "naturo see" in err.message
        assert err.context == {"ref": "e47"}


class TestStaleSnapshotEnvelope:
    """The JSON error envelope honours code + suggested_action."""

    def test_envelope_from_exception(self):
        envelope = json.loads(json_error_from_exception(StaleSnapshotCacheError("e1")))
        assert envelope["success"] is False
        error = envelope["error"]
        assert error["code"] == "STALE_SNAPSHOT_CACHE"
        assert error["suggested_action"]
        assert error["recoverable"] is True

    def test_raw_code_lookup_populates_action(self):
        # Even when emitted by raw code (no exception instance) the registry
        # fills in the recovery hint, so the envelope never regresses to 2 keys.
        envelope = json.loads(json_error("STALE_SNAPSHOT_CACHE", "ref e1 missing"))
        assert envelope["error"]["code"] == "STALE_SNAPSHOT_CACHE"
        assert envelope["error"]["suggested_action"]


class TestSetRaiseSite:
    """``set``'s ref resolver raises the semantic error on a cache miss.

    Cross-platform safe: ``_resolve_element_identifiers`` only consults the
    snapshot manager (no DLL / desktop session), so we patch it to simulate an
    empty cache and assert the raised error type.
    """

    def test_resolve_missing_ref_raises_stale_snapshot_cache(self):
        mock_mgr = MagicMock()
        mock_mgr.resolve_ref_element.return_value = None
        with patch("naturo.snapshot.get_snapshot_manager", return_value=mock_mgr):
            with pytest.raises(StaleSnapshotCacheError) as exc_info:
                _set._resolve_element_identifiers("e99999", None, None, None)
        assert exc_info.value.code == "STALE_SNAPSHOT_CACHE"
        assert exc_info.value.suggested_action


@pytest.mark.desktop
class TestGetEndToEnd:
    """Live ``get`` against a ref absent from the cache emits the envelope.

    Desktop-only: ``get``'s ref resolution runs inside the real UIA backend
    (needs the native core), so this exercises the actual raise site end to end.
    """

    def test_get_missing_ref_json_envelope(self):
        from click.testing import CliRunner

        from naturo.cli import main

        result = CliRunner().invoke(main, ["--json", "get", "e9999999"])
        assert result.exit_code != 0
        envelope = json.loads(result.output)
        assert envelope["success"] is False
        assert envelope["error"]["code"] == "STALE_SNAPSHOT_CACHE"
        assert envelope["error"]["suggested_action"]
