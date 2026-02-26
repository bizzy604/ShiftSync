# Constraint Engine Standards
## ShiftSync — constraint_engine/ (Pure Python Package)

---

## What the Constraint Engine Is

The constraint engine is a **pure Python package** with zero side effects.

- No database access — no SQLAlchemy, no session, no queries
- No HTTP calls — no FastAPI, no httpx
- No imports from `app/` — zero dependency on the application layer
- Deterministic: same inputs → same outputs, always

This design is what makes it 100% unit-testable without any infrastructure.

---

## Package Structure

```
constraint_engine/
├── __init__.py              ← Public API (create_default_engine, all types)
├── engine.py                ← ConstraintEngine class (Strategy Context)
├── types.py                 ← All dataclasses, Protocols, enums
├── checks/                  ← One file per constraint check (Strategy)
│   ├── __init__.py
│   ├── skill_match_check.py
│   ├── location_cert_check.py
│   ├── availability_check.py
│   ├── double_booking_check.py
│   ├── rest_period_check.py
│   ├── daily_hours_check.py
│   ├── weekly_hours_check.py
│   └── consecutive_days_check.py
└── utils/
    ├── __init__.py
    ├── interval_utils.py    ← Half-open interval overlap math
    └── availability_utils.py ← DST-safe clock-time resolution
```

Tests live alongside the backend at `backend/tests/unit/constraint_engine/`.

---

## Core Types

