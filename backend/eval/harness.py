"""Eval harness — runs the agent against a curated set of GitHub issues.

Design decision: Custom lightweight harness (not SWE-bench) for:
1. Fast iteration during development
2. Config-driven — add new issues by editing issues.yaml
3. Reports resolve rate, iterations, cost, and latency
"""

from __future__ import annotations

import logging
import time
from dataclasses import dataclass, field
from pathlib import Path

import yaml

from app.core.config import get_settings

logger = logging.getLogger(__name__)


@dataclass
class EvalTask:
    """A single evaluation task."""

    id: str
    repo: str
    commit_sha: str
    issue_text: str
    test_command: str
    difficulty: str = "medium"


@dataclass
class EvalResult:
    """Result of running the agent on a single eval task."""

    task_id: str
    resolved: bool = False
    iterations: int = 0
    cost_usd: float = 0.0
    latency_s: float = 0.0
    error: str | None = None


@dataclass
class EvalReport:
    """Summary report of an eval run."""

    results: list[EvalResult] = field(default_factory=list)

    @property
    def resolve_rate(self) -> float:
        if not self.results:
            return 0.0
        return sum(1 for r in self.results if r.resolved) / len(self.results)

    @property
    def total_cost(self) -> float:
        return sum(r.cost_usd for r in self.results)

    @property
    def avg_latency(self) -> float:
        if not self.results:
            return 0.0
        return sum(r.latency_s for r in self.results) / len(self.results)

    @property
    def avg_iterations(self) -> float:
        resolved = [r for r in self.results if r.resolved]
        if not resolved:
            return 0.0
        return sum(r.iterations for r in resolved) / len(resolved)

    def to_dict(self) -> dict:
        return {
            "resolve_rate": round(self.resolve_rate, 3),
            "total_cost_usd": round(self.total_cost, 4),
            "avg_latency_s": round(self.avg_latency, 2),
            "avg_iterations": round(self.avg_iterations, 2),
            "total_tasks": len(self.results),
            "resolved_tasks": sum(1 for r in self.results if r.resolved),
            "results": [
                {
                    "task_id": r.task_id,
                    "resolved": r.resolved,
                    "iterations": r.iterations,
                    "cost_usd": round(r.cost_usd, 4),
                    "latency_s": round(r.latency_s, 2),
                    "error": r.error,
                }
                for r in self.results
            ],
        }


def load_tasks(config_path: str | None = None) -> list[EvalTask]:
    """Load eval tasks from YAML config."""
    if config_path is None:
        config_path = str(
            Path(__file__).parent / "issues.yaml"
        )

    with open(config_path) as f:
        data = yaml.safe_load(f)

    return [
        EvalTask(
            id=task["id"],
            repo=task["repo"],
            commit_sha=task["commit_sha"],
            issue_text=task["issue_text"],
            test_command=task["test_command"],
            difficulty=task.get("difficulty", "medium"),
        )
        for task in data["tasks"]
    ]


async def run_eval(
    config_path: str | None = None,
    task_ids: list[str] | None = None,
) -> EvalReport:
    """Run the eval harness against all (or selected) tasks.

    Args:
        config_path: Path to the issues.yaml file.
        task_ids: Optional list of task IDs to run (runs all if None).

    Returns:
        EvalReport with results for each task.
    """
    settings = get_settings()
    tasks = load_tasks(config_path)

    if task_ids:
        tasks = [t for t in tasks if t.id in task_ids]

    report = EvalReport()

    for task in tasks:
        logger.info(
            "Running eval task",
            extra={"task_id": task.id, "repo": task.repo},
        )

        start = time.time()
        result = EvalResult(task_id=task.id)

        try:
            # Import here to avoid circular deps
            from app.agent.state_machine import AgentContext, run_agent
            from app.db.session import async_session_factory
            from app.sandbox.docker_sandbox import DockerSandbox

            repo_url = f"https://github.com/{task.repo}"

            async with async_session_factory() as db:
                # Create a run record for this eval task
                import uuid

                from app.models.run import Run

                run = Run(
                    id=uuid.uuid4(),
                    issue_url=f"{repo_url}/issues/0",
                    repo_url=repo_url,
                    status="running",
                    state="READ_ISSUE",
                )
                db.add(run)
                await db.flush()

                context = AgentContext(
                    run_id=run.id,
                    issue_url=f"{repo_url}/issues/0",
                    repo_url=repo_url,
                    max_iterations=settings.max_iterations,
                    issue_text=task.issue_text,
                    test_command=task.test_command,
                )

                async with DockerSandbox(
                    repo_url,
                    settings,
                    commit_sha=task.commit_sha,
                ) as sandbox:
                    context.work_dir = sandbox.work_dir
                    final_ctx = await run_agent(context, db)

                result.resolved = final_ctx.pr_url is not None
                result.iterations = final_ctx.iteration
                result.cost_usd = final_ctx.total_cost

        except Exception as e:
            result.error = str(e)
            logger.exception(
                "Eval task failed",
                extra={"task_id": task.id},
            )

        result.latency_s = time.time() - start
        report.results.append(result)

        logger.info(
            "Eval task complete",
            extra={
                "task_id": task.id,
                "resolved": result.resolved,
                "cost": result.cost_usd,
            },
        )

    return report
