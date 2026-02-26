# Backend Engineering Standards
## ShiftSync — Python 3.12 + FastAPI + SQLAlchemy 2.0

---

## Module Structure (Mandatory)

Every backend module follows this exact file layout. No exceptions.

```
app/modules/assignments/
├── __init__.py          ← Public barrel — ONLY import from here across modules
├── router.py            ← FastAPI APIRouter (thin — delegates to service)
├── service.py           ← Business logic, orchestration, transaction management
├── repository.py        ← SQLAlchemy data access (Repository Pattern)
├── schemas.py           ← Pydantic v2 request/response models
├── models.py            ← SQLAlchemy ORM models (if module owns its tables)
├── exceptions.py        ← Module-specific exception classes
├── dependencies.py      ← FastAPI Depends() factories for this module
├── README.md
└── tests/
    ├── test_service.py  ← Unit tests (mock everything via AsyncMock)
    └── test_router.py   ← Integration tests (real HTTP via AsyncClient)
```

---

## Layer Responsibilities

### Router Layer — Thin HTTP Shell

Routers do exactly four things:
1. Declare the endpoint path, method, and response model
2. Unpack path/query/body parameters (Pydantic handles validation automatically)
3. Call the service method
4. Return the response with the correct status code

```python
# modules/assignments/router.py

from uuid import UUID
from fastapi import APIRouter, Depends, status
from app.modules.assignments.schemas import AssignmentCreateRequest, AssignmentResponse
from app.modules.assignments.dependencies import get_assignment_service
from app.modules.assignments.service import AssignmentService
from app.shared.dependencies import require_roles
from app.shared.schemas import CurrentUser

router = APIRouter(prefix="/shifts/{shift_id}/assignments", tags=["assignments"])


@router.post(
    "",
    response_model=AssignmentResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Create a shift assignment",
    description=(
        "Assigns a staff member to a shift after running full constraint validation. "
        "Returns 422 with all violations if any HARD_BLOCK constraint fails. "
        "Returns 409 if a concurrent assignment conflict is detected."
    ),
)
async def create_assignment(
    shift_id: UUID,
    body: AssignmentCreateRequest,
    current_user: CurrentUser = Depends(require_roles(["manager", "admin"])),
    service: AssignmentService = Depends(get_assignment_service),
) -> AssignmentResponse:
    """Create a shift assignment.

    Routers only orchestrate — zero business logic here.
    All validation, constraint checking, and DB writes happen in the service.
    """
    assignment = await service.assign(
        proposal=body.to_proposal(shift_id=shift_id),
        actor_id=current_user.id,
    )
    return AssignmentResponse.model_validate(assignment)
```

**What routers must NEVER do:**
- Contain business logic or if/else decisions
- Import SQLAlchemy models or call `session.execute()` directly
- Import from another module's internal files (only their `__init__.py`)
- Handle exceptions inline — let the global exception handler do it

---

### Service Layer — All Business Logic Lives Here

Services orchestrate: they call repositories, the constraint engine, the notification service,
and the audit service. They own transaction boundaries.

