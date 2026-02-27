"""
MODULE: /apps/api/app/modules/realtime/repository.py

FUNCTION:
    Provides realtime-domain persistence helpers used during websocket authentication.

DEPENDENCIES:
    - /apps/api/app/modules/realtime/service.py

IMPORTANCE:
    Isolating data access here keeps websocket service orchestration focused on protocol
    behavior and allows easy substitution/mocking of persistence operations in tests.
"""

from __future__ import annotations

from typing import Any

from app.core.database import prisma


async def list_manager_location_ids(*, user_id: str, db: Any | None = None) -> list[str]:
    """Return location IDs managed by the provided manager user.

    Args:
        user_id: Manager user identifier.
        db: Optional database client override for tests/transactions.

    Returns:
        Sorted unique location IDs assigned to the manager.
    """
    client = db or prisma
    assignments = await client.managerlocationassignment.find_many(where={"manager_id": user_id})
    return sorted({item.location_id for item in assignments})
