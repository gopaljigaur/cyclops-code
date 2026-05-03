import asyncio
from pathlib import Path
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from cyclops_code.tools.bash import BashTool
from cyclops_code.tools.edit import EditTool
from cyclops_code.tools.glob import GlobTool
from cyclops_code.tools.grep import GrepTool
from cyclops_code.tools.read import ReadTool
from cyclops_code.tools.web_fetch import WebFetchTool
from cyclops_code.tools.write import WriteTool


# ---------------------------------------------------------------------------
# ReadTool
# ---------------------------------------------------------------------------


class TestReadTool:
    async def test_reads_file_with_line_numbers(self, tmp_path: Path) -> None:
        f = tmp_path / "hello.txt"
        f.write_text("alpha\nbeta\ngamma\n")

        tool = ReadTool()
        result = await tool.execute(path=str(f))

        assert "   1: alpha" in result
        assert "   2: beta" in result
        assert "   3: gamma" in result

    async def test_error_on_missing_file(self, tmp_path: Path) -> None:
        tool = ReadTool()
        result = await tool.execute(path=str(tmp_path / "nonexistent.txt"))

        assert "Error" in result
        assert "not found" in result

    async def test_respects_line_range(self, tmp_path: Path) -> None:
        f = tmp_path / "lines.txt"
        f.write_text("\n".join(f"line{i}" for i in range(1, 11)))

        tool = ReadTool()
        result = await tool.execute(path=str(f), start_line=3, end_line=5)

        assert "line3" in result
        assert "line5" in result
        assert "line1" not in result
        assert "line6" not in result

    async def test_truncates_at_max_lines(self, tmp_path: Path) -> None:
        f = tmp_path / "big.txt"
        f.write_text("\n".join(f"line{i}" for i in range(1, 2100)))

        tool = ReadTool()
        result = await tool.execute(path=str(f))

        assert "Truncated" in result


# ---------------------------------------------------------------------------
# WriteTool
# ---------------------------------------------------------------------------


class TestWriteTool:
    async def test_creates_file_with_content(self, tmp_path: Path) -> None:
        target = tmp_path / "output.txt"
        tool = WriteTool()
        result = await tool.execute(path=str(target), content="hello world\n")

        assert target.exists()
        assert target.read_text() == "hello world\n"
        assert "Wrote" in result
        assert str(target) in result

    async def test_creates_parent_directories(self, tmp_path: Path) -> None:
        target = tmp_path / "a" / "b" / "c" / "file.txt"
        tool = WriteTool()
        await tool.execute(path=str(target), content="nested\n")

        assert target.exists()

    async def test_overwrites_existing_file(self, tmp_path: Path) -> None:
        target = tmp_path / "existing.txt"
        target.write_text("old content\n")

        tool = WriteTool()
        await tool.execute(path=str(target), content="new content\n")

        assert target.read_text() == "new content\n"

    async def test_reports_correct_line_count(self, tmp_path: Path) -> None:
        target = tmp_path / "lines.txt"
        tool = WriteTool()
        result = await tool.execute(path=str(target), content="a\nb\nc\n")

        assert "3" in result


# ---------------------------------------------------------------------------
# EditTool
# ---------------------------------------------------------------------------


class TestEditTool:
    async def test_replaces_unique_match(self, tmp_path: Path) -> None:
        f = tmp_path / "code.py"
        f.write_text("def foo():\n    return 1\n")

        tool = EditTool()
        result = await tool.execute(
            path=str(f),
            old_string="return 1",
            new_string="return 42",
        )

        assert result == f"Edited {f}"
        assert f.read_text() == "def foo():\n    return 42\n"

    async def test_error_on_zero_matches(self, tmp_path: Path) -> None:
        f = tmp_path / "code.py"
        f.write_text("def foo():\n    pass\n")

        tool = EditTool()
        result = await tool.execute(
            path=str(f),
            old_string="return 999",
            new_string="return 0",
        )

        assert "Error" in result
        assert "not found" in result

    async def test_error_on_multiple_matches(self, tmp_path: Path) -> None:
        f = tmp_path / "code.py"
        f.write_text("x = 1\ny = 1\n")

        tool = EditTool()
        result = await tool.execute(
            path=str(f),
            old_string="= 1",
            new_string="= 2",
        )

        assert "Error" in result
        assert "2" in result

    async def test_error_on_missing_file(self, tmp_path: Path) -> None:
        tool = EditTool()
        result = await tool.execute(
            path=str(tmp_path / "missing.py"),
            old_string="foo",
            new_string="bar",
        )

        assert "Error" in result


# ---------------------------------------------------------------------------
# BashTool
# ---------------------------------------------------------------------------


class TestBashTool:
    async def test_runs_echo(self) -> None:
        tool = BashTool()
        result = await tool.execute(command="echo hello")

        assert "hello" in result
        assert "[exit 0]" in result

    async def test_captures_stderr(self) -> None:
        tool = BashTool()
        result = await tool.execute(command="echo oops >&2")

        assert "oops" in result

    async def test_respects_timeout(self) -> None:
        tool = BashTool()
        result = await tool.execute(command="sleep 10", timeout=1)

        assert "timed out" in result.lower()

    async def test_nonzero_exit_code(self) -> None:
        tool = BashTool()
        result = await tool.execute(command="exit 42")

        assert "[exit 42]" in result


