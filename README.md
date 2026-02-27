<div align="center">

# ShiftSync Workforce Scheduling System

### Enterprise-Grade Scheduling for Multi-Location Hospitality Teams

[![Backend Status](https://img.shields.io/badge/Backend-Production%20Ready-brightgreen)](apps/api/)
[![Frontend Status](https://img.shields.io/badge/Frontend-Production%20Ready-brightgreen)](apps/web/)
[![Security](https://img.shields.io/badge/Security-RBAC%20%2B%20JWT-blue)](#security)
[![Realtime](https://img.shields.io/badge/Realtime-WebSocket-blue)](#core-capabilities)
[![Timezone](https://img.shields.io/badge/Timezone-UTC%20Storage-orange)](#core-capabilities)
[![License](https://img.shields.io/badge/License-Proprietary-red)](#license)

</div>

---

## About ShiftSync

ShiftSync is a production-ready workforce scheduling platform built for restaurant operations across multiple locations and time zones. It gives Admins, Managers, and Staff a single system to create schedules, enforce labor rules, manage coverage requests, and monitor fairness.

### What Is ShiftSync?

ShiftSync is an operations platform focused on high-friction scheduling workflows:
- Shift planning and publishing
- Rule-based assignment validation
- Swap and drop coverage lifecycle
- Real-time notifications and status updates
- Overtime and fairness analytics
- Auditable schedule change history

### The Problem It Solves

Hospitality teams typically face:
- Unstructured call-out coverage
- Overtime surprises from weak weekly visibility
- Unfair distribution of premium shifts
- Location-level staffing conflicts
- No central cross-location schedule view

### The ShiftSync Solution

ShiftSync addresses these with:
- Constraint-first scheduling logic
- Real-time conflict detection and event delivery
- Manager-approved swap and drop workflows
- Timezone-correct date/time handling
- Immutable audit records for schedule-affecting actions

---

## Core Capabilities

- Role-based access control (`admin`, `manager`, `staff`)
- Shift lifecycle management (`draft`, `published`, edit/unpublish flow)
- Assignment engine with 8 scheduling constraints and clear violation details
- Qualified alternative staff suggestions after assignment failures
- Swap/drop requests with explicit state transitions and manager approvals
- Real-time updates via WebSocket (schedule, swaps, conflicts, notifications)
- Overtime, on-duty, and fairness analytics
- Persistent notification center with read state tracking
- UTC storage with location-timezone display and DST-aware resolution
- Audit trail with actor/action timestamps and change snapshots

---

## Tools Used

### Backend
- Python 3.11
- FastAPI
- SQLAlchemy 2.0 (async) + `asyncpg`
- Alembic
- Redis (`redis`)
- Pydantic Settings
- `python-jose`, `passlib`, `bcrypt`
- Uvicorn

### Frontend
- React 18
- TypeScript
- Vite
- TanStack React Query
- React Router
- Axios
- Tailwind CSS

### Infrastructure
- PostgreSQL
- Redis
- Render (backend deployment blueprint in `render.yaml`)
- Vercel (frontend hosting)

### Testing and Validation
- Pytest + `pytest-asyncio`
- API smoke runner (`scripts/smoke_phase3.py`)

---

## Architecture Overview

Monorepo layout:

```text
ShiftSync/
  apps/
    api/                    # FastAPI backend service
    web/                    # React frontend application
  Docs/                     # PRD and architecture documents
  scripts/                  # Migration/smoke utilities
  seed/                     # Baseline seed data
  render.yaml               # Backend deployment blueprint
```

---

## Quick Start

### 1) Prerequisites

- Python 3.11+
- Node.js 18+ and npm
- PostgreSQL 15+
- Redis 6+

### 2) Install Dependencies

```bash
npm install
python -m venv .venv
.venv\Scripts\activate
pip install -r apps/api/requirements.txt
```

### 3) Configure Environment

Use:
- `.env.local` for local development
- `.env.production` for production values

Local example (placeholders only):

```env
APP_ENV="development"
DATABASE_URL="<POSTGRES_CONNECTION_STRING>"
DIRECT_URL="<POSTGRES_DIRECT_CONNECTION_STRING>"
REDIS_URL="<REDIS_CONNECTION_STRING>"

JWT_SECRET="<LONG_RANDOM_SECRET>"
JWT_ALGORITHM="HS256"
ACCESS_TOKEN_EXPIRE_MINUTES=480
TOKEN_COOKIE_NAME="shiftsync_token"

FRONTEND_URL="http://localhost:5173"
FRONTEND_URLS="http://localhost:5173"
CORS_ALLOWED_ORIGINS=""
COOKIE_SECURE=false
COOKIE_SAMESITE="lax"
```

Production example (placeholders only):

```env
APP_ENV="production"
DATABASE_URL="<PRODUCTION_POSTGRES_CONNECTION_STRING>"
DIRECT_URL="<PRODUCTION_POSTGRES_DIRECT_CONNECTION_STRING>"
REDIS_URL="<PRODUCTION_REDIS_CONNECTION_STRING>"

JWT_SECRET="<LONG_RANDOM_SECRET>"
JWT_ALGORITHM="HS256"
ACCESS_TOKEN_EXPIRE_MINUTES=480
TOKEN_COOKIE_NAME="shiftsync_token"

FRONTEND_URL="https://<your-frontend-domain>"
FRONTEND_URLS="https://<your-frontend-domain>"
CORS_ALLOWED_ORIGINS=""
COOKIE_SECURE=true
COOKIE_SAMESITE="none"
```

### 4) Run Migrations and Seed Data

```bash
npm run db:upgrade
python seed/seed.py
```

### 5) Start Services

```bash
python apps/api/run.py
npm run web:dev
```

Default local endpoints:
- API: `http://localhost:8000`
- Health: `http://localhost:8000/health`
- API docs: `http://localhost:8000/docs`
- Web app: `http://localhost:5173`

---

## API Endpoints Summary

Base path: `/api/v1`

- `/auth/*`
- `/users/*`
- `/locations/*`
- `/locations/{location_id}/shifts*`
- `/shifts/{shift_id}/assignments*`
- `/swap-requests*`
- `/drop-requests*`
- `/notifications*`
- `/analytics/*`
- `/on-duty`
- `/audit-logs*`
- `/ws` (WebSocket)

---

## Testing

Run backend unit/integration tests:

```bash
cd apps/api
pytest -q
```

Run end-to-end smoke coverage:

```bash
python scripts/smoke_phase3.py
```

---

## Deployment

Backend deployment is defined in `render.yaml`.
Python runtime is pinned by `.python-version` (`3.11.11`) to avoid Render defaulting to Python 3.14.

Required production environment variables (use real values in your platform, not in repo files):
- `DATABASE_URL=<PRODUCTION_POSTGRES_CONNECTION_STRING>`
- `REDIS_URL=<PRODUCTION_REDIS_CONNECTION_STRING>`
- `JWT_SECRET=<LONG_RANDOM_SECRET>`
- `FRONTEND_URL=https://<your-frontend-domain>`
- `FRONTEND_URLS=https://<your-frontend-domain>`
- `COOKIE_SECURE=true`
- `COOKIE_SAMESITE=none`

Optional one-time production seed (non-destructive):
- `INITIAL_ADMIN_EMAIL=<admin-email>`
- `INITIAL_ADMIN_PASSWORD=<strong-password-at-least-12-chars>`
- `INITIAL_ADMIN_NAME=<optional-display-name>`
- `INITIAL_ADMIN_TIMEZONE=<optional-iana-timezone>`
- `RUN_PROD_SEED_ON_DEPLOY=true` for one deploy only, then set it back to `false`

Notes:
- Startup now runs migrations, optional one-time seed gate, then Uvicorn with `--app-dir apps/api`.
- If `RUN_PROD_SEED_ON_DEPLOY` is `false`, seeding is skipped.
- You can run production seed manually from a Render Shell: `python seed/seed_production.py`

Frontend environment variable:
- `VITE_API_BASE_URL=https://<your-backend-domain>/api/v1`

---

## Security

- Server-side RBAC on protected routes
- JWT authentication with HttpOnly cookie support
- Manager access scoped to assigned locations
- Concurrency protection for conflicting assignment writes
- UTC-first datetime model with timezone-safe conversion
- Append-only audit logging for schedule-affecting operations

---

## Documentation

- `Docs/01_ShiftSync_PRD.md`
- `Docs/02_ShiftSync_System_Design.md`
- `Docs/03_ShiftSync_API_Architecture.md`
- `Docs/04_ShiftSync_Database_Architecture.md`
- `Docs/05_ShiftSync_Software_Dev_Plan.md`

---

## License

Proprietary.
