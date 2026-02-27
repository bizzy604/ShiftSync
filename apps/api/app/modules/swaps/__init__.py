"""
MODULE: /apps/api/app/modules/swaps/__init__.py

FUNCTION:
    Defines the public API boundary and exported contracts for the swaps domain.

DEPENDENCIES:
    - /apps/api/app/api/router.py
    - /apps/api/app/modules/swaps/router.py
    - /apps/api/app/services/drop_expiry_worker.py

IMPORTANCE:
    This barrel file is the only supported import surface for swaps logic, protecting
    consumers from internal refactors while preserving backwards compatibility.
"""

from app.modules.swaps.router import (
    AvailableDropListResponse,
    DropCreateRequest,
    DropPickupRequest,
    PENDING,
    SWAP_RESPONSE_INCLUDE,
    SwapActionRequest,
    SwapCreateRequest,
    SwapRequestListResponse,
    SwapRequestResponse,
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
    router,
    shift_snapshot,
    to_resp,
    user_snapshot,
)
from app.modules.swaps.service import expire_due_drop_requests_for_worker

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
    "expire_due_drop_requests_for_worker",
]
