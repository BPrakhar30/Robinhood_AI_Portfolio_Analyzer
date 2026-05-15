"""Create baseline application schema.

Revision ID: 0001_baseline
Revises:
Create Date: 2026-05-15
"""

from __future__ import annotations

from alembic import op

from app.database.engine import Base
import app.database.models  # noqa: F401 - registers ORM tables with Base.metadata

revision = "0001_baseline"
down_revision = None
branch_labels = None
depends_on = None


def upgrade() -> None:
    bind = op.get_bind()
    Base.metadata.create_all(bind=bind)


def downgrade() -> None:
    bind = op.get_bind()
    Base.metadata.drop_all(bind=bind)
