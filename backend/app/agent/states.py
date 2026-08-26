"""Individual state handler functions for the agent FSM.

Each function is a standalone, independently testable unit:
    (context: AgentContext, db: AsyncSession) -> (AgentState, AgentContext)
"""

from __future__ import annotations

import base64
import logging
import os
import re
import time
from pathlib import Path
from typing import TYPE_CHECKING

from app.agent.llm import (
    _log_llm_call,
    calculate_cost,
    create_llm_client,
    llm_call_with_tools,
)
from app.agent.state_machine import AgentContext, AgentState
from app.core.config import get_settings
from app.services.github_service import (
    MAX_FILE_CONTENT_CHARS,
    _is_valid_token,
    create_pull_request_via_api,
    fetch_default_branch,
    fetch_file_content,
    fetch_issue,
    fetch_issue_comments,
    fetch_repo_tree,
    parse_github_url,
    parse_issue_url,
)

if TYPE_CHECKING:
    from sqlalchemy.ext.asyncio import AsyncSession

logger = logging.getLogger(__name__)

# Type alias for state handler functions
StateHandler = tuple[AgentState, AgentContext]

# Placeholder LLM API keys that should NOT trigger real LLM calls
_LLM_PLACEHOLDER_KEYS = {"sk-placeholder", "sk-your-key-here", ""}


def _has_valid_llm_key(settings) -> bool:
    """Check whether the configured LLM API key is real (not a placeholder)."""
    key = settings.openai_api_key
    if not key:
        return False
    return key.strip() not in _LLM_PLACEHOLDER_KEYS


async def read_issue(
    context: AgentContext,
    db: AsyncSession,
) -> StateHandler:
    """READ_ISSUE state: Ingest GitHub issue title, body, and comments."""
    logger.info("Reading issue from URL: %s", context.issue_url)

    try:
        issue_data = await fetch_issue(context.issue_url)
        context.issue_title = issue_data.get("title") or "Issue"
        context.issue_text = issue_data.get("body") or context.issue_title

        # Fetch issue comments for additional context (stack traces, hints)
        try:
            owner, repo, number = parse_issue_url(context.issue_url)
            comments = await fetch_issue_comments(owner, repo, number)
            if comments:
                comment_text = "\n\n".join(
                    f"**Comment by @{c['author']}:**\n{c['body']}"
                    for c in comments
                    if c.get("body")
                )
                context.issue_text += (
                    f"\n\n---\n## Issue Comments\n{comment_text}"
                )
                logger.info("Appended %d comments to issue context", len(comments))
        except Exception as e:
            logger.warning("Could not fetch issue comments: %s", e)

        logger.info("Issue retrieved successfully: %s", context.issue_title)
        return AgentState.LOCATE_CODE, context
    except Exception as e:
        logger.warning(
            "Could not fetch issue via API (%s), parsing URL fallback", e
        )
        try:
            owner, repo, number = parse_issue_url(context.issue_url)
            context.issue_title = (
                f"Fix bug reported in {owner}/{repo} #{number}"
            )
            context.issue_text = (
                f"Resolve issue #{number} in repository {owner}/{repo}."
            )
            return AgentState.LOCATE_CODE, context
        except Exception as parse_err:
            context.error_message = (
                f"Failed to parse issue URL: {parse_err}"
            )
            return AgentState.ESCALATE, context


# ---------------------------------------------------------------------------
# File relevance scoring helpers
# ---------------------------------------------------------------------------

def _extract_stack_trace_files(issue_text: str) -> list[str]:
    """Extract file paths from Python/JS/Go stack traces in issue text."""
    patterns = [
        r'File "([^"]+)", line \d+',            # Python tracebacks
        r'at .+ \((.+?):\d+:\d+\)',              # JavaScript/Node
        r'(\S+\.(?:py|js|ts|go|rs|java)):\d+',   # Generic file:line
        r'in (\S+\.(?:py|js|ts|go|rs|java))',     # "in module.py"
    ]
    files: list[str] = []
    for pat in patterns:
        files.extend(re.findall(pat, issue_text))
    # Return just basenames for matching against repo paths
    return list(set(os.path.basename(f) for f in files if f))


