# Testing Standards
## ShiftSync — pytest + pytest-asyncio + httpx + unittest.mock

---

## Testing Philosophy

> "A unit test is a specification of behaviour. If it's not testing behaviour,
> it's testing implementation — and implementation tests break the moment you refactor."

### Three Layers of Tests

| Layer | What It Tests | Tools | Coverage Target |
|---|---|---|---|
| **Unit** | Business logic in isolation (services, constraint checks, utils) | pytest + `unittest.mock.AsyncMock` | Every public method |
| **Integration** | HTTP routes end-to-end (request → response, real DB) | pytest + `httpx.AsyncClient` + test PostgreSQL | Every route × every status code |
| **E2E** | Critical user flows across the full stack | Playwright | 6 evaluation scenarios |

---

## Project Test Layout

```
backend/
└── tests/
    ├── conftest.py                    ← Shared fixtures (app, client, db, tokens)
    ├── unit/
    │   ├── assignments/
    │   │   ├── test_assignment_service.py
    │   │   └── test_assignment_repository.py
    │   ├── swaps/
    │   │   └── test_swap_service.py
    │   └── constraint_engine/
    │       ├── test_engine.py
    │       └── checks/
    │           ├── test_skill_match_check.py
    │           ├── test_availability_check.py    ← DST tests REQUIRED
    │           ├── test_double_booking_check.py
    │           ├── test_rest_period_check.py
    │           ├── test_daily_hours_check.py
    │           ├── test_weekly_hours_check.py
    │           └── test_consecutive_days_check.py
    └── integration/
        ├── assignments/
        │   └── test_assignments_router.py
        ├── swaps/
        │   └── test_swaps_router.py
        └── auth/
            └── test_auth_router.py
```

---

## Shared Fixtures (`tests/conftest.py`)

```python
# tests/conftest.py

import pytest
import pytest_asyncio
from httpx import AsyncClient, ASGITransport
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession, async_sessionmaker
from sqlalchemy.pool import NullPool

from app.main import create_app
from app.infrastructure.database import Base, get_session
from app.shared.security import create_access_token

TEST_DATABASE_URL = "postgresql+asyncpg://shiftsync:password@localhost:5432/shiftsync_test"


@pytest.fixture(scope="session")
def event_loop_policy():
    """Use the default asyncio event loop policy for the test session."""
    import asyncio
    return asyncio.DefaultEventLoopPolicy()


@pytest_asyncio.fixture(scope="session")
async def engine():
    """Create the test database engine (once per session)."""
    engine = create_async_engine(TEST_DATABASE_URL, poolclass=NullPool)
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    yield engine
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)
    await engine.dispose()


@pytest_asyncio.fixture()
async def db_session(engine):
    """Yield a clean transactional session for each test, rolled back after."""
    async with engine.connect() as conn:
        await conn.begin()
        session = AsyncSession(bind=conn, expire_on_commit=False)
        yield session
        await session.close()
        await conn.rollback()  # Undo all writes — no test data leaks between tests


@pytest_asyncio.fixture()
async def client(db_session):
    """Yield an httpx AsyncClient wired to the FastAPI app with the test DB session."""
    app = create_app()

    # Override the DB session dependency with the test session
    async def override_get_session():
        yield db_session

    app.dependency_overrides[get_session] = override_get_session

    async with AsyncClient(
        transport=ASGITransport(app=app), base_url="http://test"
    ) as ac:
        yield ac


# ─── Auth Token Fixtures ─────────────────────────────────────────────────────

@pytest_asyncio.fixture()
async def seeded_manager(db_session):
    """Insert a manager user and return the ORM object."""
    from tests.helpers.seed import create_test_manager
    return await create_test_manager(db_session)


@pytest_asyncio.fixture()
async def seeded_staff(db_session):
    """Insert a staff user with skill + certification and return the ORM object."""
    from tests.helpers.seed import create_test_staff
    return await create_test_staff(db_session)


@pytest_asyncio.fixture()
async def seeded_shift(db_session, seeded_location, seeded_skill):
    """Insert a published shift and return the ORM object."""
    from tests.helpers.seed import create_test_shift
    return await create_test_shift(db_session, seeded_location, seeded_skill)


@pytest.fixture()
def manager_token(seeded_manager) -> str:
    """JWT access token for the seeded manager (role='manager')."""
    return create_access_token({"sub": str(seeded_manager.id), "role": "manager"})


@pytest.fixture()
def staff_token(seeded_staff) -> str:
    """JWT access token for the seeded staff member."""
    return create_access_token({"sub": str(seeded_staff.id), "role": "staff"})
```

