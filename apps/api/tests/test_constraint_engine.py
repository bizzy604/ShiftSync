from datetime import date, datetime, timedelta, timezone
from zoneinfo import ZoneInfo

import pytest

from app.services.constraint_engine import (
    AssignmentSnapshot,
    AvailabilityRule,
    ShiftSnapshot,
    UserSnapshot,
    evaluate_assignment,
)


UTC = timezone.utc


def dt(value: str) -> datetime:
    return datetime.fromisoformat(value.replace("Z", "+00:00")).astimezone(UTC)


def recurring_all_day() -> list[AvailabilityRule]:
    return [
        AvailabilityRule(
            avail_type="recurring",
            day_of_week=dow,
            specific_date=None,
            start_clock="00:00",
            end_clock="23:59",
            is_available=True,
        )
        for dow in range(7)
    ]


def user_snapshot(
    *,
    skills: set[str] | None = None,
    location_ids: set[str] | None = None,
    availability: list[AvailabilityRule] | None = None,
    hourly_rate: float = 20.0,
) -> UserSnapshot:
    return UserSnapshot(
        id="user-1",
        name="Test User",
        home_timezone="America/Los_Angeles",
        skills=skills or {"skill-bartender"},
        active_location_ids=location_ids or {"loc-1"},
        availability=recurring_all_day() if availability is None else availability,
        hourly_rate=hourly_rate,
    )


def shift_snapshot(start_utc: datetime, end_utc: datetime) -> ShiftSnapshot:
    return ShiftSnapshot(
        id="shift-1",
        location_id="loc-1",
        location_name="Ocean Ave",
        location_timezone="America/Los_Angeles",
        required_skill_id="skill-bartender",
        required_skill_name="bartender",
        start_utc=start_utc,
        end_utc=end_utc,
    )


def assignment(shift_id: str, start_utc: datetime, end_utc: datetime) -> AssignmentSnapshot:
    return AssignmentSnapshot(shift_id=shift_id, start_utc=start_utc, end_utc=end_utc)


def has_rule(result: object, rule: str, severity: str | None = None) -> bool:
    for item in result.violations + result.warnings:
        if item.rule != rule:
            continue
        if severity is not None and item.severity != severity:
            continue
        return True
    return False


def test_skill_match_missing_blocks() -> None:
    shift = shift_snapshot(dt("2026-03-02T18:00:00Z"), dt("2026-03-02T22:00:00Z"))
    user = user_snapshot(skills={"skill-server"})
    result = evaluate_assignment(shift, user, [])
    assert has_rule(result, "SKILL_MATCH", "HARD_BLOCK")


def test_skill_match_present_passes_rule() -> None:
    shift = shift_snapshot(dt("2026-03-02T18:00:00Z"), dt("2026-03-02T22:00:00Z"))
    user = user_snapshot(skills={"skill-bartender"})
    result = evaluate_assignment(shift, user, [])
    assert not has_rule(result, "SKILL_MATCH")


def test_skill_match_with_multiple_skills_passes() -> None:
    shift = shift_snapshot(dt("2026-03-02T18:00:00Z"), dt("2026-03-02T22:00:00Z"))
    user = user_snapshot(skills={"skill-bartender", "skill-server"})
    result = evaluate_assignment(shift, user, [])
    assert not has_rule(result, "SKILL_MATCH")


def test_location_cert_missing_blocks() -> None:
    shift = shift_snapshot(dt("2026-03-02T18:00:00Z"), dt("2026-03-02T22:00:00Z"))
    user = user_snapshot(location_ids={"loc-2"})
    result = evaluate_assignment(shift, user, [])
    assert has_rule(result, "LOCATION_CERT", "HARD_BLOCK")


def test_location_cert_present_passes_rule() -> None:
    shift = shift_snapshot(dt("2026-03-02T18:00:00Z"), dt("2026-03-02T22:00:00Z"))
    user = user_snapshot(location_ids={"loc-1"})
    result = evaluate_assignment(shift, user, [])
    assert not has_rule(result, "LOCATION_CERT")


def test_location_cert_multiple_locations_passes() -> None:
    shift = shift_snapshot(dt("2026-03-02T18:00:00Z"), dt("2026-03-02T22:00:00Z"))
    user = user_snapshot(location_ids={"loc-1", "loc-2"})
    result = evaluate_assignment(shift, user, [])
    assert not has_rule(result, "LOCATION_CERT")


def test_availability_missing_recurring_window_blocks() -> None:
    shift = shift_snapshot(dt("2026-03-03T18:00:00Z"), dt("2026-03-03T22:00:00Z"))
    user = user_snapshot(availability=[])
    result = evaluate_assignment(shift, user, [])
    assert has_rule(result, "AVAILABILITY", "HARD_BLOCK")