def _extract_error_identifiers(issue_text: str) -> list[str]:
    """Extract error class names, function names, and identifiers from issue text."""
    identifiers: list[str] = []
    # Python exception class names (e.g., TypeError, ValueError, BuildError)
    identifiers.extend(re.findall(r'\b([A-Z][a-zA-Z]*Error)\b', issue_text))
    identifiers.extend(re.findall(r'\b([A-Z][a-zA-Z]*Exception)\b', issue_text))
    # Function/method names in backticks (common in GitHub issues)
    identifiers.extend(re.findall(r'`([a-z_][a-z0-9_]*(?:\.[a-z_][a-z0-9_]*)*)`', issue_text))
    # CamelCase class names in backticks
    identifiers.extend(re.findall(r'`([A-Z][a-zA-Z0-9]*)`', issue_text))
    return list(set(identifiers))


def _score_file_relevance(
    file_path: str,
    content: str,
    title_terms: list[str],
    query_terms: list[str],
    stack_trace_files: list[str] | None = None,
    error_identifiers: list[str] | None = None,
) -> int:
    """Score file relevance with stack trace matching, title weights, and penalties."""
    score = 0
    lower_path = file_path.lower()
    base_name = os.path.splitext(os.path.basename(lower_path))[0]
    full_basename = os.path.basename(lower_path)
    lower_content = content.lower()

    # --- Stack trace files get highest priority ---
    if stack_trace_files:
        for st_file in stack_trace_files:
            st_lower = st_file.lower()
            if st_lower == full_basename.lower():
                score += 500
            elif st_lower in lower_path:
                score += 300

    # --- Error identifiers in file content ---
    if error_identifiers:
        for ident in error_identifiers:
            ident_lower = ident.lower()
            if len(ident_lower) >= 4:
                if ident_lower in base_name:
                    score += 200
                occurrences = lower_content.count(ident_lower)
                score += min(occurrences * 10, 80)

    # --- Title term matching (strong signal) ---
    for t_term in title_terms:
        if len(t_term) >= 3 and t_term in base_name:
            score += 120

    # --- Query term matching ---
    for term in query_terms:
        if len(term) < 3:
            continue
        if term in lower_path:
            score += 30
        occurrences = lower_content.count(term)
        score += min(occurrences * 3, 40)

    # --- Penalties for test files, configs, and docs ---
    if "/test" in lower_path or lower_path.startswith("test") or "conftest" in lower_path:
        score -= 50

    if full_basename.lower() in (
        "setup.py", "setup.cfg", "pyproject.toml", "manage.py",
        "readme.md", "changelog.md", "contributing.md",
        "makefile", "dockerfile", ".gitignore",
    ):
        score -= 100

    if base_name == "__init__" and len(content) < 200:
        score -= 30

    return score


async def _gather_files_local(
    work_dir: str,
) -> list[str]:
    """Walk local work_dir to discover candidate source files."""
    candidate_files: list[str] = []
    ignored = {
        ".git", ".venv", "__pycache__",
        "node_modules", ".pytest_cache", ".tox",
        "dist", "build", ".mypy_cache", ".ruff_cache",
    }
    source_extensions = (
        ".py", ".ts", ".js", ".jsx", ".tsx",
        ".go", ".rs", ".java", ".rb", ".c", ".cpp", ".h",
        ".cs", ".swift", ".kt", ".scala", ".php", ".sh",
    )
    for root, dirs, files in os.walk(work_dir):
        dirs[:] = [d for d in dirs if d not in ignored]
        for f in files:
            if f.endswith(source_extensions):
                abs_f = os.path.join(root, f)
                rel_path = os.path.relpath(
                    abs_f, work_dir
                ).replace("\\", "/")
                candidate_files.append(rel_path)
    return candidate_files


async def _read_file_content(
    work_dir: str | None,
    rel_path: str,
    owner: str,
    repo: str,
) -> str:
    """Read file content from local disk or GitHub API (up to MAX_FILE_CONTENT_CHARS)."""
    # Try local first (much faster, no rate limit)
    if work_dir:
        abs_p = os.path.join(work_dir, rel_path)
        if os.path.exists(abs_p):
            try:
                return Path(abs_p).read_text(
                    encoding="utf-8", errors="replace"
                )[:MAX_FILE_CONTENT_CHARS]
            except Exception:
                pass

    # Fall back to GitHub API
    content = await fetch_file_content(owner, repo, rel_path)
    return content


