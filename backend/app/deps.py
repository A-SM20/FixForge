"""Dependency injection for FastAPI routes.

Why DI over global session: Each request gets its own session with
proper lifecycle management (open at start, close/rollback at end).
This prevents session leaks and ensures transaction isolation.
"""

from collections.abc import AsyncGenerator

from sqlalchemy.ext.asyncio import AsyncSession

from app.db.session import async_session_factory


async def get_db() -> AsyncGenerator[AsyncSession, None]:
    """Yield an async database session scoped to the request lifecycle."""
    async with async_session_factory() as session:
        try:
            yield session
            await session.commit()
        except Exception:
            await session.rollback()
            raise
        finally:
            await session.close()