```python
# modules/assignments/service.py

import structlog
from uuid import UUID
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import text

from constraint_engine import IConstraintEngine
from app.modules.assignments.repository import IAssignmentRepository
from app.modules.assignments.exceptions import ConstraintViolationError, ConcurrentConflictError
from app.modules.assignments.schemas import AssignmentProposal
from app.modules.assignments.models import Assignment
from app.modules.notifications import INotificationService
from app.modules.audit import IAuditService

logger = structlog.get_logger(__name__)


class AssignmentService:
    """Orchestrates shift assignment creation with full constraint enforcement.

    Coordinates the constraint engine, repository, audit, and notification services.
    Owns the transaction boundary — all writes commit or roll back together.

    PATTERN: Dependency Injection via constructor.
    All dependencies are Protocols — no concrete imports except types.
    """

    def __init__(
        self,
        repo: IAssignmentRepository,
        constraint_engine: IConstraintEngine,
        notification_service: INotificationService,
        audit_service: IAuditService,
        session: AsyncSession,
    ) -> None:
        self._repo = repo
        self._constraint_engine = constraint_engine
        self._notification_service = notification_service
        self._audit_service = audit_service
        self._session = session

    async def assign(self, proposal: AssignmentProposal, actor_id: UUID) -> Assignment:
        """Create a shift assignment after running all 8 scheduling constraint checks.

        Transaction boundary: advisory lock + constraint reads + assignment insert +
        audit log insert + notification inserts all commit or roll back together.

        WebSocket events are emitted AFTER the transaction commits — never inside it.
        Emitting inside a transaction that later rolls back sends false events to clients.

        Args:
            proposal:  The proposed assignment (shift_id, user_id, optional override_reason).
            actor_id:  UUID of the manager or admin performing the assignment.

        Returns:
            The created Assignment record.

        Raises:
            ConstraintViolationError: When any HARD_BLOCK constraint check fails.
            ConcurrentConflictError:  When the advisory lock detects a race condition.
        """
        async with self._session.begin():
            # WHY: pg_advisory_xact_lock (not SELECT FOR UPDATE) because we're detecting
            # the ABSENCE of overlapping rows, not locking an existing row.
            # Advisory lock on user_id serializes concurrent assignments for the same person.
            await self._session.execute(
                text("SELECT pg_advisory_xact_lock(hashtext(:user_id))"),
                {"user_id": str(proposal.user_id)},
            )

            context = await self._repo.load_constraint_context(proposal)
            result = self._constraint_engine.evaluate(proposal, context)

            if not result.valid:
                raise ConstraintViolationError(result)

            if result.requires_override and not proposal.override_reason:
                raise ConstraintViolationError(result)

            assignment = await self._repo.create(proposal, actor_id)
            await self._audit_service.log(
                actor_id=actor_id,
                action="shift.assign",
                entity_id=assignment.id,
                after_state=assignment,
            )
            await self._notification_service.create_assignment_notification(assignment)

        # WHY: Emit WebSocket event AFTER commit, never inside the transaction.
        logger.info("assignment_created", assignment_id=str(assignment.id), user_id=str(proposal.user_id))
        return assignment
```

---

### Repository Layer — All SQLAlchemy Access Lives Here

Repositories are the only layer that imports SQLAlchemy. Services depend on Protocol interfaces.

