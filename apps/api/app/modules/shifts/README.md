# Shifts Module

Modular domain implementation for `shifts`.

## Purpose
- Own shift scheduling workflows: list/create/get/update/delete/publish/unpublish.
- Preserve real-time schedule events and notification side effects.
- Keep legacy `/shifts` API contracts stable while routing through module boundaries.

## Public API
- `router`: FastAPI router mounted at `/api/v1/shifts`.
- `_prune_past_unclaimed_shifts`: helper used in scheduling visibility and regression tests.

## Files
- `__init__.py`: public API boundary.
- `router.py`: thin route registration that delegates to service handlers.
- `service.py`: scheduling workflow orchestration and transactional side effects.
- `repository.py`: persistence boundary scaffold for continued extraction.
- `schemas.py`: module schema boundary.
- `exceptions.py`: typed domain errors.
- `dependencies.py`: dependency wiring.

## Notes
- Legacy `app/api/routes/*` compatibility shims have been removed. Import directly from this module package.
