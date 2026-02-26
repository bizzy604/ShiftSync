from datetime import datetime

from pydantic import BaseModel, Field


class LocationCreateRequest(BaseModel):
    name: str = Field(min_length=1, max_length=255)
    address: str | None = None
    iana_timezone: str = Field(min_length=3, max_length=100)


class LocationUpdateRequest(BaseModel):
    name: str | None = Field(default=None, min_length=1, max_length=255)
    address: str | None = None
    iana_timezone: str | None = Field(default=None, min_length=3, max_length=100)
    is_active: bool | None = None


class LocationResponse(BaseModel):
    id: str
    name: str
    address: str | None
    iana_timezone: str
    is_active: bool
    created_at: datetime


class LocationListResponse(BaseModel):
    locations: list[LocationResponse]
