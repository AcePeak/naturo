"""Tests for naturo.bridge._errors — NaturoCoreError."""

import pytest

from naturo.bridge._errors import NaturoCoreError


class TestNaturoCoreError:
    """Tests for the NaturoCoreError exception class."""

    def test_known_error_code_invalid_argument(self):
        err = NaturoCoreError(-1)
        assert err.code == -1
        assert "Invalid argument" in str(err)

    def test_known_error_code_system_error(self):
        err = NaturoCoreError(-2)
        assert err.code == -2
        assert "System/COM error" in str(err)

    def test_known_error_code_file_io(self):
        err = NaturoCoreError(-3)
        assert err.code == -3
        assert "File I/O error" in str(err)

    def test_known_error_code_buffer_small(self):
        err = NaturoCoreError(-4)
        assert err.code == -4
        assert "Buffer too small" in str(err)

    def test_unknown_error_code(self):
        err = NaturoCoreError(-99)
        assert err.code == -99
        assert "Unknown error (-99)" in str(err)

    def test_with_context(self):
        err = NaturoCoreError(-1, context="get_element_tree")
        assert "get_element_tree" in str(err)
        assert "Invalid argument" in str(err)

    def test_without_context(self):
        err = NaturoCoreError(-2)
        # Should not have ": " prefix from empty context
        msg = str(err)
        assert not msg.startswith(":")

    def test_is_exception(self):
        err = NaturoCoreError(-1)
        assert isinstance(err, Exception)

    def test_can_be_raised_and_caught(self):
        with pytest.raises(NaturoCoreError) as exc_info:
            raise NaturoCoreError(-3, context="read_file")
        assert exc_info.value.code == -3
        assert "read_file" in str(exc_info.value)

    def test_error_messages_dict_completeness(self):
        """All documented error codes should be in the map."""
        assert -1 in NaturoCoreError.ERROR_MESSAGES
        assert -2 in NaturoCoreError.ERROR_MESSAGES
        assert -3 in NaturoCoreError.ERROR_MESSAGES
        assert -4 in NaturoCoreError.ERROR_MESSAGES
