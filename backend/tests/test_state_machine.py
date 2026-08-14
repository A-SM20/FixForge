"""Unit tests for the agent state machine.

Tests the FSM transitions independently by injecting mock state handlers.
This validates the control flow logic without needing LLM calls,
Docker, or GitHub API access.
"""

import uuid

import pytest

from app.agent.state_machine import AgentContext, AgentState, run_agent

# --- Helper: mock state handlers ---


def make_mock_handler(next_state: AgentState, mutator=None):
    """Create a mock state handler that transitions to next_state.

    Args:
        next_state: The state to transition to.
        mutator: Optional callable to modify context before returning.
    """

    async def handler(context: AgentContext, db):
        if mutator:
            mutator(context)
        return next_state, context

    return handler


# --- Tests ---


@pytest.mark.asyncio
async def test_happy_path_transitions(test_session):
    """Agent should follow READ_ISSUE -> LOCATE_CODE -> GENERATE_PATCH ->
    RUN_TESTS -> OPEN_PR -> DONE on the happy path."""
    transition_log = []

    def log_transition(state_name):
        def mutator(ctx):
            transition_log.append(state_name)
            if state_name == "OPEN_PR":
                ctx.pr_url = "https://github.com/test/repo/pull/1"
            if state_name == "GENERATE_PATCH":
                ctx.iteration += 1

        return mutator

    handlers = {
        AgentState.READ_ISSUE: make_mock_handler(
            AgentState.LOCATE_CODE, log_transition("READ_ISSUE")
        ),
        AgentState.LOCATE_CODE: make_mock_handler(
            AgentState.GENERATE_PATCH, log_transition("LOCATE_CODE")
        ),
        AgentState.GENERATE_PATCH: make_mock_handler(
            AgentState.RUN_TESTS, log_transition("GENERATE_PATCH")
        ),
        AgentState.RUN_TESTS: make_mock_handler(
            AgentState.OPEN_PR, log_transition("RUN_TESTS")
        ),
        AgentState.OPEN_PR: make_mock_handler(
            AgentState.DONE, log_transition("OPEN_PR")
        ),
        AgentState.ESCALATE: make_mock_handler(
            AgentState.DONE, log_transition("ESCALATE")
        ),
    }

    context = AgentContext(
        run_id=uuid.uuid4(),
        issue_url="https://github.com/test/repo/issues/1",
        repo_url="https://github.com/test/repo",
    )

    result = await run_agent(context, test_session, state_handlers=handlers)

    assert transition_log == [
        "READ_ISSUE",
        "LOCATE_CODE",
        "GENERATE_PATCH",
        "RUN_TESTS",
        "OPEN_PR",
    ]
    assert result.pr_url == "https://github.com/test/repo/pull/1"


@pytest.mark.asyncio
async def test_retry_loop_on_test_failure(test_session):
    """Agent should retry GENERATE_PATCH -> RUN_TESTS up to max_iterations."""
    call_count = {"run_tests": 0}

    def run_tests_mutator(ctx):
        call_count["run_tests"] += 1
        # Fail the first 2 times, pass on the 3rd
        if call_count["run_tests"] >= 3:
            ctx.pr_url = "https://github.com/test/repo/pull/1"

    def gen_patch_mutator(ctx):
        ctx.iteration += 1

    async def run_tests_handler(ctx, db):
        run_tests_mutator(ctx)
        if call_count["run_tests"] >= 3:
            return AgentState.OPEN_PR, ctx
        elif ctx.iteration >= ctx.max_iterations:
            ctx.error_message = "Max iterations reached"
            return AgentState.ESCALATE, ctx
        else:
            return AgentState.GENERATE_PATCH, ctx

    handlers = {
        AgentState.READ_ISSUE: make_mock_handler(AgentState.LOCATE_CODE),
        AgentState.LOCATE_CODE: make_mock_handler(AgentState.GENERATE_PATCH),
        AgentState.GENERATE_PATCH: make_mock_handler(
            AgentState.RUN_TESTS, gen_patch_mutator
        ),
        AgentState.RUN_TESTS: run_tests_handler,
        AgentState.OPEN_PR: make_mock_handler(
            AgentState.DONE,
            lambda ctx: setattr(ctx, "pr_url", ctx.pr_url or "https://github.com/test/repo/pull/1"),
        ),
        AgentState.ESCALATE: make_mock_handler(AgentState.DONE),
    }

    context = AgentContext(
        run_id=uuid.uuid4(),
        issue_url="https://github.com/test/repo/issues/1",
        repo_url="https://github.com/test/repo",
        max_iterations=5,
    )

    result = await run_agent(context, test_session, state_handlers=handlers)

    # Should have retried: 3 GENERATE_PATCH + 3 RUN_TESTS
    assert call_count["run_tests"] == 3
    assert result.iteration == 3
    assert result.pr_url is not None


