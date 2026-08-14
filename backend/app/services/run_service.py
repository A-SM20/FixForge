"""Run service — orchestrates the full agent lifecycle.

Bridges the API layer and the agent state machine. Creates the
AgentContext, manages the sandbox lifecycle, and coordinates
the agent run as a background task.
"""

from __future__ import annotations

import logging
import uuid
from typing import TYPE_CHECKING

from app.agent.state_machine import AgentContext, run_agent
from app.core.config import get_settings
from app.db.session import async_session_factory
from app.sandbox.docker_sandbox import DockerSandbox

if TYPE_CHECKING:
    pass

logger = logging.getLogger(__name__)


async def execute_run(run_id: uuid.UUID, issue_url: str, repo_url: str) -> None:
    """Execute a full agent run as a background task.

    This is the entry point called from the API route's BackgroundTasks.
    It manages its own DB session and sandbox lifecycle.
    """
    settings = get_settings()

    logger.info(
        "Starting run execution",
        extra={
            "run_id": str(run_id),
            "issue_url": issue_url,
            "repo_url": repo_url,
        },
    )

    # Create the agent context
    context = AgentContext(
        run_id=run_id,
        issue_url=issue_url,
        repo_url=repo_url,
        max_iterations=settings.max_iterations,
    )

    # Run with its own session (background task needs its own session)
    async with async_session_factory() as db:
        try:
            async with DockerSandbox(repo_url, settings) as sandbox:
                context.work_dir = sandbox.work_dir

                # Execute the state machine
                result = await run_agent(context, db)

                logger.info(
                    "Run completed",
                    extra={
                        "run_id": str(run_id),
                        "status": "success" if result.pr_url else "failed",
                        "iterations": result.iteration,
                        "cost": result.total_cost,
                    },
                )
        except Exception as e:
            logger.exception(
                "Run execution failed",
                extra={"run_id": str(run_id)},
            )
            # Update the run status to error
            from sqlalchemy import update

            from app.models.run import Run

            stmt = (
                update(Run)
                .where(Run.id == run_id)
                .values(
                    status="error",
                    error_message=str(e),
                )
            )
            await db.execute(stmt)
            await db.commit()