```python
# modules/assignments/repository.py

from typing import Protocol
from uuid import UUID
from sqlalchemy.ext.asyncio import AsyncSession
from app.modules.assignments.schemas import AssignmentProposal, DateRange
from app.modules.assignments.models import Assignment
from constraint_engine.types import ConstraintContext


class IAssignmentRepository(Protocol):
    """Data access contract for the assignment module.

    PATTERN: Repository — isolates SQLAlchemy from business logic.

    Enables:
        1. Test doubles (AsyncMock) in unit tests without a real DB.
        2. Swapping SQLAlchemy for another ORM without touching the service layer.
        3. Single place to add query logging or caching.
    """

    async def load_constraint_context(self, proposal: AssignmentProposal) -> ConstraintContext:
        """Load all data needed by the constraint engine in a single round trip.

        Fetches: user certifications, skills, availability, existing assignments ±24h.

        Args:
            proposal: The proposed assignment (shift + user).
        """
        ...

    async def create(self, proposal: AssignmentProposal, actor_id: UUID) -> Assignment:
        """Insert an assignment record inside the active transaction.

        Must be called within an active SQLAlchemy session.begin() block that
        holds a pg_advisory_xact_lock on the user_id.

        Args:
            proposal:  Assignment details including shift_id, user_id, override_reason.
            actor_id:  ID of the manager or admin performing the action (for audit trail).

        Raises:
            IntegrityError: On UNIQUE constraint violation (last-resort double-booking guard).
        """
        ...

    async def find_active_by_user_and_range(
        self, user_id: UUID, date_range: DateRange
    ) -> list[Assignment]:
        """Return all active assignments for a user within a UTC half-open range [start, end).

        Used by the constraint engine for overlap detection and rest-period checks.
        """
        ...


class SQLAlchemyAssignmentRepository:
    """SQLAlchemy implementation of IAssignmentRepository.

    All queries use bound parameters (SQLAlchemy handles this by default).
    Raw SQL is only used for PostgreSQL-specific features (advisory locks, AT TIME ZONE).
    """

    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def load_constraint_context(self, proposal: AssignmentProposal) -> ConstraintContext:
        """Load all constraint-relevant data in one round trip using joinedload."""
        from sqlalchemy.orm import joinedload
        from sqlalchemy import select

        user_stmt = (
            select(User)
            .where(User.id == proposal.user_id)
            .options(
                joinedload(User.skills),
                # Active certs only — WHERE revoked_at IS NULL
                joinedload(User.location_certifications.and_(
                    LocationCertification.revoked_at.is_(None)
                )),
                joinedload(User.availability),
            )
        )
        shift_stmt = (
            select(Shift)
            .where(Shift.id == proposal.shift_id)
            .options(joinedload(Shift.location), joinedload(Shift.required_skill))
        )
        # ±24h window covers both double-booking and rest period checks
        assignments_stmt = (
            select(ShiftAssignment)
            .join(Shift)
            .where(
                ShiftAssignment.user_id == proposal.user_id,
                ShiftAssignment.status == "assigned",
                Shift.start_utc >= proposal.shift.start_utc - timedelta(hours=24),
                Shift.end_utc <= proposal.shift.end_utc + timedelta(hours=24),
            )
            .options(joinedload(ShiftAssignment.shift))
        )

        user = (await self._session.execute(user_stmt)).scalar_one()
        shift = (await self._session.execute(shift_stmt)).scalar_one()
        existing = (await self._session.execute(assignments_stmt)).scalars().all()

        return ConstraintContext(user=user, shift=shift, existing_assignments=list(existing))

    async def create(self, proposal: AssignmentProposal, actor_id: UUID) -> Assignment:
        """Insert a new assignment. IntegrityError on UNIQUE violation = last-resort guard."""
        assignment = ShiftAssignment(
            shift_id=proposal.shift_id,
            user_id=proposal.user_id,
            status="assigned",
            version=1,
            assigned_by=actor_id,
            override_reason=proposal.override_reason,
        )
        self._session.add(assignment)
        await self._session.flush()  # Flush to get the DB-assigned ID before commit
        await self._session.refresh(assignment)
        return assignment
```

---

## Pydantic v2 Schemas — Request & Response Models

All request bodies, query parameters, and response shapes are Pydantic models.

```python
# modules/assignments/schemas.py

from uuid import UUID
from datetime import datetime
from pydantic import BaseModel, Field, field_validator
from typing import Literal


class AssignmentCreateRequest(BaseModel):
    """Request body for creating a shift assignment.

    Attributes:
        user_id:         UUID of the staff member to assign.
        override_reason: Required when the assignment triggers an OVERRIDE_REQUIRED
                         constraint (e.g., 7th consecutive day, post-cutoff edit).
                         Must be 10–500 characters if provided.
    """
    user_id: UUID
    override_reason: str | None = Field(
        default=None, min_length=10, max_length=500
    )

    def to_proposal(self, shift_id: UUID) -> "AssignmentProposal":
        """Convert the request body into a domain proposal object."""
        return AssignmentProposal(
            shift_id=shift_id,
            user_id=self.user_id,
            override_reason=self.override_reason,
        )


class AssignmentResponse(BaseModel):
    """Response shape for a created or retrieved shift assignment.

    Sensitive fields (password_hash, etc.) are never included — excluded at schema level.
    """
    id: UUID
    shift_id: UUID
    user_id: UUID
    status: Literal["assigned", "swap_pending", "dropped", "removed"]
    version: int
    assigned_by: UUID
    assigned_at: datetime

    model_config = {"from_attributes": True}  # Allow from SQLAlchemy ORM objects
```

---

## FastAPI Dependencies — Dependency Injection via `Depends()`

FastAPI's `Depends()` is our dependency injection mechanism.

