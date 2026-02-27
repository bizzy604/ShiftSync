# Swaps Module

## Purpose
The swaps module owns shift swap and drop workflows, including state transitions,
qualification checks, manager approvals, audit logs, and realtime notifications.

## Public API
Import from `app.modules.swaps` only.

- `router`: FastAPI router mounted at `/api/v1/swaps`
- Route handlers: `create_swap_request`, `accept_swap`, `approve_swap_like`, `create_drop`, etc.
- Workflow helpers: `approve_transfer`, `expire_due_drop_requests_for_worker`

## Internal Structure
- `router.py`: Thin HTTP registration only.
- `service.py`: Swap/drop state-machine orchestration.
- `schemas.py`: Request/response models re-exported for module-local imports.
- `repository.py`: Reserved for future persistence extraction.

## Runtime Dependencies
- Database client: `app.core.database.prisma`
- Constraint evaluation: `app.services.constraint_engine.evaluate_assignment`
- Audit and notifications: `app.services.audit`, `app.services.notifications`
- Drop expiry transitions: `app.services.drop_expiry`

## Validation
- `python -m pytest -q`
- `python scripts/check_module_boundaries.py`