@pytest.mark.asyncio
async def test_escalate_on_max_iterations(test_session):
    """Agent should escalate after max_iterations failures."""

    def gen_patch_mutator(ctx):
        ctx.iteration += 1

    async def run_tests_handler(ctx, db):
        if ctx.iteration >= ctx.max_iterations:
            ctx.error_message = f"Failed after {ctx.max_iterations} iterations"
            return AgentState.ESCALATE, ctx
        return AgentState.GENERATE_PATCH, ctx

    async def escalate_handler(ctx, db):
        if not ctx.error_message:
            ctx.error_message = "Agent could not resolve the issue"
        return AgentState.DONE, ctx

    handlers = {
        AgentState.READ_ISSUE: make_mock_handler(AgentState.LOCATE_CODE),
        AgentState.LOCATE_CODE: make_mock_handler(AgentState.GENERATE_PATCH),
        AgentState.GENERATE_PATCH: make_mock_handler(
            AgentState.RUN_TESTS, gen_patch_mutator
        ),
        AgentState.RUN_TESTS: run_tests_handler,
        AgentState.OPEN_PR: make_mock_handler(AgentState.DONE),
        AgentState.ESCALATE: escalate_handler,
    }

    context = AgentContext(
        run_id=uuid.uuid4(),
        issue_url="https://github.com/test/repo/issues/1",
        repo_url="https://github.com/test/repo",
        max_iterations=3,
    )

    result = await run_agent(context, test_session, state_handlers=handlers)

    assert result.iteration == 3
    assert result.error_message is not None
    assert "3" in result.error_message
    assert result.pr_url is None


@pytest.mark.asyncio
async def test_exception_in_handler_sets_error_status(test_session):
    """An exception in a state handler should set status to 'error'."""

    async def failing_handler(ctx, db):
        raise RuntimeError("Simulated LLM API failure")

    handlers = {
        AgentState.READ_ISSUE: failing_handler,
        AgentState.LOCATE_CODE: make_mock_handler(AgentState.GENERATE_PATCH),
        AgentState.GENERATE_PATCH: make_mock_handler(AgentState.RUN_TESTS),
        AgentState.RUN_TESTS: make_mock_handler(AgentState.OPEN_PR),
        AgentState.OPEN_PR: make_mock_handler(AgentState.DONE),
        AgentState.ESCALATE: make_mock_handler(AgentState.DONE),
    }

    context = AgentContext(
        run_id=uuid.uuid4(),
        issue_url="https://github.com/test/repo/issues/1",
        repo_url="https://github.com/test/repo",
    )

    result = await run_agent(context, test_session, state_handlers=handlers)

    assert result.error_message == "Simulated LLM API failure"


@pytest.mark.asyncio
async def test_early_escalate_from_read_issue(test_session):
    """If READ_ISSUE fails, should escalate immediately."""

    async def escalate_handler(ctx, db):
        if not ctx.error_message:
            ctx.error_message = "Agent could not resolve the issue"
        return AgentState.DONE, ctx

    handlers = {
        AgentState.READ_ISSUE: make_mock_handler(
            AgentState.ESCALATE,
            lambda ctx: setattr(ctx, "error_message", "Issue not found"),
        ),
        AgentState.LOCATE_CODE: make_mock_handler(AgentState.GENERATE_PATCH),
        AgentState.GENERATE_PATCH: make_mock_handler(AgentState.RUN_TESTS),
        AgentState.RUN_TESTS: make_mock_handler(AgentState.OPEN_PR),
        AgentState.OPEN_PR: make_mock_handler(AgentState.DONE),
        AgentState.ESCALATE: escalate_handler,
    }

    context = AgentContext(
        run_id=uuid.uuid4(),
        issue_url="https://github.com/test/repo/issues/999",
        repo_url="https://github.com/test/repo",
    )

    result = await run_agent(context, test_session, state_handlers=handlers)

    assert result.error_message == "Issue not found"
    assert result.pr_url is None


@pytest.mark.asyncio
async def test_agent_context_defaults():
    """AgentContext should have sensible defaults."""
    ctx = AgentContext(
        run_id=uuid.uuid4(),
        issue_url="https://github.com/test/repo/issues/1",
        repo_url="https://github.com/test/repo",
    )

    assert ctx.max_iterations == 5
    assert ctx.iteration == 0
    assert ctx.issue_text is None
    assert ctx.relevant_files == []
    assert ctx.file_contents == {}
    assert ctx.test_passed is False
    assert ctx.total_cost == 0.0
    assert ctx.messages == []
