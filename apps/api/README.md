# ShiftSync Backend API

FastAPI-based REST API for the ShiftSync multi-location restaurant scheduling platform.

## Tech Stack

- **Framework:** FastAPI 0.116.1
- **Language:** Python 3.11+
- **Database:** PostgreSQL 15+ (via SQLAlchemy 2.0 + asyncpg)
- **Cache/Sessions:** Redis 6.4+
- **ORM:** SQLAlchemy 2.0 (async)
- **Migrations:** Alembic 1.14
- **Authentication:** JWT (python-jose)
- **Password Hashing:** bcrypt (passlib)
- **WebSocket:** FastAPI WebSocket (for real-time updates)
- **Validation:** Pydantic v2

## Prerequisites

- Python 3.11 or higher
- PostgreSQL 15+ (running and accessible)
- Redis 6.4+ (running and accessible)
- Virtual environment (recommended)

## Installation

1. **Navigate to the backend directory:**
   ```bash
   cd apps/api
   ```

2. **Create and activate a virtual environment:**
   ```bash
   python -m venv .venv
   # Windows
   .venv\Scripts\activate
   # Linux/Mac
   source .venv/bin/activate
   ```

3. **Install dependencies:**
   ```bash
   pip install -r requirements.txt
   ```

## Configuration

1. **Copy the example environment file:**
   ```bash
   # From project root
   cp .env.example .env
   # Or create .env.local for local overrides
   ```

2. **Configure environment variables** in `.env` or `.env.local` (in project root):

   ```env
   # Database (required)
   DATABASE_URL="postgresql://postgres:postgres@localhost:5432/shiftsync"
   
   # Redis (required)
   REDIS_URL="redis://localhost:6379/0"
   
   # JWT (required)
   JWT_SECRET="change-me-in-production"
   JWT_ALGORITHM="HS256"
   
   # Optional JWT (for RS256)
   JWT_PRIVATE_KEY=""
   JWT_PUBLIC_KEY=""
   
   # Token settings
   ACCESS_TOKEN_EXPIRE_MINUTES=480
   TOKEN_COOKIE_NAME="shiftsync_token"
   
   # Frontend URL (for CORS)
   FRONTEND_URL="http://localhost:5173"
   ```

3. **Create the PostgreSQL database:**
   ```sql
   CREATE DATABASE shiftsync;
   ```

## Database Migrations

This project uses **Alembic** for database migrations.

### Running Migrations

```bash
# From apps/api directory
alembic upgrade head
```

### Creating a New Migration

```bash
# Generate a new migration from model changes
alembic revision --autogenerate -m "description of changes"

# Review the generated migration file in alembic/versions/
# Then apply it:
alembic upgrade head
```

### Migration Commands

```bash
# Show current revision
alembic current

# Show migration history
alembic history

# Downgrade one revision
alembic downgrade -1

# Upgrade to specific revision
alembic upgrade <revision_id>
```

**Note:** The `alembic.ini` file uses `DATABASE_URL` from your `.env` file automatically via `app.core.config`.

## Running the Server

### Development (with auto-reload)

```bash
# From apps/api directory
python -m uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```

Or use the convenience script:

```bash
python run.py
```

With environment variables:

```bash
# Enable reload
set UVICORN_RELOAD=true
set PORT=8000
python run.py
```

### Production

```bash
uvicorn app.main:app --host 0.0.0.0 --port 8000 --workers 4
```

## API Documentation

Once the server is running, access the interactive API documentation:

- **Swagger UI:** http://localhost:8000/docs
- **ReDoc:** http://localhost:8000/redoc
- **OpenAPI JSON:** http://localhost:8000/openapi.json

## Health Check

```bash
curl http://localhost:8000/health
```

Response:
```json
{"status": "ok"}
```

## API Endpoints

All API routes are prefixed with `/api/v1`:

- `/api/v1/auth` - Authentication (login, logout, refresh)
- `/api/v1/users` - User management (CRUD, skills, certifications, availability)
- `/api/v1/locations` - Location management
- `/api/v1/shifts` - Shift CRUD, publish/unpublish
- `/api/v1/assignments` - Shift assignments with constraint validation
- `/api/v1/swaps` - Swap and drop request management
- `/api/v1/notifications` - User notifications
- `/api/v1/analytics` - Overtime dashboard, fairness reports, on-duty view
- `/api/v1/audit` - Audit log viewing and CSV export
- `/api/v1/realtime` - WebSocket endpoint (`/ws`)

## Testing

Run tests with pytest:

```bash
# From apps/api directory
pytest

# With coverage
pytest --cov=app --cov-report=html

# Specific test file
pytest tests/test_constraint_engine.py

# Verbose output
pytest -v
```

## Project Structure

