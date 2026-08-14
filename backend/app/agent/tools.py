"""Agent tools — the five functions available to the LLM via function calling.

Design decision: Exactly five tools, no raw shell access.
Principle of least privilege — the LLM can only do what we explicitly expose.
Each tool has a well-defined JSON schema that constrains its inputs.

Tools:
1. read_file     — Read contents of a file in the repo
2. search_code   — Keyword/regex search via ripgrep
3. write_patch   — Write a unified diff (applied via git apply)
4. run_tests     — Execute the test command in the sandbox
5. git_diff      — Show the current working tree diff
"""

from __future__ import annotations

import logging
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from app.sandbox.docker_sandbox import DockerSandbox

logger = logging.getLogger(__name__)


# --- OpenAI Function-Calling Tool Definitions ---

TOOL_DEFINITIONS = [
    {
        "type": "function",
        "function": {
            "name": "read_file",
            "description": (
                "Read the contents of a file in the repository. "
                "Use this to understand the code before generating a patch."
            ),
            "parameters": {
                "type": "object",
                "properties": {
                    "path": {
                        "type": "string",
                        "description": (
                            "Relative path from the repository root "
                            "(e.g., 'src/utils.py')"
                        ),
                    },
                },
                "required": ["path"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "search_code",
            "description": (
                "Search the repository for code matching a pattern using ripgrep. "
                "Returns matching lines with file paths and line numbers. "
                "Use this to find relevant code related to the issue."
            ),
            "parameters": {
                "type": "object",
                "properties": {
                    "pattern": {
                        "type": "string",
                        "description": "Search pattern (regex supported)",
                    },
                    "path": {
                        "type": "string",
                        "description": (
                            "Optional subdirectory to search within "
                            "(default: entire repo)"
                        ),
                        "default": ".",
                    },
                    "file_glob": {
                        "type": "string",
                        "description": "Optional glob to filter files (e.g., '*.py', '*.js')",
                    },
                },
                "required": ["pattern"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "write_patch",
            "description": (
                "Apply a unified diff patch to the repository. "
                "The patch is validated with 'git apply --check' before applying. "
                "Use standard unified diff format (--- a/file, +++ b/file, @@ hunks)."
            ),
            "parameters": {
                "type": "object",
                "properties": {
                    "diff": {
                        "type": "string",
                        "description": (
                            "The unified diff to apply. Must be in standard format:\n"
                            "--- a/path/to/file\n"
                            "+++ b/path/to/file\n"
                            "@@ -start,count +start,count @@\n"
                            " context line\n"
                            "-removed line\n"
                            "+added line"
                        ),
                    },
                },
                "required": ["diff"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "run_tests",
            "description": (
                "Run the test suite in the sandbox environment. "
                "Returns stdout/stderr and the exit code. "
                "Tests run with no network access and resource limits."
            ),
            "parameters": {
                "type": "object",
                "properties": {
                    "command": {
                        "type": "string",
                        "description": (
                            "Test command to run (e.g., 'pytest tests/ -x', "
                            "'python -m pytest tests/test_specific.py')"
                        ),
                    },
                },
                "required": ["command"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "git_diff",
            "description": (
                "Show the current git diff of the working tree. "
                "Use this to review changes before running tests or to "
                "verify that a patch was applied correctly."
            ),
            "parameters": {
                "type": "object",
                "properties": {},
                "required": [],
            },
        },
    },
]


# --- Tool Execution Functions ---
# Each function executes inside the Docker sandbox via container.exec_run()


async def tool_read_file(path: str, sandbox: DockerSandbox) -> str:
    """Read a file from the repository in the sandbox.

    Security: Path is relative to /workspace, preventing directory traversal.
    """
    # Sanitize path — prevent directory traversal
    clean_path = path.lstrip("/").replace("..", "")
    exit_code, output = await sandbox.exec(f"cat '/workspace/{clean_path}'")

    if exit_code != 0:
        return f"Error reading file '{path}': {output}"

    # Truncate very large files to avoid context window overflow
    max_chars = 50_000
    if len(output) > max_chars:
        return output[:max_chars] + f"\n\n[... truncated, {len(output)} total chars]"

    return output


async def tool_search_code(
    pattern: str,
    sandbox: DockerSandbox,
    path: str = ".",
    file_glob: str | None = None,
) -> str:
    """Search the repository using ripgrep.

    Why ripgrep: Fast (Rust-based), respects .gitignore, supports regex.
    Deterministic results — no ML dependency.
    """
    cmd_parts = ["rg", "--no-heading", "--line-number", "--max-count", "50"]

    if file_glob:
        cmd_parts.extend(["--glob", f"'{file_glob}'"])

    # Escape the pattern for shell safety
    safe_pattern = pattern.replace("'", "'\\''")
    cmd_parts.append(f"'{safe_pattern}'")

    clean_path = path.lstrip("/").replace("..", "") or "."
    cmd_parts.append(f"'/workspace/{clean_path}'")

    cmd = " ".join(cmd_parts)
    exit_code, output = await sandbox.exec(cmd)

    if exit_code == 1:  # rg returns 1 when no matches found
        return f"No matches found for pattern: {pattern}"
    elif exit_code != 0:
        return f"Search error: {output}"

    # Truncate if too many results
    lines = output.strip().split("\n")
    if len(lines) > 100:
        return "\n".join(lines[:100]) + f"\n\n[... {len(lines)} total matches, showing first 100]"

    return output


async def tool_write_patch(diff: str, sandbox: DockerSandbox) -> str:
    """Apply a unified diff using git apply.

    Design decision: Use `git apply` instead of LLM-trusted file rewrites.
    `git apply` is strict: if the diff context doesn't match, it fails
    loudly instead of silently corrupting the file. The `--check` flag
    provides a dry run before the actual apply.
    """
    if not diff.strip():
        return "Error: Empty diff provided"

    # Write diff to a temp file in the container
    # Using heredoc to avoid shell escaping issues
    write_cmd = f"cat > /tmp/patch.diff << 'FIXFORGE_PATCH_EOF'\n{diff}\nFIXFORGE_PATCH_EOF"
    exit_code, output = await sandbox.exec(f"sh -c \"{write_cmd}\"")

    if exit_code != 0:
        return f"Error writing patch file: {output}"

    # Dry-run validation
    exit_code, output = await sandbox.exec("git apply --check /tmp/patch.diff")
    if exit_code != 0:
        return f"Patch validation failed (git apply --check):\n{output}"

    # Apply the patch
    exit_code, output = await sandbox.exec("git apply /tmp/patch.diff")
    if exit_code != 0:
        return f"Patch application failed (git apply):\n{output}"

    # Verify with git diff
    _, diff_output = await sandbox.exec("git diff --stat")

    return f"Patch applied successfully.\n\nChanges:\n{diff_output}"


async def tool_run_tests(command: str, sandbox: DockerSandbox) -> str:
    """Run the test command in the sandbox.

    Security: Runs in an ephemeral container with no network access,
    CPU/memory limits, and a timeout.
    """
    if not command.strip():
        return "Error: No test command provided"

    # Run with a timeout to prevent infinite loops
    exit_code, output = await sandbox.exec(command, timeout=180)

    result = f"Exit code: {exit_code}\n\n{output}"

    # Truncate very long test output
    max_chars = 30_000
    if len(result) > max_chars:
        result = result[:max_chars] + f"\n\n[... truncated, {len(result)} total chars]"

    return result


async def tool_git_diff(sandbox: DockerSandbox) -> str:
    """Show the current git diff of the working tree."""
    exit_code, output = await sandbox.exec("git diff")

    if exit_code != 0:
        return f"Error running git diff: {output}"

    if not output.strip():
        return "No changes in the working tree."

    return output


# --- Tool Executor ---


async def execute_tool(name: str, args: dict, sandbox: DockerSandbox) -> str:
    """Execute a tool by name with the given arguments.

    This is the single dispatch point — the LLM calls a tool name
    and we route to the correct function.
    """
    logger.info(
        "Executing tool",
        extra={"tool": name, "args_keys": list(args.keys())},
    )

    match name:
        case "read_file":
            return await tool_read_file(args["path"], sandbox)
        case "search_code":
            return await tool_search_code(
                pattern=args["pattern"],
                sandbox=sandbox,
                path=args.get("path", "."),
                file_glob=args.get("file_glob"),
            )
        case "write_patch":
            return await tool_write_patch(args["diff"], sandbox)
        case "run_tests":
            return await tool_run_tests(args["command"], sandbox)
        case "git_diff":
            return await tool_git_diff(sandbox)
        case _:
            raise ValueError(f"Unknown tool: {name}")
