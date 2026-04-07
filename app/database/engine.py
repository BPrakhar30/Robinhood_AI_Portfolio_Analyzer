"""Async SQLAlchemy engine and session factory for the API.

``echo`` is fixed to ``False`` to limit SQL log noise (previously tied to
``settings.debug``). SQLite URLs skip connection pool options because SQLite's
driver does not support ``pool_size`` / ``max_overflow``; PostgreSQL and other
servers get a small pool with ``pool_pre_ping`` for stale connection recovery.

``get_async_session`` is intended as a FastAPI dependency: yield inside
``try``/``except``/``finally`` commits on success, rolls back on errors, and
always closes the session.

Added: 2026-04-03
"""
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine, async_sessionmaker
from sqlalchemy.orm import DeclarativeBase
from app.config import get_settings

settings = get_settings()

_engine_kwargs: dict = {
    "echo": False,  # Intentionally not tied to debug — avoids noisy SQL logs in dev
}

# SQLite doesn't support pool_size/max_overflow
if not settings.database_url.startswith("sqlite"):
    _engine_kwargs.update(
        {
            "pool_size": 10,
            "max_overflow": 20,
            "pool_pre_ping": True,
        }
    )

async_engine = create_async_engine(settings.database_url, **_engine_kwargs)

AsyncSessionLocal = async_sessionmaker(
    bind=async_engine,
    class_=AsyncSession,
    expire_on_commit=False,
)


class Base(DeclarativeBase):
    pass


async def get_async_session() -> AsyncSession:
    # FastAPI Depends pattern: commit on success, rollback on error, always close.
    async with AsyncSessionLocal() as session:
        try:
            yield session
            await session.commit()
        except Exception:
            await session.rollback()
            raise
        finally:
            await session.close()


async def init_db():
    """Create tables that don't already exist. Used for development/testing only."""
    async with async_engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
