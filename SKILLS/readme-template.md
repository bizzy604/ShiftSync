# README Template
## ShiftSync — Project, Module & Package README Standards

---

## Project-Level README (Root `README.md`)

```markdown
# ShiftSync

> Multi-location restaurant staff scheduling platform for Coastal Eats.
> Manages 4 locations, 2 time zones, 3 user roles (Admin / Manager / Staff).

---

## Quick Start

### Prerequisites

- Python 3.12+
- Node.js 20+ (frontend)
- Docker (PostgreSQL + Redis)
- [uv](https://github.com/astral-sh/uv) (Python package manager — fast)

### Setup

```bash
# Clone and enter the repo
git clone https://github.com/org/shiftsync && cd shiftsync

# Start infrastructure (PostgreSQL + Redis)
docker compose up -d

# Backend setup
cd backend
uv sync                    # Install all Python deps from pyproject.toml
uv run alembic upgrade head  # Apply all migrations
uv run python -m seed        # Seed dev data (covers all 6 evaluation scenarios)
uv run uvicorn app.main:app --reload  # API at http://localhost:8000

# Frontend setup (separate terminal)
cd frontend
npm install
npm run dev                # SPA at http://localhost:5173
```

### Login Credentials (Seeded)

| Role | Email | Password |
|---|---|---|
| Admin | admin@coastaleats.com | Admin123! |
| Manager (PT locations) | jordan@coastaleats.com | Manager123! |
| Manager (ET locations) | sam@coastaleats.com | Manager123! |
| Staff (cross-TZ certified) | carlos@coastaleats.com | Staff123! |
| Staff (near-OT) | maria@coastaleats.com | Staff123! |

---

## Project Structure

```
shiftsync/
├── backend/
│   ├── app/
│   │   ├── main.py              # FastAPI app factory and router registration
│   │   ├── modules/             # All business logic — one folder per domain
│   │   ├── shared/              # Cross-cutting utilities and middleware
│   │   └── infrastructure/      # DB engine, Redis, WebSocket manager
│   ├── constraint_engine/       # Pure Python — zero side effects
│   ├── alembic/                 # Database migrations
│   ├── tests/
│   │   ├── unit/                # No DB, AsyncMock everything
│   │   └── integration/         # Real DB, real HTTP via httpx
│   └── pyproject.toml
├── frontend/
│   └── src/
│       ├── modules/             # Feature-scoped React modules
│       └── shared/              # Generic components, hooks, utils
└── docker-compose.yml
```

---

## Running Tests

```bash
cd backend

# Full test suite
uv run pytest

# Unit tests only (no Docker required — runs in seconds)
uv run pytest tests/unit/

# Integration tests (requires Docker services running)
uv run pytest tests/integration/

# Constraint engine tests (pure Python — fastest)
uv run pytest tests/unit/constraint_engine/

# Coverage report
uv run pytest --cov=app --cov=constraint_engine --cov-report=term-missing

# Watch mode (install pytest-watch)
uv run ptw tests/unit/
```

---

## Key Design Decisions

| Decision | Rationale |
|---|---|
| **Modular monolith, not microservices** | The constraint engine requires atomic DB transactions across user, availability, and assignment data. Cross-service transactions would require distributed sagas. |
| **Clock-time availability storage** | DST-safe. Storing UTC offsets breaks on transition dates. '09:00 PT' always means 9am local — `ZoneInfo` resolves the correct UTC offset per date. |
| **`pg_advisory_xact_lock` on `user_id`** | Prevents double-booking without requiring a lockable row. Two managers assigning the same bartender: one wins, one gets a 409 + WebSocket conflict event. |
| **WebSocket events emitted after commit** | Emitting inside a transaction that later rolls back sends false schedule updates to staff clients. |
| **All constraint violations collected** | Short-circuiting on first failure forces managers into a "one fix, re-submit, find next error" loop. All violations at once = one informed decision. |
| **Pure constraint engine package** | No DB access inside the engine. Data is pre-loaded by the caller and passed as frozen dataclasses. This makes the engine 100% unit-testable without any infrastructure. |

---

## Documented Assumptions

See `docs/PRD.md` for the full list of ambiguity resolutions (AR-01–AR-06).

---

## Known Limitations

| # | Limitation |
|---|---|
| L1 | Email notifications are simulated (no SMTP — stored as DB records only) |
| L2 | On-Duty Now dashboard uses shift time windows, not biometric clock-in |
| L3 | One IANA timezone per location — locations spanning a timezone boundary not supported |
| L4 | Fairness score uses standard deviation (not weighted by location size) |

---

## Environment Variables

```bash
# backend/.env (copy from .env.example)
DATABASE_URL="postgresql+asyncpg://shiftsync:password@localhost:5432/shiftsync"
TEST_DATABASE_URL="postgresql+asyncpg://shiftsync:password@localhost:5432/shiftsync_test"
REDIS_URL="redis://localhost:6379"
SECRET_KEY="your-256-bit-secret-key-here"
ACCESS_TOKEN_EXPIRE_MINUTES=60
DEBUG=true

