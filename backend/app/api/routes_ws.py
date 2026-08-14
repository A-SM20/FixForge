"""WebSocket endpoint for live run progress updates.

Pushes state-machine transitions to the frontend in real-time.
Falls back to polling if WebSocket connection drops.
"""

from __future__ import annotations

import asyncio
import uuid

from fastapi import APIRouter, WebSocket, WebSocketDisconnect
from sqlalchemy import select

from app.models.run import Run

router = APIRouter(tags=["websocket"])


@router.websocket("/ws/runs/{run_id}")
async def run_progress_ws(
    websocket: WebSocket,
    run_id: uuid.UUID,
) -> None:
    """WebSocket endpoint for live run progress.

    Sends JSON updates every 2 seconds with the current run state.
    The frontend connects here on the Run Detail page.
    """
    await websocket.accept()

    try:
        from app.db.session import async_session_factory

        while True:
            async with async_session_factory() as db:
                result = await db.execute(
                    select(Run).where(Run.id == run_id)
                )
                run = result.scalar_one_or_none()

                if not run:
                    await websocket.send_json({"error": "Run not found"})
                    break

                await websocket.send_json({
                    "id": str(run.id),
                    "status": run.status,
                    "state": run.state,
                    "iteration_count": run.iteration_count,
                    "total_cost": run.total_cost,
                    "total_latency": run.total_latency,
                    "pr_url": run.pr_url,
                    "error_message": run.error_message,
                })

                # Stop pushing if run is complete
                if run.status in ("success", "failed", "error"):
                    break

            await asyncio.sleep(2)

    except WebSocketDisconnect:
        pass
    except Exception:
        try:
            await websocket.close()
        except Exception:
            pass
