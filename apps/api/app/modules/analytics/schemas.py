"""
MODULE: /apps/api/app/modules/analytics/schemas.py

FUNCTION:
    Re-exports analytics request/response schemas for the modular domain boundary.

DEPENDENCIES:
    - /apps/api/app/modules/analytics/router.py
    - /apps/api/app/modules/analytics/__init__.py

IMPORTANCE:
    Keeping schema imports local to the module improves discoverability while preserving
    existing shared API contracts.
"""

from app.schemas.analytics import (
    FairnessPeriod,
    FairnessReportResponse,
    FairnessStaffRow,
    HoursDistributionResponse,
    HoursDistributionRow,
    OnDutyCurrentShift,
    OnDutyLocationRow,
    OnDutyResponse,
    OnDutyStaffRow,
    OvertimeDashboardResponse,
    OvertimeStaffRow,
)

__all__ = [
    "FairnessPeriod",
    "FairnessStaffRow",
    "FairnessReportResponse",
    "HoursDistributionRow",
    "HoursDistributionResponse",
    "OnDutyCurrentShift",
    "OnDutyStaffRow",
    "OnDutyLocationRow",
    "OnDutyResponse",
    "OvertimeStaffRow",
    "OvertimeDashboardResponse",
]