# ---------------------------------------------------------------------------
# GlobTool
# ---------------------------------------------------------------------------


class TestGlobTool:
    async def test_finds_files_by_pattern(self, tmp_path: Path) -> None:
        (tmp_path / "a.py").write_text("")
        (tmp_path / "b.py").write_text("")
        (tmp_path / "c.txt").write_text("")

        tool = GlobTool()
        result = await tool.execute(pattern="*.py", path=str(tmp_path))

        assert "a.py" in result
        assert "b.py" in result
        assert "c.txt" not in result

    async def test_skips_excluded_dirs(self, tmp_path: Path) -> None:
        excluded = tmp_path / "node_modules"
        excluded.mkdir()
        (excluded / "dep.py").write_text("")
        (tmp_path / "main.py").write_text("")

        tool = GlobTool()
        result = await tool.execute(pattern="**/*.py", path=str(tmp_path))

        assert "main.py" in result
        assert "dep.py" not in result

    async def test_no_results(self, tmp_path: Path) -> None:
        tool = GlobTool()
        result = await tool.execute(pattern="*.nonexistent", path=str(tmp_path))

        assert "No files" in result


# ---------------------------------------------------------------------------
# GrepTool
# ---------------------------------------------------------------------------


class TestGrepTool:
    async def test_finds_pattern(self, tmp_path: Path) -> None:
        f = tmp_path / "src.py"
        f.write_text("def hello():\n    print('hello world')\n")

        tool = GrepTool()
        result = await tool.execute(pattern="hello", path=str(tmp_path))

        assert "src.py" in result
        assert "hello" in result

    async def test_returns_path_line_content_format(self, tmp_path: Path) -> None:
        f = tmp_path / "code.py"
        f.write_text("x = 42\n")

        tool = GrepTool()
        result = await tool.execute(pattern="42", path=str(tmp_path))

        assert "code.py:1:" in result

    async def test_no_matches(self, tmp_path: Path) -> None:
        (tmp_path / "empty.py").write_text("pass\n")

        tool = GrepTool()
        result = await tool.execute(pattern="ZZZNOTHERE", path=str(tmp_path))

        assert "No matches" in result

    async def test_include_filter(self, tmp_path: Path) -> None:
        (tmp_path / "match.py").write_text("target = 1\n")
        (tmp_path / "skip.txt").write_text("target = 1\n")

        tool = GrepTool()
        result = await tool.execute(pattern="target", path=str(tmp_path), include="*.py")

        assert "match.py" in result
        assert "skip.txt" not in result

    async def test_invalid_regex(self, tmp_path: Path) -> None:
        tool = GrepTool()
        result = await tool.execute(pattern="[invalid", path=str(tmp_path))

        assert "Error" in result


# ---------------------------------------------------------------------------
# WebFetchTool
# ---------------------------------------------------------------------------


class TestWebFetchTool:
    async def test_fetches_and_returns_content(self) -> None:
        mock_response = MagicMock()
        mock_response.headers = {"content-type": "text/plain"}
        mock_response.text = "Hello from the web"
        mock_response.raise_for_status = MagicMock()

        mock_client = AsyncMock()
        mock_client.__aenter__ = AsyncMock(return_value=mock_client)
        mock_client.__aexit__ = AsyncMock(return_value=False)
        mock_client.get = AsyncMock(return_value=mock_response)

        with patch("cyclops_code.tools.web_fetch.httpx.AsyncClient", return_value=mock_client):
            tool = WebFetchTool()
            result = await tool.execute(url="https://example.com")

        assert "https://example.com" in result
        assert "Hello from the web" in result

    async def test_strips_html_tags(self) -> None:
        mock_response = MagicMock()
        mock_response.headers = {"content-type": "text/html"}
        mock_response.text = "<html><body><h1>Title</h1><p>Body text</p></body></html>"
        mock_response.raise_for_status = MagicMock()

        mock_client = AsyncMock()
        mock_client.__aenter__ = AsyncMock(return_value=mock_client)
        mock_client.__aexit__ = AsyncMock(return_value=False)
        mock_client.get = AsyncMock(return_value=mock_response)

        with patch("cyclops_code.tools.web_fetch.httpx.AsyncClient", return_value=mock_client):
            tool = WebFetchTool()
            result = await tool.execute(url="https://example.com")

        assert "<html>" not in result
        assert "Title" in result
        assert "Body text" in result

    async def test_handles_timeout(self) -> None:
        import httpx

        mock_client = AsyncMock()
        mock_client.__aenter__ = AsyncMock(return_value=mock_client)
        mock_client.__aexit__ = AsyncMock(return_value=False)
        mock_client.get = AsyncMock(side_effect=httpx.TimeoutException("timeout"))

        with patch("cyclops_code.tools.web_fetch.httpx.AsyncClient", return_value=mock_client):
            tool = WebFetchTool()
            result = await tool.execute(url="https://slow.example.com")

        assert "Error" in result
        assert "timed out" in result
