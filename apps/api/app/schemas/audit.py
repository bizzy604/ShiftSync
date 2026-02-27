"""
MODULE: /apps/api/app/schemas/audit.py

FUNCTION:
    Defines Pydantic API contract models for `audit` requests and responses.

DEPENDENCIES:
    - /apps/api/app/modules/audit/router.py

IMPORTANCE:
    This module defines API contracts that protect type safety and compatibility between
    backend and frontend.
"""

from datetime import datetime
from typing import Any

from pydantic import BaseModel


class AuditLogResponse(BaseModel):
    """AuditLogResponse response model."""
    id: str
    actor_id: str
    actor_name: str
    action_type: str
    entity_type: str
    entity_id: str
    before_state: dict[str, Any] | None
    after_state: dict[str, Any] | None
    reason: str | None
    location_id: str | None
    created_at: datetime


class AuditLogListResponse(BaseModel):
    """AuditLogListResponse response model."""
    logs: list[AuditLogResponse]
    pagination: dict[str, int]
