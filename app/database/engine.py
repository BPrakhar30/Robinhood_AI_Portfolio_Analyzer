"""Async SQLAlchemy engine and session factory (PostgreSQL via asyncpg).

``get_async_session`` is the FastAPI dependency: commits on success,
rolls back on errors, always closes.
"""

from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine, async_sessionmaker
from sqlalchemy.orm import DeclarativeBase
from app.config import get_settings

settings = get_settings()

async_engine = create_async_engine(
    settings.database_url,
    echo=False,
    pool_size=10,
    max_overflow=20,
    pool_pre_ping=True,
    pool_recycle=300,
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
    """Create tables (and enum types) that don't already exist.

    PostgreSQL enum types must be created with ``checkfirst=True`` before
    ``create_all`` is called, otherwise SQLAlchemy emits a bare CREATE TYPE
    that blows up if the type already exists.
    """
    from sqlalchemy import event, DDL
    import sqlalchemy as sa

    def _create_enums_first(conn):
        for schema_item in Base.metadata.sorted_tables:
            for col in schema_item.columns:
                if isinstance(col.type, sa.Enum) and col.type.name:
                    col.type.create(conn, checkfirst=True)
        Base.metadata.create_all(conn, checkfirst=True)

    async with async_engine.begin() as conn:
        await conn.run_sync(_create_enums_first)
