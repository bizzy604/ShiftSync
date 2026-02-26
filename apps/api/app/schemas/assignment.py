from datetime import datetime
from typing import Literal

from pydantic import BaseModel


AssignmentStatus = Literal["assigned", "swap_pending", "dropped", "removed"]
ConstraintSeverity = Literal["HARD_BLOCK", "WARNING", "OVERRIDE_REQUIRED"]


class AssignmentCreateRequest(BaseModel):
    user_id: str
    override_reason: str | None = None


class AssignmentShiftInfo(BaseModel):
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
    id: str
    status: AssignmentStatus
    shift: AssignmentShiftInfo


class MyAssignmentListResponse(BaseModel):
    assignments: list[MyAssignmentResponse]


class AssignmentListResponse(BaseModel):
    assignments: list[AssignmentResponse]


class ConstraintDetail(BaseModel):
    rule: str
    description: str
    severity: ConstraintSeverity


class ConstraintSuggestion(BaseModel):
    user_id: str
    name: str
    reason: str


class AssignmentPreviewResponse(BaseModel):
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
