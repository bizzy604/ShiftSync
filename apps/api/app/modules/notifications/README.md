# Notifications Module

Modular domain implementation for `notifications`.

## Purpose
- Own notifications listing and read-state workflows.
- Own notification preference read/update workflows.
- Preserve existing `/notifications` API contract while moving logic out of route handlers.

## Public API
- `router`: FastAPI router mounted at `/api/v1/notifications`.
- `list_notifications_record`: paginated notifications workflow.
- `mark_all_read_record`: mark-all-read workflow.
- `mark_notification_read_record`: single-notification ownership/read workflow.
- `get_preferences_record` / `update_preferences_record`: preference workflows.

## Files
- `__init__.py`: public API boundary.
- `router.py`: thin transport orchestration.
- `service.py`: domain workflows.
- `repository.py`: persistence operations.
- `schemas.py`: schema re-exports for discoverability.
- `exceptions.py`: typed domain errors.
- `dependencies.py`: dependency wiring.

## Notes
- Shared creator utility `app.services.notifications.create_notification` remains in place for other domains.
- Legacy `app/api/routes/*` compatibility shims have been removed. Import directly from this module package.
