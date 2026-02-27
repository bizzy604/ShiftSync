"""
MODULE: /apps/api/app/schemas/swap.py

FUNCTION:
    Defines Pydantic API contract models for `swap` requests and responses.

DEPENDENCIES:
    - /apps/api/app/modules/swaps/router.py

IMPORTANCE:
    This module defines API contracts that protect type safety and compatibility between
    backend and frontend.
"""

from datetime import datetime
from typing import Literal

from pydantic import BaseModel, Field


SwapType = Literal["swap", "drop"]
SwapStatus = Literal["OPEN", "PENDING_ACCEPTEE", "PENDING_MANAGER", "APPROVED", "REJECTED", "CANCELLED", "EXPIRED"]


class SwapCreateRequest(BaseModel):
    """SwapCreateRequest request model."""
    my_assignment_id: str
    target_user_id: str
    target_assignment_id: str | None = None


class SwapActionRequest(BaseModel):
    """SwapActionRequest request model."""
    note: str | None = None


class DropCreateRequest(BaseModel):
    """DropCreateRequest request model."""
    assignment_id: str


class DropPickupRequest(BaseModel):
    """DropPickupRequest request model."""
    note: str | None = None


class SwapRequestResponse(BaseModel):
    """SwapRequestResponse response model."""
    request_id: str = Field(alias="id") # ID of the swap request
    type: SwapType
    status: SwapStatus
    requester_assignment_id: str
    shift_id: str | None = None
    requester_name: str | None = None
    target_user_id: str | None = None
    target_name: str | None = None
    candidate_assignment_id: str | None = None
    pickup_user_id: str | None = None
    pickup_name: str | None = None
    initiated_by: str
    expires_at: datetime | None = None
    created_at: datetime
    resolved_at: datetime | None = None
    resolution_note: str | None = None
    
    # Nested info for UI convenience
    shift_date: str | None = None
    shift_time: str | None = None
    shift_label: str | None = None


class SwapRequestListResponse(BaseModel):
    """SwapRequestListResponse response model."""
    requests: list[SwapRequestResponse]


class AvailableDropShift(BaseModel):
    """AvailableDropShift domain type."""
    id: str
    date: str
    start_local: str
    end_local: str
    location: dict
    required_skill: str


class AvailableDropRequest(BaseModel):
    """AvailableDropRequest request model."""
    drop_request_id: str
    shift: AvailableDropShift
    original_staff: dict
    expires_at: datetime | None


class AvailableDropListResponse(BaseModel):
    """AvailableDropListResponse response model."""
    available: list[AvailableDropRequest]


class PendingLimitError(BaseModel):
    """PendingLimitError error model."""
    error: dict = Field(
        default_factory=lambda: {
            "code": "MAX_PENDING_REQUESTS",
            "message": "You already have 3 pending swap/drop requests. Resolve existing requests before creating new ones.",
        }
    )
