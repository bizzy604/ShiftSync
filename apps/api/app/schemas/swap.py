from datetime import datetime
from typing import Literal

from pydantic import BaseModel, Field


SwapType = Literal["swap", "drop"]
SwapStatus = Literal["OPEN", "PENDING_ACCEPTEE", "PENDING_MANAGER", "APPROVED", "REJECTED", "CANCELLED", "EXPIRED"]


class SwapCreateRequest(BaseModel):
    my_assignment_id: str
    target_user_id: str
    target_assignment_id: str | None = None


class SwapActionRequest(BaseModel):
    note: str | None = None


class DropCreateRequest(BaseModel):
    assignment_id: str


class DropPickupRequest(BaseModel):
    note: str | None = None


class SwapRequestResponse(BaseModel):
    request_id: str = Field(alias="id") # ID of the swap request
    type: SwapType
    status: SwapStatus
    requester_assignment_id: str
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
    requests: list[SwapRequestResponse]


class AvailableDropShift(BaseModel):
    id: str
    date: str
    start_local: str
    end_local: str
    location: dict
    required_skill: str


class AvailableDropRequest(BaseModel):
    drop_request_id: str
    shift: AvailableDropShift
    original_staff: dict
    expires_at: datetime | None


class AvailableDropListResponse(BaseModel):
    available: list[AvailableDropRequest]


class PendingLimitError(BaseModel):
    error: dict = Field(
        default_factory=lambda: {
            "code": "MAX_PENDING_REQUESTS",
            "message": "You already have 3 pending swap/drop requests. Resolve existing requests before creating new ones.",
        }
    )
