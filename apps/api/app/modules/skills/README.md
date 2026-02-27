# Skills Module

Domain module skeleton for `skills`.

## Purpose
- Provide a stable modular-monolith boundary for `skills` workflows.
- Keep routing, business logic, persistence, and schema contracts organized in one domain package.

## Files
- `__init__.py`: public API boundary.
- `router.py`: thin transport orchestration.
- `service.py`: domain workflows.
- `repository.py`: persistence operations.
- `schemas.py`: module contracts.
- `exceptions.py`: typed domain errors.
- `dependencies.py`: dependency wiring.

## Migration Note
This is a scaffold phase. Existing runtime routes continue using legacy modules until domain migration is completed.
