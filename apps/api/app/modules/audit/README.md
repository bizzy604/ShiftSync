# Audit Module

Modular domain implementation for `audit`.

## Purpose
- Own audit-log list and export workflows.
- Centralize audit query filters and manager scope handling.
- Keep CSV export transport logic thin by delegating query/filter preparation to services.

## Public API
- `router`: FastAPI router mounted at `/api/v1/audit`.
- `list_audit_logs_record`: paginated audit-log query workflow.
- `export_audit_logs_record`: audit-log export query workflow.

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
- Manager scope enforcement still uses shared dependency helper `ensure_manager_location_access`.
