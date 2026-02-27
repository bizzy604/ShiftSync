# Route Modules (`app/api/routes`)

This directory contains domain-oriented route handlers.

## Current Modules
- `auth.py`, `users.py`, `locations.py`, `shifts.py`, `assignments.py`, `swaps.py`, `notifications.py`, `analytics.py`, `audit.py`, `realtime.py`, `skills.py`

## Responsibilities
- Parse request inputs and enforce access checks.
- Return response schema models.
- Delegate reusable business logic to service functions in `app/services`.

## Testing
- Route registration and API surface checks: `tests/integration/test_route_surface.py`.
- Domain route behavior tests: `tests/integration/test_*` files.
