# Assignments Module

Modular domain implementation for `assignments`.

## Purpose
- Own assignment workflows: list/preview/suggest/create/delete and personal assignment view.
- Preserve constraint-evaluation, conflict, and overtime-warning behavior.
- Keep legacy `/assignments` API contracts stable while routing through module boundaries.

## Public API
- `router`: FastAPI router mounted at `/api/v1/assignments`.
- `_weekly_hours_warning`: helper for overtime-warning selection.
- `_create_overtime_warning_notifications`: helper for manager overtime alerts.

## Files
- `__init__.py`: public API boundary.
- `router.py`: thin route registration that delegates to service handlers.
- `service.py`: assignment workflow orchestration, constraint checks, conflicts, and locking.
- `repository.py`: persistence boundary scaffold for continued extraction.
- `schemas.py`: module schema boundary.
- `exceptions.py`: typed domain errors.
- `dependencies.py`: dependency wiring.

## Notes
- Legacy `app/api/routes/*` compatibility shims have been removed. Import directly from this module package.
