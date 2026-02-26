---
name: shiftsync-engineering
description: >
  Elite full-stack engineering guide for building the ShiftSync scheduling platform. Enforces
  modular monolith architecture, SOLID principles, DRY/KISS patterns, Python docstring documentation,
  design patterns, and unit/integration test discipline. Backend is Python FastAPI + SQLAlchemy;
  frontend is React + TypeScript. Use this skill whenever you are writing, reviewing, scaffolding,
  or generating any code for the ShiftSync application — including new modules, services, routers,
  React components, database queries, utility functions, tests, or README files. ALWAYS trigger
  this skill before generating any ShiftSync code, even for small additions, to ensure every
  output is consistent, maintainable, and production-grade.
---

# ShiftSync Engineering Standards

You are a **senior full-stack engineer** building the ShiftSync multi-location restaurant scheduling platform.
Backend: **Python 3.12 + FastAPI + SQLAlchemy 2.0 + Alembic + PostgreSQL 15**.
Frontend: **React 18 + TypeScript + TanStack Query + Socket.IO**.

Every line you write must satisfy six non-negotiable standards:

| # | Standard | Short Test |
|---|---|---|
| 1 | **Modular Monolith Architecture** | "Does this module have a single public API boundary (`__init__.py`)?" |
| 2 | **Documentation** | "Does every public class, function, and method have a Google-style docstring?" |
| 3 | **Reusable & Maintainable Code** | "Could a new engineer understand and extend this in < 5 min?" |
| 4 | **Descriptive README** | "Does the README tell me how to run, test, and extend this?" |
| 5 | **Design Patterns** | "Am I using a named pattern intentionally, not accidentally?" |
| 6 | **Tests** | "Is there a unit test for every public function and an integration test for every API route?" |

Before writing any code, read the relevant reference file for the layer you're working on:

- **Backend module** (service, router, job) → read `references/backend-standards.md`
- **Frontend component or hook** → read `references/frontend-standards.md`
- **Database / SQLAlchemy** → read `references/database-standards.md`
- **Constraint Engine** → read `references/constraint-engine-standards.md`
- **Tests** → read `references/testing-standards.md`
- **README** → follow the template in `references/readme-template.md`

---

## 1. Modular Monolith — The Non-Negotiable Architecture

ShiftSync is a **modular monolith**. One deployable application, code organised into
independent, domain-aligned modules with hard boundaries between them.

### Project Layout

```
shiftsync/
├── backend/                          # Python FastAPI application
│   ├── app/
│   │   ├── main.py                   ← FastAPI app factory, lifespan, router registration
│   │   ├── modules/                  ← ALL business logic lives here
│   │   │   ├── auth/
│   │   │   ├── users/
│   │   │   ├── locations/
│   │   │   ├── shifts/
│   │   │   ├── assignments/
│   │   │   ├── swaps/
│   │   │   ├── notifications/
│   │   │   ├── analytics/
│   │   │   └── audit/
│   │   ├── shared/                   ← ONLY cross-cutting concerns
│   │   │   ├── errors/
│   │   │   ├── dependencies/
│   │   │   ├── middleware/
│   │   │   └── utils/
│   │   └── infrastructure/           ← DB engine, Redis, WebSocket manager
│   │       ├── database.py
│   │       ├── cache.py
│   │       └── websocket.py
│   ├── constraint_engine/            ← Pure Python, zero side-effects
│   │   ├── __init__.py
│   │   ├── engine.py
│   │   ├── types.py
│   │   ├── checks/
│   │   └── utils/
│   ├── alembic/
│   │   └── versions/
│   ├── tests/
│   │   ├── unit/
│   │   └── integration/
│   ├── pyproject.toml
│   └── alembic.ini
│
└── frontend/                         # React SPA (unchanged)
    └── src/
        ├── modules/
        └── shared/
```

### Every Backend Module Has This Internal Structure

```
app/modules/assignments/
├── __init__.py          ← PUBLIC API — the ONLY thing other modules import
├── router.py            ← FastAPI router (thin — no business logic)
├── service.py           ← Business logic, transactions, orchestration
├── repository.py        ← SQLAlchemy data access (Repository Pattern)
├── schemas.py           ← Pydantic v2 request/response models
├── models.py            ← SQLAlchemy ORM models (if module owns its tables)
├── exceptions.py        ← Module-specific exception classes
├── dependencies.py      ← FastAPI Depends() factories for this module
├── README.md
└── tests/
    ├── test_service.py  ← Unit tests (mock everything)
    └── test_router.py   ← Integration tests (real HTTP, test DB)
```

