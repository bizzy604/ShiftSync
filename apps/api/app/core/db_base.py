"""
MODULE: /apps/api/app/core/db_base.py

FUNCTION:
    Provides core infrastructure logic for `db_base` used across backend modules.

DEPENDENCIES:
    - /apps/api/alembic/env.py
    - /apps/api/app/core/models.py

IMPORTANCE:
    This module is foundational infrastructure; regressions here can cascade across the
    backend.
"""

from sqlalchemy.orm import DeclarativeBase


class Base(DeclarativeBase):
    """Shared SQLAlchemy declarative base for all ORM models."""
