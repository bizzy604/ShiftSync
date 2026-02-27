"""
MODULE: /apps/api/app/modules/analytics/service.py

FUNCTION:
    Implements analytics report workflows and domain calculations using repository reads.

DEPENDENCIES:
    - /apps/api/app/modules/analytics/router.py
    - /apps/api/app/modules/analytics/__init__.py

IMPORTANCE:
    Centralized analytics logic keeps route handlers thin, preserves consistent reporting
    behavior, and enables isolated service testing.
"""

from __future__ import annotations

from datetime import date, datetime, time, timedelta, timezone
from statistics import pstdev
from zoneinfo import ZoneInfo

from app.api.deps import CurrentUser, ensure_manager_location_access
from app.modules.analytics.exceptions import AnalyticsLocationNotFoundError, AnalyticsValidationError
from app.modules.analytics.repository import AnalyticsRepository, get_analytics_repository
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
from app.services.timezone_utils import format_local_iso


def _date_as_datetime(value: date) -> datetime:
    """Convert a date into a midnight datetime for query filters."""

    return datetime.combine(value, time.min)


def _shift_duration_hours(shift: object) -> float:
    """Return shift duration in hours."""

    return (shift.end_utc - shift.start_utc).total_seconds() / 3600.0


def _overlap_hours(start_a: datetime, end_a: datetime, start_b: datetime, end_b: datetime) -> float:
    """Return overlap duration in hours for two datetime ranges."""

    overlap_start = max(start_a, start_b)
    overlap_end = min(end_a, end_b)
    if overlap_start >= overlap_end:
        return 0.0
    return (overlap_end - overlap_start).total_seconds() / 3600.0


def _is_premium_shift(shift: object, timezone_name: str) -> bool:
    """Return true when a shift qualifies as premium by local weekday/time."""

    local_start = shift.start_utc.astimezone(ZoneInfo(timezone_name))
    # Friday=4, Saturday=5 in Python's weekday() semantics.
    return local_start.weekday() in {4, 5} and local_start.hour >= 17


def _grade_from_score(score: float) -> str:
    """Map fairness score to a human-readable grade."""

    if score <= 1.0:
        return "GOOD"
    if score <= 2.0:
        return "FAIR"
    return "POOR"


async def _location_or_404(*, location_id: str, repository: AnalyticsRepository) -> object:
    """Return a location by id or raise a typed not-found exception."""

    location = await repository.find_location(location_id)
    if location is None:
        raise AnalyticsLocationNotFoundError(location_id)
    return location


# PATTERN: Transaction Script
# Each workflow function orchestrates repository reads and in-memory analytics calculations.
async def overtime_dashboard(
    *,
    location_id: str,
    week_start: date,
    current_user: CurrentUser,
    repository: AnalyticsRepository | None = None,
) -> OvertimeDashboardResponse:
    """Build overtime exposure metrics for one location/week."""

    repo = repository or get_analytics_repository()
    location = await _location_or_404(location_id=location_id, repository=repo)
    if current_user.role == "manager":
        ensure_manager_location_access(current_user, location_id)

    shifts = await repo.list_week_shifts(location_id=location_id, week_start=_date_as_datetime(week_start))
    if not shifts:
        return OvertimeDashboardResponse(
            week_start=week_start,
            location_id=location_id,
            total_projected_overtime_cost=0.0,
            staff=[],
        )

    shift_ids = [shift.id for shift in shifts]
    week_assignments = await repo.list_assigned_shift_assignments(shift_ids=shift_ids)
    if not week_assignments:
        return OvertimeDashboardResponse(
            week_start=week_start,
            location_id=location_id,
            total_projected_overtime_cost=0.0,
            staff=[],
        )

    user_ids = sorted({assignment.user_id for assignment in week_assignments})
    week_start_local = datetime.combine(week_start, time.min, tzinfo=ZoneInfo(location.iana_timezone))
    week_start_utc = week_start_local.astimezone(timezone.utc)
    week_end_utc = week_start_utc + timedelta(days=7)

    all_assignments = await repo.list_assigned_user_assignments(user_ids=user_ids)

    per_user_totals: dict[str, float] = {user_id: 0.0 for user_id in user_ids}
    per_user_rows: dict[str, list[tuple[str, str, datetime, float, bool, object]]] = {user_id: [] for user_id in user_ids}
    for item in all_assignments:
        if item.shift is None:
            continue
        hours = _overlap_hours(item.shift.start_utc, item.shift.end_utc, week_start_utc, week_end_utc)
        if hours <= 0:
            continue
        in_selected_location = item.shift.location_id == location_id and item.shift.week_start == _date_as_datetime(week_start)
        per_user_totals[item.user_id] = per_user_totals.get(item.user_id, 0.0) + hours
        per_user_rows.setdefault(item.user_id, []).append(
            (item.id, item.shift_id, item.shift.start_utc, hours, in_selected_location, item.user)
        )

    rows: list[OvertimeStaffRow] = []
    total_projected_cost = 0.0
    for user_id, total_hours in per_user_totals.items():
        user_rows = sorted(per_user_rows.get(user_id, []), key=lambda x: x[2])
        cumulative = 0.0
        offending_assignment_ids: list[str] = []
        name = "unknown"
        hourly_rate = 0.0
        for assignment_id, _, _, hours, in_location, user in user_rows:
            if user is not None:
                name = user.name
                hourly_rate = float(user.hourly_rate or 0)
            cumulative += hours
            if in_location and cumulative > 40:
                offending_assignment_ids.append(assignment_id)

        overtime_hours = max(0.0, total_hours - 40.0)
        projected_cost = overtime_hours * hourly_rate * 1.5
        total_projected_cost += projected_cost

        rows.append(
            OvertimeStaffRow(
                user_id=user_id,
                name=name,
                projected_weekly_hours=round(total_hours, 2),
                overtime_hours=round(overtime_hours, 2),
                projected_overtime_cost=round(projected_cost, 2),
                offending_assignment_ids=offending_assignment_ids,
            )
        )

    rows.sort(key=lambda row: row.projected_weekly_hours, reverse=True)
    return OvertimeDashboardResponse(
        week_start=week_start,
        location_id=location_id,
        total_projected_overtime_cost=round(total_projected_cost, 2),
        staff=rows,
    )


