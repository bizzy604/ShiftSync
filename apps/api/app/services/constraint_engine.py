from dataclasses import dataclass
from datetime import date, datetime, time, timedelta, timezone
from zoneinfo import ZoneInfo


HARD_BLOCK = "HARD_BLOCK"
WARNING = "WARNING"
OVERRIDE_REQUIRED = "OVERRIDE_REQUIRED"


@dataclass(frozen=True)
class AvailabilityRule:
    avail_type: str
    day_of_week: int | None
    specific_date: date | None
    start_clock: str | None
    end_clock: str | None
    is_available: bool


@dataclass(frozen=True)
class AssignmentSnapshot:
    shift_id: str
    start_utc: datetime
    end_utc: datetime


@dataclass(frozen=True)
class ShiftSnapshot:
    id: str
    location_id: str
    location_name: str
    location_timezone: str
    required_skill_id: str
    required_skill_name: str
    start_utc: datetime
    end_utc: datetime


@dataclass(frozen=True)
class UserSnapshot:
    id: str
    name: str
    home_timezone: str
    skills: set[str]
    active_location_ids: set[str]
    availability: list[AvailabilityRule]
    hourly_rate: float


@dataclass(frozen=True)
class ConstraintItem:
    rule: str
    description: str
    severity: str


@dataclass(frozen=True)
class ConstraintResult:
    valid: bool
    violations: list[ConstraintItem]
    warnings: list[ConstraintItem]
    requires_override: bool
    projected_weekly_hours: float
    projected_daily_hours: float
    projected_overtime_cost: float


def evaluate_assignment(
    shift: ShiftSnapshot,
    user: UserSnapshot,
    existing_assignments: list[AssignmentSnapshot],
) -> ConstraintResult:
    violations: list[ConstraintItem] = []
    warnings: list[ConstraintItem] = []

    user_tz = ZoneInfo(user.home_timezone)

    if shift.required_skill_id not in user.skills:
        violations.append(
            ConstraintItem(
                rule="SKILL_MATCH",
                severity=HARD_BLOCK,
                description=f"{user.name} does not have required skill '{shift.required_skill_name}'.",
            )
        )

    if shift.location_id not in user.active_location_ids:
        violations.append(
            ConstraintItem(
                rule="LOCATION_CERT",
                severity=HARD_BLOCK,
                description=f"{user.name} is not certified at location '{shift.location_name}'.",
            )
        )

    availability_issue = _check_availability(shift=shift, user=user, user_tz=user_tz)
    if availability_issue:
        violations.append(availability_issue)

    overlap = _find_overlap(shift=shift, existing_assignments=existing_assignments)
    if overlap:
        violations.append(
            ConstraintItem(
                rule="DOUBLE_BOOKING",
                severity=HARD_BLOCK,
                description=(
                    f"{user.name} is already assigned to overlapping shift "
                    f"{_format_utc(overlap.start_utc)} to {_format_utc(overlap.end_utc)}."
                ),
            )
        )

    rest_issue = _check_rest_period(shift=shift, existing_assignments=existing_assignments)
    if rest_issue:
        violations.append(rest_issue)

    daily_total, daily_issue, daily_warning = _check_daily_hours(
        shift=shift,
        existing_assignments=existing_assignments,
        user_tz=user_tz,
    )
    if daily_issue:
        violations.append(daily_issue)
    if daily_warning:
        warnings.append(daily_warning)

    weekly_total, overtime_cost, weekly_warning = _check_weekly_hours(
        shift=shift,
        existing_assignments=existing_assignments,
        user_tz=user_tz,
        hourly_rate=user.hourly_rate,
    )
    if weekly_warning:
        warnings.append(weekly_warning)

    consecutive_issue, consecutive_warning = _check_consecutive_days(
        shift=shift,
        existing_assignments=existing_assignments,
        user_tz=user_tz,
    )
    if consecutive_issue:
        violations.append(consecutive_issue)
    if consecutive_warning:
        warnings.append(consecutive_warning)

    hard_block_count = sum(1 for item in violations if item.severity == HARD_BLOCK)
    requires_override = any(item.severity == OVERRIDE_REQUIRED for item in violations)

    return ConstraintResult(
        valid=hard_block_count == 0,
        violations=violations,
        warnings=warnings,
        requires_override=requires_override,
        projected_weekly_hours=round(weekly_total, 2),
        projected_daily_hours=round(daily_total, 2),
        projected_overtime_cost=round(overtime_cost, 2),
    )


def _check_availability(shift: ShiftSnapshot, user: UserSnapshot, user_tz: ZoneInfo) -> ConstraintItem | None:
    segments = _split_interval_by_midnight(shift.start_utc, shift.end_utc, user_tz)
    for segment_start_utc, segment_end_utc, segment_date in segments:
        windows, unavailable_reason = _resolve_windows_for_date(
            rules=user.availability,
            target_date=segment_date,
            timezone_name=user.home_timezone,
        )
        if unavailable_reason:
            return ConstraintItem(
                rule="AVAILABILITY",
                severity=HARD_BLOCK,
                description=f"{user.name} is unavailable on {segment_date.isoformat()}: {unavailable_reason}",
            )

        covered = any(window_start <= segment_start_utc and window_end >= segment_end_utc for window_start, window_end in windows)
        if not covered:
            return ConstraintItem(
                rule="AVAILABILITY",
                severity=HARD_BLOCK,
                description=(
                    f"{user.name}'s availability does not cover segment "
                    f"{_format_utc(segment_start_utc)} to {_format_utc(segment_end_utc)}."
                ),
            )
    return None


