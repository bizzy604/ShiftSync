"""
MODULE: /apps/api/app/modules/swaps/schemas.py

FUNCTION:
    Exposes swaps request/response schema contracts through the swaps domain boundary.

DEPENDENCIES:
    - /apps/api/app/modules/swaps/router.py
    - /apps/api/app/modules/swaps/service.py
    - /apps/api/app/modules/swaps/__init__.py

IMPORTANCE:
    Re-exporting schema contracts here keeps swaps consumers insulated from legacy
    schema package paths while preserving existing API payload shapes.
"""

from app.schemas.swap import (
    AvailableDropListResponse,
    AvailableDropRequest,
    AvailableDropShift,
    DropCreateRequest,
    DropPickupRequest,
    SwapActionRequest,
    SwapCreateRequest,
    SwapRequestListResponse,
    SwapRequestResponse,
)

__all__ = [
    "SwapCreateRequest",
    "SwapActionRequest",
    "DropCreateRequest",
    "DropPickupRequest",
    "SwapRequestResponse",
    "SwapRequestListResponse",
    "AvailableDropShift",
    "AvailableDropRequest",
    "AvailableDropListResponse",
]