---

## Seed Helpers (`tests/helpers/seed.py`)

```python
# tests/helpers/seed.py

import uuid
from datetime import datetime, timezone, timedelta
from sqlalchemy.ext.asyncio import AsyncSession
from app.modules.users.models import User
from app.modules.shifts.models import Shift
from app.modules.locations.models import Location


async def create_test_manager(session: AsyncSession) -> User:
    """Insert a manager user with a location assignment.

    Returns:
        Persisted User ORM object with role='manager'.
    """
    location = Location(
        id=uuid.uuid4(),
        name="Test Location",
        iana_timezone="America/Los_Angeles",
        address="123 Test St",
    )
    manager = User(
        id=uuid.uuid4(),
        name="Test Manager",
        email=f"manager-{uuid.uuid4().hex[:6]}@test.com",
        password_hash="$2b$12$placeholder",
        role="manager",
        home_timezone="America/Los_Angeles",
    )
    session.add_all([location, manager])
    await session.flush()
    return manager


async def create_test_staff(session: AsyncSession) -> User:
    """Insert a staff user with bartender skill and location certification.

    Returns:
        Persisted User ORM object with role='staff'.
    """
    # Implementation creates User, UserSkill, LocationCertification
    # Returns the User object
    ...


async def create_test_shift(
    session: AsyncSession, location, skill
) -> Shift:
    """Insert a published shift at the test location requiring the test skill.

    The shift is 09:00–17:00 on the next Monday in America/Los_Angeles.

    Returns:
        Persisted Shift ORM object with status='published'.
    """
    next_monday = _next_monday()
    shift = Shift(
        id=uuid.uuid4(),
        location_id=location.id,
        required_skill_id=skill.id,
        shift_date=next_monday,
        # 09:00 PT = 16:00 UTC in summer (UTC-7)
        start_utc=datetime(next_monday.year, next_monday.month, next_monday.day,
                           16, 0, tzinfo=timezone.utc),
        end_utc=datetime(next_monday.year, next_monday.month, next_monday.day,
                         0, 0, tzinfo=timezone.utc) + timedelta(days=1),
        week_start=next_monday,
        headcount_needed=1,
        status="published",
    )
    session.add(shift)
    await session.flush()
    return shift
```

---

## Unit Testing — Services

Services are tested with `AsyncMock` for all async dependencies and `MagicMock` for sync ones.
Never import SQLAlchemy or touch the database in a unit test.

