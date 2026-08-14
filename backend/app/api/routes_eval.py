"""API routes for evaluation harness."""

from __future__ import annotations

from fastapi import APIRouter, Query

from eval.harness import load_tasks, run_eval

router = APIRouter(prefix="/api/eval", tags=["eval"])


@router.get("/tasks")
async def list_eval_tasks():
    """List all available eval tasks."""
    tasks = load_tasks()
    return {
        "tasks": [
            {
                "id": t.id,
                "repo": t.repo,
                "difficulty": t.difficulty,
                "issue_text_preview": t.issue_text[:200],
            }
            for t in tasks
        ]
    }


@router.post("/run")
async def trigger_eval(
    task_ids: list[str] | None = Query(None),
):
    """Trigger an eval run.

    Pass task_ids to run specific tasks, or omit to run all.
    """
    report = await run_eval(task_ids=task_ids)
    return report.to_dict()
