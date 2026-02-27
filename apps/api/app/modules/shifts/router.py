"""
MODULE: /apps/api/app/modules/shifts/router.py

FUNCTION:
    Exposes thin HTTP route registration for shifts workflows implemented in service.

DEPENDENCIES:
    - /apps/api/app/api/router.py
    - /apps/api/app/modules/shifts/router.py
    - /apps/api/tests/integration/test_shifts_prune_unclaimed.py

IMPORTANCE:
    This module keeps transport concerns separate while all scheduling orchestration lives
    in the shifts service layer.
"""

from fastapi import APIRouter

from app.modules.shifts.service import (
    PublishWeekRequest,
    PublishWeekResponse,
    ShiftCreateRequest,
    ShiftListResponse,
    ShiftResponse,
    ShiftUpdateRequest,
    UnpublishShiftRequest,
    _prune_past_unclaimed_shifts,
    create_shift,
    delete_shift,
    get_shift,
    list_shifts,
    publish_week,
    unpublish_shift,
    update_shift,
)


router = APIRouter()
router.add_api_route("", list_shifts, methods=["GET"], response_model=ShiftListResponse)
router.add_api_route("", create_shift, methods=["POST"], response_model=ShiftResponse)
router.add_api_route("/{shift_id}", get_shift, methods=["GET"], response_model=ShiftResponse)
router.add_api_route("/{shift_id}", update_shift, methods=["PUT"], response_model=ShiftResponse)
router.add_api_route("/{shift_id}", delete_shift, methods=["DELETE"])
router.add_api_route("/publish", publish_week, methods=["POST"], response_model=PublishWeekResponse)
router.add_api_route(
    "/locations/{location_id}/shifts/{shift_id}/unpublish",
    unpublish_shift,
    methods=["POST"],
    response_model=ShiftResponse,
)

__all__ = [
    "router",
    "ShiftCreateRequest",
    "ShiftUpdateRequest",
    "ShiftResponse",
    "ShiftListResponse",
    "PublishWeekRequest",
    "PublishWeekResponse",
    "UnpublishShiftRequest",
    "list_shifts",
    "create_shift",
    "get_shift",
    "update_shift",
    "delete_shift",
    "publish_week",
    "unpublish_shift",
    "_prune_past_unclaimed_shifts",
]