def test_availability_exception_unavailable_blocks() -> None:
    shift_start = dt("2026-03-03T18:00:00Z")
    shift_end = dt("2026-03-03T22:00:00Z")
    local_date = shift_start.astimezone(ZoneInfo("America/Los_Angeles")).date()
    rules = recurring_all_day()
    rules.append(
        AvailabilityRule(
            avail_type="exception",
            day_of_week=None,
            specific_date=local_date,
            start_clock=None,
            end_clock=None,
            is_available=False,
        )
    )
    result = evaluate_assignment(shift_snapshot(shift_start, shift_end), user_snapshot(availability=rules), [])
    assert has_rule(result, "AVAILABILITY", "HARD_BLOCK")


def test_availability_overnight_cross_midnight_passes() -> None:
    rules = [
        AvailabilityRule("recurring", 5, None, "22:00", "00:00", True),
        AvailabilityRule("recurring", 6, None, "00:00", "04:00", True),
    ]
    shift = shift_snapshot(dt("2026-03-07T07:00:00Z"), dt("2026-03-07T11:00:00Z"))
    result = evaluate_assignment(shift, user_snapshot(availability=rules), [])
    assert not has_rule(result, "AVAILABILITY")


def test_availability_dst_spring_forward_passes() -> None:
    rules = [AvailabilityRule("recurring", 0, None, "01:00", "04:00", True)]
    shift = shift_snapshot(dt("2026-03-08T09:30:00Z"), dt("2026-03-08T10:30:00Z"))
    result = evaluate_assignment(shift, user_snapshot(availability=rules), [])
    assert not has_rule(result, "AVAILABILITY")


def test_availability_dst_fall_back_passes() -> None:
    rules = [AvailabilityRule("recurring", 0, None, "01:00", "03:00", True)]
    shift = shift_snapshot(dt("2026-11-01T08:30:00Z"), dt("2026-11-01T10:30:00Z"))
    result = evaluate_assignment(shift, user_snapshot(availability=rules), [])
    assert not has_rule(result, "AVAILABILITY")


def test_double_booking_overlap_blocks() -> None:
    shift = shift_snapshot(dt("2026-03-03T20:00:00Z"), dt("2026-03-04T00:00:00Z"))
    existing = [assignment("a-1", dt("2026-03-03T19:00:00Z"), dt("2026-03-03T21:00:00Z"))]
    result = evaluate_assignment(shift, user_snapshot(), existing)
    assert has_rule(result, "DOUBLE_BOOKING", "HARD_BLOCK")


def test_double_booking_touching_boundary_not_overlap() -> None:
    shift = shift_snapshot(dt("2026-03-04T00:00:00Z"), dt("2026-03-04T04:00:00Z"))
    existing = [assignment("a-1", dt("2026-03-03T20:00:00Z"), dt("2026-03-04T00:00:00Z"))]
    result = evaluate_assignment(shift, user_snapshot(), existing)
    assert not has_rule(result, "DOUBLE_BOOKING")


def test_double_booking_separate_windows_not_overlap() -> None:
    shift = shift_snapshot(dt("2026-03-05T20:00:00Z"), dt("2026-03-06T00:00:00Z"))
    existing = [assignment("a-1", dt("2026-03-03T20:00:00Z"), dt("2026-03-04T00:00:00Z"))]
    result = evaluate_assignment(shift, user_snapshot(), existing)
    assert not has_rule(result, "DOUBLE_BOOKING")


def test_rest_period_previous_gap_under_10_blocks() -> None:
    shift = shift_snapshot(dt("2026-03-03T20:00:00Z"), dt("2026-03-04T00:00:00Z"))
    existing = [assignment("a-1", dt("2026-03-03T10:00:00Z"), dt("2026-03-03T14:00:00Z"))]
    result = evaluate_assignment(shift, user_snapshot(), existing)
    assert has_rule(result, "REST_PERIOD", "HARD_BLOCK")


def test_rest_period_next_gap_under_10_blocks() -> None:
    shift = shift_snapshot(dt("2026-03-03T20:00:00Z"), dt("2026-03-04T00:00:00Z"))
    existing = [assignment("a-1", dt("2026-03-04T08:00:00Z"), dt("2026-03-04T12:00:00Z"))]
    result = evaluate_assignment(shift, user_snapshot(), existing)
    assert has_rule(result, "REST_PERIOD", "HARD_BLOCK")


def test_rest_period_exactly_10_hours_passes_rule() -> None:
    shift = shift_snapshot(dt("2026-03-03T20:00:00Z"), dt("2026-03-04T00:00:00Z"))
    existing = [assignment("a-1", dt("2026-03-03T06:00:00Z"), dt("2026-03-03T10:00:00Z"))]
    result = evaluate_assignment(shift, user_snapshot(), existing)
    assert not has_rule(result, "REST_PERIOD")