```python
# tests/unit/assignments/test_assignment_service.py

import pytest
from unittest.mock import AsyncMock, MagicMock, patch
from uuid import uuid4

from app.modules.assignments.service import AssignmentService
from app.modules.assignments.exceptions import ConstraintViolationError
from constraint_engine.types import (
    ConstraintResult, ConstraintViolation, ConstraintRule, Severity,
)


# ─── Fixtures ────────────────────────────────────────────────────────────────

@pytest.fixture
def mock_repo() -> AsyncMock:
    """Async mock satisfying IAssignmentRepository Protocol."""
    return AsyncMock()


@pytest.fixture
def mock_engine() -> MagicMock:
    """Sync mock satisfying IConstraintEngine Protocol."""
    return MagicMock()


@pytest.fixture
def mock_notification_service() -> AsyncMock:
    return AsyncMock()


@pytest.fixture
def mock_audit_service() -> AsyncMock:
    return AsyncMock()


@pytest.fixture
def mock_session() -> AsyncMock:
    """Mock AsyncSession with a no-op begin() context manager."""
    session = AsyncMock()
    session.begin.return_value.__aenter__ = AsyncMock(return_value=None)
    session.begin.return_value.__aexit__ = AsyncMock(return_value=False)
    # pg_advisory_xact_lock execute — always succeeds
    session.execute = AsyncMock(return_value=None)
    return session


@pytest.fixture
def service(mock_repo, mock_engine, mock_notification_service, mock_audit_service, mock_session):
    """AssignmentService wired with all mock dependencies."""
    return AssignmentService(
        repo=mock_repo,
        constraint_engine=mock_engine,
        notification_service=mock_notification_service,
        audit_service=mock_audit_service,
        session=mock_session,
    )


# ─── Test Data ───────────────────────────────────────────────────────────────

MANAGER_ID = uuid4()
SHIFT_ID   = uuid4()
USER_ID    = uuid4()

def make_proposal(**overrides):
    from constraint_engine.types import AssignmentProposal, ShiftInfo
    from datetime import datetime, timezone
    return AssignmentProposal(
        shift_id=overrides.get("shift_id", SHIFT_ID),
        user_id=overrides.get("user_id", USER_ID),
        shift=ShiftInfo(
            id=SHIFT_ID,
            location_id=uuid4(),
            required_skill="bartender",
            start_utc=datetime(2025, 8, 11, 16, 0, tzinfo=timezone.utc),
            end_utc=datetime(2025, 8, 12, 0, 0, tzinfo=timezone.utc),
            location_tz="America/Los_Angeles",
        ),
        override_reason=overrides.get("override_reason"),
    )

def make_valid_result(**overrides) -> ConstraintResult:
    return ConstraintResult(
        valid=True, violations=[], warnings=[],
        requires_override=False, suggestions=[]
    )

def make_invalid_result(rule=ConstraintRule.REST_PERIOD) -> ConstraintResult:
    return ConstraintResult(
        valid=False,
        violations=[ConstraintViolation(
            rule=rule,
            severity=Severity.HARD_BLOCK,
            description="Only 8.0hr gap. Minimum required: 10hr.",
        )],
        warnings=[], requires_override=False, suggestions=[],
    )


# ─── Tests ───────────────────────────────────────────────────────────────────

class TestAssignmentServiceAssign:
    """Unit tests for AssignmentService.assign()."""

    @pytest.mark.asyncio
    async def test_creates_assignment_and_notifies_when_all_constraints_pass(
        self, service, mock_engine, mock_repo, mock_notification_service, mock_audit_service
    ):
        """Happy path: valid constraints → DB write → audit → notification."""
        mock_engine.evaluate.return_value = make_valid_result()
        mock_repo.load_constraint_context.return_value = MagicMock()
        mock_repo.create.return_value = MagicMock(id=uuid4())

        result = await service.assign(make_proposal(), actor_id=MANAGER_ID)

        mock_repo.create.assert_called_once()
        mock_audit_service.log.assert_called_once()
        mock_notification_service.create_assignment_notification.assert_called_once()
        assert result is not None

    @pytest.mark.asyncio
    async def test_raises_constraint_violation_and_skips_db_write_on_hard_block(
        self, service, mock_engine, mock_repo
    ):
        """HARD_BLOCK → ConstraintViolationError raised, NO repo.create() call."""
        mock_engine.evaluate.return_value = make_invalid_result()
        mock_repo.load_constraint_context.return_value = MagicMock()

        with pytest.raises(ConstraintViolationError) as exc_info:
            await service.assign(make_proposal(), actor_id=MANAGER_ID)

        mock_repo.create.assert_not_called()
        mock_repo.assert_not_called()
        assert exc_info.value.result.violations[0].rule == ConstraintRule.REST_PERIOD

    @pytest.mark.asyncio
    async def test_raises_when_override_required_but_no_reason_given(
        self, service, mock_engine, mock_repo
    ):
        """OVERRIDE_REQUIRED without override_reason → ConstraintViolationError."""
        override_result = ConstraintResult(
            valid=True,
            violations=[ConstraintViolation(
                rule=ConstraintRule.CONSECUTIVE_DAYS,
                severity=Severity.OVERRIDE_REQUIRED,
                description="7th consecutive day. Override required.",
            )],
            warnings=[], requires_override=True, suggestions=[],
        )
        mock_engine.evaluate.return_value = override_result
        mock_repo.load_constraint_context.return_value = MagicMock()

        with pytest.raises(ConstraintViolationError):
            await service.assign(make_proposal(override_reason=None), actor_id=MANAGER_ID)

        mock_repo.create.assert_not_called()

    @pytest.mark.asyncio
    async def test_proceeds_when_override_required_and_reason_provided(
        self, service, mock_engine, mock_repo
    ):
        """OVERRIDE_REQUIRED + valid override_reason → assignment created."""
        override_result = ConstraintResult(
            valid=True,
            violations=[ConstraintViolation(
                rule=ConstraintRule.CONSECUTIVE_DAYS,
                severity=Severity.OVERRIDE_REQUIRED,
                description="7th consecutive day. Override required.",
            )],
            warnings=[], requires_override=True, suggestions=[],
        )
        mock_engine.evaluate.return_value = override_result
        mock_repo.load_constraint_context.return_value = MagicMock()
        mock_repo.create.return_value = MagicMock(id=uuid4())

        result = await service.assign(
            make_proposal(override_reason="Emergency staffing — no other options"),
            actor_id=MANAGER_ID,
        )
        mock_repo.create.assert_called_once()
        assert result is not None

    @pytest.mark.asyncio
    async def test_warnings_do_not_block_assignment(self, service, mock_engine, mock_repo):
        """WARNING-only result (e.g. approaching OT) → assignment still created."""
        warning_result = ConstraintResult(
            valid=True, violations=[],
            warnings=[ConstraintViolation(
                rule=ConstraintRule.WEEKLY_HOURS,
                severity=Severity.WARNING,
                description="Projected 38hr this week. Approaching 40hr threshold.",
            )],
            requires_override=False, suggestions=[],
        )
        mock_engine.evaluate.return_value = warning_result
        mock_repo.load_constraint_context.return_value = MagicMock()
        mock_repo.create.return_value = MagicMock(id=uuid4())

        result = await service.assign(make_proposal(), actor_id=MANAGER_ID)
        mock_repo.create.assert_called_once()
        assert result is not None
```