```python
# constraint_engine/types.py

from __future__ import annotations
from dataclasses import dataclass, field
from datetime import datetime, time
from enum import StrEnum
from typing import Protocol
from uuid import UUID


class Severity(StrEnum):
    HARD_BLOCK       = "HARD_BLOCK"
    WARNING          = "WARNING"
    OVERRIDE_REQUIRED = "OVERRIDE_REQUIRED"


class ConstraintRule(StrEnum):
    SKILL_MATCH      = "SKILL_MATCH"
    LOCATION_CERT    = "LOCATION_CERT"
    AVAILABILITY     = "AVAILABILITY"
    DOUBLE_BOOKING   = "DOUBLE_BOOKING"
    REST_PERIOD      = "REST_PERIOD"
    DAILY_HOURS      = "DAILY_HOURS"
    WEEKLY_HOURS     = "WEEKLY_HOURS"
    CONSECUTIVE_DAYS = "CONSECUTIVE_DAYS"


@dataclass(frozen=True)
class ShiftInfo:
    """Immutable shift data needed by the constraint engine.

    Attributes:
        id:             UUID of the shift.
        location_id:    UUID of the location (for certification checks).
        required_skill: Skill name string (e.g. 'bartender').
        start_utc:      Shift start as a UTC-aware datetime.
        end_utc:        Shift end as a UTC-aware datetime.
        location_tz:    IANA timezone string of the shift location (e.g. 'America/Los_Angeles').
    """
    id: UUID
    location_id: UUID
    required_skill: str
    start_utc: datetime
    end_utc: datetime
    location_tz: str


@dataclass(frozen=True)
class AvailabilityEntry:
    """A single availability window for a staff member.

    Attributes:
        avail_type:   'recurring' or 'exception'.
        day_of_week:  0=Monday … 6=Sunday (for recurring entries).
        specific_date: Exact date (for exception entries).
        start_clock:  'HH:MM' in the staff member's home timezone.
        end_clock:    'HH:MM' in the staff member's home timezone.
        is_available: False = explicitly unavailable on this day/date.
    """
    avail_type: str
    day_of_week: int | None
    specific_date: "date | None"
    start_clock: str
    end_clock: str
    is_available: bool


@dataclass(frozen=True)
class UserForConstraints:
    """All user data needed by the constraint engine.

    Attributes:
        id:                    UUID of the staff member.
        skill_names:           Set of skill name strings this user has.
        certified_location_ids: Set of location UUIDs where this user is certified (revoked_at IS NULL).
        home_timezone:         IANA timezone string of the staff member's home.
        availability:          List of recurring and exception availability entries.
    """
    id: UUID
    skill_names: frozenset[str]
    certified_location_ids: frozenset[UUID]
    home_timezone: str
    availability: tuple[AvailabilityEntry, ...]


@dataclass(frozen=True)
class ExistingAssignment:
    """A previously confirmed assignment used for overlap and rest-period checks."""
    shift_id: UUID
    start_utc: datetime
    end_utc: datetime


@dataclass(frozen=True)
class AssignmentProposal:
    """The proposed assignment being evaluated by the constraint engine.

    Attributes:
        shift_id:        UUID of the target shift.
        user_id:         UUID of the staff member to assign.
        shift:           Full shift details needed by checks.
        override_reason: Present only when the manager is bypassing an OVERRIDE_REQUIRED rule.
    """
    shift_id: UUID
    user_id: UUID
    shift: ShiftInfo
    override_reason: str | None = None


@dataclass(frozen=True)
class ConstraintContext:
    """All data pre-loaded by the caller for the constraint engine to evaluate.

    WHY: Keeping data loading outside the engine keeps it pure and independently testable.
    The engine receives a fully populated context — it never touches the database.

    Attributes:
        user:                 User profile with skills, certifications, and availability.
        existing_assignments: User's confirmed assignments in a ±24h window around the proposed shift.
    """
    user: UserForConstraints
    existing_assignments: tuple[ExistingAssignment, ...]


@dataclass(frozen=True)
class ConstraintViolation:
    """A single constraint violation with all context needed for a manager to act.

    Attributes:
        rule:        Machine-readable rule identifier.
        severity:    HARD_BLOCK, WARNING, or OVERRIDE_REQUIRED.
        description: Human-readable sentence with specific values, e.g.
                     'Only 8.0hr gap. Minimum required: 10hr.'
    """
    rule: ConstraintRule
    severity: Severity
    description: str


@dataclass
class ConstraintResult:
    """Output of the full constraint engine after running all checks.

    Attributes:
        valid:            True if zero HARD_BLOCK violations. Warnings/overrides may still exist.
        violations:       All HARD_BLOCK and OVERRIDE_REQUIRED violations.
        warnings:         All WARNING-severity violations.
        requires_override: True if any OVERRIDE_REQUIRED violations are present.
        suggestions:      Initially empty — populated by AssignmentService after evaluation.
    """
    valid: bool
    violations: list[ConstraintViolation]
    warnings: list[ConstraintViolation]
    requires_override: bool
    suggestions: list[dict] = field(default_factory=list)


@dataclass(frozen=True)
class ConstraintCheckResult:
    """Output of a single constraint check."""
    passed: bool
    severity: Severity = Severity.HARD_BLOCK
    description: str = ""


class IConstraintCheck(Protocol):
    """Strategy interface for a single scheduling constraint check.

    PATTERN: Strategy — each check is an independent, pluggable Strategy.
    """
    name: ConstraintRule
    severity: Severity

    def evaluate(
        self, proposal: AssignmentProposal, context: ConstraintContext
    ) -> ConstraintCheckResult: ...


class IConstraintEngine(Protocol):
    """Public interface for the constraint engine.

    Depends on this Protocol in FastAPI service layer, not the concrete class.
    """
    def evaluate(
        self, proposal: AssignmentProposal, context: ConstraintContext
    ) -> ConstraintResult: ...
```

---

## The Engine — Strategy Context

