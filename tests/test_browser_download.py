"""Tests for naturo.browser._download — file download management."""

from __future__ import annotations

import json
import os
import time
from unittest.mock import MagicMock, patch

import pytest
from click.testing import CliRunner

from naturo.browser._download import (
    set_download_dir,
    wait_for_download,
    _is_partial,
    _list_files,
)
from naturo.cli.browser_cmd import browser


# ---------------------------------------------------------------------------
# set_download_dir
# ---------------------------------------------------------------------------


class TestSetDownloadDir:
    """Test download directory configuration."""

    def test_sets_download_behavior(self, tmp_path):
        """Sends Browser.setDownloadBehavior with correct path."""
        mock_page = MagicMock()
        mock_page._cdp = MagicMock()

        set_download_dir(mock_page, str(tmp_path))

        mock_page._cdp.send.assert_called_once_with(
            "Browser.setDownloadBehavior",
            {
                "behavior": "allow",
                "downloadPath": str(tmp_path),
            },
        )

    def test_rejects_nonexistent_directory(self):
        """Raises ValueError for missing directory."""
        mock_page = MagicMock()
        with pytest.raises(ValueError, match="does not exist"):
            set_download_dir(mock_page, "/nonexistent/path/xyz")

    def test_resolves_relative_path(self, tmp_path, monkeypatch):
        """Resolves relative paths to absolute."""
        mock_page = MagicMock()
        mock_page._cdp = MagicMock()
        monkeypatch.chdir(tmp_path)
        subdir = tmp_path / "downloads"
        subdir.mkdir()

        set_download_dir(mock_page, "downloads")

        call_args = mock_page._cdp.send.call_args[0]
        assert os.path.isabs(call_args[1]["downloadPath"])


# ---------------------------------------------------------------------------
# wait_for_download
# ---------------------------------------------------------------------------


class TestWaitForDownload:
    """Test download wait logic."""

    def test_detects_new_file(self, tmp_path):
        """Returns path when a new file appears."""
        # Simulate file appearing after short delay
        def create_file():
            time.sleep(0.2)
            (tmp_path / "report.pdf").write_bytes(b"PDF content")

        import threading
        t = threading.Thread(target=create_file)
        t.start()

        result = wait_for_download(str(tmp_path), timeout=5, poll_interval=0.1)
        t.join()

        assert result.endswith("report.pdf")
        assert os.path.isabs(result)

    def test_waits_for_partial_to_complete(self, tmp_path):
        """Waits for .crdownload file to become the final file."""
        # Create partial file first
        partial = tmp_path / "file.zip.crdownload"
        partial.write_bytes(b"partial")

        def finish_download():
            time.sleep(0.3)
            partial.unlink()
            (tmp_path / "file.zip").write_bytes(b"complete")

        import threading
        t = threading.Thread(target=finish_download)
        t.start()

        result = wait_for_download(str(tmp_path), timeout=5, poll_interval=0.1)
        t.join()

        assert result.endswith("file.zip")

    def test_timeout_no_new_file(self, tmp_path):
        """Raises TimeoutError when no file appears."""
        with pytest.raises(TimeoutError, match="No new file appeared"):
            wait_for_download(str(tmp_path), timeout=0.3, poll_interval=0.1)

    def test_timeout_stuck_partial(self, tmp_path):
        """Raises TimeoutError when partial never completes."""
        # Create a partial that never finishes
        def create_partial():
            time.sleep(0.1)
            (tmp_path / "stuck.zip.crdownload").write_bytes(b"partial")

        import threading
        t = threading.Thread(target=create_partial)
        t.start()

        with pytest.raises(TimeoutError, match="did not complete"):
            wait_for_download(str(tmp_path), timeout=0.5, poll_interval=0.1)
        t.join()

    def test_rejects_nonexistent_directory(self):
        """Raises ValueError for missing directory."""
        with pytest.raises(ValueError, match="does not exist"):
            wait_for_download("/nonexistent/xyz", timeout=1)

    def test_ignores_preexisting_files(self, tmp_path):
        """Does not return files that existed before the call."""
        (tmp_path / "old.txt").write_bytes(b"existing")

        def create_new():
            time.sleep(0.2)
            (tmp_path / "new.txt").write_bytes(b"new")

        import threading
        t = threading.Thread(target=create_new)
        t.start()

        result = wait_for_download(str(tmp_path), timeout=5, poll_interval=0.1)
        t.join()

        assert result.endswith("new.txt")


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