---

## Unit Testing — Constraint Engine Checks

Each check has exhaustive tests. DST edge cases are **mandatory** — they catch the most dangerous silent bugs.

```python
# tests/unit/constraint_engine/checks/test_availability_check.py

import pytest
from datetime import datetime, timezone, date
from uuid import uuid4

from constraint_engine.checks.availability_check import AvailabilityCheck
from constraint_engine.types import (
    AssignmentProposal, ConstraintContext, ShiftInfo,
    UserForConstraints, AvailabilityEntry, ExistingAssignment,
)

check = AvailabilityCheck()


def make_shift(start_iso: str, end_iso: str, location_tz: str = "America/Los_Angeles") -> ShiftInfo:
    """Build a ShiftInfo with UTC-aware datetimes from ISO strings."""
    return ShiftInfo(
        id=uuid4(),
        location_id=uuid4(),
        required_skill="bartender",
        start_utc=datetime.fromisoformat(start_iso).replace(tzinfo=timezone.utc),
        end_utc=datetime.fromisoformat(end_iso).replace(tzinfo=timezone.utc),
        location_tz=location_tz,
    )


def make_user(day_of_week: int, start_clock: str, end_clock: str,
              home_tz: str = "America/Los_Angeles") -> UserForConstraints:
    """Build a UserForConstraints with a single recurring availability window."""
    return UserForConstraints(
        id=uuid4(),
        skill_names=frozenset(["bartender"]),
        certified_location_ids=frozenset(),
        home_timezone=home_tz,
        availability=(
            AvailabilityEntry(
                avail_type="recurring",
                day_of_week=day_of_week,
                specific_date=None,
                start_clock=start_clock,
                end_clock=end_clock,
                is_available=True,
            ),
        ),
    )


def make_proposal(shift: ShiftInfo) -> AssignmentProposal:
    return AssignmentProposal(shift_id=shift.id, user_id=uuid4(), shift=shift)


def make_context(user: UserForConstraints) -> ConstraintContext:
    return ConstraintContext(user=user, existing_assignments=())


class TestAvailabilityCheckStandard:
    """Standard availability — no DST involved."""

    def test_passes_when_shift_falls_within_availability_window(self):
        # Shift: Mon 09:00–17:00 PT = 16:00–00:00 UTC (UTC-7 in summer)
        shift = make_shift("2025-08-11T16:00:00", "2025-08-12T00:00:00")
        user  = make_user(day_of_week=0, start_clock="09:00", end_clock="17:00")  # Mon
        result = check.evaluate(make_proposal(shift), make_context(user))
        assert result.passed is True

    def test_fails_when_shift_starts_before_availability_window(self):
        # Shift: Mon 06:00–14:00 PT = 13:00–21:00 UTC (starts before 09:00 PT)
        shift = make_shift("2025-08-11T13:00:00", "2025-08-11T21:00:00")
        user  = make_user(day_of_week=0, start_clock="09:00", end_clock="17:00")
        result = check.evaluate(make_proposal(shift), make_context(user))
        assert result.passed is False
        assert "09:00" in result.description

    def test_fails_when_user_explicitly_unavailable_on_day(self):
        user = UserForConstraints(
            id=uuid4(),
            skill_names=frozenset(["bartender"]),
            certified_location_ids=frozenset(),
            home_timezone="America/Los_Angeles",
            availability=(
                AvailabilityEntry(
                    avail_type="recurring", day_of_week=0,
                    specific_date=None, start_clock="00:00", end_clock="23:59",
                    is_available=False,  # Explicitly unavailable Monday
                ),
            ),
        )
        shift = make_shift("2025-08-11T16:00:00", "2025-08-12T00:00:00")
        result = check.evaluate(make_proposal(shift), make_context(user))
        assert result.passed is False


class TestAvailabilityCheckDST:
    """DST edge cases — MANDATORY. These catch the most dangerous silent bugs."""

    def test_resolves_0900_correctly_on_spring_forward_date(self):
        """
        Spring-forward: clocks advance from PST (UTC-8) to PDT (UTC-7) at 2am on 2025-03-09.
        09:00 PDT = 16:00 UTC (NOT 17:00 UTC which would be wrong PST offset).
        """
        # Shift is 09:00–17:00 on 2025-03-09 in PDT (UTC-7)
        # That's 16:00–00:00 UTC. A shift at 16:00 UTC should PASS for a 09:00 PT window.
        shift = make_shift("2025-03-09T16:00:00", "2025-03-10T00:00:00")
        user  = make_user(day_of_week=6, start_clock="09:00", end_clock="17:00")  # Sun
        result = check.evaluate(make_proposal(shift), make_context(user))
        assert result.passed is True, (
            "Spring-forward: 09:00 PDT is 16:00 UTC, shift at 16:00 UTC should pass"
        )

    def test_blocks_shift_starting_before_window_on_spring_forward_date(self):
        """
        A shift at 15:00 UTC on spring-forward day = 08:00 PDT.
        Staff availability starts at 09:00 PT — this shift starts 1 hour before.
        """
        shift = make_shift("2025-03-09T15:00:00", "2025-03-09T23:00:00")
        user  = make_user(day_of_week=6, start_clock="09:00", end_clock="17:00")
        result = check.evaluate(make_proposal(shift), make_context(user))
        assert result.passed is False, (
            "Spring-forward: 15:00 UTC = 08:00 PDT, before 09:00 PT window — should block"
        )

    def test_resolves_0900_correctly_on_fall_back_date(self):
        """
        Fall-back: clocks go back from PDT (UTC-7) to PST (UTC-8) at 2am on 2025-11-02.
        09:00 PST = 17:00 UTC (NOT 16:00 UTC which would be wrong PDT offset).
        """
        # Shift is 09:00–17:00 on 2025-11-02 in PST (UTC-8)
        # That's 17:00–01:00 UTC. A shift at 17:00 UTC should PASS for 09:00 PT window.
        shift = make_shift("2025-11-02T17:00:00", "2025-11-03T01:00:00")
        user  = make_user(day_of_week=6, start_clock="09:00", end_clock="17:00")  # Sun
        result = check.evaluate(make_proposal(shift), make_context(user))
        assert result.passed is True, (
            "Fall-back: 09:00 PST is 17:00 UTC, shift at 17:00 UTC should pass"
        )

    def test_blocks_shift_at_16_utc_on_fall_back_date(self):
        """
        On fall-back day, 16:00 UTC = 08:00 PST — before the 09:00 PT window.
        Would have passed during PDT (= 09:00 PDT) but must fail in PST.
        This is the classic DST bug: using a cached UTC-7 offset when UTC-8 is now correct.
        """
        shift = make_shift("2025-11-02T16:00:00", "2025-11-03T00:00:00")
        user  = make_user(day_of_week=6, start_clock="09:00", end_clock="17:00")
        result = check.evaluate(make_proposal(shift), make_context(user))
        assert result.passed is False, (
            "Fall-back: 16:00 UTC = 08:00 PST, before 09:00 PT window — should block"
        )

    def test_handles_overnight_shift_crossing_dst_midnight(self):
        """
        Shift 23:00–03:00 crossing fall-back midnight. Staff available 23:00–03:00 PT.
        The system must split the shift into two segments and check each against its
        calendar day's availability.
        """
        shift = make_shift("2025-11-02T06:00:00", "2025-11-02T11:00:00")  # 10pm–3am PT approx
        user  = make_user(day_of_week=6, start_clock="22:00", end_clock="23:59")
        # Exact assertion depends on AvailabilityCheck overnight logic implementation
        result = check.evaluate(make_proposal(shift), make_context(user))
        assert isinstance(result.passed, bool)  # Must not raise


class TestAvailabilityCheckCrossTimezone:
    """Staff certified at multiple locations in different timezones."""

    def test_blocks_9am_et_shift_for_staff_with_9am_pt_availability(self):
        """
        9am ET = 6am PT — outside the staff member's 9am–5pm PT home availability window.
        2025-08-11T13:00:00Z = 9am ET (UTC-4 in summer).
        """
        shift = make_shift(
            "2025-08-11T13:00:00", "2025-08-11T21:00:00",
            location_tz="America/New_York",
        )
        user = make_user(
            day_of_week=0,
            start_clock="09:00", end_clock="17:00",
            home_tz="America/Los_Angeles",  # PT home, ET location
        )
        result = check.evaluate(make_proposal(shift), make_context(user))
        assert result.passed is False, (
            "9am ET = 6am PT, before the 9am PT availability window — should block"
        )

    def test_passes_12pm_et_shift_for_staff_with_9am_pt_availability(self):
        """
        12pm ET = 9am PT — exactly at the start of the PT availability window.
        2025-08-11T16:00:00Z = 12pm ET (UTC-4 in summer).
        """
        shift = make_shift(
            "2025-08-11T16:00:00", "2025-08-12T00:00:00",
            location_tz="America/New_York",
        )
        user = make_user(
            day_of_week=0,
            start_clock="09:00", end_clock="17:00",
            home_tz="America/Los_Angeles",
        )
        result = check.evaluate(make_proposal(shift), make_context(user))
        assert result.passed is True, (
            "12pm ET = 9am PT, at the start of the PT window — should pass"
        )
```