async def locate_code(
    context: AgentContext,
    db: AsyncSession,
) -> StateHandler:
    """LOCATE_CODE state: Identify faulty files via local scan or GitHub API."""
    logger.info("Locating candidate files for run: %s", context.run_id)
    owner, repo = parse_github_url(context.repo_url)

    # 1. Discover candidate source files
    candidate_files: list[str] = []
    if context.work_dir and os.path.exists(context.work_dir):
        candidate_files = await _gather_files_local(context.work_dir)
    else:
        # No local clone — fetch tree from GitHub API
        candidate_files = await fetch_repo_tree(owner, repo)

    logger.info("Discovered %d candidate files", len(candidate_files))

    # 2. Extract key terms + stack trace files + error identifiers
    combined = f"{context.issue_title} {context.issue_text}".lower()
    title_terms = list(set(
        re.findall(r"[a-z0-9_]{3,}", context.issue_title.lower())
    ))
    query_terms = list(set(re.findall(r"[a-z0-9_]{3,}", combined)))

    issue_full = f"{context.issue_title or ''} {context.issue_text or ''}"
    stack_trace_files = _extract_stack_trace_files(issue_full)
    error_identifiers = _extract_error_identifiers(issue_full)

    logger.info(
        "Search signals — title_terms: %d, stack_trace_files: %s, error_ids: %s",
        len(title_terms),
        stack_trace_files[:5],
        error_identifiers[:5],
    )

    # 3. Score and rank (read content for top files)
    scored: list[tuple[str, int]] = []
    for rel_f in candidate_files:
        content = await _read_file_content(
            context.work_dir, rel_f, owner, repo
        )
        score = _score_file_relevance(
            rel_f, content, title_terms, query_terms,
            stack_trace_files=stack_trace_files,
            error_identifiers=error_identifiers,
        )
        scored.append((rel_f, score))

    scored.sort(key=lambda x: x[1], reverse=True)
    top = [f for f, s in scored if s > 0]
    if not top:
        top = [f for f, _ in scored[:5]]

    context.relevant_files = top[:4]

    # 4. Fetch and cache actual file contents for generate_patch
    for rel_f in context.relevant_files:
        content = await _read_file_content(
            context.work_dir, rel_f, owner, repo
        )
        if content:
            context.file_contents[rel_f] = content

    logger.info(
        "Relevant files: %s (with %d having content)",
        context.relevant_files,
        len(context.file_contents),
    )
    return AgentState.GENERATE_PATCH, context


def _validate_llm_diff(
    diff: str, known_files: list[str]
) -> bool:
    """Check that LLM-generated diff references actual repo files."""
    if not diff or "--- a/" not in diff:
        return False

    # Extract file paths from diff headers
    diff_files = re.findall(r"--- a/(.+)", diff)
    if not diff_files:
        return False

    # Check that at least one diff path matches a known file
    for df in diff_files:
        df_clean = df.strip()
        for kf in known_files:
            if df_clean == kf or df_clean.endswith(kf) or kf.endswith(df_clean):
                return True

    return False


def _extract_diff_from_text(raw: str) -> str:
    """Extract a unified diff from LLM output text.

    Handles:
    - Fenced ```diff blocks
    - Unfenced diffs with --- a/ and +++ b/ markers
    """
    # Try fenced code block first
    m = re.search(r"```(?:diff)?\s*([\s\S]*?)\s*```", raw)
    if m:
        candidate = m.group(1).strip()
        if "--- a/" in candidate and "+++ b/" in candidate:
            return candidate

    # Try raw diff in the output
    if "--- a/" in raw and "+++ b/" in raw:
        # Extract from first --- a/ to end of diff content
        lines = raw.split("\n")
        diff_lines: list[str] = []
        in_diff = False
        for line in lines:
            if line.startswith("--- a/"):
                in_diff = True
            if in_diff:
                # Stop at obvious non-diff content
                if line.startswith("```") and diff_lines:
                    break
                diff_lines.append(line)
        if diff_lines:
            return "\n".join(diff_lines).strip()

    return ""


