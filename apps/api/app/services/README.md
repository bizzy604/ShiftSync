# Service Layer (`app/services`)

This folder hosts reusable backend domain services and workflow helpers.

## Responsibilities
- Constraint evaluation and scheduling domain logic.
- Notification orchestration.
- Audit helper functions.
- Timezone and lifecycle support utilities.

## Current Service Modules
- `constraint_engine.py`
- `notifications.py`
- `audit.py`
- `swap_lifecycle.py`
- `drop_expiry.py`
- `drop_expiry_worker.py`
- `timezone_utils.py`
- `assignment_lock.py`
- `realtime.py`
- `email_simulator.py`
- `user_access.py`

## Testing
- Service-focused tests live in `tests/unit/`.
- API behavior using these services is validated in `tests/integration/`.
