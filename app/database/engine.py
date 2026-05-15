"""Async SQLAlchemy engine and session factory (PostgreSQL via asyncpg).

``get_async_session`` is the FastAPI dependency: commits on success,
rolls back on errors, always closes.
"""

from __future__ import annotations

from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine, async_sessionmaker
from sqlalchemy.orm import DeclarativeBase
from sqlalchemy.engine import make_url
from app.config import get_settings

settings = get_settings()


def asyncpg_engine_kwargs(database_url: str) -> tuple[str, dict]:
    """Normalize managed Postgres URLs for asyncpg.

    Hosted Postgres providers commonly expose ``sslmode=require`` URLs for
    psycopg. ``asyncpg`` expects SSL through ``connect_args`` instead, so we
    strip psycopg-only query parameters before building the async engine.
    """
    url = make_url(database_url)
    query = dict(url.query)
    connect_args: dict = {}
    sslmode = query.pop("sslmode", None)
    if sslmode and str(sslmode).lower() not in {"disable", "allow"}:
        connect_args["ssl"] = True
    if "ssl" in query:
        raw_ssl = str(query.pop("ssl")).lower()
        if raw_ssl in {"1", "true", "require", "verify-full", "verify-ca"}:
            connect_args["ssl"] = True
    return url.set(query=query).render_as_string(hide_password=False), connect_args


_database_url, _connect_args = asyncpg_engine_kwargs(settings.database_url)

async_engine = create_async_engine(
    _database_url,
    echo=False,
    pool_size=10,
    max_overflow=20,
    pool_pre_ping=True,
    pool_recycle=300,
    connect_args=_connect_args,
)

AsyncSessionLocal = async_sessionmaker(
    bind=async_engine,
    class_=AsyncSession,
    expire_on_commit=False,
)


class Base(DeclarativeBase):
    pass


async def get_async_session() -> AsyncSession:
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
    """Create tables that don't already exist."""
    async with async_engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