class TestHelpers:
    """Test helper functions."""

    def test_is_partial_crdownload(self):
        assert _is_partial("file.zip.crdownload") is True

    def test_is_partial_tmp(self):
        assert _is_partial("data.tmp") is True

    def test_is_partial_part(self):
        assert _is_partial("file.part") is True

    def test_is_not_partial(self):
        assert _is_partial("report.pdf") is False
        assert _is_partial("data.csv") is False

    def test_list_files_empty(self, tmp_path):
        assert _list_files(str(tmp_path)) == set()

    def test_list_files_ignores_dirs(self, tmp_path):
        (tmp_path / "subdir").mkdir()
        (tmp_path / "file.txt").write_bytes(b"data")
        result = _list_files(str(tmp_path))
        assert result == {"file.txt"}

    def test_list_files_nonexistent(self):
        assert _list_files("/nonexistent/xyz") == set()


# ---------------------------------------------------------------------------
# CLI command
# ---------------------------------------------------------------------------


class TestDownloadCLI:
    """Test browser download CLI command."""

    @pytest.fixture
    def runner(self):
        return CliRunner()

    def test_download_set_dir(self, runner, tmp_path):
        """browser download --dir sets the directory."""
        mock_page = MagicMock()
        with patch("naturo.cli.browser_cmd._get_page", return_value=mock_page), \
             patch("naturo.browser._download.set_download_dir") as mock_set:
            result = runner.invoke(
                browser, ["download", "--dir", str(tmp_path)]
            )
        assert result.exit_code == 0
        assert "Download directory set" in result.output
        mock_set.assert_called_once()
        mock_page.close.assert_called_once()

    def test_download_set_dir_json(self, runner, tmp_path):
        """browser download --dir --json outputs JSON."""
        mock_page = MagicMock()
        with patch("naturo.cli.browser_cmd._get_page", return_value=mock_page), \
             patch("naturo.browser._download.set_download_dir"):
            result = runner.invoke(
                browser, ["download", "--dir", str(tmp_path), "--json"]
            )
        assert result.exit_code == 0
        data = json.loads(result.output)
        assert data["success"] is True
        assert "download_dir" in data

    def test_download_wait_success(self, runner, tmp_path):
        """browser download --dir --wait reports downloaded file."""
        mock_page = MagicMock()
        fake_path = str(tmp_path / "report.pdf")
        with patch("naturo.cli.browser_cmd._get_page", return_value=mock_page), \
             patch("naturo.browser._download.set_download_dir"), \
             patch("naturo.browser._download.wait_for_download", return_value=fake_path):
            result = runner.invoke(
                browser, ["download", "--dir", str(tmp_path), "--wait"]
            )
        assert result.exit_code == 0
        assert "report.pdf" in result.output

    def test_download_wait_json(self, runner, tmp_path):
        """browser download --dir --wait --json returns file info."""
        mock_page = MagicMock()
        fake_path = str(tmp_path / "data.csv")
        with patch("naturo.cli.browser_cmd._get_page", return_value=mock_page), \
             patch("naturo.browser._download.set_download_dir"), \
             patch("naturo.browser._download.wait_for_download", return_value=fake_path):
            result = runner.invoke(
                browser, ["download", "--dir", str(tmp_path), "--wait", "--json"]
            )
        assert result.exit_code == 0
        data = json.loads(result.output)
        assert data["success"] is True
        assert data["filename"] == "data.csv"

    def test_download_wait_timeout(self, runner, tmp_path):
        """browser download --wait exits 1 on timeout."""
        mock_page = MagicMock()
        with patch("naturo.cli.browser_cmd._get_page", return_value=mock_page), \
             patch("naturo.browser._download.set_download_dir"), \
             patch("naturo.browser._download.wait_for_download",
                   side_effect=TimeoutError("No new file")):
            result = runner.invoke(
                browser, ["download", "--dir", str(tmp_path), "--wait"]
            )
        assert result.exit_code != 0

    def test_download_wait_timeout_json(self, runner, tmp_path):
        """browser download --wait --json reports timeout in JSON."""
        mock_page = MagicMock()
        with patch("naturo.cli.browser_cmd._get_page", return_value=mock_page), \
             patch("naturo.browser._download.set_download_dir"), \
             patch("naturo.browser._download.wait_for_download",
                   side_effect=TimeoutError("No new file")):
            result = runner.invoke(
                browser, ["download", "--dir", str(tmp_path), "--wait", "--json"]
            )
        assert result.exit_code != 0
        data = json.loads(result.output)
        assert data["success"] is False

    def test_download_help(self, runner):
        """browser download --help shows usage."""
        result = runner.invoke(browser, ["download", "--help"])
        assert result.exit_code == 0
        assert "--dir" in result.output
        assert "--wait" in result.output