async def generate_patch(
    context: AgentContext,
    db: AsyncSession,
) -> StateHandler:
    """GENERATE_PATCH state: Synthesize multi-file unified diff.

    Uses two modes:
    1. AGENTIC MODE (sandbox available): Uses llm_call_with_tools so the LLM
       can explore the codebase with read_file, search_code, write_patch, etc.
    2. SINGLE-SHOT MODE (fallback): Sends top files as context, asks for diff.
    """
    context.iteration += 1
    logger.info(
        "Generating patch (iteration #%d) for run %s",
        context.iteration,
        context.run_id,
    )
    owner, repo = parse_github_url(context.repo_url)
    settings = get_settings()
    synthesized_diff = ""

    if not _has_valid_llm_key(settings):
        logger.warning(
            "No valid LLM API key configured — skipping LLM call. "
            "Set OPENAI_API_KEY in .env to enable patch generation."
        )
    elif context.sandbox:
        # ---- AGENTIC MODE: LLM with tool calling ----
        synthesized_diff = await _generate_patch_agentic(context, db, settings)
    else:
        # ---- SINGLE-SHOT MODE: No sandbox, static file context ----
        synthesized_diff = await _generate_patch_single_shot(
            context, db, settings, owner, repo
        )

    # Fallback: generic minimal diff using actual discovered files
    if not synthesized_diff:
        if context.relevant_files and context.file_contents:
            primary = context.relevant_files[0]
            synthesized_diff = (
                f"--- a/{primary}\n"
                f"+++ b/{primary}\n"
                "@@ -1,3 +1,4 @@\n"
                "+# FixForge: auto-generated patch placeholder\n"
            )
            first_lines = context.file_contents.get(primary, "").split("\n")[:3]
            for line in first_lines:
                synthesized_diff += f" {line}\n"
        else:
            logger.warning(
                "No LLM diff and no relevant files found — cannot generate fallback patch"
            )
            context.current_patch = ""
            return AgentState.RUN_TESTS, context

    context.current_patch = synthesized_diff
    return AgentState.RUN_TESTS, context


async def _generate_patch_agentic(
    context: AgentContext,
    db,
    settings,
) -> str:
    """Generate a patch using the LLM tool-calling loop.

    The LLM can explore the codebase using read_file, search_code,
    write_patch, run_tests, and git_diff tools.
    """
    feedback = context.test_output or "This is the first attempt."

    # Build file context summary (brief, since the LLM can read more via tools)
    file_summary = ""
    if context.relevant_files:
        file_summary = (
            "Pre-identified relevant files (you can read more with read_file):\n"
            + "\n".join(f"  - {f}" for f in context.relevant_files[:6])
        )

    system_msg = {
        "role": "system",
        "content": (
            "You are FixForge, an autonomous bug repair agent. "
            "You have access to tools to explore a cloned repository:\n"
            "- read_file(path): Read any file in the repo\n"
            "- search_code(pattern, file_glob?): Grep for patterns\n"
            "- write_patch(diff): Apply a unified diff to the repo\n"
            "- run_tests(command): Run test commands\n"
            "- git_diff(): See current changes\n\n"
            "Your workflow:\n"
            "1. Read the relevant files to understand the bug\n"
            "2. Search for related functions, classes, or error patterns\n"
            "3. Synthesize a fix as a Git unified diff\n"
            "4. Use write_patch to apply it\n"
            "5. Output your FINAL diff in a ```diff code fence\n\n"
            "Rules:\n"
            "- Use EXACT file paths from the repository\n"
            "- Include --- a/path and +++ b/path headers\n"
            "- Include correct @@ hunk headers with accurate line numbers\n"
            "- Include 3+ context lines around each change\n"
            "- End your final message with the complete diff in a ```diff fence"
        ),
    }

    user_msg = {
        "role": "user",
        "content": (
            f"Repository: {context.repo_url}\n"
            f"Issue Title: {context.issue_title}\n"
            f"Issue Description:\n{context.issue_text}\n\n"
            f"{file_summary}\n\n"
            f"Iteration: #{context.iteration}\n"
            f"Previous Feedback:\n{feedback}\n\n"
            "Please investigate the bug and produce a fix."
        ),
    }

    messages = [system_msg, user_msg]

    try:
        final_text, messages, cost, latency = await llm_call_with_tools(
            messages=messages,
            run_id=context.run_id,
            state="GENERATE_PATCH",
            sandbox=context.sandbox,
            db=db,
        )

        context.total_cost += cost
        context.total_latency += latency

        # Extract diff from the LLM's final response
        synthesized_diff = _extract_diff_from_text(final_text)

        if synthesized_diff and _validate_llm_diff(
            synthesized_diff, context.relevant_files
        ):
            logger.info(
                "Agentic mode produced valid diff (%d chars, cost=$%.4f)",
                len(synthesized_diff),
                cost,
            )
            return synthesized_diff

        # If the tool-calling agent used write_patch directly, check git diff
        if context.sandbox:
            exit_code, git_diff_output = await context.sandbox.exec(
                "git diff 2>&1"
            )
            if exit_code == 0 and git_diff_output.strip():
                logger.info("Using git diff from sandbox (agent applied patch via tools)")
                return git_diff_output.strip()

        logger.warning("Agentic mode did not produce a valid diff")
        return ""

    except Exception as e:
        logger.warning("Agentic patch generation failed (%s), will use fallback", e)
        return ""


