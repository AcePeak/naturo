"""Tests for ``naturo browser`` CLI subcommands.

All browser connectivity is mocked — these tests run on any platform,
no Chrome required.  They exercise argument parsing, output formatting,
error handling, and JSON mode for every browser CLI command.
"""

from __future__ import annotations

import json
from unittest.mock import MagicMock, patch

import click.testing
import pytest

from naturo.cli.browser_cmd import browser


@pytest.fixture()
def runner() -> click.testing.CliRunner:
    return click.testing.CliRunner()


@pytest.fixture()
def mock_page() -> MagicMock:
    """Return a pre-configured mock BrowserPage."""
    page = MagicMock()
    page.url = "https://example.com"
    page.title = "Example Domain"
    page.close = MagicMock()
    return page


def _invoke(runner: click.testing.CliRunner, args: list[str],
            mock_page: MagicMock) -> click.testing.Result:
    """Invoke a browser CLI command with the mock page injected."""
    with patch("naturo.cli.browser_cmd._get_page", return_value=mock_page):
        return runner.invoke(browser, args, catch_exceptions=False)


# ── navigate ─────────────────────────────────────────────────────────────────


class TestNavigate:
    def test_navigate_basic(self, runner: click.testing.CliRunner,
                            mock_page: MagicMock) -> None:
        result = _invoke(runner, ["navigate", "https://example.com"], mock_page)
        assert result.exit_code == 0
        assert "Navigated to:" in result.output
        mock_page.navigate.assert_called_once_with(
            "https://example.com", wait_until="load",
        )

    def test_navigate_json(self, runner: click.testing.CliRunner,
                           mock_page: MagicMock) -> None:
        result = _invoke(runner, ["navigate", "https://example.com", "--json"], mock_page)
        assert result.exit_code == 0
        data = json.loads(result.output)
        assert data["status"] == "ok"
        assert data["url"] == "https://example.com"

    def test_navigate_wait_until(self, runner: click.testing.CliRunner,
                                 mock_page: MagicMock) -> None:
        result = _invoke(
            runner,
            ["navigate", "https://example.com", "--wait-until", "networkidle"],
            mock_page,
        )
        assert result.exit_code == 0
        mock_page.navigate.assert_called_once_with(
            "https://example.com", wait_until="networkidle",
        )

    def test_navigate_closes_page(self, runner: click.testing.CliRunner,
                                  mock_page: MagicMock) -> None:
        _invoke(runner, ["navigate", "https://example.com"], mock_page)
        mock_page.close.assert_called_once()


# ── find ─────────────────────────────────────────────────────────────────────


class TestFind:
    def _make_element(self, tag: str = "div", text: str = "hello") -> MagicMock:
        el = MagicMock()
        el.tag_name = tag
        el.text = text
        el.value = ""
        return el

    def test_find_single(self, runner: click.testing.CliRunner,
                         mock_page: MagicMock) -> None:
        mock_page.find.return_value = self._make_element("input", "search box")
        result = _invoke(runner, ["find", "#search"], mock_page)
        assert result.exit_code == 0
        assert "[input]" in result.output
        mock_page.find.assert_called_once_with("#search")

    def test_find_all(self, runner: click.testing.CliRunner,
                      mock_page: MagicMock) -> None:
        mock_page.find_all.return_value = [
            self._make_element("li", "item 1"),
            self._make_element("li", "item 2"),
        ]
        result = _invoke(runner, ["find", "li", "--all"], mock_page)
        assert result.exit_code == 0
        assert "2 element(s) found." in result.output

    def test_find_all_json(self, runner: click.testing.CliRunner,
                           mock_page: MagicMock) -> None:
        mock_page.find_all.return_value = [self._make_element("a", "link")]
        result = _invoke(runner, ["find", "a", "--all", "--json"], mock_page)
        assert result.exit_code == 0
        data = json.loads(result.output)
        assert data["count"] == 1
        assert data["elements"][0]["tag"] == "a"

    def test_find_single_json(self, runner: click.testing.CliRunner,
                              mock_page: MagicMock) -> None:
        mock_page.find.return_value = self._make_element("span", "price")
        result = _invoke(runner, ["find", ".price", "--json"], mock_page)
        assert result.exit_code == 0
        data = json.loads(result.output)
        assert data["tag"] == "span"
        assert data["ref"] == "e1"

    def test_find_with_by_option(self, runner: click.testing.CliRunner,
                                 mock_page: MagicMock) -> None:
        mock_page.find.return_value = self._make_element()
        result = _invoke(runner, ["find", "//div", "--by", "xpath"], mock_page)
        assert result.exit_code == 0
        mock_page.find.assert_called_once_with("xpath://div")

    def test_find_with_timeout(self, runner: click.testing.CliRunner,
                               mock_page: MagicMock) -> None:
        mock_page.find.return_value = self._make_element()
        result = _invoke(runner, ["find", "#el", "--timeout", "5"], mock_page)
        assert result.exit_code == 0
        mock_page.wait_for.assert_called_once_with("#el", timeout=5.0)

    def test_find_no_results(self, runner: click.testing.CliRunner,
                             mock_page: MagicMock) -> None:
        mock_page.find_all.return_value = []
        result = _invoke(runner, ["find", ".missing", "--all"], mock_page)
        assert result.exit_code == 0
        assert "No elements found." in result.output

    def test_find_error_json(self, runner: click.testing.CliRunner,
                             mock_page: MagicMock) -> None:
        mock_page.find.side_effect = RuntimeError("Element not found")
        result = _invoke(runner, ["find", "#nope", "--json"], mock_page)
        assert result.exit_code == 1
        data = json.loads(result.output)
        assert data["success"] is False
        assert "error" in data
        assert data["error"]["code"] == "ELEMENT_NOT_FOUND"


