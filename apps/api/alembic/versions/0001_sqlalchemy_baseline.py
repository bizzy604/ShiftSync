"""SQLAlchemy baseline after Prisma-managed schema.

Revision ID: 0001_sqlalchemy_baseline
Revises:
Create Date: 2026-02-26
"""
from __future__ import annotations


from alembic import op  # noqa: F401
import sqlalchemy as sa  # noqa: F401


# revision identifiers, used by Alembic.
revision = "0001_sqlalchemy_baseline"
down_revision = None
branch_labels = None
depends_on = None


def upgrade() -> None:
    """Adopt existing schema as Alembic baseline without DDL changes."""
    pass


def downgrade() -> None:
    """Baseline downgrade is intentionally a no-op."""
    pass

