"""
MODULE: /apps/api/app/core/__init__.py

FUNCTION:
    Provides package-level exports and initialization for `apps/api/app/core/__init__.py`.

DEPENDENCIES:
    - (No in-repo dependents detected.)

IMPORTANCE:
    This module is foundational infrastructure; regressions here can cascade across the
    backend.
"""


from app.core.errors import AppError

__all__ = ["AppError"]
