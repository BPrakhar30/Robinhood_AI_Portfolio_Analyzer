from __future__ import annotations

from logging.config import fileConfig

from alembic import context
from sqlalchemy import engine_from_config, pool
from sqlalchemy.engine import make_url

from app.config import get_settings
from app.database.engine import Base
import app.database.models  # noqa: F401 - registers ORM tables with Base.metadata

config = context.config

if config.config_file_name is not None:
    fileConfig(config.config_file_name)

target_metadata = Base.metadata


def _database_url_sync() -> str:
    settings = get_settings()
    raw_url = settings.database_url_sync or settings.database_url
    url = make_url(raw_url)
    if url.drivername == "postgresql+asyncpg":
        url = url.set(drivername="postgresql")
    return url.render_as_string(hide_password=False)


def run_migrations_offline() -> None:
    context.configure(
        url=_database_url_sync(),
        target_metadata=target_metadata,
        literal_binds=True,
        dialect_opts={"paramstyle": "named"},
    )

    with context.begin_transaction():
        context.run_migrations()


def run_migrations_online() -> None:
    configuration = config.get_section(config.config_ini_section, {})
    configuration["sqlalchemy.url"] = _database_url_sync()
    connectable = engine_from_config(
        configuration,
        prefix="sqlalchemy.",
        poolclass=pool.NullPool,
    )

    with connectable.connect() as connection:
        context.configure(connection=connection, target_metadata=target_metadata)

        with context.begin_transaction():
            context.run_migrations()


if context.is_offline_mode():
    run_migrations_offline()
else:
    run_migrations_online()