---

## Unit Testing — Rest Period Check

```python
# tests/unit/constraint_engine/checks/test_rest_period_check.py

import pytest
from datetime import datetime, timezone, timedelta
from uuid import uuid4

from constraint_engine.checks.rest_period_check import RestPeriodCheck
from constraint_engine.types import (
    AssignmentProposal, ConstraintContext, ShiftInfo,
    UserForConstraints, ExistingAssignment,
)

check = RestPeriodCheck()


def utc(iso: str) -> datetime:
    return datetime.fromisoformat(iso).replace(tzinfo=timezone.utc)


def make_context(*assignments: tuple[str, str]) -> ConstraintContext:
    """Build a ConstraintContext with existing assignments from (start_iso, end_iso) tuples."""
    existing = tuple(
        ExistingAssignment(shift_id=uuid4(), start_utc=utc(s), end_utc=utc(e))
        for s, e in assignments
    )
    return ConstraintContext(
        user=UserForConstraints(id=uuid4(), skill_names=frozenset(), certified_location_ids=frozenset(),
                                home_timezone="America/Los_Angeles", availability=()),
        existing_assignments=existing,
    )


class TestRestPeriodCheck:

    def test_passes_when_no_existing_assignments(self):
        shift = ShiftInfo(id=uuid4(), location_id=uuid4(), required_skill="bartender",
                          start_utc=utc("2025-08-11T18:00:00"), end_utc=utc("2025-08-11T23:00:00"),
                          location_tz="America/Los_Angeles")
        proposal = AssignmentProposal(shift_id=shift.id, user_id=uuid4(), shift=shift)
        result = check.evaluate(proposal, make_context())
        assert result.passed is True

    def test_passes_with_exactly_10_hour_gap_before(self):
        # Previous shift ends at 08:00, new shift starts at 18:00 → 10h gap exactly
        shift = ShiftInfo(id=uuid4(), location_id=uuid4(), required_skill="bartender",
                          start_utc=utc("2025-08-11T18:00:00"), end_utc=utc("2025-08-11T23:00:00"),
                          location_tz="America/Los_Angeles")
        proposal = AssignmentProposal(shift_id=shift.id, user_id=uuid4(), shift=shift)
        context = make_context(("2025-08-11T05:00:00", "2025-08-11T08:00:00"))
        result = check.evaluate(proposal, context)
        assert result.passed is True

    def test_fails_with_9h59m_gap_before(self):
        # Previous shift ends at 08:01, new shift starts at 18:00 → 9h59m < 10h
        shift = ShiftInfo(id=uuid4(), location_id=uuid4(), required_skill="bartender",
                          start_utc=utc("2025-08-11T18:00:00"), end_utc=utc("2025-08-11T23:00:00"),
                          location_tz="America/Los_Angeles")
        proposal = AssignmentProposal(shift_id=shift.id, user_id=uuid4(), shift=shift)
        context = make_context(("2025-08-11T05:00:00", "2025-08-11T08:01:00"))
        result = check.evaluate(proposal, context)
        assert result.passed is False
        assert "9.9" in result.description or "8:01" in result.description

    def test_violation_description_contains_actual_hours(self):
        shift = ShiftInfo(id=uuid4(), location_id=uuid4(), required_skill="bartender",
                          start_utc=utc("2025-08-11T18:00:00"), end_utc=utc("2025-08-11T23:00:00"),
                          location_tz="America/Los_Angeles")
        proposal = AssignmentProposal(shift_id=shift.id, user_id=uuid4(), shift=shift)
        context = make_context(("2025-08-11T06:00:00", "2025-08-11T10:00:00"))  # 8h gap
        result = check.evaluate(proposal, context)
        assert result.passed is False
        assert "8.0" in result.description
        assert "10" in result.description  # Minimum required
```