def _find_overlap(shift: ShiftSnapshot, existing_assignments: list[AssignmentSnapshot]) -> AssignmentSnapshot | None:
    for assignment in existing_assignments:
        if assignment.start_utc < shift.end_utc and assignment.end_utc > shift.start_utc:
            return assignment
    return None


def _check_rest_period(shift: ShiftSnapshot, existing_assignments: list[AssignmentSnapshot]) -> ConstraintItem | None:
    min_gap = timedelta(hours=10)

    previous = [a for a in existing_assignments if a.end_utc <= shift.start_utc]
    next_items = [a for a in existing_assignments if a.start_utc >= shift.end_utc]

    if previous:
        nearest_previous = max(previous, key=lambda a: a.end_utc)
        gap = shift.start_utc - nearest_previous.end_utc
        if gap < min_gap:
            gap_hours = round(gap.total_seconds() / 3600, 2)
            return ConstraintItem(
                rule="REST_PERIOD",
                severity=HARD_BLOCK,
                description=f"Only {gap_hours} hours rest gap. Minimum required is 10 hours.",
            )

    if next_items:
        nearest_next = min(next_items, key=lambda a: a.start_utc)
        gap = nearest_next.start_utc - shift.end_utc
        if gap < min_gap:
            gap_hours = round(gap.total_seconds() / 3600, 2)
            return ConstraintItem(
                rule="REST_PERIOD",
                severity=HARD_BLOCK,
                description=f"Only {gap_hours} hours rest gap to next shift. Minimum required is 10 hours.",
            )

    return None


def _check_daily_hours(
    shift: ShiftSnapshot,
    existing_assignments: list[AssignmentSnapshot],
    user_tz: ZoneInfo,
) -> tuple[float, ConstraintItem | None, ConstraintItem | None]:
    totals: dict[date, float] = {}
    for assignment in existing_assignments:
        _add_interval_hours_by_date(totals, assignment.start_utc, assignment.end_utc, user_tz)
    _add_interval_hours_by_date(totals, shift.start_utc, shift.end_utc, user_tz)

    if not totals:
        return 0.0, None, None

    peak_date = max(totals, key=totals.get)
    peak_hours = totals[peak_date]
    hard_issue = None
    warning_issue = None

    if peak_hours > 12:
        hard_issue = ConstraintItem(
            rule="DAILY_HOURS",
            severity=HARD_BLOCK,
            description=f"Projected daily hours on {peak_date.isoformat()} would be {peak_hours:.2f}, over hard limit of 12.",
        )
    elif peak_hours >= 8:
        warning_issue = ConstraintItem(
            rule="DAILY_HOURS",
            severity=WARNING,
            description=f"Projected daily hours on {peak_date.isoformat()} would be {peak_hours:.2f} (warning threshold is 8).",
        )

    return peak_hours, hard_issue, warning_issue


def _check_weekly_hours(
    shift: ShiftSnapshot,
    existing_assignments: list[AssignmentSnapshot],
    user_tz: ZoneInfo,
    hourly_rate: float,
) -> tuple[float, float, ConstraintItem | None]:
    shift_local = shift.start_utc.astimezone(user_tz)
    week_start_local = datetime.combine(shift_local.date() - timedelta(days=shift_local.weekday()), time.min, tzinfo=user_tz)
    week_end_local = week_start_local + timedelta(days=7)
    week_start_utc = week_start_local.astimezone(timezone.utc)
    week_end_utc = week_end_local.astimezone(timezone.utc)

    total_hours = 0.0
    for assignment in existing_assignments:
        total_hours += _overlap_hours(assignment.start_utc, assignment.end_utc, week_start_utc, week_end_utc)
    total_hours += _overlap_hours(shift.start_utc, shift.end_utc, week_start_utc, week_end_utc)

    overtime_hours = max(0.0, total_hours - 40.0)
    overtime_cost = overtime_hours * hourly_rate * 1.5

    warning_issue = None
    if total_hours >= 35.0:
        warning_issue = ConstraintItem(
            rule="WEEKLY_HOURS",
            severity=WARNING,
            description=f"Projected weekly hours would be {total_hours:.2f} (warning threshold is 35).",
        )

    return total_hours, overtime_cost, warning_issue


