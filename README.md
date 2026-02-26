# ShiftSync

ShiftSync is a scheduling and workforce coordination platform for multi-location hospitality teams.

This repository is a monorepo with:
- FastAPI backend (`apps/api`)
- React + Vite frontend (`apps/web`)
- PostgreSQL data model and migrations managed with Prisma (`prisma/`)

## Table of Contents
- Overview
- Current Implementation Status
- Technology Stack
- Repository Structure
- Getting Started
- Environment Configuration
- Running the System
- Operational Commands
- API Surface (Implemented)
- Smoke Testing
- Demo Accounts
- Reference Documents
- Troubleshooting

## Overview
ShiftSync supports:
- Role-based access (`admin`, `manager`, `staff`)
- Skills, certifications, and availability management
- Shift creation and weekly publishing
- Constraint-based assignment validation (8-rule engine)
- Swap/drop request workflows with manager approvals
- Real-time events (WebSocket) and in-app notifications

## Current Implementation Status
- Phase 1: Foundation API and auth implemented
- Phase 2: Constraint engine + shifts + assignments implemented
- Phase 3: Swap/drop workflows + notifications + realtime implemented
- Phase 4: Analytics (`overtime`, `fairness`, `hours distribution`, `on-duty`) + audit log APIs implemented

## Technology Stack
- Backend: Python 3.11, FastAPI, Uvicorn
- ORM and migrations: Prisma + `prisma-client-py`
- Database: PostgreSQL
- Session/cache: Redis (with in-memory fallback for local dev if Redis is unavailable)
- Frontend: React 18, TypeScript, Vite, React Query
- Auth: JWT in HttpOnly cookies

## Repository Structure
```text
ShiftSync/
  apps/
    api/                  # FastAPI service
    web/                  # React application
  prisma/                 # Prisma schema and SQL migrations
  scripts/                # Prisma and smoke-test scripts
  seed/                   # Seed script
  01_ShiftSync_PRD.md
  02_ShiftSync_System_Design.md
  03_ShiftSync_API_Architecture.md
  04_ShiftSync_Database_Architecture.md
  05_ShiftSync_Software_Dev_Plan.md
```

## Getting Started

### 1) Prerequisites
- Python 3.11+
- Node.js 18+ and npm
- PostgreSQL 15+ (or Dockerized PostgreSQL)
- Redis (optional in local development)

### 2) Install dependencies
```bash
npm install
python -m venv .venv
.venv\Scripts\activate
pip install -r apps/api/requirements.txt
```

### 3) Configure environment
Copy `.env.example` to `.env` if needed, then verify `.env.local`.

Current local defaults are set for Docker PostgreSQL on port `5434`:
```env
DATABASE_URL="postgresql://postgres:postgres@localhost:5434/shiftsync"
DIRECT_URL="postgresql://postgres:postgres@localhost:5434/shiftsync"
REDIS_URL="redis://localhost:6379/0"
```

### 4) Start database (example Docker command)
```bash
docker run --name shiftsync-db \
  -e POSTGRES_USER=postgres \
  -e POSTGRES_PASSWORD=postgres \
  -e POSTGRES_DB=shiftsync \
  -p 5434:5432 \
  -d postgres:15
```

### 5) Generate Prisma client and apply migrations
```bash
python scripts/prisma_generate.py
npm run prisma:deploy
```

### 6) Seed baseline data
```bash
python seed/seed.py
```

## Environment Configuration

Key environment variables:

| Variable | Required | Description |
|---|---|---|
| `DATABASE_URL` | Yes | PostgreSQL connection string used by Prisma |
| `DIRECT_URL` | Yes | Direct PostgreSQL URL for migrations/introspection |
| `REDIS_URL` | No | Redis URL for session store |
| `JWT_SECRET` | Yes | JWT signing secret (HS256 mode) |
| `JWT_ALGORITHM` | Yes | JWT algorithm (`HS256` by default) |
| `ACCESS_TOKEN_EXPIRE_MINUTES` | Yes | Access token lifetime |
| `TOKEN_COOKIE_NAME` | Yes | Auth cookie name |
| `FRONTEND_URL` | Yes | CORS allowlist origin |

## Running the System

Run API:
```bash
python apps/api/run.py
```

Run frontend:
```bash
npm run web:dev
```

Default local URLs:
- API: `http://localhost:8000`
- Health: `http://localhost:8000/health`
- API base: `http://localhost:8000/api/v1`
- Web: `http://localhost:5173`

## Operational Commands

| Task | Command |
|---|---|
| Generate Prisma Python client | `python scripts/prisma_generate.py` |
| Create/apply dev migration | `npm run prisma:migrate` |
| Apply existing migrations | `npm run prisma:deploy` |
| Seed baseline data | `python seed/seed.py` |
| Build frontend | `npm run web:build` |
| Run integrated API smoke checks | `python scripts/smoke_phase3.py` |

## API Surface (Implemented)

Core route groups:
- Auth: `/api/v1/auth/*`
- Users: `/api/v1/users/*`
- Locations: `/api/v1/locations/*`
- Shifts: `/api/v1/locations/{location_id}/shifts*`
- Assignments: `/api/v1/shifts/{shift_id}/assignments*`
- Swaps/Drops: `/api/v1/swap-requests*`, `/api/v1/drop-requests*`
- Notifications: `/api/v1/notifications*`
- Analytics: `/api/v1/analytics/*`, `/api/v1/on-duty`
- Audit: `/api/v1/audit-logs*`
- Realtime WebSocket: `/api/v1/ws`

## Smoke Testing

End-to-end smoke coverage is available via:
```bash
python scripts/smoke_phase3.py
```

The script verifies:
- Login/auth and role-scoped access
- Users/locations/availability APIs
- Shift and assignment flows
- Swap/drop lifecycle flows
- Notifications read/write endpoints
- WebSocket events (`schedule.published`, `assignment.conflict`, ping/pong)

Rule-level backend tests:
```bash
cd apps/api && python -m pytest -q tests/test_constraint_engine.py
```

Quality gate tracker:
- `BACKEND_QUALITY_GATES.md`

## Demo Accounts

| Role | Email | Password |
|---|---|---|
| Admin | `admin@coastaleats.com` | `Admin123!` |
| Manager | `jordan@coastaleats.com` | `Manager123!` |
| Manager | `sam@coastaleats.com` | `Manager123!` |
| Staff | `carlos@coastaleats.com` | `Staff123!` |
| Staff | `maria@coastaleats.com` | `Staff123!` |

## Reference Documents

Primary project docs at the repo root:
- `01_ShiftSync_PRD.md`
- `02_ShiftSync_System_Design.md`
- `03_ShiftSync_API_Architecture.md`
- `04_ShiftSync_Database_Architecture.md`
- `05_ShiftSync_Software_Dev_Plan.md`

## Troubleshooting

- Prisma client errors after schema changes:
  - Run `python scripts/prisma_generate.py` again.
- Migration issues:
  - Confirm `.env.local` points to the intended database.
  - Run `npm run prisma:deploy` and review output.
- Auth/session issues in local:
  - If Redis is unavailable, local in-memory session fallback is used.
  - Re-login if token/session has expired.
- Port conflicts:
  - Set `PORT` before starting API, for example: `set PORT=8010` (Windows cmd) or `$env:PORT='8010'` (PowerShell).
