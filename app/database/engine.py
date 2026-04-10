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
    """Create tables that don't already exist and add missing columns.

    SQLite's create_all won't add new columns to existing tables, so
    _ensure_columns handles lightweight schema migrations at startup.
    """
    async with async_engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
        if settings.database_url.startswith("sqlite"):
            await conn.run_sync(_ensure_columns)


def _ensure_columns(conn):
    """Add columns that may be missing from existing SQLite tables."""
    import sqlalchemy as sa

    _add_column_if_missing(conn, "users", "password_reset_token", "VARCHAR(255)")
    _add_column_if_missing(conn, "users", "password_reset_expires_at", "DATETIME")


def _add_column_if_missing(conn, table: str, column: str, col_type: str):
    """Safely add a column to a SQLite table if it doesn't exist yet."""
    import sqlalchemy as sa

    result = conn.execute(sa.text(f"PRAGMA table_info({table})"))
    existing = {row[1] for row in result}
    if column not in existing:
        conn.execute(sa.text(f"ALTER TABLE {table} ADD COLUMN {column} {col_type}"))
        conn.execute(sa.text("SELECT 1"))