def _check_consecutive_days(
    shift: ShiftSnapshot,
    existing_assignments: list[AssignmentSnapshot],
    user_tz: ZoneInfo,
) -> tuple[ConstraintItem | None, ConstraintItem | None]:
    worked_dates: set[date] = set()
    for assignment in existing_assignments:
        worked_dates.update(_dates_touched(assignment.start_utc, assignment.end_utc, user_tz))

    proposed_dates = _dates_touched(shift.start_utc, shift.end_utc, user_tz)
    worked_dates.update(proposed_dates)

    max_streak = 0
    for candidate in proposed_dates:
        streak = _streak_len(candidate, worked_dates)
        max_streak = max(max_streak, streak)

    if max_streak >= 7:
        return (
            ConstraintItem(
                rule="CONSECUTIVE_DAYS",
                severity=OVERRIDE_REQUIRED,
                description=f"Projected consecutive work days would be {max_streak}. Manager override is required on day 7+.",
            ),
            None,
        )

    if max_streak >= 6:
        return (
            None,
            ConstraintItem(
                rule="CONSECUTIVE_DAYS",
                severity=WARNING,
                description=f"Projected consecutive work days would be {max_streak} (warning on day 6).",
            ),
        )

    return None, None


def _resolve_windows_for_date(
    rules: list[AvailabilityRule],
    target_date: date,
    timezone_name: str,
) -> tuple[list[tuple[datetime, datetime]], str | None]:
    tz = ZoneInfo(timezone_name)
    exception_rules = [rule for rule in rules if rule.avail_type == "exception" and rule.specific_date == target_date]
    if exception_rules:
        if any(not rule.is_available and not rule.start_clock and not rule.end_clock for rule in exception_rules):
            return [], "marked unavailable all day"
        windows = [
            _clock_window_to_utc(target_date, rule.start_clock, rule.end_clock, tz)
            for rule in exception_rules
            if rule.is_available and rule.start_clock and rule.end_clock
        ]
        if not windows:
            return [], "no available exception window configured"
        return windows, None

    day_of_week = _dow_sunday0(target_date)
    recurring = [
        rule
        for rule in rules
        if rule.avail_type == "recurring" and rule.day_of_week == day_of_week and rule.is_available
    ]
    windows = [
        _clock_window_to_utc(target_date, rule.start_clock, rule.end_clock, tz)
        for rule in recurring
        if rule.start_clock and rule.end_clock
    ]
    if not windows:
        return [], "no recurring availability window configured"
    return windows, None


def _clock_window_to_utc(window_date: date, start_clock: str | None, end_clock: str | None, tz: ZoneInfo) -> tuple[datetime, datetime]:
    if start_clock is None or end_clock is None:
        raise ValueError("Availability windows require start and end clock values.")

    start_local = datetime.combine(window_date, _parse_clock(start_clock), tzinfo=tz)
    end_local = datetime.combine(window_date, _parse_clock(end_clock), tzinfo=tz)
    if end_local <= start_local:
        end_local += timedelta(days=1)

    return start_local.astimezone(timezone.utc), end_local.astimezone(timezone.utc)


def _split_interval_by_midnight(
    start_utc: datetime,
    end_utc: datetime,
    tz: ZoneInfo,
) -> list[tuple[datetime, datetime, date]]:
    segments: list[tuple[datetime, datetime, date]] = []
    start_local = start_utc.astimezone(tz)
    end_local = end_utc.astimezone(tz)

    cursor = start_local
    while cursor < end_local:
        next_midnight = datetime.combine(cursor.date() + timedelta(days=1), time.min, tzinfo=tz)
        segment_end = min(next_midnight, end_local)
        segments.append((cursor.astimezone(timezone.utc), segment_end.astimezone(timezone.utc), cursor.date()))
        cursor = segment_end

    return segments


def _add_interval_hours_by_date(totals: dict[date, float], start_utc: datetime, end_utc: datetime, tz: ZoneInfo) -> None:
    for segment_start, segment_end, segment_date in _split_interval_by_midnight(start_utc, end_utc, tz):
        hours = (segment_end - segment_start).total_seconds() / 3600
        totals[segment_date] = totals.get(segment_date, 0.0) + hours


def _dates_touched(start_utc: datetime, end_utc: datetime, tz: ZoneInfo) -> set[date]:
    return {segment_date for _, _, segment_date in _split_interval_by_midnight(start_utc, end_utc, tz)}


def _streak_len(anchor: date, worked_dates: set[date]) -> int:
    if anchor not in worked_dates:
        return 0

    streak = 1
    pointer = anchor - timedelta(days=1)
    while pointer in worked_dates:
        streak += 1
        pointer -= timedelta(days=1)

    pointer = anchor + timedelta(days=1)
    while pointer in worked_dates:
        streak += 1
        pointer += timedelta(days=1)

    return streak


def _overlap_hours(start_a: datetime, end_a: datetime, start_b: datetime, end_b: datetime) -> float:
    overlap_start = max(start_a, start_b)
    overlap_end = min(end_a, end_b)
    if overlap_start >= overlap_end:
        return 0.0
    return (overlap_end - overlap_start).total_seconds() / 3600


def _parse_clock(value: str) -> time:
    hour, minute = value.split(":")
    return time(hour=int(hour), minute=int(minute))


def _dow_sunday0(value: date) -> int:
    return (value.weekday() + 1) % 7


def _format_utc(value: datetime) -> str:
    return value.astimezone(timezone.utc).isoformat().replace("+00:00", "Z")