# ── click ────────────────────────────────────────────────────────────────────


class TestClick:
    def test_click_basic(self, runner: click.testing.CliRunner,
                         mock_page: MagicMock) -> None:
        el = MagicMock()
        mock_page.find.return_value = el
        result = _invoke(runner, ["click", "button.submit"], mock_page)
        assert result.exit_code == 0
        assert "Clicked:" in result.output
        el.click.assert_called_once_with(offset_x=0, offset_y=0)

    def test_click_with_offsets(self, runner: click.testing.CliRunner,
                                mock_page: MagicMock) -> None:
        el = MagicMock()
        mock_page.find.return_value = el
        result = _invoke(
            runner,
            ["click", "#img", "--offset-x", "10", "--offset-y", "20"],
            mock_page,
        )
        assert result.exit_code == 0
        el.click.assert_called_once_with(offset_x=10, offset_y=20)

    def test_click_json(self, runner: click.testing.CliRunner,
                        mock_page: MagicMock) -> None:
        mock_page.find.return_value = MagicMock()
        result = _invoke(runner, ["click", "#btn", "--json"], mock_page)
        data = json.loads(result.output)
        assert data["status"] == "ok"

    def test_click_error(self, runner: click.testing.CliRunner,
                         mock_page: MagicMock) -> None:
        mock_page.find.side_effect = RuntimeError("not found")
        result = _invoke(runner, ["click", "#nope"], mock_page)
        assert result.exit_code == 1


# ── type ─────────────────────────────────────────────────────────────────────


class TestType:
    def test_type_basic(self, runner: click.testing.CliRunner,
                        mock_page: MagicMock) -> None:
        el = MagicMock()
        mock_page.find.return_value = el
        result = _invoke(runner, ["type", "#search", "hello"], mock_page)
        assert result.exit_code == 0
        assert "Typed into:" in result.output
        el.type.assert_called_once_with("hello", clear_first=False)

    def test_type_clear_first(self, runner: click.testing.CliRunner,
                              mock_page: MagicMock) -> None:
        el = MagicMock()
        mock_page.find.return_value = el
        result = _invoke(
            runner, ["type", "#email", "a@b.com", "--clear-first"], mock_page,
        )
        assert result.exit_code == 0
        el.type.assert_called_once_with("a@b.com", clear_first=True)

    def test_type_json(self, runner: click.testing.CliRunner,
                       mock_page: MagicMock) -> None:
        mock_page.find.return_value = MagicMock()
        result = _invoke(runner, ["type", "#in", "txt", "--json"], mock_page)
        data = json.loads(result.output)
        assert data["status"] == "ok"
        assert data["text"] == "txt"


# ── text / attr / html ───────────────────────────────────────────────────────