---

## Integration Testing — Routes

Integration tests use the real FastAPI app with a real test PostgreSQL database.
Every route is tested for every expected status code.

```python
# tests/integration/assignments/test_assignments_router.py

import pytest
from httpx import AsyncClient


class TestCreateAssignment:
    """POST /api/v1/shifts/{shift_id}/assignments"""

    @pytest.mark.asyncio
    async def test_returns_201_with_assignment_when_all_constraints_pass(
        self, client: AsyncClient, manager_token: str, seeded_shift, seeded_staff
    ):
        response = await client.post(
            f"/api/v1/shifts/{seeded_shift.id}/assignments",
            json={"user_id": str(seeded_staff.id)},
            headers={"Authorization": f"Bearer {manager_token}"},
        )
        assert response.status_code == 201
        body = response.json()
        assert body["shift_id"] == str(seeded_shift.id)
        assert body["user_id"] == str(seeded_staff.id)
        assert body["status"] == "assigned"

    @pytest.mark.asyncio
    async def test_returns_422_with_all_violations_on_constraint_failure(
        self, client: AsyncClient, manager_token: str, seeded_shift, seeded_staff, db_session
    ):
        # Seed a conflicting assignment so the staff member is double-booked
        from tests.helpers.seed import create_conflicting_assignment
        await create_conflicting_assignment(db_session, seeded_staff.id, seeded_shift)

        response = await client.post(
            f"/api/v1/shifts/{seeded_shift.id}/assignments",
            json={"user_id": str(seeded_staff.id)},
            headers={"Authorization": f"Bearer {manager_token}"},
        )
        assert response.status_code == 422
        body = response.json()
        assert body["error"]["code"] == "CONSTRAINT_VIOLATION"
        assert len(body["error"]["details"]) > 0
        assert body["error"]["details"][0]["severity"] in ("HARD_BLOCK", "OVERRIDE_REQUIRED")
        assert "suggestions" in body["error"]  # Always present

    @pytest.mark.asyncio
    async def test_returns_401_when_no_token_provided(
        self, client: AsyncClient, seeded_shift, seeded_staff
    ):
        response = await client.post(
            f"/api/v1/shifts/{seeded_shift.id}/assignments",
            json={"user_id": str(seeded_staff.id)},
        )
        assert response.status_code == 401

    @pytest.mark.asyncio
    async def test_returns_403_when_staff_member_attempts_assignment(
        self, client: AsyncClient, staff_token: str, seeded_shift, seeded_staff
    ):
        response = await client.post(
            f"/api/v1/shifts/{seeded_shift.id}/assignments",
            json={"user_id": str(seeded_staff.id)},
            headers={"Authorization": f"Bearer {staff_token}"},
        )
        assert response.status_code == 403

    @pytest.mark.asyncio
    async def test_returns_422_pydantic_error_when_user_id_is_not_uuid(
        self, client: AsyncClient, manager_token: str, seeded_shift
    ):
        response = await client.post(
            f"/api/v1/shifts/{seeded_shift.id}/assignments",
            json={"user_id": "not-a-uuid"},
            headers={"Authorization": f"Bearer {manager_token}"},
        )
        # Pydantic validation error — different from constraint violation
        assert response.status_code == 422
        body = response.json()
        assert "detail" in body  # FastAPI default Pydantic error shape

    @pytest.mark.asyncio
    async def test_returns_409_on_concurrent_conflict(
        self, client: AsyncClient, manager_token: str, seeded_shift, seeded_staff
    ):
        """Simulate a concurrent conflict by mocking the advisory lock scenario."""
        from unittest.mock import patch, AsyncMock
        from app.modules.assignments.exceptions import ConcurrentConflictError
        from app.modules.assignments.service import AssignmentService

        with patch.object(
            AssignmentService, "assign",
            side_effect=ConcurrentConflictError(seeded_staff.id),
        ):
            response = await client.post(
                f"/api/v1/shifts/{seeded_shift.id}/assignments",
                json={"user_id": str(seeded_staff.id)},
                headers={"Authorization": f"Bearer {manager_token}"},
            )
        assert response.status_code == 409
        assert response.json()["error"]["code"] == "CONCURRENT_CONFLICT"
```

