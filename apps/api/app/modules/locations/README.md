# Locations Module

Modular domain implementation for `locations`.

## Purpose
- Own location list/read/update/create workflows.
- Enforce role-scoped access checks for admin, manager, and staff users.
- Keep location mutation audit logging consistent.

## Public API
- `router`: FastAPI router mounted at `/api/v1/locations`.
- `list_locations_record`: service workflow for role-scoped listing.
- `get_location_record`: service workflow for location read access checks.
- `create_location_record`: service workflow for audited create.
- `update_location_record`: service workflow for audited update.

## Files
- `__init__.py`: public API boundary.
- `router.py`: thin transport orchestration.
- `service.py`: domain workflows.
- `repository.py`: persistence operations.
- `schemas.py`: schema re-exports for discoverability.
- `exceptions.py`: typed domain errors.
- `dependencies.py`: dependency wiring.

## Notes
- Legacy `app/api/routes/*` compatibility shims have been removed. Import directly from this module package.
- Keep cross-domain imports through `app.modules.locations` only.
