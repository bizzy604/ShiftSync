"""
MODULE: /apps/api/app/modules/swaps/router.py

FUNCTION:
    Registers swaps and drops HTTP endpoints while delegating orchestration to swaps service.

DEPENDENCIES:
    - /apps/api/app/api/router.py
    - /apps/api/app/modules/swaps/router.py
    - /apps/api/app/modules/swaps/__init__.py

IMPORTANCE:
    Keeping endpoint registration here preserves a thin transport layer and ensures the
    swaps state machine logic remains centralized in service functions.
"""

from fastapi import APIRouter

from app.modules.swaps.schemas import (
    AvailableDropListResponse,
    DropCreateRequest,
    DropPickupRequest,
    SwapActionRequest,
    SwapCreateRequest,
    SwapRequestListResponse,
    SwapRequestResponse,
)
from app.modules.swaps.service import (
    PENDING,
    SWAP_RESPONSE_INCLUDE,
    _load_swap_for_response,
    accept_swap,
    approve_drop,
    approve_swap_like,
    approve_transfer,
    available_drops,
    cancel_swap,
    create_drop,
    create_swap_request,
    decline_drop,
    decline_swap_like,
    emit_notifications,
    enforce_pending_limit,
    existing_assignments,
    get_swap_request,
    list_swap_requests,
    manager_notify,
    notify_qualified_staff,
    pickup_drop,
    reject_swap,
    shift_snapshot,
    to_resp,
    user_snapshot,
)


router = APIRouter()
router.add_api_route("", list_swap_requests, methods=["GET"], response_model=SwapRequestListResponse)
router.add_api_route("/{request_id}", get_swap_request, methods=["GET"], response_model=SwapRequestResponse)
router.add_api_route("", create_swap_request, methods=["POST"], response_model=SwapRequestResponse)
router.add_api_route("/{request_id}/accept", accept_swap, methods=["POST"], response_model=SwapRequestResponse)
router.add_api_route("/{request_id}/reject", reject_swap, methods=["POST"], response_model=SwapRequestResponse)
router.add_api_route("/{request_id}/cancel", cancel_swap, methods=["POST"], response_model=SwapRequestResponse)
router.add_api_route("/{request_id}/approve", approve_swap_like, methods=["POST"], response_model=SwapRequestResponse)
router.add_api_route("/{request_id}/decline", decline_swap_like, methods=["POST"], response_model=SwapRequestResponse)
router.add_api_route("/drops", create_drop, methods=["POST"], response_model=SwapRequestResponse)
router.add_api_route("/drops/available", available_drops, methods=["GET"], response_model=AvailableDropListResponse)
router.add_api_route("/drops/{request_id}/pickup", pickup_drop, methods=["POST"], response_model=SwapRequestResponse)
router.add_api_route("/drops/{request_id}/approve", approve_drop, methods=["POST"], response_model=SwapRequestResponse)
router.add_api_route("/drops/{request_id}/decline", decline_drop, methods=["POST"], response_model=SwapRequestResponse)
router.add_api_route("/drops/{request_id}/notify-qualified", notify_qualified_staff, methods=["POST"])

__all__ = [
    "router",
    "SwapCreateRequest",
    "SwapActionRequest",
    "DropCreateRequest",
    "DropPickupRequest",
    "SwapRequestResponse",
    "SwapRequestListResponse",
    "AvailableDropListResponse",
    "PENDING",
    "SWAP_RESPONSE_INCLUDE",
    "to_resp",
    "user_snapshot",
    "shift_snapshot",
    "existing_assignments",
    "enforce_pending_limit",
    "manager_notify",
    "emit_notifications",
    "approve_transfer",
    "_load_swap_for_response",
    "list_swap_requests",
    "get_swap_request",
    "create_swap_request",
    "accept_swap",
    "reject_swap",
    "cancel_swap",
    "approve_swap_like",
    "decline_swap_like",
    "create_drop",
    "available_drops",
    "pickup_drop",
    "approve_drop",
    "decline_drop",
    "notify_qualified_staff",
]