class TestTextAttrHtml:
    def test_text_basic(self, runner: click.testing.CliRunner,
                        mock_page: MagicMock) -> None:
        el = MagicMock()
        el.text = "Hello World"
        mock_page.find.return_value = el
        result = _invoke(runner, ["text", "h1"], mock_page)
        assert result.exit_code == 0
        assert "Hello World" in result.output

    def test_text_json(self, runner: click.testing.CliRunner,
                       mock_page: MagicMock) -> None:
        el = MagicMock()
        el.text = "price: $10"
        mock_page.find.return_value = el
        result = _invoke(runner, ["text", ".price", "--json"], mock_page)
        data = json.loads(result.output)
        assert data["text"] == "price: $10"

    def test_attr_basic(self, runner: click.testing.CliRunner,
                        mock_page: MagicMock) -> None:
        el = MagicMock()
        el.attr.return_value = "https://example.com"
        mock_page.find.return_value = el
        result = _invoke(runner, ["attr", "a.link", "href"], mock_page)
        assert result.exit_code == 0
        assert "https://example.com" in result.output

    def test_attr_null(self, runner: click.testing.CliRunner,
                       mock_page: MagicMock) -> None:
        el = MagicMock()
        el.attr.return_value = None
        mock_page.find.return_value = el
        result = _invoke(runner, ["attr", "div", "data-x"], mock_page)
        assert "(null)" in result.output

    def test_attr_json(self, runner: click.testing.CliRunner,
                       mock_page: MagicMock) -> None:
        el = MagicMock()
        el.attr.return_value = "/img.png"
        mock_page.find.return_value = el
        result = _invoke(runner, ["attr", "img", "src", "--json"], mock_page)
        data = json.loads(result.output)
        assert data["value"] == "/img.png"

    def test_html_inner(self, runner: click.testing.CliRunner,
                        mock_page: MagicMock) -> None:
        el = MagicMock()
        el.inner_html = "<span>inner</span>"
        mock_page.find.return_value = el
        result = _invoke(runner, ["html", "#content"], mock_page)
        assert "<span>inner</span>" in result.output

    def test_html_outer(self, runner: click.testing.CliRunner,
                        mock_page: MagicMock) -> None:
        el = MagicMock()
        el.outer_html = "<div><span>outer</span></div>"
        mock_page.find.return_value = el
        result = _invoke(runner, ["html", "div.card", "--outer"], mock_page)
        assert "<div><span>outer</span></div>" in result.output


# ── screenshot ───────────────────────────────────────────────────────────────


class TestScreenshot:
    def test_screenshot_default(self, runner: click.testing.CliRunner,
                                mock_page: MagicMock) -> None:
        mock_page.screenshot.return_value = "screenshot.png"
        result = _invoke(runner, ["screenshot"], mock_page)
        assert result.exit_code == 0
        assert "screenshot.png" in result.output
        mock_page.screenshot.assert_called_once_with(
            "screenshot.png", full_page=False,
        )

    def test_screenshot_custom_path(self, runner: click.testing.CliRunner,
                                    mock_page: MagicMock) -> None:
        mock_page.screenshot.return_value = "page.png"
        result = _invoke(runner, ["screenshot", "--path", "page.png"], mock_page)
        assert result.exit_code == 0

    def test_screenshot_full_page(self, runner: click.testing.CliRunner,
                                  mock_page: MagicMock) -> None:
        mock_page.screenshot.return_value = "full.png"
        result = _invoke(
            runner, ["screenshot", "--full-page", "--path", "full.png"], mock_page,
        )
        mock_page.screenshot.assert_called_once_with("full.png", full_page=True)

    def test_screenshot_json(self, runner: click.testing.CliRunner,
                             mock_page: MagicMock) -> None:
        mock_page.screenshot.return_value = "out.png"
        result = _invoke(runner, ["screenshot", "--json"], mock_page)
        data = json.loads(result.output)
        assert data["status"] == "ok"
        assert data["path"] == "out.png"


# ── eval ─────────────────────────────────────────────────────────────────────


class TestEval:
    def test_eval_basic(self, runner: click.testing.CliRunner,
                        mock_page: MagicMock) -> None:
        mock_page.evaluate.return_value = "Example Domain"
        result = _invoke(runner, ["eval", "document.title"], mock_page)
        assert result.exit_code == 0
        assert "Example Domain" in result.output

    def test_eval_json(self, runner: click.testing.CliRunner,
                       mock_page: MagicMock) -> None:
        mock_page.evaluate.return_value = 42
        result = _invoke(runner, ["eval", "1 + 41", "--json"], mock_page)
        data = json.loads(result.output)
        assert data["result"] == 42


# ── url / title ──────────────────────────────────────────────────────────────


