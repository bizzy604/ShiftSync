"""
MODULE: /apps/api/app/schemas/shift.py

FUNCTION:
    Defines Pydantic API contract models for `shift` requests and responses.

DEPENDENCIES:
    - /apps/api/app/api/routes/shifts.py
    - /apps/api/app/api/routes/skills.py

IMPORTANCE:
    This module defines API contracts that protect type safety and compatibility between
    backend and frontend.
"""

from __future__ import annotations

from datetime import date, datetime
from typing import Annotated
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field


ShiftStatus = Literal["draft", "published", "cancelled"]


class ShiftCreateRequest(BaseModel):
    """ShiftCreateRequest request model."""
    model_config = ConfigDict(populate_by_name=True)

    shift_date: Annotated[date, Field(alias="date")]
    start_time: str = Field(pattern=r"^([01]\d|2[0-3]):([0-5]\d)$")
    end_time: str = Field(pattern=r"^([01]\d|2[0-3]):([0-5]\d)$")
    required_skill_id: str
    headcount_needed: int = Field(default=1, ge=1, le=50)


class ShiftUpdateRequest(BaseModel):
    """ShiftUpdateRequest request model."""
    model_config = ConfigDict(populate_by_name=True)

    shift_date: Annotated[date | None, Field(alias="date")] = None
    start_time: str | None = Field(default=None, pattern=r"^([01]\d|2[0-3]):([0-5]\d)$")
    end_time: str | None = Field(default=None, pattern=r"^([01]\d|2[0-3]):([0-5]\d)$")
    required_skill_id: str | None = None
    headcount_needed: int | None = Field(default=None, ge=1, le=50)
    override_reason: str | None = None


class PublishWeekRequest(BaseModel):
    """PublishWeekRequest request model."""
    week_start: date


class UnpublishShiftRequest(BaseModel):
    """UnpublishShiftRequest request model."""
    override_reason: str | None = None


class ShiftRequiredSkill(BaseModel):
    """ShiftRequiredSkill domain type."""
    id: str
    name: str


class ShiftResponse(BaseModel):
    """ShiftResponse response model."""
    id: str
    location_id: str
    date: date
    start_utc: datetime
    end_utc: datetime
    start_local: str
    end_local: str
    required_skill: ShiftRequiredSkill
    headcount_needed: int
    status: ShiftStatus
    week_start: date
    edit_cutoff_utc: datetime | None
    created_at: datetime


class ShiftListResponse(BaseModel):
    """ShiftListResponse response model."""
    shifts: list[ShiftResponse]


class PublishWeekResponse(BaseModel):
    """PublishWeekResponse response model."""
    published_shifts: int
    edit_cutoff_utc: datetime | None
    notified_staff_count: int = 0
