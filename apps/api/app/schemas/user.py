from datetime import date, datetime
from decimal import Decimal
from typing import Literal

from pydantic import BaseModel, EmailStr, Field, model_validator


UserRole = Literal["admin", "manager", "staff"]
NotificationPref = Literal["in_app", "in_app_email"]


class UserCreateRequest(BaseModel):
    name: str = Field(min_length=1, max_length=255)
    email: EmailStr
    password: str = Field(min_length=8, max_length=128)
    role: UserRole
    home_timezone: str = Field(default="America/New_York")
    desired_hours_per_week: int = Field(default=40, ge=0, le=120)
    hourly_rate: Decimal | None = Field(default=None, ge=0, max_digits=8, decimal_places=2)
    notification_pref: NotificationPref = "in_app"


class UserUpdateRequest(BaseModel):
    name: str | None = Field(default=None, min_length=1, max_length=255)
    home_timezone: str | None = None
    desired_hours_per_week: int | None = Field(default=None, ge=0, le=120)
    hourly_rate: Decimal | None = Field(default=None, ge=0, max_digits=8, decimal_places=2)
    notification_pref: NotificationPref | None = None
    is_active: bool | None = None


class UserResponse(BaseModel):
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
    users: list[UserResponse]
    total: int
    page: int
    limit: int


class SkillAttachRequest(BaseModel):
    skill_id: str


class UserSkillResponse(BaseModel):
    skill_id: str
    skill_name: str


class CertificationAttachRequest(BaseModel):
    location_id: str


class UserCertificationResponse(BaseModel):
    location_id: str
    location_name: str
    certified_at: datetime
    revoked_at: datetime | None


class RecurringAvailabilityIn(BaseModel):
    day_of_week: int = Field(ge=0, le=6)
    start_clock_time: str
    end_clock_time: str


class ExceptionAvailabilityIn(BaseModel):
    date: date
    is_available: bool = True
    start_clock_time: str | None = None
    end_clock_time: str | None = None

    @model_validator(mode="after")
    def validate_time_window(self) -> "ExceptionAvailabilityIn":
        if self.is_available and (not self.start_clock_time or not self.end_clock_time):
            raise ValueError("Available exception entries require start_clock_time and end_clock_time.")
        return self


class AvailabilityReplaceRequest(BaseModel):
    recurring: list[RecurringAvailabilityIn] = Field(default_factory=list)
    exceptions: list[ExceptionAvailabilityIn] = Field(default_factory=list)


class AvailabilityEntryResponse(BaseModel):
    id: str
    avail_type: Literal["recurring", "exception"]
    day_of_week: int | None
    specific_date: date | None
    start_clock: str | None
    end_clock: str | None
    is_available: bool


class AvailabilityResponse(BaseModel):
    user_id: str
    recurring: list[AvailabilityEntryResponse]
    exceptions: list[AvailabilityEntryResponse]
