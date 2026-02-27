"""
MODULE: /apps/api/app/schemas/user.py

FUNCTION:
    Defines Pydantic API contract models for `user` requests and responses.

DEPENDENCIES:
    - /apps/api/app/api/routes/users.py
    - /apps/api/tests/integration/test_users_availability_exceptions.py

IMPORTANCE:
    This module defines API contracts that protect type safety and compatibility between
    backend and frontend.
"""

from datetime import date, datetime
from decimal import Decimal
from typing import Literal

from pydantic import BaseModel, EmailStr, Field, model_validator


UserRole = Literal["admin", "manager", "staff"]
NotificationPref = Literal["in_app", "in_app_email"]


class UserCreateRequest(BaseModel):
    """UserCreateRequest request model."""
    name: str = Field(min_length=1, max_length=255)
    email: EmailStr
    password: str = Field(min_length=8, max_length=128)
    role: UserRole
    home_timezone: str = Field(default="America/New_York")
    desired_hours_per_week: int = Field(default=40, ge=0, le=120)
    hourly_rate: Decimal | None = Field(default=None, ge=0, max_digits=8, decimal_places=2)
    notification_pref: NotificationPref = "in_app"


class UserUpdateRequest(BaseModel):
    """UserUpdateRequest request model."""
    name: str | None = Field(default=None, min_length=1, max_length=255)
    home_timezone: str | None = None
    desired_hours_per_week: int | None = Field(default=None, ge=0, le=120)
    hourly_rate: Decimal | None = Field(default=None, ge=0, max_digits=8, decimal_places=2)
    notification_pref: NotificationPref | None = None
    is_active: bool | None = None


class UserResponse(BaseModel):
    """UserResponse response model."""
    id: str
    name: str
    email: EmailStr
    role: UserRole
    home_timezone: str
    desired_hours_per_week: int
    hourly_rate: Decimal | None
    notification_pref: NotificationPref
    is_active: bool
    created_at: datetime
    updated_at: datetime


class UserListResponse(BaseModel):
    """UserListResponse response model."""
    users: list[UserResponse]
    total: int
    page: int
    limit: int


class SkillAttachRequest(BaseModel):
    """SkillAttachRequest request model."""
    skill_id: str


class UserSkillResponse(BaseModel):
    """UserSkillResponse response model."""
    skill_id: str
    skill_name: str


class CertificationAttachRequest(BaseModel):
    """CertificationAttachRequest request model."""
    location_id: str


class UserCertificationResponse(BaseModel):
    """UserCertificationResponse response model."""
    location_id: str
    location_name: str
    certified_at: datetime
    revoked_at: datetime | None


class RecurringAvailabilityIn(BaseModel):
    """RecurringAvailabilityIn domain type."""
    day_of_week: int = Field(ge=0, le=6)
    start_clock_time: str
    end_clock_time: str


class ExceptionAvailabilityIn(BaseModel):
    """ExceptionAvailabilityIn domain type."""
    date: date
    is_available: bool = True
    start_clock_time: str | None = None
    end_clock_time: str | None = None

    @model_validator(mode="after")
    def validate_time_window(self) -> "ExceptionAvailabilityIn":
        """Validate that available exception entries include a full time window."""
        if self.is_available and (not self.start_clock_time or not self.end_clock_time):
            raise ValueError("Available exception entries require start_clock_time and end_clock_time.")
        return self


class AvailabilityReplaceRequest(BaseModel):
    """AvailabilityReplaceRequest request model."""
    recurring: list[RecurringAvailabilityIn] = Field(default_factory=list)
    exceptions: list[ExceptionAvailabilityIn] = Field(default_factory=list)


class AvailabilityEntryResponse(BaseModel):
    """AvailabilityEntryResponse response model."""
    id: str
    avail_type: Literal["recurring", "exception"]
    day_of_week: int | None
    specific_date: date | None
    start_clock: str | None
    end_clock: str | None
    is_available: bool


class AvailabilityResponse(BaseModel):
    """AvailabilityResponse response model."""
    user_id: str
    recurring: list[AvailabilityEntryResponse]
    exceptions: list[AvailabilityEntryResponse]
