"""
MODULE: /apps/api/alembic/versions/0001_sqlalchemy_baseline.py

FUNCTION:
    Defines database migration/runtime infrastructure for schema evolution.

DEPENDENCIES:
    - (No in-repo dependents detected.)

IMPORTANCE:
    This module supports operational reliability for setup, deployment, or data lifecycle
    workflows.
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