async def _generate_patch_single_shot(
    context: AgentContext,
    db,
    settings,
    owner: str,
    repo: str,
) -> str:
    """Generate a patch using a single-shot LLM call (no tools).

    Used when the sandbox is not available. Sends the top files as
    context and asks the LLM to produce a unified diff.
    """
    # Build file context from cached contents
    files_context = []
    for rel_file in context.relevant_files[:4]:
        content = context.file_contents.get(rel_file, "")
        if not content:
            content = await _read_file_content(
                context.work_dir, rel_file, owner, repo
            )
        files_context.append(
            f"--- File: {rel_file} ---\n{content or '(empty)'}"
        )

    combined_file_text = "\n\n".join(files_context)

    try:
        client = await create_llm_client()
        feedback = context.test_output or "Initial round."
        prompt = (
            "You are FixForge, an autonomous bug repair agent.\n\n"
            f"Repository: {context.repo_url}\n"
            f"Issue Title: {context.issue_title}\n"
            f"Issue Description:\n{context.issue_text}\n\n"
            f"Source Files:\n{combined_file_text}\n\n"
            f"Iteration: #{context.iteration}\n"
            f"Previous Feedback:\n{feedback}\n\n"
            "Task: Synthesize a COMPLETE Git Unified Diff.\n"
            "Rules:\n"
            "- Use EXACT file paths as shown above.\n"
            "- Include `--- a/path` and `+++ b/path` for "
            "every modified file.\n"
            "- Include correct @@ hunk headers with accurate "
            "line numbers.\n"
            "- Include sufficient context lines (3+ unchanged "
            "lines around each change).\n"
            "- Output ONLY the diff in a ```diff fence.\n"
            "- Do NOT truncate. Include ALL changes.\n"
            "- If the previous feedback shows test failures, "
            "analyze the error messages and adjust your patch "
            "accordingly.\n"
        )

        start_t = time.perf_counter()
        resp = await client.chat.completions.create(
            model=settings.openai_model,
            messages=[{"role": "user", "content": prompt}],
            temperature=0.1,
        )
        latency_ms = (time.perf_counter() - start_t) * 1000
        raw = resp.choices[0].message.content or ""

        synthesized_diff = _extract_diff_from_text(raw)

        # Validate LLM output against known files
        if synthesized_diff and not _validate_llm_diff(
            synthesized_diff, context.relevant_files
        ):
            logger.warning("LLM diff failed validation, discarding")
            synthesized_diff = ""

        if resp.usage:
            u = resp.usage
            cost = calculate_cost(
                settings.openai_model,
                u.prompt_tokens,
                u.completion_tokens,
            )
            context.total_cost += cost
            context.total_latency += latency_ms
            await _log_llm_call(
                db,
                context.run_id,
                "GENERATE_PATCH",
                u.prompt_tokens,
                u.completion_tokens,
                latency_ms,
                cost,
            )

        return synthesized_diff

    except Exception as e:
        logger.warning("Single-shot LLM patch synthesis failed (%s)", e)
        return ""


