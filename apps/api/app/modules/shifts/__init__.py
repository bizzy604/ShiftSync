"""
MODULE: /apps/api/app/modules/shifts/__init__.py

FUNCTION:
    Defines the public API boundary and exported contracts for the shifts domain.

DEPENDENCIES:
    - /apps/api/app/api/router.py
    - /apps/api/app/modules/shifts/router.py

IMPORTANCE:
    Exporting a stable surface here prevents external callers from depending on private
    module internals.
"""

from app.modules.shifts.router import (
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
    router,
    unpublish_shift,
    update_shift,
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
