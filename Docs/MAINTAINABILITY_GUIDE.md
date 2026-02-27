# ShiftSync Maintainability Guide

Last updated: 2026-02-27

## Goals
- Keep code discoverable for new engineers.
- Reduce hidden coupling across backend and frontend layers.
- Make behavior changes safe through clear contracts and tests.

## Backend Organization
- `app/api`: HTTP transport and access control only.
- `app/services`: reusable domain workflows and orchestration.
- `app/core`: infrastructure primitives (config, db client, security, sessions, errors).
- `app/schemas`: API boundary contracts.

### Backend Conventions
- Add Google-style docstrings to all public classes/functions/methods.
- Use typed exceptions (`AppError` and service-specific subclasses) for domain failures.
- Use Protocol contracts for injectable service dependencies.
- Keep named pattern annotations (`PATTERN:`) on non-trivial orchestration modules.

## Frontend Organization
- `src/main.tsx`: route map and provider composition.
- `src/lib/api`: API contracts, client, and React Query hooks.
- `src/pages`: screen-level composition grouped by role.
- `src/components`: shared UI and cross-cutting providers.

### Frontend Conventions
- Keep data-fetching and cache invalidation logic inside API hooks.
- Keep page components orchestration-focused (render + local view state).
- Add JSDoc comments to exported hooks and context/provider interfaces.
- Keep route guard behavior explicit in `main.tsx`.

## Test Structure
- `apps/api/tests/unit`: service and utility behavior tests.
- `apps/api/tests/integration`: route/module integration behavior and API surface checks.

## Documentation Hygiene
- Update folder-level README files when responsibilities change.
- Use precise examples in docs for commands developers run often.
- Prefer short, specific docs near the code they describe.
