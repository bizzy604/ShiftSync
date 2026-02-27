"""
MODULE: /apps/api/app/schemas/assignment.py

FUNCTION:
    Defines Pydantic API contract models for `assignment` requests and responses.

DEPENDENCIES:
    - /apps/api/app/api/routes/assignments.py

IMPORTANCE:
    This module defines API contracts that protect type safety and compatibility between
    backend and frontend.
"""

from datetime import datetime
from typing import Literal

from pydantic import BaseModel


AssignmentStatus = Literal["assigned", "swap_pending", "dropped", "removed"]
ConstraintSeverity = Literal["HARD_BLOCK", "WARNING", "OVERRIDE_REQUIRED"]


class AssignmentCreateRequest(BaseModel):
    """AssignmentCreateRequest request model."""
    user_id: str
    override_reason: str | None = None


class AssignmentShiftInfo(BaseModel):
    """AssignmentShiftInfo domain type."""
    id: str
    location_id: str
    location_name: str
    shift_date: datetime
    start_utc: datetime
    end_utc: datetime
    start_local: str
    end_local: str
    required_skill: str


class AssignmentResponse(BaseModel):
    """AssignmentResponse response model."""
    id: str
    shift_id: str
    user_id: str
    user_name: str
    status: AssignmentStatus
    version: int
    assigned_by: str
    assigned_at: datetime
    shift: AssignmentShiftInfo | None = None


class MyAssignmentResponse(BaseModel):
    """MyAssignmentResponse response model."""
    id: str
    status: AssignmentStatus
    shift: AssignmentShiftInfo


class MyAssignmentListResponse(BaseModel):
    """MyAssignmentListResponse response model."""
    assignments: list[MyAssignmentResponse]


class AssignmentListResponse(BaseModel):
    """AssignmentListResponse response model."""
    assignments: list[AssignmentResponse]


class ConstraintDetail(BaseModel):
    """ConstraintDetail domain type."""
    rule: str
    description: str
    severity: ConstraintSeverity


class ConstraintSuggestion(BaseModel):
    """ConstraintSuggestion domain type."""
    user_id: str
    name: str
    reason: str


class AssignmentPreviewResponse(BaseModel):
    """AssignmentPreviewResponse response model."""
    user_id: str
    user_name: str
    valid: bool
    violations: list[ConstraintDetail]
    warnings: list[ConstraintDetail]
    requires_override: bool
    projected_weekly_hours: float
    projected_daily_hours: float
    projected_overtime_cost: float
    suggestions: list[ConstraintSuggestion]
