"""Agent state machine — explicit FSM for the bug-fix loop.

Design decision: We use an explicit state machine (enum + dispatch dict)
rather than ReAct/LangChain/LangGraph because:
1. Each state is a standalone, independently testable function.
2. The control flow is visible in code — no framework magic.
3. Every transition is logged, making the agent fully auditable.
4. You can draw the FSM on a whiteboard during an interview.

States: READ_ISSUE -> LOCATE_CODE -> GENERATE_PATCH -> RUN_TESTS
        -> (OPEN_PR on success | GENERATE_PATCH on failure up to max_iterations | ESCALATE)
"""

from __future__ import annotations

import asyncio
import logging
import uuid
from dataclasses import dataclass, field
from enum import StrEnum
from typing import TYPE_CHECKING

from sqlalchemy import update

if TYPE_CHECKING:
    from sqlalchemy.ext.asyncio import AsyncSession

    from app.sandbox.docker_sandbox import DockerSandbox

logger = logging.getLogger(__name__)


class AgentState(StrEnum):
    """States in the agent's finite state machine."""

    READ_ISSUE = "READ_ISSUE"
    LOCATE_CODE = "LOCATE_CODE"
    GENERATE_PATCH = "GENERATE_PATCH"
    RUN_TESTS = "RUN_TESTS"
    OPEN_PR = "OPEN_PR"
    ESCALATE = "ESCALATE"
    DONE = "DONE"


# Terminal states — the FSM stops when it reaches one of these
TERMINAL_STATES = {AgentState.DONE}


@dataclass
class AgentContext:
    """Mutable context passed between state transitions.

    Contains all the data the agent accumulates during a run.
    Immutable config (run_id, URLs) + mutable working data (issue text,
    relevant files, current patch, test output).
    """

    # Immutable config
    run_id: uuid.UUID
    issue_url: str
    repo_url: str
    max_iterations: int = 5

    # Working data accumulated during the run
    issue_text: str | None = None
    issue_title: str | None = None
    relevant_files: list[str] = field(default_factory=list)
    file_contents: dict[str, str] = field(default_factory=dict)
    current_patch: str | None = None
    test_output: str | None = None
    test_passed: bool = False
    iteration: int = 0
    pr_url: str | None = None
    error_message: str | None = None

    # Cost tracking (accumulated from logged LLM calls)
    total_cost: float = 0.0
    total_latency: float = 0.0

    # Repo working directory (set when sandbox starts)
    work_dir: str | None = None
    test_command: str | None = None

    # Sandbox reference for executing commands in the cloned repo
    sandbox: "DockerSandbox | None" = None

    # Conversation history for the LLM (persisted across iterations)
    messages: list[dict] = field(default_factory=list)


async def update_run_state(
    db: AsyncSession,
    run_id: uuid.UUID,
    state: AgentState,
    iteration: int,
    status: str | None = None,
    total_cost: float | None = None,
    total_latency: float | None = None,
    pr_url: str | None = None,
    error_message: str | None = None,
) -> None:
    """Update the run record in the database with the current FSM state.

    This is called after every state transition so the frontend
    can display live progress.
    """
    from app.models.run import Run

    values: dict = {
        "state": state.value,
        "iteration_count": iteration,
    }
    if status is not None:
        values["status"] = status
    if total_cost is not None:
        values["total_cost"] = total_cost
    if total_latency is not None:
        values["total_latency"] = total_latency
    if pr_url is not None:
        values["pr_url"] = pr_url
    if error_message is not None:
        values["error_message"] = error_message

    stmt = update(Run).where(Run.id == run_id).values(**values)
    await db.execute(stmt)
    await db.commit()


async def run_agent(
    context: AgentContext,
    db: AsyncSession,
    state_handlers: dict | None = None,
) -> AgentContext:
    """Execute the agent's state machine loop.

    Args:
        context: The agent context with run configuration.
        db: Async database session for state persistence.
        state_handlers: Optional override of state handlers (for testing).
            If not provided, uses the default handlers from states.py.

    Returns:
        The final AgentContext after the run completes.
    """
    # Import default handlers lazily to allow easy testing with mocks
    if state_handlers is None:
        from app.agent.states import DEFAULT_HANDLERS

        state_handlers = DEFAULT_HANDLERS

    state = AgentState.READ_ISSUE

    # Mark the run as running
    await update_run_state(db, context.run_id, state, context.iteration, status="running")

    logger.info(
        "Agent run started",
        extra={"run_id": str(context.run_id), "state": state.value},
    )

    try:
        while state not in TERMINAL_STATES:
            handler = state_handlers.get(state)
            if handler is None:
                raise ValueError(f"No handler registered for state: {state}")

            logger.info(
                "State transition",
                extra={
                    "run_id": str(context.run_id),
                    "state": state.value,
                    "iteration": context.iteration,
                },
            )

            # Small pacing delay for smooth live frontend stepper visualization
            await asyncio.sleep(1.0)

            # Execute the state handler — returns (next_state, updated_context)
            next_state, context = await handler(context, db)

            # Persist state to DB for live frontend updates
            await update_run_state(
                db,
                context.run_id,
                next_state,
                context.iteration,
                total_cost=context.total_cost,
                total_latency=context.total_latency,
            )

            state = next_state

        # Determine final status
        if context.pr_url:
            final_status = "success"
        elif context.error_message:
            final_status = "failed"
        else:
            final_status = "failed"

        await update_run_state(
            db,
            context.run_id,
            AgentState.DONE,
            context.iteration,
            status=final_status,
            total_cost=context.total_cost,
            total_latency=context.total_latency,
            pr_url=context.pr_url,
            error_message=context.error_message,
        )

        logger.info(
            "Agent run completed",
            extra={
                "run_id": str(context.run_id),
                "status": final_status,
                "iterations": context.iteration,
                "cost": context.total_cost,
            },
        )

    except Exception as e:
        logger.exception(
            "Agent run failed with exception",
            extra={"run_id": str(context.run_id)},
        )
        context.error_message = str(e)
        await update_run_state(
            db,
            context.run_id,
            AgentState.DONE,
            context.iteration,
            status="error",
            error_message=str(e),
        )

    return context
