"""
MODULE: /apps/api/app/schemas/auth.py

FUNCTION:
    Defines Pydantic API contract models for `auth` requests and responses.

DEPENDENCIES:
    - /apps/api/app/modules/auth/router.py

IMPORTANCE:
    This module defines API contracts that protect type safety and compatibility between
    backend and frontend.
"""

from pydantic import BaseModel, EmailStr


class LoginRequest(BaseModel):
    """LoginRequest request model."""
    email: EmailStr
    password: str


class AuthenticatedUser(BaseModel):
    """AuthenticatedUser domain type."""
    id: str
    name: str
    email: EmailStr
    role: str
    location_ids: list[str]


class LoginResponse(BaseModel):
    """LoginResponse response model."""
    user: AuthenticatedUser


class RefreshResponse(BaseModel):
    """RefreshResponse response model."""
    refreshed: bool