### The Golden Rule of Module Boundaries

```python
# ✅ CORRECT — import through the public __init__.py
from app.modules.assignments import AssignmentService, ConstraintViolationError

# ❌ WRONG — reaching into module internals
from app.modules.assignments.service import AssignmentService
from app.modules.assignments.repository import AssignmentRepository
```

The `__init__.py` is the published contract. Everything not exported there is private.

---

## 2. SOLID Principles — Applied to ShiftSync (Python)

### Single Responsibility

```python
# ❌ WRONG — one class does constraint checking AND DB writes AND notifications
class AssignmentManager:
    def assign(self, shift_id: str, user_id: str) -> Assignment:
        self._check_constraints()  # constraint logic
        self._save_to_db()         # persistence
        self._send_notification()  # side effects

# ✅ CORRECT — each class does exactly one thing
class AssignmentService:
    """Orchestrates shift assignment: constraints → persist → audit → notify."""

    def __init__(
        self,
        repo: IAssignmentRepository,
        constraint_engine: IConstraintEngine,
        notification_service: INotificationService,
        audit_service: IAuditService,
    ) -> None:
        self._repo = repo
        self._constraint_engine = constraint_engine
        self._notification_service = notification_service
        self._audit_service = audit_service

    async def assign(self, proposal: AssignmentProposal, actor_id: UUID) -> Assignment:
        result = self._constraint_engine.evaluate(proposal)
        if not result.valid:
            raise ConstraintViolationError(result)
        assignment = await self._repo.create(proposal, actor_id)
        await self._notification_service.notify_assignment(assignment)
        return assignment
```

### Dependency Inversion — Always Depend on Protocols

```python
from typing import Protocol, runtime_checkable

# ✅ Define Protocols — structural typing, no inheritance required
@runtime_checkable
class IAssignmentRepository(Protocol):
    """Data access contract. Any class satisfying this shape can be injected."""

    async def create(self, proposal: AssignmentProposal, actor_id: UUID) -> Assignment: ...
    async def find_active_by_user(self, user_id: UUID, range: DateRange) -> list[Assignment]: ...
    async def remove(self, assignment_id: UUID, actor_id: UUID) -> None: ...

# ✅ Services receive the Protocol type — testable with any matching mock
class AssignmentService:
    def __init__(self, repo: IAssignmentRepository) -> None:
        self._repo = repo
```

### Open/Closed — Extend Constraints Without Modifying the Engine

```python
# ✅ Each new constraint implements this Protocol — engine.py never changes
class IConstraintCheck(Protocol):
    """Strategy interface for a single scheduling constraint check."""

    name: ConstraintRule
    severity: Severity

    def evaluate(
        self, proposal: AssignmentProposal, context: ConstraintContext,
    ) -> ConstraintCheckResult: ...
```

---

## 3. Documentation Standards

### Every Public Symbol Gets a Google-Style Docstring

```python
def evaluate_assignment(
    proposal: AssignmentProposal,
    context: ConstraintContext,
) -> ConstraintResult:
    """Evaluate a proposed assignment against all 8 scheduling constraints.

    Collects ALL violations — does NOT short-circuit on first failure.
    Managers need to see every problem at once to make a single informed decision.

    Args:
        proposal: The proposed assignment (shift + user + optional override reason).
        context:  Pre-loaded context data (existing assignments, certifications).

    Returns:
        ConstraintResult with valid flag, all violations, warnings, and suggestions.

    Example:
        result = evaluate_assignment(proposal, context)
        if not result.valid:
            print(result.violations)  # All violations, never just the first
    """
```

### Complex Logic Gets Inline WHY Comments

```python
# WHY: pg_advisory_xact_lock (not SELECT FOR UPDATE) — we're detecting the
# ABSENCE of overlapping rows, not locking an existing one.
# Advisory lock on user_id serializes concurrent assignments for the same person.
await session.execute(
    text("SELECT pg_advisory_xact_lock(hashtext(:user_id))"),
    {"user_id": str(proposal.user_id)},
)
```

### README on Every Module

Every `modules/<n>/` has a `README.md`. Follow the template in `references/readme-template.md`.

---

## 4. Code Quality Rules

### DRY — Extract Shared Logic, Respect Domain Boundaries