# ---------------------------------------------------------------------------
# Test command auto-detection
# ---------------------------------------------------------------------------

def _detect_test_command_local(work_dir: str) -> str | None:
    """Detect the test command using local filesystem checks (cross-platform).

    This works on both Windows and Linux, without requiring sandbox shell commands.
    Returns None if no framework is detected.
    """
    if not work_dir or not os.path.isdir(work_dir):
        return None

    def has(*filenames: str) -> bool:
        return any(os.path.exists(os.path.join(work_dir, f)) for f in filenames)

    # Python
    if has("setup.py", "pyproject.toml", "requirements.txt", "setup.cfg"):
        return (
            "python -m pytest tests/ -x -q --tb=short 2>&1 "
            "|| python -m pytest -x -q --tb=short 2>&1"
        )

    # Node.js
    if has("package.json"):
        return "npm test 2>&1"

    # Go
    if has("go.mod"):
        return "go test ./... 2>&1"

    # Rust
    if has("Cargo.toml"):
        return "cargo test 2>&1"

    # Java (Maven)
    if has("pom.xml"):
        return "mvn test -q 2>&1"

    # Java (Gradle)
    if has("build.gradle", "build.gradle.kts"):
        return "./gradlew test 2>&1"

    return None


async def _detect_test_command(sandbox, work_dir: str | None = None) -> str:
    """Auto-detect the test command based on repo contents.

    Uses local filesystem checks first (works on all platforms),
    then falls back to sandbox shell commands for Docker containers.
    """
    # Try cross-platform local filesystem detection first
    if work_dir:
        result = _detect_test_command_local(work_dir)
        if result:
            return result

    # Fallback to sandbox shell commands (Linux/Docker)
    if sandbox is None:
        return "echo 'No sandbox available for test detection'"

    # Python (most common for FixForge's target repos)
    exit_code, _ = await sandbox.exec(
        "test -f setup.py -o -f pyproject.toml -o -f requirements.txt -o -f setup.cfg"
    )
    if exit_code == 0:
        exit_code_pytest, _ = await sandbox.exec("python -m pytest --version 2>/dev/null")
        if exit_code_pytest == 0:
            return "python -m pytest tests/ -x -q --tb=short 2>&1 || python -m pytest -x -q --tb=short 2>&1"
        return "python -m unittest discover -s tests -q 2>&1"

    # Node.js
    exit_code, _ = await sandbox.exec("test -f package.json")
    if exit_code == 0:
        return "npm test 2>&1"

    # Go
    exit_code, _ = await sandbox.exec("test -f go.mod")
    if exit_code == 0:
        return "go test ./... 2>&1"

    # Rust
    exit_code, _ = await sandbox.exec("test -f Cargo.toml")
    if exit_code == 0:
        return "cargo test 2>&1"

    # Java (Maven)
    exit_code, _ = await sandbox.exec("test -f pom.xml")
    if exit_code == 0:
        return "mvn test -q 2>&1"

    # Java (Gradle)
    exit_code, _ = await sandbox.exec("test -f build.gradle -o -f build.gradle.kts")
    if exit_code == 0:
        return "./gradlew test 2>&1"

    # Fallback
    return "echo 'No test framework detected — manual verification required'"


