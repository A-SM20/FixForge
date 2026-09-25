import asyncio
import uuid
import sys
import os
import logging

logging.basicConfig(level=logging.DEBUG)

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

# Ensure models are registered with SQLAlchemy
import app.models.log_entry
import app.models.patch
import app.models.run

from app.services.run_service import execute_run
from app.db.session import engine

from app.db.base import Base
from app.agent.state_machine import AgentContext, run_agent
from app.agent.states import read_issue, locate_code, generate_patch, run_tests, open_pr, escalate
from app.agent.states import AgentState
from app.db.session import async_session_factory

async def main():
    run_id = uuid.uuid4()

    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

    issue_url = "https://github.com/A-SM20/myapp1/issues/1"
    repo_url = "https://github.com/A-SM20/myapp1"

    print(f"\n{'='*60}")
    print(f"Starting E2E run: {run_id}")
    print(f"Issue: {issue_url}")
    print(f"{'='*60}\n")

    await execute_run(run_id, issue_url, repo_url)

    # Read back the run record from DB
    from sqlalchemy import select
    from app.models.run import Run
    from app.models.patch import Patch as PatchModel
    async with async_session_factory() as db:
        result = await db.execute(select(Run).where(Run.id == run_id))
        run_rec = result.scalar_one_or_none()
        if run_rec:
            print(f"\n{'='*60}")
            print(f"RUN RESULT")
            print(f"  status:      {run_rec.status}")
            print(f"  state:       {run_rec.state}")
            print(f"  pr_url:      {run_rec.pr_url}")
            print(f"  iterations:  {run_rec.iteration_count}")
            print(f"  error:       {run_rec.error_message}")
            print(f"{'='*60}")

        patches = await db.execute(
            select(PatchModel).where(PatchModel.run_id == run_id).order_by(PatchModel.iteration_number)
        )
        for p in patches.scalars():
            print(f"\n--- Patch #{p.iteration_number} ---")
            print(f"  test_passed: {p.test_passed}")
            print(f"  test_result (first 500 chars):\n{(p.test_result or '')[:500]}")
            print(f"  diff (first 800 chars):\n{(p.diff or '')[:800]}")

    await engine.dispose()

if __name__ == "__main__":
    asyncio.run(main())