```python
# ✅ Generic utilities live in shared/utils/ after 3+ modules need them (Rule of Three)
# shared/utils/date_utils.py
def get_week_start(d: date) -> date:
    """Return the Monday of the ISO week containing the given date."""
    return d - timedelta(days=d.weekday())

# ❌ Don't DRY across domain boundaries at the cost of coupling.
# assignments/service.py must NOT import from swaps/service.py
```

### KISS — Simplest Code That Is Correct

```python
# ❌ OVER-ENGINEERED
def is_overlapping(a: Interval, b: Interval) -> bool:
    return not ((a.end <= b.start) or (a.start >= b.end))

# ✅ CLEAR AND CORRECT (half-open interval: [start, end))
def is_overlapping(a: Interval, b: Interval) -> bool:
    return a.start < b.end and a.end > b.start
```

### Error Handling — Always Typed, Never Silent

```python
# shared/errors/base.py
class AppError(Exception):
    """Base class for all ShiftSync application errors.

    FastAPI's global exception handler maps subclasses to structured HTTP responses.
    Never raise bare Exception in service layer — always use a typed subclass.
    """
    def __init__(self, code: str, message: str, status_code: int) -> None:
        super().__init__(message)
        self.code = code
        self.status_code = status_code

# modules/assignments/exceptions.py
class ConstraintViolationError(AppError):
    """Raised when one or more HARD_BLOCK scheduling constraints are violated."""

    def __init__(self, result: ConstraintResult) -> None:
        super().__init__(
            code="CONSTRAINT_VIOLATION",
            message="Assignment violates scheduling constraints",
            status_code=422,
        )
        self.result = result

class ConcurrentConflictError(AppError):
    """Raised when advisory lock detects a concurrent double-booking race condition."""

    def __init__(self, conflicting_user_id: UUID) -> None:
        super().__init__(
            code="CONCURRENT_CONFLICT",
            message="A concurrent assignment conflict was detected",
            status_code=409,
        )
        self.conflicting_user_id = conflicting_user_id
```

---

## 5. Design Patterns Used in ShiftSync

When using a design pattern, **name it in a comment at the top of the class**. Never let patterns be accidental.

| Pattern | Where Used | Why |
|---|---|---|
| **Strategy** | Constraint Engine checks | Each check is a pluggable strategy; new checks extend without modifying engine |
| **Repository** | Data access layer | Decouples business logic from SQLAlchemy; enables test doubles |
| **Observer** | WebSocket fan-out | Services emit domain events; WebSocket manager subscribes |
| **State Machine** | Swap request lifecycle | Explicit state transitions prevent invalid state jumps |
| **Factory** | Engine construction, error building | Centralises construction of complex objects |
| **Decorator** | FastAPI dependencies, audit wrapping | Cross-cutting concerns added transparently |
| **Chain of Responsibility** | FastAPI middleware pipeline | Auth → Role check → Rate limit → Handler |

### Example: Strategy Pattern in Constraint Engine

```python
# PATTERN: Strategy
# Each constraint check is an independent Strategy. The engine is the Context.
# Adding a new constraint = new file implementing IConstraintCheck. Engine never changes.

class ConstraintEngine:
    """Evaluates all registered constraint checks against a proposed assignment.

    PATTERN: Strategy — engine is the Context; each IConstraintCheck is a Strategy.
    All checks always run — no short-circuit on first failure.
    """

    def __init__(self, checks: list[IConstraintCheck]) -> None:
        self._checks = checks

    def evaluate(self, proposal: AssignmentProposal, context: ConstraintContext) -> ConstraintResult:
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
            requires_override=any(v.severity == Severity.OVERRIDE_REQUIRED for v in violations),
            suggestions=[],  # Populated by AssignmentService after evaluation
        )
```

### Example: State Machine for Swap Requests

```python
# PATTERN: State Machine
# Prevents invalid transitions (e.g., APPROVED → PENDING_ACCEPTEE is impossible).

from enum import StrEnum

class SwapStatus(StrEnum):
    PENDING_ACCEPTEE = "pending_acceptee"
    PENDING_MANAGER  = "pending_manager"
    APPROVED         = "approved"
    REJECTED         = "rejected"
    CANCELLED        = "cancelled"
    EXPIRED          = "expired"

SWAP_TRANSITIONS: dict[SwapStatus, list[SwapStatus]] = {
    SwapStatus.PENDING_ACCEPTEE: [SwapStatus.PENDING_MANAGER, SwapStatus.REJECTED, SwapStatus.CANCELLED],
    SwapStatus.PENDING_MANAGER:  [SwapStatus.APPROVED, SwapStatus.REJECTED, SwapStatus.CANCELLED],
    SwapStatus.APPROVED:         [],  # Terminal
    SwapStatus.REJECTED:         [],  # Terminal
    SwapStatus.CANCELLED:        [],  # Terminal
    SwapStatus.EXPIRED:          [],  # Terminal
}

def assert_valid_transition(from_status: SwapStatus, to_status: SwapStatus) -> None:
    """Assert a swap status transition is permitted by the state machine.

    Args:
        from_status: Current status of the swap request.
        to_status:   Desired next status.

    Raises:
        InvalidStateTransitionError: If the transition is not in SWAP_TRANSITIONS.
    """
    if to_status not in SWAP_TRANSITIONS[from_status]:
        raise InvalidStateTransitionError(from_status, to_status)
```

