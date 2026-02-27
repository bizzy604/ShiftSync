# API Layer (`app/api`)

This folder contains the HTTP delivery layer for ShiftSync.

## Responsibilities
- Define API route registration and URL namespace composition.
- Host request-level dependencies (authentication, RBAC guards, access checks).
- Keep transport concerns in this layer and delegate domain operations to `app/modules/*`.

## Structure
- `router.py`: central `/api/v1` router composition.
- `deps.py`: FastAPI dependency helpers.

## How to Extend
1. Add/modify handlers in the target domain module under `app/modules/<domain>/router.py`.
2. Register the module router in `router.py` if adding a new module.
3. Add integration tests under `tests/integration/`.
4. Add unit tests under `tests/unit/` for extracted domain logic.
