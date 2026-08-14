"""Individual state handler functions for the agent FSM.

Each function is a standalone, independently testable unit:
    (context: AgentContext, db: AsyncSession) -> (AgentState, AgentContext)

Design decision: State functions are pure-ish (they receive all deps
via arguments). Side effects (LLM calls, tool calls) are delegated to
injected clients, making each state trivially mockable in tests.
"""

from __future__ import annotations

import logging
from typing import TYPE_CHECKING

from app.agent.state_machine import AgentContext, AgentState

if TYPE_CHECKING:
    from sqlalchemy.ext.asyncio import AsyncSession

logger = logging.getLogger(__name__)


# Type alias for state handler functions
StateHandler = tuple[AgentState, AgentContext]


async def read_issue(
    context: AgentContext,
    db: AsyncSession,
) -> StateHandler:
    """READ_ISSUE state: Fetch the GitHub issue text.

    Uses the GitHub API to retrieve the issue title and body.
    Populates context.issue_text and context.issue_title.
    """
    logger.info("Reading issue", extra={"issue_url": context.issue_url})

    # TODO (Stage 3): Replace with actual GitHub API call
    # For now, extract issue info from URL and store placeholder
    try:
        # Parse owner/repo/issue_number from URL
        # e.g., https://github.com/owner/repo/issues/123
        parts = context.issue_url.rstrip("/").split("/")
        issue_number = parts[-1]
        repo_name = parts[-3]
        owner = parts[-4]

        # Placeholder — will be replaced with PyGithub call in Stage 3
        context.issue_title = f"Issue #{issue_number} in {owner}/{repo_name}"
        context.issue_text = (
            f"Issue #{issue_number} from {owner}/{repo_name}. "
            "Full text will be fetched via GitHub API."
        )

        logger.info(
            "Issue read successfully",
            extra={"issue_title": context.issue_title},
        )
        return AgentState.LOCATE_CODE, context

    except Exception as e:
        context.error_message = f"Failed to read issue: {e}"
        logger.error("Failed to read issue", extra={"error": str(e)})
        return AgentState.ESCALATE, context


async def locate_code(
    context: AgentContext,
    db: AsyncSession,
) -> StateHandler:
    """LOCATE_CODE state: Find relevant files for the bug fix.

    Uses the LLM with the search_code and read_file tools to identify
    which files in the repository are relevant to the issue.
    """
    logger.info("Locating relevant code", extra={"run_id": str(context.run_id)})

    # TODO (Stage 3): Replace with LLM + tool-calling loop
    # The LLM will use search_code (ripgrep) and read_file to explore the repo
    # For now, pass through with empty file list

    if not context.issue_text:
        context.error_message = "No issue text available for code location"
        return AgentState.ESCALATE, context

    # Placeholder: will be replaced with actual LLM-driven code search
    context.relevant_files = []

    logger.info(
        "Code location complete",
        extra={"relevant_files": context.relevant_files},
    )
    return AgentState.GENERATE_PATCH, context


async def generate_patch(
    context: AgentContext,
    db: AsyncSession,
) -> StateHandler:
    """GENERATE_PATCH state: Generate a unified diff to fix the issue.

    Uses the LLM with the read_file and write_patch tools to produce
    a unified diff that addresses the issue. The LLM sees:
    - The issue text
    - Relevant file contents
    - Previous test output (on retry iterations)
    """
    logger.info(
        "Generating patch",
        extra={
            "run_id": str(context.run_id),
            "iteration": context.iteration,
        },
    )

    context.iteration += 1

    # TODO (Stage 3): Replace with LLM + tool-calling loop
    # The LLM will generate a unified diff using context from locate_code
    # For now, set a placeholder patch

    context.current_patch = (
        "--- a/placeholder.py\n"
        "+++ b/placeholder.py\n"
        "@@ -1 +1 @@\n"
        "-# placeholder\n"
        "+# fixed\n"
    )

    logger.info(
        "Patch generated",
        extra={"iteration": context.iteration},
    )
    return AgentState.RUN_TESTS, context


async def run_tests(
    context: AgentContext,
    db: AsyncSession,
) -> StateHandler:
    """RUN_TESTS state: Apply the patch and run the test suite.

    Steps:
    1. Apply the patch via `git apply` (Stage 5)
    2. Run the test command in the sandbox (Stage 4)
    3. Check test results
    4. Decide next state based on results + iteration count
    """
    logger.info(
        "Running tests",
        extra={
            "run_id": str(context.run_id),
            "iteration": context.iteration,
        },
    )

    # Store the patch record in the database
    from app.models.patch import Patch

    patch = Patch(
        run_id=context.run_id,
        diff=context.current_patch or "",
        test_result=context.test_output,
        test_passed=context.test_passed,
        iteration_number=context.iteration,
    )
    db.add(patch)
    await db.flush()

    # TODO (Stage 4-5): Replace with actual sandbox execution
    # 1. Apply patch via git apply --check && git apply
    # 2. Run tests in Docker sandbox
    # 3. Parse test results

    # Placeholder: tests fail by default (will be replaced)
    context.test_passed = False
    context.test_output = "Tests not yet implemented (placeholder)"

    # Update patch record with test results
    patch.test_result = context.test_output
    patch.test_passed = context.test_passed
    await db.flush()

    if context.test_passed:
        logger.info("Tests passed!", extra={"iteration": context.iteration})
        return AgentState.OPEN_PR, context
    elif context.iteration >= context.max_iterations:
        logger.warning(
            "Max iterations reached, escalating",
            extra={
                "iteration": context.iteration,
                "max": context.max_iterations,
            },
        )
        context.error_message = (
            f"Failed to fix the issue after {context.max_iterations} iterations"
        )
        return AgentState.ESCALATE, context
    else:
        logger.info(
            "Tests failed, retrying",
            extra={
                "iteration": context.iteration,
                "max": context.max_iterations,
            },
        )
        return AgentState.GENERATE_PATCH, context


async def open_pr(
    context: AgentContext,
    db: AsyncSession,
) -> StateHandler:
    """OPEN_PR state: Create a pull request with the fix.

    Uses the GitHub API to:
    1. Create a new branch
    2. Commit the patch
    3. Open a PR referencing the original issue
    """
    logger.info("Opening PR", extra={"run_id": str(context.run_id)})

    # TODO (Stage 3): Replace with actual GitHub API call
    # For now, set a placeholder PR URL
    context.pr_url = "https://github.com/placeholder/repo/pull/1"

    logger.info(
        "PR opened successfully",
        extra={"pr_url": context.pr_url},
    )
    return AgentState.DONE, context


async def escalate(
    context: AgentContext,
    db: AsyncSession,
) -> StateHandler:
    """ESCALATE state: Mark the run as failed and notify.

    Called when:
    - Max iterations reached without passing tests
    - An unrecoverable error occurred in a previous state
    """
    logger.warning(
        "Escalating run to human",
        extra={
            "run_id": str(context.run_id),
            "error": context.error_message,
            "iterations": context.iteration,
        },
    )

    if not context.error_message:
        context.error_message = "Agent could not resolve the issue"

    return AgentState.DONE, context


# Default handler mapping — maps each state to its handler function
DEFAULT_HANDLERS: dict = {
    AgentState.READ_ISSUE: read_issue,
    AgentState.LOCATE_CODE: locate_code,
    AgentState.GENERATE_PATCH: generate_patch,
    AgentState.RUN_TESTS: run_tests,
    AgentState.OPEN_PR: open_pr,
    AgentState.ESCALATE: escalate,
}