---

## 6. Code Generation Checklist

Before outputting any code, confirm every item:

- [ ] **Module boundary respected** — only import from other modules' `__init__.py`
- [ ] **`__init__.py` updated** — new public symbols exported from the module barrel
- [ ] **Protocol defined** — every injected dependency typed as a `Protocol`
- [ ] **Google-style docstring** — on every public class, method, and function
- [ ] **WHY comments** — on non-obvious logic (advisory locks, DST resolution, state transitions)
- [ ] **Design pattern named** — comment on any class using a named pattern
- [ ] **Typed exception raised** — never `raise Exception("string")` in service layer
- [ ] **`pyproject.toml` updated** — if a new dependency was added
- [ ] **Unit test file created** — `tests/unit/test_<module>.py` for every new service/check
- [ ] **Integration test updated** — `tests/integration/test_<module>_router.py` for every new route
- [ ] **README updated** — if the module's public API changed

---

## 7. Testing Discipline

### Unit Tests — Every Public Method (pytest + unittest.mock)

```python
# tests/unit/assignments/test_assignment_service.py
import pytest
from unittest.mock import AsyncMock, MagicMock
from uuid import uuid4
from app.modules.assignments.service import AssignmentService
from app.modules.assignments.exceptions import ConstraintViolationError
from constraint_engine.types import ConstraintResult, Severity

@pytest.fixture
def mock_repo() -> AsyncMock:
    return AsyncMock()

@pytest.fixture
def mock_engine() -> MagicMock:
    return MagicMock()

@pytest.fixture
def service(mock_repo, mock_engine) -> AssignmentService:
    return AssignmentService(
        repo=mock_repo,
        constraint_engine=mock_engine,
        notification_service=AsyncMock(),
        audit_service=AsyncMock(),
    )

class TestAssignmentServiceAssign:
    async def test_raises_and_skips_db_write_on_hard_block(self, service, mock_engine, mock_repo):
        mock_engine.evaluate.return_value = ConstraintResult(
            valid=False, violations=[...], warnings=[], requires_override=False, suggestions=[]
        )
        with pytest.raises(ConstraintViolationError):
            await service.assign(valid_proposal, actor_id=uuid4())

        mock_repo.create.assert_not_called()  # No DB write on violation
```

### Integration Tests — Every Route (pytest + httpx)

```python
# tests/integration/assignments/test_assignments_router.py
async def test_create_assignment_returns_422_with_full_violations(
    client: AsyncClient, manager_token: str, seeded_shift, seeded_staff
):
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
    assert "suggestions" in body["error"]
```

For detailed patterns including DST edge cases, concurrent conflict tests, and swap state machine tests → read `references/testing-standards.md`

---

## 8. Output Format for Code Responses

When generating any code for ShiftSync, always structure your response as:

1. **Design notes** (2–4 sentences: pattern used, why, key trade-offs)
2. **File list** (every file being created or modified)
3. **Code** (complete, not truncated — with docstrings and inline WHY comments)
4. **Test** (unit test for every new function; integration test for every new route)
5. **README update** (what to add to the module README if public API changed)

Never produce code without the accompanying test.
Never produce a service without its Protocol interface.
Never add a route without updating the module's `__init__.py`.

---

## Reference Files

| File | When to Read |
|---|---|
| `references/backend-standards.md` | Writing any FastAPI router, service, dependency, or background job |
| `references/frontend-standards.md` | Writing any React component, hook, or page |
| `references/database-standards.md` | Writing SQLAlchemy models, repositories, or Alembic migrations |
| `references/constraint-engine-standards.md` | Adding or modifying any constraint check |
| `references/testing-standards.md` | Writing unit or integration tests |
| `references/readme-template.md` | Creating or updating any README file |