async def fairness_report(
    *,
    location_id: str,
    start_date: date,
    end_date: date,
    current_user: CurrentUser,
    repository: AnalyticsRepository | None = None,
) -> FairnessReportResponse:
    """Build scheduling fairness report for one location/date range."""

    if end_date < start_date:
        raise AnalyticsValidationError("end_date must be >= start_date.")

    repo = repository or get_analytics_repository()
    location = await _location_or_404(location_id=location_id, repository=repo)
    if current_user.role == "manager":
        ensure_manager_location_access(current_user, location_id)

    certs = await repo.list_active_staff_certifications(location_id=location_id)
    staff_map: dict[str, object] = {}
    for cert in certs:
        if cert.user and cert.user.role == "staff" and cert.user.is_active:
            staff_map[cert.user_id] = cert.user

    shifts = await repo.list_shifts_in_date_range(
        location_id=location_id,
        start_at=_date_as_datetime(start_date),
        end_at=_date_as_datetime(end_date),
    )
    shift_ids = [shift.id for shift in shifts]
    assignments = []
    if shift_ids:
        assignments = await repo.list_assigned_shift_assignments(shift_ids=shift_ids)
        for assignment in assignments:
            if assignment.user and assignment.user.role == "staff" and assignment.user.is_active:
                staff_map.setdefault(assignment.user_id, assignment.user)

    totals: dict[str, float] = {user_id: 0.0 for user_id in staff_map}
    assignment_counts: dict[str, int] = {user_id: 0 for user_id in staff_map}
    premium_counts: dict[str, int] = {user_id: 0 for user_id in staff_map}

    for assignment in assignments:
        if assignment.shift is None:
            continue
        if assignment.user_id not in staff_map:
            continue
        totals[assignment.user_id] = totals.get(assignment.user_id, 0.0) + _shift_duration_hours(assignment.shift)
        assignment_counts[assignment.user_id] = assignment_counts.get(assignment.user_id, 0) + 1
        if _is_premium_shift(assignment.shift, location.iana_timezone):
            premium_counts[assignment.user_id] = premium_counts.get(assignment.user_id, 0) + 1

    period_days = (end_date - start_date).days + 1
    period_weeks = period_days / 7.0
    staff_rows: list[FairnessStaffRow] = []
    for user_id, user in staff_map.items():
        desired_hours = int(user.desired_hours_per_week or 0)
        expected_hours = desired_hours * period_weeks
        total_hours = totals.get(user_id, 0.0)
        variance_pct = 0.0
        if expected_hours > 0:
            variance_pct = ((total_hours - expected_hours) / expected_hours) * 100.0

        assigned_shift_count = assignment_counts.get(user_id, 0)
        premium_count = premium_counts.get(user_id, 0)
        premium_pct = (premium_count / assigned_shift_count * 100.0) if assigned_shift_count else 0.0

        staff_rows.append(
            FairnessStaffRow(
                user_id=user_id,
                name=user.name,
                total_hours=round(total_hours, 2),
                desired_hours_per_week=desired_hours,
                scheduling_variance_pct=round(variance_pct, 2),
                premium_shift_count=premium_count,
                premium_shift_pct=round(premium_pct, 2),
            )
        )

    # Prioritize largest variance (under/over desired hours) first for managerial review.
    staff_rows.sort(key=lambda row: (-abs(row.scheduling_variance_pct), row.name.lower()))
    premium_values = [float(row.premium_shift_count) for row in staff_rows]
    fairness_score = round(float(pstdev(premium_values)) if len(premium_values) > 1 else 0.0, 2)

    return FairnessReportResponse(
        period=FairnessPeriod(start_date=start_date, end_date=end_date),
        location_id=location_id,
        fairness_score=fairness_score,
        fairness_grade=_grade_from_score(fairness_score),
        staff=staff_rows,
    )


