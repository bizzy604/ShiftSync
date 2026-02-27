"""
MODULE: /apps/api/app/schemas/location.py

FUNCTION:
    Defines Pydantic API contract models for `location` requests and responses.

DEPENDENCIES:
    - /apps/api/app/api/routes/locations.py

IMPORTANCE:
    This module defines API contracts that protect type safety and compatibility between
    backend and frontend.
"""

from datetime import datetime

from pydantic import BaseModel, Field


class LocationCreateRequest(BaseModel):
    """LocationCreateRequest request model."""
    name: str = Field(min_length=1, max_length=255)
    address: str | None = None
    iana_timezone: str = Field(min_length=3, max_length=100)


class LocationUpdateRequest(BaseModel):
    """LocationUpdateRequest request model."""
    name: str | None = Field(default=None, min_length=1, max_length=255)
    address: str | None = None
    iana_timezone: str | None = Field(default=None, min_length=3, max_length=100)
    is_active: bool | None = None


class LocationResponse(BaseModel):
    """LocationResponse response model."""
    id: str
    name: str
    address: str | None
    iana_timezone: str
    is_active: bool
    created_at: datetime


class LocationListResponse(BaseModel):
    """LocationListResponse response model."""
    locations: list[LocationResponse]
