"""FastAPI application entry point.

Why lifespan context manager: Replaces deprecated on_event("startup")/
on_event("shutdown"). Provides clean setup/teardown for DB connections
and other resources.
"""

from contextlib import asynccontextmanager
from pathlib import Path

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles

from app.api.routes_eval import router as eval_router
from app.api.routes_runs import router as runs_router
from app.api.routes_ws import router as ws_router
from app.core.config import get_settings


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifespan: setup and teardown."""
    # Startup
    settings = get_settings()
    app.state.settings = settings

    import app.models.log_entry  # noqa: F401
    import app.models.patch  # noqa: F401
    import app.models.run  # noqa: F401
    from app.db.base import Base
    from app.db.session import engine

    try:
        async with engine.begin() as conn:
            await conn.run_sync(Base.metadata.create_all)
    except Exception:
        pass

    yield

    # Shutdown
    await engine.dispose()


def create_app() -> FastAPI:
    """Application factory pattern — enables different configs for test/prod."""
    settings = get_settings()

    app = FastAPI(
        title="FixForge",
        description="Autonomous bug-fix / PR agent API",
        version="0.1.0",
        lifespan=lifespan,
    )

    # CORS — allow the Vite dev server during development
    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.cors_origins,
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    # Register API routers
    app.include_router(runs_router)
    app.include_router(ws_router)
    app.include_router(eval_router)

    @app.get("/health", tags=["meta"])
    async def health_check():
        """Health check endpoint for load balancers and uptime monitors."""
        return {"status": "ok", "version": "0.1.0"}

    # Mount static frontend build if it exists
    frontend_dist = Path(__file__).resolve().parent.parent.parent / "frontend" / "dist"
    if frontend_dist.exists() and (frontend_dist / "index.html").exists():
        app.mount("/", StaticFiles(directory=str(frontend_dist), html=True), name="frontend")

    return app


app = create_app()