def test_daily_hours_under_8_no_daily_signal() -> None:
    shift = shift_snapshot(dt("2026-03-04T08:00:00Z"), dt("2026-03-04T13:00:00Z"))
    existing = [assignment("a-1", dt("2026-03-05T00:00:00Z"), dt("2026-03-05T02:00:00Z"))]
    result = evaluate_assignment(shift, user_snapshot(), existing)
    assert not has_rule(result, "DAILY_HOURS")


def test_daily_hours_8_or_more_warns() -> None:
    shift = shift_snapshot(dt("2026-03-04T08:00:00Z"), dt("2026-03-04T14:00:00Z"))
    existing = [assignment("a-1", dt("2026-03-04T16:00:00Z"), dt("2026-03-04T19:00:00Z"))]
    result = evaluate_assignment(shift, user_snapshot(), existing)
    assert has_rule(result, "DAILY_HOURS", "WARNING")


def test_daily_hours_over_12_blocks() -> None:
    shift = shift_snapshot(dt("2026-03-04T08:00:00Z"), dt("2026-03-04T14:00:00Z"))
    existing = [assignment("a-1", dt("2026-03-04T16:00:00Z"), dt("2026-03-04T23:00:00Z"))]
    result = evaluate_assignment(shift, user_snapshot(), existing)
    assert has_rule(result, "DAILY_HOURS", "HARD_BLOCK")


def _week_assignments(hours: float, week_anchor: datetime) -> list[AssignmentSnapshot]:
    out: list[AssignmentSnapshot] = []
    remaining = hours
    day = 0
    while remaining > 0:
        chunk = min(8.0, remaining)
        start = week_anchor + timedelta(days=day, hours=12)
        out.append(assignment(f"a-{day}", start, start + timedelta(hours=chunk)))
        remaining -= chunk
        day += 1
    return out


def test_weekly_hours_below_35_no_warning() -> None:
    shift = shift_snapshot(dt("2026-03-08T06:00:00Z"), dt("2026-03-08T10:00:00Z"))
    existing = _week_assignments(30.0, dt("2026-03-02T00:00:00Z"))
    result = evaluate_assignment(shift, user_snapshot(), existing)
    assert not has_rule(result, "WEEKLY_HOURS")
    assert result.projected_weekly_hours == pytest.approx(34.0, 0.01)


def test_weekly_hours_35_or_more_warns() -> None:
    shift = shift_snapshot(dt("2026-03-08T06:00:00Z"), dt("2026-03-08T10:00:00Z"))
    existing = _week_assignments(32.0, dt("2026-03-02T00:00:00Z"))
    result = evaluate_assignment(shift, user_snapshot(), existing)
    assert has_rule(result, "WEEKLY_HOURS", "WARNING")


def test_weekly_hours_overtime_cost_projects() -> None:
    shift = shift_snapshot(dt("2026-03-08T06:00:00Z"), dt("2026-03-08T10:00:00Z"))
    existing = _week_assignments(40.0, dt("2026-03-02T00:00:00Z"))
    result = evaluate_assignment(shift, user_snapshot(hourly_rate=20.0), existing)
    assert has_rule(result, "WEEKLY_HOURS", "WARNING")
    assert result.projected_overtime_cost == pytest.approx(120.0, 0.01)


def _consecutive_assignments(days: int, start_day: datetime) -> list[AssignmentSnapshot]:
    out = []
    for i in range(days):
        start = start_day + timedelta(days=i, hours=12)
        out.append(assignment(f"c-{i}", start, start + timedelta(hours=4)))
    return out


def test_consecutive_days_five_no_signal() -> None:
    shift = shift_snapshot(dt("2026-03-06T20:00:00Z"), dt("2026-03-07T00:00:00Z"))
    existing = _consecutive_assignments(4, dt("2026-03-02T00:00:00Z"))
    result = evaluate_assignment(shift, user_snapshot(), existing)
    assert not has_rule(result, "CONSECUTIVE_DAYS")


def test_consecutive_days_six_warns() -> None:
    shift = shift_snapshot(dt("2026-03-07T20:00:00Z"), dt("2026-03-08T00:00:00Z"))
    existing = _consecutive_assignments(5, dt("2026-03-02T00:00:00Z"))
    result = evaluate_assignment(shift, user_snapshot(), existing)
    assert has_rule(result, "CONSECUTIVE_DAYS", "WARNING")


def test_consecutive_days_seven_requires_override() -> None:
    shift = shift_snapshot(dt("2026-03-08T20:00:00Z"), dt("2026-03-09T00:00:00Z"))
    existing = _consecutive_assignments(6, dt("2026-03-02T00:00:00Z"))
    result = evaluate_assignment(shift, user_snapshot(), existing)
    assert has_rule(result, "CONSECUTIVE_DAYS", "OVERRIDE_REQUIRED")