```
apps/api/
├── app/
│   ├── main.py              # FastAPI app factory, lifespan, middleware
│   ├── api/
│   │   ├── router.py        # Main API router
│   │   ├── deps.py          # FastAPI dependencies (auth, RBAC)
│   │   └── routes/          # Route handlers (thin layer)
│   │       ├── auth.py
│   │       ├── users.py
│   │       ├── locations.py
│   │       ├── shifts.py
│   │       ├── assignments.py
│   │       ├── swaps.py
│   │       ├── notifications.py
│   │       ├── analytics.py
│   │       ├── audit.py
│   │       └── realtime.py
│   ├── core/
│   │   ├── config.py        # Settings (Pydantic)
│   │   ├── database.py      # SQLAlchemy engine, Prisma-like facade
│   │   ├── db_base.py       # Declarative base
│   │   ├── models.py        # SQLAlchemy ORM models
│   │   ├── security.py      # JWT encoding/decoding, password hashing
│   │   └── session_store.py # Redis session management
│   ├── schemas/             # Pydantic request/response models
│   │   ├── auth.py
│   │   ├── user.py
│   │   ├── location.py
│   │   ├── shift.py
│   │   ├── assignment.py
│   │   ├── swap.py
│   │   ├── notification.py
│   │   ├── analytics.py
│   │   └── audit.py
│   └── services/            # Business logic layer
│       ├── constraint_engine.py    # 8 scheduling constraint checks
│       ├── assignment_lock.py      # Concurrent assignment prevention
│       ├── drop_expiry_worker.py    # Background job for drop expiry
│       ├── realtime.py              # WebSocket manager
│       ├── notifications.py         # Notification creation
│       ├── audit.py                 # Audit log creation
│       ├── user_access.py           # RBAC helpers
│       └── timezone_utils.py        # DST-safe timezone utilities
├── alembic/                 # Database migrations
│   ├── versions/
│   └── env.py
├── alembic.ini              # Alembic configuration
├── tests/                   # Test suite
│   └── test_constraint_engine.py
├── requirements.txt         # Python dependencies
├── run.py                  # Convenience script to run server
└── README.md               # This file
```

## Key Features

### 1. Constraint Engine
- **8 scheduling constraints** enforced on every assignment:
  - Skill match
  - Location certification
  - Availability (DST-safe)
  - Double-booking prevention
  - Rest period (10-hour minimum)
  - Daily hours limits
  - Weekly hours warnings
  - Consecutive days limits
- Returns **all violations** (no short-circuit) with human-readable messages
- Provides **suggestions** for alternative staff members

### 2. Real-Time Updates
- WebSocket support for live schedule updates
- Events: `schedule.published`, `assignment.changed`, `swap.status_changed`, `notification.new`, `assignment.conflict`
- Location-based room subscriptions for managers

### 3. Concurrent Assignment Protection
- PostgreSQL advisory locks prevent race conditions
- Returns HTTP 409 Conflict with conflict details when detected

### 4. Audit Logging
- Every mutation (create/update/delete) is logged
- Includes before/after state, actor, reason, timestamp
- CSV export available for admin users

### 5. Swap/Drop Workflow
- State machine: OPEN → PENDING_MANAGER → APPROVED/REJECTED
- Max 3 pending requests per staff member
- Drop requests expire 24 hours before shift start
- Background worker automatically expires drops

### 6. Analytics
- Overtime dashboard (projected weekly hours per staff)
- Fairness report (premium shift distribution, fairness score)
- Hours distribution (date range analysis)
- On-duty view (current active staff per location)

## Authentication & Authorization

- **JWT-based** authentication (HS256 or RS256)
- **Role-based access control:** `admin`, `manager`, `staff`
- **Location scoping:** Managers can only access their assigned locations
- **Session storage:** Redis-backed session store

## Error Handling

All errors follow a consistent format:

```json
{
  "error": {
    "code": "ERROR_CODE",
    "message": "Human-readable message",
    "details": [...],  // Optional: constraint violations, etc.
    "suggestions": [...]  // Optional: alternative actions
  }
}
```

## Development Notes

- **Database access:** Uses a Prisma-like facade (`prisma` object) over SQLAlchemy for easier migration from Prisma-style code
- **Async/await:** All database operations are async
- **Transactions:** Use `prisma.tx()` context manager for multi-step operations
- **Timezone handling:** All times stored as UTC; conversion happens at API boundary using DST-safe utilities

## Troubleshooting

### Database Connection Error

```
OSError: Connect call failed ('127.0.0.1', 5432)
```

**Solution:** Ensure PostgreSQL is running and `DATABASE_URL` in `.env` is correct.

### Redis Connection Error

**Solution:** Ensure Redis is running and `REDIS_URL` in `.env` is correct.

### Module Not Found

**Solution:** Ensure you're running commands from `apps/api` directory and virtual environment is activated.

### Migration Errors

**Solution:** Ensure database exists and `DATABASE_URL` is correct. Check Alembic version history with `alembic current`.

## License

[Your License Here]