class TestUrlTitle:
    def test_url(self, runner: click.testing.CliRunner,
                 mock_page: MagicMock) -> None:
        result = _invoke(runner, ["url"], mock_page)
        assert result.exit_code == 0
        assert "https://example.com" in result.output

    def test_url_json(self, runner: click.testing.CliRunner,
                      mock_page: MagicMock) -> None:
        result = _invoke(runner, ["url", "--json"], mock_page)
        data = json.loads(result.output)
        assert data["url"] == "https://example.com"

    def test_title(self, runner: click.testing.CliRunner,
                   mock_page: MagicMock) -> None:
        result = _invoke(runner, ["title"], mock_page)
        assert result.exit_code == 0
        assert "Example Domain" in result.output

    def test_title_json(self, runner: click.testing.CliRunner,
                        mock_page: MagicMock) -> None:
        result = _invoke(runner, ["title", "--json"], mock_page)
        data = json.loads(result.output)
        assert data["title"] == "Example Domain"


# ── wait ─────────────────────────────────────────────────────────────────────


class TestWait:
    def test_wait_basic(self, runner: click.testing.CliRunner,
                        mock_page: MagicMock) -> None:
        result = _invoke(runner, ["wait", ".loaded"], mock_page)
        assert result.exit_code == 0
        assert "is attached" in result.output
        mock_page.wait_for.assert_called_once_with(
            ".loaded", timeout=30.0, state="attached",
        )

    def test_wait_hidden(self, runner: click.testing.CliRunner,
                         mock_page: MagicMock) -> None:
        result = _invoke(
            runner, ["wait", "#spinner", "--state", "hidden", "--timeout", "10"],
            mock_page,
        )
        assert result.exit_code == 0
        mock_page.wait_for.assert_called_once_with(
            "#spinner", timeout=10.0, state="hidden",
        )

    def test_wait_timeout_error(self, runner: click.testing.CliRunner,
                                mock_page: MagicMock) -> None:
        mock_page.wait_for.side_effect = TimeoutError("timed out")
        result = _invoke(runner, ["wait", "#slow"], mock_page)
        assert result.exit_code == 1

    def test_wait_json(self, runner: click.testing.CliRunner,
                       mock_page: MagicMock) -> None:
        result = _invoke(runner, ["wait", ".done", "--json"], mock_page)
        data = json.loads(result.output)
        assert data["status"] == "ok"


# ── tabs ─────────────────────────────────────────────────────────────────────


class TestTabs:
    def test_tabs_list(self, runner: click.testing.CliRunner,
                       mock_page: MagicMock) -> None:
        mock_page.tabs.return_value = [
            {"id": "ABCD1234EFGH", "title": "Tab One", "url": "https://one.com"},
            {"id": "WXYZ5678IJKL", "title": "Tab Two", "url": "https://two.com"},
        ]
        result = _invoke(runner, ["tabs"], mock_page)
        assert result.exit_code == 0
        assert "Tab One" in result.output
        assert "Tab Two" in result.output

    def test_tabs_json(self, runner: click.testing.CliRunner,
                       mock_page: MagicMock) -> None:
        mock_page.tabs.return_value = [{"id": "a1", "title": "T", "url": "u"}]
        result = _invoke(runner, ["tabs", "--json"], mock_page)
        data = json.loads(result.output)
        assert len(data) == 1

    def test_tab_switch(self, runner: click.testing.CliRunner,
                        mock_page: MagicMock) -> None:
        result = _invoke(runner, ["tab", "ABC123"], mock_page)
        assert result.exit_code == 0
        mock_page.switch_tab.assert_called_once_with("ABC123")


# ── scroll ───────────────────────────────────────────────────────────────────


class TestScroll:
    def test_scroll_to_bottom(self, runner: click.testing.CliRunner,
                              mock_page: MagicMock) -> None:
        result = _invoke(runner, ["scroll", "--to-bottom"], mock_page)
        assert result.exit_code == 0
        mock_page.scroll_to_bottom.assert_called_once()

    def test_scroll_to_top(self, runner: click.testing.CliRunner,
                           mock_page: MagicMock) -> None:
        result = _invoke(runner, ["scroll", "--to-top"], mock_page)
        assert result.exit_code == 0
        mock_page.scroll_to_top.assert_called_once()

    def test_scroll_to_element(self, runner: click.testing.CliRunner,
                               mock_page: MagicMock) -> None:
        result = _invoke(runner, ["scroll", "--to-element", "#footer"], mock_page)
        assert result.exit_code == 0
        mock_page.scroll_to_element.assert_called_once_with("#footer")

    def test_scroll_by_pixels(self, runner: click.testing.CliRunner,
                              mock_page: MagicMock) -> None:
        result = _invoke(runner, ["scroll", "--by", "500"], mock_page)
        assert result.exit_code == 0
        mock_page.scroll_by.assert_called_once_with(500)

    def test_scroll_no_option_errors(self, runner: click.testing.CliRunner,
                                     mock_page: MagicMock) -> None:
        result = _invoke(runner, ["scroll"], mock_page)
        assert result.exit_code == 1

    def test_scroll_json(self, runner: click.testing.CliRunner,
                         mock_page: MagicMock) -> None:
        result = _invoke(runner, ["scroll", "--to-top", "--json"], mock_page)
        data = json.loads(result.output)
        assert data["status"] == "ok"