```python
# modules/assignments/dependencies.py

from fastapi import Depends
from sqlalchemy.ext.asyncio import AsyncSession
from app.infrastructure.database import get_session
from app.modules.assignments.service import AssignmentService
from app.modules.assignments.repository import SQLAlchemyAssignmentRepository
from constraint_engine import create_default_engine
from app.modules.notifications import get_notification_service
from app.modules.audit import get_audit_service


def get_assignment_service(
    session: AsyncSession = Depends(get_session),
) -> AssignmentService:
    """Factory that wires the AssignmentService with all concrete dependencies.

    PATTERN: Factory Method — centralises construction of the service and its dependencies.
    Each request gets a fresh service instance scoped to the request's DB session.
    """
    repo = SQLAlchemyAssignmentRepository(session)
    return AssignmentService(
        repo=repo,
        constraint_engine=create_default_engine(),
        notification_service=get_notification_service(session),
        audit_service=get_audit_service(session),
        session=session,
    )
```

---

## Global Exception Handler

```python
# app/main.py (excerpt)

from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse
from app.shared.errors import AppError

app = FastAPI()

@app.exception_handler(AppError)
async def app_error_handler(request: Request, exc: AppError) -> JSONResponse:
    """Convert all AppError subclasses to structured JSON responses.

    Response shape:
        {
          "error": {
            "code":    "CONSTRAINT_VIOLATION",
            "message": "Assignment violates scheduling constraints",
            "details": [...violations...],     # present on ConstraintViolationError
            "suggestions": [...]               # present on ConstraintViolationError
          }
        }
    """
    payload: dict = {"error": {"code": exc.code, "message": str(exc)}}

    if hasattr(exc, "result"):  # ConstraintViolationError
        payload["error"]["details"] = [v.model_dump() for v in exc.result.violations]
        payload["error"]["warnings"] = [v.model_dump() for v in exc.result.warnings]
        payload["error"]["suggestions"] = exc.result.suggestions

    return JSONResponse(status_code=exc.status_code, content=payload)
```

---

## Shared Utilities — When to Use `shared/`

The `shared/` directory is for code that is:
1. Truly generic (no business logic)
2. Used by 3 or more modules (Rule of Three before extracting)
3. Has no dependency on any module

```
shared/
├── errors/
│   └── base.py            ← AppError base class
├── dependencies/
│   ├── auth.py            ← require_roles(), get_current_user()
│   └── pagination.py      ← cursor-based pagination Depends()
├── middleware/
│   └── logging.py         ← structlog request ID injection
└── utils/
    ├── date_utils.py      ← get_week_start(), is_same_calendar_day()
    ├── tz_utils.py        ← resolve_clock_time_to_utc(), split_overnight_shift()
    └── pagination.py      ← CursorPage dataclass
```

**Never put business logic in `shared/`.** It belongs in the owning module.

---

## Background Jobs — APScheduler

Jobs live in `app/jobs/` and follow the same interface pattern.

```python
# app/jobs/swap_expiry_job.py

import structlog
from app.modules.swaps import ISwapService

logger = structlog.get_logger(__name__)


async def expire_overdue_swap_requests(swap_service: ISwapService) -> None:
    """Expire swap and drop requests that have passed their expires_at timestamp.

    Runs every 15 minutes via APScheduler.

    IMPORTANT: This job is idempotent — running it twice has no additional effect.
    The drop pickup endpoint also defensively re-checks expiry at claim time,
    providing a second expiry guard independent of this scheduled job.

    Args:
        swap_service: Injected swap service (satisfies ISwapService Protocol).
    """
    expired = await swap_service.expire_overdue_requests()
    logger.info("swap_expiry_job_complete", expired_count=len(expired))
```

---

## Logging — Structured, Never print()

```python
import structlog

logger = structlog.get_logger(__name__)

# ✅ Structured with context — queryable in log aggregation tools
logger.info("assignment_created", assignment_id=str(assignment.id), user_id=str(user_id))
logger.warning("swap_request_expired", swap_request_id=str(swap_id), expired_at=str(expires_at))
logger.error("constraint_engine_error", error=str(exc), proposal=proposal.model_dump())

# ❌ Never
print("Assignment created")
```