async def run_tests(
    context: AgentContext,
    db: AsyncSession,
) -> StateHandler:
    """RUN_TESTS state: Apply patch and execute real tests in the sandbox."""
    logger.info(
        "Executing test validation for iteration #%d",
        context.iteration,
    )

    from app.models.patch import Patch

    sandbox = context.sandbox

    # ---- Step 1: Apply the current patch in the sandbox ----
    patch_applied = False
    if context.current_patch and sandbox:
        # Reset any previous patch application (clean state for retry)
        if context.iteration > 1:
            await sandbox.exec("git checkout -- . 2>/dev/null")
            await sandbox.exec("git clean -fd 2>/dev/null")

        # Write the diff to a temp file using base64 encoding
        # (avoids all shell escaping issues with printf/heredoc)
        b64_diff = base64.b64encode(
            context.current_patch.encode("utf-8")
        ).decode("ascii")

        # Split into chunks to avoid shell argument limits (~128KB)
        CHUNK_SIZE = 65536
        if len(b64_diff) <= CHUNK_SIZE:
            write_cmd = f"echo '{b64_diff}' | base64 -d > /tmp/fixforge_patch.diff"
            exit_code, output = await sandbox.exec(write_cmd)
        else:
            # Write in chunks for very large diffs
            await sandbox.exec("> /tmp/fixforge_b64.txt")
            for i in range(0, len(b64_diff), CHUNK_SIZE):
                chunk = b64_diff[i : i + CHUNK_SIZE]
                exit_code, output = await sandbox.exec(
                    f"echo '{chunk}' >> /tmp/fixforge_b64.txt"
                )
                if exit_code != 0:
                    break
            exit_code, output = await sandbox.exec(
                "base64 -d /tmp/fixforge_b64.txt > /tmp/fixforge_patch.diff"
            )

        if exit_code == 0:
            # Validate the patch first
            exit_code, check_output = await sandbox.exec(
                "git apply --check /tmp/fixforge_patch.diff 2>&1"
            )
            if exit_code == 0:
                # Apply the patch
                exit_code, apply_output = await sandbox.exec(
                    "git apply /tmp/fixforge_patch.diff 2>&1"
                )
                if exit_code == 0:
                    patch_applied = True
                    logger.info("Patch applied successfully")
                else:
                    logger.warning("git apply failed: %s", apply_output)
                    context.test_output = (
                        f"Patch application failed (git apply):\n{apply_output}\n\n"
                        "The diff format or context lines do not match the "
                        "actual file content. Please regenerate the patch with "
                        "correct line numbers and sufficient context lines."
                    )
            else:
                logger.warning("git apply --check failed: %s", check_output)
                context.test_output = (
                    f"Patch validation failed (git apply --check):\n{check_output}\n\n"
                    "The diff hunks do not match the file content. Ensure "
                    "@@ line numbers are accurate and context lines match exactly."
                )
        else:
            context.test_output = f"Failed to write patch file to sandbox: {output}"

        if not patch_applied:
            context.test_passed = False
            # Persist patch record (failed application)
            patch = Patch(
                run_id=context.run_id,
                diff=context.current_patch or "",
                test_result=context.test_output,
                test_passed=False,
                iteration_number=context.iteration,
            )
            db.add(patch)
            await db.flush()

            if context.iteration >= context.max_iterations:
                context.error_message = (
                    f"Patch application failed after {context.max_iterations} iterations"
                )
                return AgentState.ESCALATE, context
            return AgentState.GENERATE_PATCH, context

    elif not sandbox:
        logger.warning("No sandbox available — cannot run real tests")
        context.test_output = "No sandbox available for test execution"
        context.test_passed = False

    # ---- Step 2: Detect and run tests ----
    if sandbox and patch_applied:
        # Determine test command (cross-platform detection first)
        test_cmd = context.test_command or await _detect_test_command(
            sandbox, work_dir=context.work_dir
        )
        logger.info("Running test command: %s", test_cmd)

        # Install dependencies if needed (Python repos)
        has_requirements = (
            context.work_dir
            and os.path.exists(os.path.join(context.work_dir, "requirements.txt"))
        ) if context.work_dir else False

        if not has_requirements:
            # Fallback: check via sandbox
            exit_code_req, _ = await sandbox.exec("test -f requirements.txt")
            has_requirements = (exit_code_req == 0)

        if has_requirements:
            await sandbox.exec(
                "pip install -q -r requirements.txt 2>/dev/null",
                timeout=120,
            )

        # Also try installing the package itself in development mode
        has_setup = (
            context.work_dir
            and any(
                os.path.exists(os.path.join(context.work_dir, f))
                for f in ("setup.py", "pyproject.toml")
            )
        ) if context.work_dir else False

        if not has_setup:
            exit_code_setup, _ = await sandbox.exec("test -f setup.py -o -f pyproject.toml")
            has_setup = (exit_code_setup == 0)

        if has_setup:
            await sandbox.exec(
                "pip install -q -e . 2>/dev/null",
                timeout=120,
            )

        # Run the actual test suite
        exit_code, test_output = await sandbox.exec(test_cmd, timeout=180)

        context.test_passed = (exit_code == 0)
        context.test_output = test_output

        # Truncate very long test output for storage/display
        if len(context.test_output) > 10_000:
            context.test_output = (
                context.test_output[:5000]
                + "\n\n... [truncated] ...\n\n"
                + context.test_output[-3000:]
            )

        logger.info(
            "Tests %s (exit_code=%d) on iteration %d",
            "PASSED" if context.test_passed else "FAILED",
            exit_code,
            context.iteration,
        )

    # ---- Step 3: Persist patch record to DB ----
    patch = Patch(
        run_id=context.run_id,
        diff=context.current_patch or "",
        test_result=context.test_output,
        test_passed=context.test_passed,
        iteration_number=context.iteration,
    )
    db.add(patch)
    await db.flush()

    # ---- Step 4: Determine next state ----
    if context.test_passed:
        logger.info(
            "Tests passed on iteration %d!", context.iteration
        )
        return AgentState.OPEN_PR, context
    elif context.iteration >= context.max_iterations:
        context.error_message = (
            f"Failed after {context.max_iterations} iterations"
        )
        return AgentState.ESCALATE, context
    else:
        logger.info(
            "Tests failed on iteration %d, retrying",
            context.iteration,
        )
        return AgentState.GENERATE_PATCH, context


