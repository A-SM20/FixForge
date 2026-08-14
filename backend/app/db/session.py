"""Async database session factory.

Why async: The agent loop is I/O-heavy (LLM calls, Docker API, GitHub API).
A blocking ORM would stall the event loop and prevent serving other
requests while an agent run is in progress.

Why connection pooling: FastAPI handles many concurrent requests;
pool_size and max_overflow control how many simultaneous DB connections
we maintain.
"""

from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

from app.core.config import get_settings

settings = get_settings()

engine = create_async_engine(
    settings.database_url,
    echo=settings.debug,
    pool_size=10,
    max_overflow=20,
    pool_pre_ping=True,  # Detect stale connections
)

async_session_factory = async_sessionmaker(
    engine,
    class_=AsyncSession,
    expire_on_commit=False,  # Prevent lazy-load issues after commit
)
