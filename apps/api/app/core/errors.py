"""
MODULE: /apps/api/app/core/errors.py

FUNCTION:
    Provides core infrastructure logic for `errors` used across backend modules.

DEPENDENCIES:
    - /apps/api/app/core/__init__.py
    - /apps/api/app/main.py
    - /apps/api/app/services/errors.py
    - /apps/api/tests/integration/test_skills_routes.py

IMPORTANCE:
    This module is foundational infrastructure; regressions here can cascade across the
    backend.
"""

from __future__ import annotations

from typing import Any


class AppError(Exception):
    """Base typed application error for structured API responses."""

    def __init__(
        self,
        *,
        code: str,
        message: str,
        status_code: int,
        details: list[dict[str, Any]] | None = None,
    ) -> None:
        super().__init__(message)
        self.code = code
        self.message = message
        self.status_code = status_code
        self.details = details or []