# frontend/.env
VITE_API_URL="http://localhost:8000"
VITE_WS_URL="ws://localhost:8000"
```

---

## API Documentation

FastAPI auto-generates interactive docs at:
- **Swagger UI**: http://localhost:8000/docs
- **ReDoc**: http://localhost:8000/redoc
- **OpenAPI JSON**: http://localhost:8000/openapi.json
```

---

## Module-Level README Template

Use this template for every `app/modules/<n>/README.md`:

```markdown
# [Module Name] Module

> One-sentence description of what this module owns and is responsible for.

---

## Responsibility

**This module owns:** [list the data and operations this module is the single authority on]

**This module does NOT:** [explicitly state what is delegated to other modules]

---

## Public API (`__init__.py` exports)

```python
# Everything importable by other modules:

from app.modules.assignments import (
    AssignmentService,           # Service class
    IAssignmentRepository,       # Protocol for DI and testing
    ConstraintViolationError,    # Module-specific exceptions
    ConcurrentConflictError,
    AssignmentCreateRequest,     # Pydantic schemas
    AssignmentResponse,
    assignment_router,           # FastAPI APIRouter, registered in main.py
)
```

Other modules MUST NOT import from internal files like `service.py`, `repository.py`, etc.

---

## Key Design Decisions

| Decision | Why |
|---|---|
| Constraint engine called inside `session.begin()` | Constraint reads and the assignment write are atomic. Running the engine outside the transaction opens a race window between "check" and "write". |
| `pg_advisory_xact_lock` on `user_id` | Advisory locks prevent concurrent double-booking without requiring a lockable row to exist. See `references/database-standards.md`. |
| WebSocket events emitted after `session.begin()` exits | Avoids sending schedule update events for transactions that subsequently roll back. |
| Repository Protocol instead of concrete class | Services unit-test with `AsyncMock` without needing a real DB. The concrete `SQLAlchemyAssignmentRepository` only wires in via `Depends()`. |

---

## Running Tests

```bash
# Unit tests for this module (no DB)
uv run pytest tests/unit/assignments/ -v

# Integration tests for this module (requires Docker)
uv run pytest tests/integration/assignments/ -v

# With coverage for this module only
uv run pytest tests/unit/assignments/ --cov=app/modules/assignments --cov-report=term-missing
```

---

## Module Dependencies

**Imports FROM** (other modules this module depends on):
- `app.shared.errors` — `AppError` base class
- `app.shared.utils.date_utils` — calendar day helpers
- `constraint_engine` — pure constraint evaluation
- `app.modules.notifications` — via `INotificationService` Protocol only
- `app.modules.audit` — via `IAuditService` Protocol only

**Does NOT import from:** `app.modules.shifts.service`, `app.modules.swaps.*`, `app.modules.analytics.*`
(avoids circular dependencies)
```

---

## Constraint Engine README (`constraint_engine/README.md`)

```markdown
# constraint_engine

> Pure Python scheduling constraint evaluation library.
> Zero side effects. Zero database access. 100% unit-testable without any infrastructure.

---

## What It Does

Evaluates whether a proposed shift assignment satisfies all 8 scheduling constraints:

1. **Skill match** — Staff has the required skill
2. **Location certification** — Staff is certified at the location (revoked_at IS NULL)
3. **Availability** — Shift falls within staff's availability window (DST-safe)
4. **No double-booking** — Staff not already assigned to an overlapping shift
5. **Rest period** — At least 10 hours between consecutive shifts (HARD_BLOCK)
6. **Daily hours** — Below 8h (warning) or 12h (HARD_BLOCK) on the shift calendar day
7. **Weekly hours** — Below 35h (warning) for the Mon–Sun week
8. **Consecutive days** — Fewer than 6 consecutive days (warning), 7th requires OVERRIDE_REQUIRED

**All 8 checks always run. No short-circuit on first failure.**

---

## Usage

```python
from constraint_engine import create_default_engine
from constraint_engine.types import AssignmentProposal, ConstraintContext

engine = create_default_engine()
result = engine.evaluate(proposal, context)

if not result.valid:
    print(result.violations)
    # [ConstraintViolation(rule='REST_PERIOD', severity='HARD_BLOCK',
    #   description='Only 8.0hr gap. Minimum required: 10hr.')]

if result.warnings:
    print(result.warnings)  # Non-blocking — shown to manager but assignment proceeds

if result.requires_override:
    # Manager must provide override_reason in the proposal
    pass
```

---

## Adding a New Constraint

1. Create `constraint_engine/checks/your_check.py` implementing `IConstraintCheck`
2. Add tests in `tests/unit/constraint_engine/checks/test_your_check.py`
   - Include happy path, failure, and edge cases at threshold
3. Register the check in `create_default_engine()` inside `engine.py`
4. Update this README with the new constraint entry

The engine itself never changes — this is the Open/Closed Principle in practice.

---

## Running Tests

```bash
# From the backend/ directory:

# All constraint engine tests
uv run pytest tests/unit/constraint_engine/ -v

# Specific check
uv run pytest tests/unit/constraint_engine/checks/test_availability_check.py -v

# With coverage (target: 100% branch coverage)
uv run pytest tests/unit/constraint_engine/ --cov=constraint_engine --cov-branch --cov-report=term-missing
```
```
