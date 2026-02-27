# Core Infrastructure (`app/core`)

This directory contains cross-cutting platform primitives shared by API and services.

## Responsibilities
- Application settings and configuration loading.
- Database connectivity and data access client.
- Security helpers for hashing and token encoding/decoding.
- Session store integration.

## Key Files
- `config.py`
- `database.py`
- `security.py`
- `session_store.py`

## Extension Rules
- Keep this folder framework-agnostic where possible.
- Avoid domain-specific business rules in `core`.
- Add unit tests in `tests/unit/` whenever behavior changes.