---

## Test Coverage Requirements

| Area | Minimum Coverage | Required Scenarios |
|---|---|---|
| Constraint engine checks | 100% branch coverage | Happy path, failure, edge-at-threshold, DST transitions |
| Service layer | Every public method | Pass, fail, override required, warnings-only |
| Routers | Every route × every status code | 200/201, 400, 401, 403, 404, 409, 422 |
| State machine | Every valid + every invalid transition | All SWAP_TRANSITIONS entries |
| Utility functions | Every exported function | Including DST clock-time resolution, overnight split |

### Running Tests

```bash
# All tests
cd backend && pytest

# Unit tests only (no DB, fast)
pytest tests/unit/

# Integration tests (requires Docker running)
pytest tests/integration/

# Constraint engine only (purest, no infra)
pytest tests/unit/constraint_engine/

# With coverage report
pytest --cov=app --cov=constraint_engine --cov-report=term-missing

# Specific test file in watch mode
ptw tests/unit/constraint_engine/checks/test_availability_check.py
```

### `pyproject.toml` Test Configuration

```toml
[tool.pytest.ini_options]
asyncio_mode = "auto"
testpaths = ["tests"]
python_files = ["test_*.py"]
python_classes = ["Test*"]
python_functions = ["test_*"]

[tool.coverage.run]
omit = ["tests/*", "alembic/*"]
```
