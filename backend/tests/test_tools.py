"""Unit tests for agent tools.

Tests the tool definitions (schema validation) and tool execution
functions using a mock sandbox. We don't need Docker running for
these tests — the sandbox is mocked.
"""

import pytest

from app.agent.tools import (
    TOOL_DEFINITIONS,
    execute_tool,
    tool_git_diff,
    tool_read_file,
    tool_run_tests,
    tool_search_code,
    tool_write_patch,
)

# --- Mock Sandbox ---


class MockSandbox:
    """A mock DockerSandbox for testing tool functions without Docker."""

    def __init__(self, responses: dict[str, tuple[int, str]] | None = None):
        """
        Args:
            responses: Dict mapping command substrings to (exit_code, output) tuples.
                       If a command matches multiple keys, the first match is used.
        """
        self.responses = responses or {}
        self.exec_log: list[str] = []

    async def exec(self, cmd: str, timeout: int = 120) -> tuple[int, str]:
        """Mock command execution."""
        self.exec_log.append(cmd)

        for key, response in self.responses.items():
            if key in cmd:
                return response

        # Default: success with empty output
        return 0, ""


# --- Tool Definition Tests ---


class TestToolDefinitions:
    """Validate the tool JSON schemas match OpenAI's format."""

    def test_tool_count(self):
        """Should have exactly 5 tools."""
        assert len(TOOL_DEFINITIONS) == 5

    def test_tool_names(self):
        """All expected tool names should be present."""
        names = {t["function"]["name"] for t in TOOL_DEFINITIONS}
        assert names == {"read_file", "search_code", "write_patch", "run_tests", "git_diff"}

    def test_tool_structure(self):
        """Each tool should have the required OpenAI schema fields."""
        for tool in TOOL_DEFINITIONS:
            assert tool["type"] == "function"
            func = tool["function"]
            assert "name" in func
            assert "description" in func
            assert "parameters" in func
            assert func["parameters"]["type"] == "object"

    def test_read_file_requires_path(self):
        """read_file should require the 'path' parameter."""
        tool = next(t for t in TOOL_DEFINITIONS if t["function"]["name"] == "read_file")
        assert "path" in tool["function"]["parameters"]["required"]

    def test_search_code_requires_pattern(self):
        """search_code should require the 'pattern' parameter."""
        tool = next(t for t in TOOL_DEFINITIONS if t["function"]["name"] == "search_code")
        assert "pattern" in tool["function"]["parameters"]["required"]

    def test_write_patch_requires_diff(self):
        """write_patch should require the 'diff' parameter."""
        tool = next(t for t in TOOL_DEFINITIONS if t["function"]["name"] == "write_patch")
        assert "diff" in tool["function"]["parameters"]["required"]

    def test_run_tests_requires_command(self):
        """run_tests should require the 'command' parameter."""
        tool = next(t for t in TOOL_DEFINITIONS if t["function"]["name"] == "run_tests")
        assert "command" in tool["function"]["parameters"]["required"]

    def test_git_diff_no_required_params(self):
        """git_diff should have no required parameters."""
        tool = next(t for t in TOOL_DEFINITIONS if t["function"]["name"] == "git_diff")
        assert tool["function"]["parameters"]["required"] == []


# --- Tool Execution Tests ---


class TestReadFile:
    @pytest.mark.asyncio
    async def test_read_file_success(self):
        sandbox = MockSandbox({"cat": (0, "file contents here\n")})
        result = await tool_read_file("src/main.py", sandbox)
        assert result == "file contents here\n"
        assert "/workspace/src/main.py" in sandbox.exec_log[0]

    @pytest.mark.asyncio
    async def test_read_file_not_found(self):
        sandbox = MockSandbox({"cat": (1, "No such file or directory")})
        result = await tool_read_file("nonexistent.py", sandbox)
        assert "Error" in result

    @pytest.mark.asyncio
    async def test_read_file_path_traversal_prevention(self):
        sandbox = MockSandbox({"cat": (0, "contents")})
        await tool_read_file("../../etc/passwd", sandbox)
        # Should sanitize the path
        cmd = sandbox.exec_log[0]
        assert ".." not in cmd

    @pytest.mark.asyncio
    async def test_read_file_truncation(self):
        long_content = "x" * 60_000
        sandbox = MockSandbox({"cat": (0, long_content)})
        result = await tool_read_file("big_file.py", sandbox)
        assert "truncated" in result
        assert len(result) < 60_000


