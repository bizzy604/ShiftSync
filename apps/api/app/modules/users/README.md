# Users Module

Modular domain implementation for `users`.

## Purpose
- Own users CRUD, skill links, certifications, and availability workflows.
- Preserve existing `/users` API contracts while centralizing visibility/scope helpers.
- Keep manager-scope and clock-time validation logic reusable in domain services.

## Public API
- `router`: FastAPI router mounted at `/api/v1/users`.
- `get_manager_user_scope`: domain helper for manager-visible user ids.
- `assert_user_visible_to_actor`: domain helper for actor-target visibility checks.
- `ensure_clock`: domain helper for availability clock-time validation.

## Files
- `__init__.py`: public API boundary.
- `router.py`: thin transport orchestration.
- `service.py`: shared users-domain scope/validation helpers.
- `repository.py`: persistence operations.
- `schemas.py`: schema re-exports for discoverability.
- `exceptions.py`: typed domain errors.
- `dependencies.py`: dependency wiring.

## Notes
- Legacy `app/api/routes/*` compatibility shims have been removed. Import directly from this module package.
- Compatibility facade `app/services/user_access.py` now delegates to this module service.