async def open_pr(
    context: AgentContext,
    db: AsyncSession,
) -> StateHandler:
    """OPEN_PR state: Submit verified Pull Request via GitHub API.

    Attempts to create a real PR using the GitHub REST API. Falls back
    to generating a PR URL if the token lacks write access.
    """
    owner, repo = parse_github_url(context.repo_url)
    issue_num = context.issue_url.split("/")[-1]

    branch = f"fixforge/fix-issue-{issue_num}"
    settings = get_settings()

    # Attempt real PR creation if we have a valid token and a real diff
    if context.current_patch and _is_valid_token(settings.github_token):
        try:
            base_branch = await fetch_default_branch(owner, repo)
            pr_title = f"fix: resolve #{issue_num} — {context.issue_title or 'bug fix'}"
            pr_body = (
                "## 🛠️ Automated Fix by FixForge\n\n"
                f"**Issue:** {context.issue_url}\n\n"
                f"**Description:** {(context.issue_text or '')[:500]}\n\n"
                f"**Iterations:** {context.iteration}\n"
                f"**Cost:** ${context.total_cost:.4f}\n\n"
                "---\n"
                "*This PR was generated by [FixForge](https://github.com/A-SM20/FixForge), "
                "an autonomous bug-fixing agent.*"
            )

            pr_url = await create_pull_request_via_api(
                owner=owner,
                repo=repo,
                branch=branch,
                title=pr_title,
                body=pr_body,
                diff=context.current_patch,
                base=base_branch,
            )
            context.pr_url = pr_url
            logger.info("Real PR created: %s", context.pr_url)
            return AgentState.DONE, context

        except Exception as e:
            logger.warning(
                "Real PR creation failed (%s), falling back to URL generation", e
            )

    # Fallback: generate a PR URL for manual creation
    context.pr_url = (
        f"https://github.com/{owner}/{repo}/pull/new/{branch}"
    )
    logger.info("PR URL ready (fallback): %s", context.pr_url)

    return AgentState.DONE, context


async def escalate(
    context: AgentContext,
    db: AsyncSession,
) -> StateHandler:
    """ESCALATE state: Log failure."""
    if not context.error_message:
        context.error_message = (
            "Agent reached maximum iteration threshold"
        )
    return AgentState.DONE, context


# Default handler mapping
DEFAULT_HANDLERS: dict = {
    AgentState.READ_ISSUE: read_issue,
    AgentState.LOCATE_CODE: locate_code,
    AgentState.GENERATE_PATCH: generate_patch,
    AgentState.RUN_TESTS: run_tests,
    AgentState.OPEN_PR: open_pr,
    AgentState.ESCALATE: escalate,
}