class TestSearchCode:
    @pytest.mark.asyncio
    async def test_search_code_with_results(self):
        output = "src/main.py:10: def fix_bug():\nsrc/utils.py:5: # bug fix\n"
        sandbox = MockSandbox({"rg": (0, output)})
        result = await tool_search_code("fix_bug", sandbox)
        assert "fix_bug" in result

    @pytest.mark.asyncio
    async def test_search_code_no_results(self):
        sandbox = MockSandbox({"rg": (1, "")})
        result = await tool_search_code("nonexistent_pattern", sandbox)
        assert "No matches" in result

    @pytest.mark.asyncio
    async def test_search_code_with_glob(self):
        sandbox = MockSandbox({"rg": (0, "match")})
        await tool_search_code("pattern", sandbox, file_glob="*.py")
        cmd = sandbox.exec_log[0]
        assert "--glob" in cmd
        assert "*.py" in cmd


class TestWritePatch:
    @pytest.mark.asyncio
    async def test_write_patch_success(self):
        sandbox = MockSandbox({
            "sh -c": (0, ""),
            "git apply --check": (0, ""),
            "git apply /tmp": (0, ""),
            "git diff": (0, " main.py | 2 +-\n"),
        })
        diff = "--- a/main.py\n+++ b/main.py\n@@ -1 +1 @@\n-old\n+new\n"
        result = await tool_write_patch(diff, sandbox)
        assert "successfully" in result

    @pytest.mark.asyncio
    async def test_write_patch_validation_failure(self):
        sandbox = MockSandbox({
            "sh -c": (0, ""),
            "git apply --check": (1, "error: patch does not apply"),
        })
        result = await tool_write_patch("bad diff", sandbox)
        assert "validation failed" in result

    @pytest.mark.asyncio
    async def test_write_patch_empty_diff(self):
        sandbox = MockSandbox({})
        result = await tool_write_patch("", sandbox)
        assert "Empty diff" in result


class TestRunTests:
    @pytest.mark.asyncio
    async def test_run_tests_success(self):
        sandbox = MockSandbox({"pytest": (0, "3 passed\n")})
        result = await tool_run_tests("pytest tests/", sandbox)
        assert "Exit code: 0" in result
        assert "3 passed" in result

    @pytest.mark.asyncio
    async def test_run_tests_failure(self):
        sandbox = MockSandbox({"pytest": (1, "1 failed\n")})
        result = await tool_run_tests("pytest tests/", sandbox)
        assert "Exit code: 1" in result

    @pytest.mark.asyncio
    async def test_run_tests_empty_command(self):
        sandbox = MockSandbox({})
        result = await tool_run_tests("", sandbox)
        assert "Error" in result


class TestGitDiff:
    @pytest.mark.asyncio
    async def test_git_diff_with_changes(self):
        sandbox = MockSandbox({"git diff": (0, "diff --git a/main.py b/main.py\n")})
        result = await tool_git_diff(sandbox)
        assert "diff --git" in result

    @pytest.mark.asyncio
    async def test_git_diff_no_changes(self):
        sandbox = MockSandbox({"git diff": (0, "")})
        result = await tool_git_diff(sandbox)
        assert "No changes" in result


class TestExecuteTool:
    @pytest.mark.asyncio
    async def test_dispatch_read_file(self):
        sandbox = MockSandbox({"cat": (0, "content")})
        result = await execute_tool("read_file", {"path": "f.py"}, sandbox)
        assert result == "content"

    @pytest.mark.asyncio
    async def test_dispatch_unknown_tool(self):
        sandbox = MockSandbox({})
        with pytest.raises(ValueError, match="Unknown tool"):
            await execute_tool("delete_repo", {}, sandbox)
