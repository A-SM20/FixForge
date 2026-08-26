"""API routes for managing agent runs.

CRUD endpoints for the /api/runs resource. The POST endpoint
creates a run record and enqueues the agent loop as a background task
so the response returns immediately (201 Created).
"""

import uuid

from fastapi import APIRouter, BackgroundTasks, Depends, HTTPException, Query
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.deps import get_db
from app.models.run import Run
from app.schemas.run import PatchSummary, RunCreate, RunDetail, RunListItem, RunListResponse
from app.services.run_service import execute_run

router = APIRouter(prefix="/api/runs", tags=["runs"])


@router.post("/", response_model=RunDetail, status_code=201)
async def create_run(
    body: RunCreate,
    background_tasks: BackgroundTasks,
    db: AsyncSession = Depends(get_db),
) -> RunDetail:
    """Create a new agent run.

    Creates the DB record, commits to Postgres, and enqueues the agent
    state machine as a FastAPI background task.
    """
    run = Run(
        issue_url=str(body.issue_url),
        repo_url=str(body.repo_url),
        status="pending",
        state="READ_ISSUE",
    )
    db.add(run)
    await db.commit()
    await db.refresh(run)

    # Enqueue the agent loop as a background task
    background_tasks.add_task(
        execute_run, run.id, str(body.issue_url), str(body.repo_url)
    )

    return _run_to_detail(run, patches_loaded=False)


@router.get("/", response_model=RunListResponse)
async def list_runs(
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    status: str | None = Query(None, description="Filter by status"),
    db: AsyncSession = Depends(get_db),
) -> RunListResponse:
    """List all runs with pagination and optional status filter."""
    query = select(Run)
    count_query = select(func.count(Run.id))

    if status:
        query = query.where(Run.status == status)
        count_query = count_query.where(Run.status == status)

    total_result = await db.execute(count_query)
    total = total_result.scalar_one()

    query = query.order_by(Run.created_at.desc())
    query = query.offset((page - 1) * page_size).limit(page_size)
    result = await db.execute(query)
    runs = list(result.scalars().all())

    return RunListResponse(
        items=[RunListItem.model_validate(r) for r in runs],
        total=total,
        page=page,
        page_size=page_size,
    )


@router.get("/{run_id}", response_model=RunDetail)
async def get_run(
    run_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
) -> RunDetail:
    """Get full details of a specific run, including patches."""
    query = (
        select(Run)
        .where(Run.id == run_id)
        .options(selectinload(Run.patches))
    )
    result = await db.execute(query)
    run = result.scalar_one_or_none()

    if not run:
        raise HTTPException(status_code=404, detail="Run not found")

    return _run_to_detail(run)


@router.delete("/{run_id}", status_code=204)
async def delete_run(
    run_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
) -> None:
    """Cancel and delete a run.

    Cascade delete removes associated patches and log entries.
    """
    query = select(Run).where(Run.id == run_id)
    result = await db.execute(query)
    run = result.scalar_one_or_none()

    if not run:
        raise HTTPException(status_code=404, detail="Run not found")

    await db.delete(run)
    await db.commit()


def _run_to_detail(run: Run, patches_loaded: bool = True) -> RunDetail:
    """Convert a Run ORM instance to a RunDetail response."""
    patches = []
    if patches_loaded:
        try:
            patches = [
                PatchSummary(
                    id=p.id,
                    iteration_number=p.iteration_number,
                    test_passed=p.test_passed,
                    test_result=p.test_result,
                    diff_preview=p.diff[:500] if p.diff else "",
                    created_at=p.created_at,
                )
                for p in run.patches
            ]
        except Exception:
            patches = []

    return RunDetail(
        id=run.id,
        issue_url=run.issue_url,
        repo_url=run.repo_url,
        status=run.status,
        state=run.state,
        iteration_count=run.iteration_count,
        total_cost=run.total_cost,
        total_latency=run.total_latency,
        pr_url=run.pr_url,
        error_message=run.error_message,
        created_at=run.created_at,
        updated_at=run.updated_at,
        patches=patches,
    )
