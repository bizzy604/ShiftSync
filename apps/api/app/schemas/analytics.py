"""
MODULE: /apps/api/app/schemas/analytics.py

FUNCTION:
    Defines Pydantic API contract models for `analytics` requests and responses.

DEPENDENCIES:
    - /apps/api/app/api/routes/analytics.py

IMPORTANCE:
    This module defines API contracts that protect type safety and compatibility between
    backend and frontend.
"""

from datetime import date, datetime

from pydantic import BaseModel


class OvertimeStaffRow(BaseModel):
    """OvertimeStaffRow domain type."""
    user_id: str
    name: str
    projected_weekly_hours: float
    overtime_hours: float
    projected_overtime_cost: float
    offending_assignment_ids: list[str]


class OvertimeDashboardResponse(BaseModel):
    """OvertimeDashboardResponse response model."""
    week_start: date
    location_id: str
    total_projected_overtime_cost: float
    staff: list[OvertimeStaffRow]


class FairnessStaffRow(BaseModel):
    """FairnessStaffRow domain type."""
    user_id: str
    name: str
    total_hours: float
    desired_hours_per_week: int
    scheduling_variance_pct: float
    premium_shift_count: int
    premium_shift_pct: float


class FairnessPeriod(BaseModel):
    """FairnessPeriod domain type."""
    start_date: date
    end_date: date


class FairnessReportResponse(BaseModel):
    """FairnessReportResponse response model."""
    period: FairnessPeriod
    location_id: str
    fairness_score: float
    fairness_grade: str
    staff: list[FairnessStaffRow]


class HoursDistributionRow(BaseModel):
    """HoursDistributionRow domain type."""
    user_id: str
    name: str
    total_hours: float
    assigned_shift_count: int


class HoursDistributionResponse(BaseModel):
    """HoursDistributionResponse response model."""
    period: FairnessPeriod
    location_id: str
    total_hours: float
    staff: list[HoursDistributionRow]


class OnDutyCurrentShift(BaseModel):
    """OnDutyCurrentShift domain type."""
    id: str
    start_local: str
    end_local: str


class OnDutyStaffRow(BaseModel):
    """OnDutyStaffRow domain type."""
    user_id: str
    name: str
    skill: str


class OnDutyLocationRow(BaseModel):
    """OnDutyLocationRow domain type."""
    location_id: str
    location_name: str
    iana_timezone: str
    local_time: str
    current_shift: OnDutyCurrentShift | None
    on_duty_staff: list[OnDutyStaffRow]


class OnDutyResponse(BaseModel):
    """OnDutyResponse response model."""
    as_of: datetime
    locations: list[OnDutyLocationRow]