```python
# constraint_engine/engine.py

from constraint_engine.types import (
    IConstraintCheck, AssignmentProposal, ConstraintContext,
    ConstraintResult, ConstraintViolation, Severity,
)
from constraint_engine.checks import (
    SkillMatchCheck, LocationCertCheck, AvailabilityCheck, DoubleBookingCheck,
    RestPeriodCheck, DailyHoursCheck, WeeklyHoursCheck, ConsecutiveDaysCheck,
)


class ConstraintEngine:
    """Evaluates all registered constraint checks against a proposed assignment.

    PATTERN: Strategy — engine is the Context; each IConstraintCheck is a Strategy.
    Adding a new constraint = implement IConstraintCheck, register in create_default_engine().
    The engine itself never changes (Open/Closed Principle).

    IMPORTANT: All checks always run. No short-circuit on first failure.
    Managers need the full picture to make one informed decision.
    """

    def __init__(self, checks: list[IConstraintCheck]) -> None:
        self._checks = checks

    def evaluate(
        self, proposal: AssignmentProposal, context: ConstraintContext
    ) -> ConstraintResult:
        """Run all registered checks and collect violations and warnings.

        Args:
            proposal: The proposed assignment to evaluate.
            context:  Pre-loaded data (user, existing assignments).

        Returns:
            ConstraintResult with all violations, warnings, and requires_override flag.
        """
        violations: list[ConstraintViolation] = []
        warnings: list[ConstraintViolation] = []

        for check in self._checks:
            result = check.evaluate(proposal, context)
            if not result.passed:
                violation = ConstraintViolation(
                    rule=check.name,
                    severity=result.severity,
                    description=result.description,
                )
                if violation.severity == Severity.WARNING:
                    warnings.append(violation)
                else:
                    violations.append(violation)

        hard_blocks = [v for v in violations if v.severity == Severity.HARD_BLOCK]
        return ConstraintResult(
            valid=len(hard_blocks) == 0,
            violations=violations,
            warnings=warnings,
            requires_override=any(
                v.severity == Severity.OVERRIDE_REQUIRED for v in violations
            ),
            suggestions=[],  # Populated by AssignmentService after evaluation
        )


def create_default_engine() -> ConstraintEngine:
    """Construct the constraint engine with all 8 default checks registered.

    PATTERN: Factory Method — centralises construction of engine and its strategies.

    Returns:
        A fully configured ConstraintEngine with all default checks.
    """
    return ConstraintEngine([
        SkillMatchCheck(),
        LocationCertCheck(),
        AvailabilityCheck(),
        DoubleBookingCheck(),
        RestPeriodCheck(),
        DailyHoursCheck(),
        WeeklyHoursCheck(),
        ConsecutiveDaysCheck(),
    ])
```

---

## Individual Check — Full Example (Rest Period)

```python
# constraint_engine/checks/rest_period_check.py

from constraint_engine.types import (
    IConstraintCheck, AssignmentProposal, ConstraintContext,
    ConstraintCheckResult, ConstraintRule, Severity,
)
from constraint_engine.utils.interval_utils import hours_between


class RestPeriodCheck:
    """Constraint: Staff must have a minimum 10-hour gap between consecutive shifts.

    Checks the nearest assignment ending before the proposed shift starts,
    and the nearest assignment starting after it ends. If either gap is less
    than 10 hours, the check fails with a HARD_BLOCK.
    """

    name: ConstraintRule = ConstraintRule.REST_PERIOD
    severity: Severity = Severity.HARD_BLOCK
    MIN_REST_HOURS: float = 10.0

    def evaluate(
        self, proposal: AssignmentProposal, context: ConstraintContext
    ) -> ConstraintCheckResult:
        """Check the rest period before and after the proposed shift.

        Args:
            proposal: Contains the proposed shift's start_utc and end_utc.
            context:  Contains existing_assignments for this user.

        Returns:
            ConstraintCheckResult with passed=True if both gaps are >= 10 hours.
        """
        shift = proposal.shift
        assignments = context.existing_assignments

        # Find the nearest assignment ending before this shift starts
        before = [a for a in assignments if a.end_utc <= shift.start_utc]
        previous = max(before, key=lambda a: a.end_utc, default=None)

        # Find the nearest assignment starting after this shift ends
        after = [a for a in assignments if a.start_utc >= shift.end_utc]
        next_shift = min(after, key=lambda a: a.start_utc, default=None)

        if previous:
            gap = hours_between(previous.end_utc, shift.start_utc)
            if gap < self.MIN_REST_HOURS:
                return ConstraintCheckResult(
                    passed=False,
                    severity=Severity.HARD_BLOCK,
                    description=(
                        f"Previous shift ends at {previous.end_utc.strftime('%H:%M UTC')}. "
                        f"This shift starts at {shift.start_utc.strftime('%H:%M UTC')}. "
                        f"Only {gap:.1f}hr gap. Minimum required: {self.MIN_REST_HOURS:.0f}hr."
                    ),
                )

        if next_shift:
            gap = hours_between(shift.end_utc, next_shift.start_utc)
            if gap < self.MIN_REST_HOURS:
                return ConstraintCheckResult(
                    passed=False,
                    severity=Severity.HARD_BLOCK,
                    description=(
                        f"This shift ends at {shift.end_utc.strftime('%H:%M UTC')}. "
                        f"Next shift starts at {next_shift.start_utc.strftime('%H:%M UTC')}. "
                        f"Only {gap:.1f}hr gap. Minimum required: {self.MIN_REST_HOURS:.0f}hr."
                    ),
                )

        return ConstraintCheckResult(passed=True)
```

---

## DST-Safe Availability Resolution