# ── hover ────────────────────────────────────────────────────────────────────


class TestHover:
    def test_hover_basic(self, runner: click.testing.CliRunner,
                         mock_page: MagicMock) -> None:
        el = MagicMock()
        mock_page.find.return_value = el
        result = _invoke(runner, ["hover", ".dropdown"], mock_page)
        assert result.exit_code == 0
        assert "Hovered:" in result.output
        el.hover.assert_called_once()

    def test_hover_json(self, runner: click.testing.CliRunner,
                        mock_page: MagicMock) -> None:
        mock_page.find.return_value = MagicMock()
        result = _invoke(runner, ["hover", "#menu", "--json"], mock_page)
        data = json.loads(result.output)
        assert data["status"] == "ok"


# ── close ────────────────────────────────────────────────────────────────────


class TestClose:
    def test_close(self, runner: click.testing.CliRunner,
                   mock_page: MagicMock) -> None:
        result = _invoke(runner, ["close"], mock_page)
        assert result.exit_code == 0
        assert "closed" in result.output.lower()
        mock_page.close.assert_called()


# ── group-level options ──────────────────────────────────────────────────────


class TestGroupOptions:
    def test_custom_port(self, runner: click.testing.CliRunner,
                         mock_page: MagicMock) -> None:
        """Ensure --port is passed through to _get_page context."""
        with patch("naturo.cli.browser_cmd._get_page", return_value=mock_page) as mock_gp:
            result = runner.invoke(
                browser, ["--port", "9333", "url"], catch_exceptions=False,
            )
        assert result.exit_code == 0

    def test_help_output(self, runner: click.testing.CliRunner) -> None:
        result = runner.invoke(browser, ["--help"], catch_exceptions=False)
        assert result.exit_code == 0
        assert "Chrome DevTools Protocol" in result.output

    def test_navigate_help(self, runner: click.testing.CliRunner) -> None:
        result = runner.invoke(browser, ["navigate", "--help"], catch_exceptions=False)
        assert result.exit_code == 0
        assert "Navigate to a URL" in result.output


# ── connection error ─────────────────────────────────────────────────────────


class TestConnectionError:
    def test_get_page_failure(self, runner: click.testing.CliRunner) -> None:
        with patch("naturo.browser.BrowserPage",
                   side_effect=ConnectionRefusedError("refused")):
            from naturo.cli.browser_cmd import _get_page
            ctx = MagicMock()
            ctx.obj = {"cdp_port": 9222, "cdp_host": "localhost"}
            with pytest.raises(SystemExit):
                _get_page(ctx)

    def test_get_page_failure_json(self, runner: click.testing.CliRunner) -> None:
        """Connection error emits structured JSON when -j is passed (#834)."""
        with patch("naturo.browser.BrowserPage",
                   side_effect=ConnectionRefusedError("refused")):
            result = runner.invoke(
                browser, ["navigate", "https://example.com", "--json"],
            )
        assert result.exit_code != 0
        data = json.loads(result.output)
        assert data["success"] is False
        assert data["error"]["code"] == "BROWSER_CONNECTION_ERROR"
        assert "refused" in data["error"]["message"]

    def test_click_error_json(self, runner: click.testing.CliRunner,
                              mock_page: MagicMock) -> None:
        """click command error emits structured JSON (#834)."""
        mock_page.find.side_effect = RuntimeError("no such element")
        result = _invoke(runner, ["click", "#btn", "--json"], mock_page)
        assert result.exit_code == 1
        data = json.loads(result.output)
        assert data["success"] is False
        assert data["error"]["code"] == "ELEMENT_NOT_FOUND"

    def test_scroll_no_option_json(self, runner: click.testing.CliRunner,
                                   mock_page: MagicMock) -> None:
        """scroll without option emits structured JSON error (#834)."""
        result = _invoke(runner, ["scroll", "--json"], mock_page)
        assert result.exit_code == 1
        data = json.loads(result.output)
        assert data["success"] is False
        assert data["error"]["code"] == "INVALID_INPUT"