async def hours_distribution(
    *,
    location_id: str,
    start_date: date,
    end_date: date,
    current_user: CurrentUser,
    repository: AnalyticsRepository | None = None,
) -> HoursDistributionResponse:
    """Build total-hours distribution report for one location/date range."""

    if end_date < start_date:
        raise AnalyticsValidationError("end_date must be >= start_date.")

    repo = repository or get_analytics_repository()
    await _location_or_404(location_id=location_id, repository=repo)
    if current_user.role == "manager":
        ensure_manager_location_access(current_user, location_id)

    shifts = await repo.list_shifts_in_date_range(
        location_id=location_id,
        start_at=_date_as_datetime(start_date),
        end_at=_date_as_datetime(end_date),
    )
    shift_ids = [shift.id for shift in shifts]
    if not shift_ids:
        return HoursDistributionResponse(
            period=FairnessPeriod(start_date=start_date, end_date=end_date),
            location_id=location_id,
            total_hours=0.0,
            staff=[],
        )

    assignments = await repo.list_assigned_shift_assignments(shift_ids=shift_ids)
    totals: dict[str, float] = {}
    counts: dict[str, int] = {}
    names: dict[str, str] = {}
    for assignment in assignments:
        if assignment.shift is None or assignment.user is None:
            continue
        totals[assignment.user_id] = totals.get(assignment.user_id, 0.0) + _shift_duration_hours(assignment.shift)
        counts[assignment.user_id] = counts.get(assignment.user_id, 0) + 1
        names[assignment.user_id] = assignment.user.name

    staff = [
        HoursDistributionRow(
            user_id=user_id,
            name=names.get(user_id, "unknown"),
            total_hours=round(hours, 2),
            assigned_shift_count=counts.get(user_id, 0),
        )
        for user_id, hours in totals.items()
    ]
    staff.sort(key=lambda row: row.total_hours, reverse=True)

    return HoursDistributionResponse(
        period=FairnessPeriod(start_date=start_date, end_date=end_date),
        location_id=location_id,
        total_hours=round(sum(totals.values()), 2),
        staff=staff,
    )


async def on_duty(
    *,
    location_id: str | None,
    current_user: CurrentUser,
    repository: AnalyticsRepository | None = None,
) -> OnDutyResponse:
    """Return currently on-duty staff grouped by location."""

    now = datetime.now(tz=timezone.utc)
    repo = repository or get_analytics_repository()

    scoped_location_ids: list[str]
    if current_user.role == "admin":
        if location_id:
            scoped_location_ids = [location_id]
        else:
            locations = await repo.list_active_locations()
            scoped_location_ids = [item.id for item in locations]
    else:
        if location_id:
            ensure_manager_location_access(current_user, location_id)
            scoped_location_ids = [location_id]
        else:
            scoped_location_ids = current_user.location_ids

    if not scoped_location_ids:
        return OnDutyResponse(as_of=now, locations=[])

    active_shifts = await repo.list_active_shifts_at(location_ids=scoped_location_ids, now=now)
    shift_ids = [item.id for item in active_shifts]
    active_assignments = []
    if shift_ids:
        active_assignments = await repo.list_assigned_shift_assignments(shift_ids=shift_ids)

    shifts_by_location: dict[str, list[object]] = {}
    for shift in active_shifts:
        shifts_by_location.setdefault(shift.location_id, []).append(shift)

    assignments_by_location: dict[str, list[object]] = {}
    for assignment in active_assignments:
        if assignment.shift is None:
            continue
        assignments_by_location.setdefault(assignment.shift.location_id, []).append(assignment)

    location_rows: list[OnDutyLocationRow] = []
    for loc_id in scoped_location_ids:
        shifts_here = sorted(shifts_by_location.get(loc_id, []), key=lambda item: item.start_utc)
        location_obj = shifts_here[0].location if shifts_here else await repo.find_location(loc_id)
        if location_obj is None:
            continue

        shift_payload = None
        if shifts_here:
            lead = shifts_here[0]
            shift_payload = OnDutyCurrentShift(
                id=lead.id,
                start_local=format_local_iso(lead.start_utc, location_obj.iana_timezone),
                end_local=format_local_iso(lead.end_utc, location_obj.iana_timezone),
            )

        seen_users: set[str] = set()
        staff_rows: list[OnDutyStaffRow] = []
        for assignment in assignments_by_location.get(loc_id, []):
            if assignment.user is None or assignment.shift is None:
                continue
            if assignment.user_id in seen_users:
                continue
            seen_users.add(assignment.user_id)
            skill_name = assignment.shift.required_skill.name if assignment.shift.required_skill else "unknown"
            staff_rows.append(
                OnDutyStaffRow(
                    user_id=assignment.user_id,
                    name=assignment.user.name,
                    skill=skill_name,
                )
            )

        location_rows.append(
            OnDutyLocationRow(
                location_id=loc_id,
                location_name=location_obj.name,
                iana_timezone=location_obj.iana_timezone,
                local_time=now.astimezone(ZoneInfo(location_obj.iana_timezone)).isoformat(),
                current_shift=shift_payload,
                on_duty_staff=staff_rows,
            )
        )

    return OnDutyResponse(as_of=now, locations=location_rows)