```python
# constraint_engine/utils/availability_utils.py

from datetime import datetime, date, timedelta
from zoneinfo import ZoneInfo


def resolve_clock_time_to_utc(clock_time: str, for_date: date, timezone: str) -> datetime:
    """Resolve a staff member's clock-time availability to a UTC datetime for a specific date.

    WHY clock-time semantics, not UTC offset semantics:
        Storing availability as UTC offsets breaks on DST transition dates.
        '09:00 America/Los_Angeles' on Nov 2 2025 (fall-back) should resolve to
        UTC-8, not UTC-7. ZoneInfo handles this correctly using the IANA database.

    Args:
        clock_time: 'HH:MM' string in the staff member's home timezone (e.g. '09:00').
        for_date:   The specific calendar date to resolve for (DST may differ per date).
        timezone:   IANA timezone identifier (e.g. 'America/Los_Angeles').

    Returns:
        A UTC-aware datetime representing the clock time on that date.

    Example:
        # Spring-forward: 2:00 AM skips to 3:00 AM on March 9, 2025
        resolve_clock_time_to_utc('09:00', date(2025, 3, 9), 'America/Los_Angeles')
        # Returns 2025-03-09 16:00:00+00:00  (09:00 PDT = UTC-7)

        # Fall-back: Nov 2, 2025
        resolve_clock_time_to_utc('09:00', date(2025, 11, 2), 'America/Los_Angeles')
        # Returns 2025-11-02 17:00:00+00:00  (09:00 PST = UTC-8)
    """
    hour, minute = map(int, clock_time.split(":"))
    tz = ZoneInfo(timezone)
    local_dt = datetime(for_date.year, for_date.month, for_date.day, hour, minute, tzinfo=tz)
    return local_dt.astimezone(ZoneInfo("UTC"))


def split_overnight_shift(
    shift_start: datetime, shift_end: datetime, timezone: str
) -> list[tuple[datetime, datetime, date]]:
    """Split an overnight shift into calendar-day segments for availability checking.

    WHY: A shift from 23:00 to 03:00 crosses midnight. A staff member may have
    different availability on each side (e.g., MON vs TUE). Each segment is
    checked against the availability for its own calendar day independently.

    Args:
        shift_start: UTC-aware datetime of shift start.
        shift_end:   UTC-aware datetime of shift end.
        timezone:    IANA timezone to determine calendar day boundaries.

    Returns:
        List of (segment_start_utc, segment_end_utc, calendar_date) tuples.
        Single entry if start and end fall on the same calendar day in the timezone.

    Example:
        # Shift 11pm–3am PT returns two segments:
        # [(23:00 UTC, midnight UTC, date(2025,8,10)), (midnight UTC, 06:00 UTC, date(2025,8,11))]
    """
    tz = ZoneInfo(timezone)
    start_local = shift_start.astimezone(tz)
    end_local = shift_end.astimezone(tz)

    # Same calendar day in the location timezone — single segment
    if start_local.date() == end_local.date():
        return [(shift_start, shift_end, start_local.date())]

    # Overnight — split at local midnight on the day the shift ends
    midnight_next_day = datetime(
        end_local.year, end_local.month, end_local.day,
        0, 0, 0, tzinfo=tz
    ).astimezone(ZoneInfo("UTC"))

    return [
        (shift_start, midnight_next_day, start_local.date()),
        (midnight_next_day, shift_end, end_local.date()),
    ]
```

---

## Required Test Coverage for Every Check

| Scenario | Test Required |
|---|---|
| Happy path — check passes | `test_returns_passed_true_when_constraint_satisfied` |
| Failure path — check fails | `test_returns_hard_block_with_specific_values_in_description` |
| Exactly at threshold | `test_passes_at_exactly_10_hours_gap_fails_at_9h59m` |
| Overnight shift | `test_correctly_handles_shifts_crossing_midnight` |
| DST spring-forward | `test_resolves_0900_correctly_on_spring_forward_date_2025_03_09` |
| DST fall-back | `test_resolves_0900_correctly_on_fall_back_date_2025_11_02` |
| Consecutive days: 1-min shift | `test_counts_one_minute_shift_as_a_worked_day` |
| Cross-TZ staff | `test_blocks_9am_et_shift_for_staff_with_9am_5pm_pt_availability` |

See `references/testing-standards.md` for the full test implementations.
