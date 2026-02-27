"""
MODULE: /apps/api/app/modules/analytics/router.py

FUNCTION:
    Exposes analytics HTTP endpoints through a thin modular route layer.

DEPENDENCIES:
    - /apps/api/app/api/router.py
    - /apps/api/app/modules/analytics/router.py

IMPORTANCE:
    This route layer preserves existing analytics API contracts while delegating domain
    calculations to services and repositories.
"""

from datetime import date

from fastapi import APIRouter, Depends, HTTPException, Query, status

from app.api.deps import CurrentUser, require_roles
from app.modules.analytics.exceptions import AnalyticsLocationNotFoundError, AnalyticsValidationError
from app.modules.analytics.service import (
    fairness_report as build_fairness_report,
    hours_distribution as build_hours_distribution,
    on_duty as build_on_duty,
    overtime_dashboard as build_overtime_dashboard,
)
from app.schemas.analytics import (
    FairnessReportResponse,
    HoursDistributionResponse,
    OnDutyResponse,
    OvertimeDashboardResponse,
)


router = APIRouter()


def _translate_analytics_error(exc: Exception) -> HTTPException:
    """Convert analytics domain exceptions into HTTP exceptions."""

    if isinstance(exc, AnalyticsLocationNotFoundError):
        return HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Location not found.")
    if isinstance(exc, AnalyticsValidationError):
        return HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail=str(exc))
    raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="Unexpected analytics error.")


async def overtime_dashboard(
    location_id: str = Query(...),
    week_start: date = Query(...),
    current_user: CurrentUser = Depends(require_roles("admin", "manager")),
) -> OvertimeDashboardResponse:
    """Return projected overtime metrics for a location/week."""

    try:
        return await build_overtime_dashboard(
            location_id=location_id,
            week_start=week_start,
            current_user=current_user,
        )
    except (AnalyticsLocationNotFoundError, AnalyticsValidationError) as exc:
        raise _translate_analytics_error(exc) from exc


async def fairness_report(
    location_id: str = Query(...),
    start_date: date = Query(...),
    end_date: date = Query(...),
    current_user: CurrentUser = Depends(require_roles("admin", "manager")),
) -> FairnessReportResponse:
    """Return fairness distribution metrics for a location/date range."""

    try:
        return await build_fairness_report(
            location_id=location_id,
            start_date=start_date,
            end_date=end_date,
            current_user=current_user,
        )
    except (AnalyticsLocationNotFoundError, AnalyticsValidationError) as exc:
        raise _translate_analytics_error(exc) from exc


async def hours_distribution(
    location_id: str = Query(...),
    start_date: date = Query(...),
    end_date: date = Query(...),
    current_user: CurrentUser = Depends(require_roles("admin", "manager")),
) -> HoursDistributionResponse:
    """Return assigned-hours distribution metrics for a location/date range."""

    try:
        return await build_hours_distribution(
            location_id=location_id,
            start_date=start_date,
            end_date=end_date,
            current_user=current_user,
        )
    except (AnalyticsLocationNotFoundError, AnalyticsValidationError) as exc:
        raise _translate_analytics_error(exc) from exc


async def on_duty(
    location_id: str | None = Query(default=None),
    current_user: CurrentUser = Depends(require_roles("admin", "manager")),
) -> OnDutyResponse:
    """Return currently on-duty staff grouped by location."""

    try:
        return await build_on_duty(location_id=location_id, current_user=current_user)
    except (AnalyticsLocationNotFoundError, AnalyticsValidationError) as exc:
        raise _translate_analytics_error(exc) from exc


router.add_api_route("/overtime-dashboard", overtime_dashboard, methods=["GET"], response_model=OvertimeDashboardResponse)
router.add_api_route("/fairness-report", fairness_report, methods=["GET"], response_model=FairnessReportResponse)
router.add_api_route("/hours-distribution", hours_distribution, methods=["GET"], response_model=HoursDistributionResponse)
router.add_api_route("/on-duty", on_duty, methods=["GET"], response_model=OnDutyResponse)
