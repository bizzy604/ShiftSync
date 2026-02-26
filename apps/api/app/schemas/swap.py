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
    id: str
    type: SwapType
    status: SwapStatus
    requester_assignment_id: str
    target_user_id: str | None
    candidate_assignment_id: str | None
    pickup_user_id: str | None
    initiated_by: str
    expires_at: datetime | None
    created_at: datetime
    resolved_at: datetime | None
    resolution_note: str | None


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
