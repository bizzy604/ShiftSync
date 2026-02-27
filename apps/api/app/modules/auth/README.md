# Auth Module

Modular domain implementation for `auth`.

## Purpose
- Own login/logout/refresh/me authentication workflows.
- Preserve cookie + session semantics while centralizing token/session logic.
- Keep route layer thin and session-token orchestration in service/repository layers.

## Public API
- `router`: FastAPI router mounted at `/api/v1/auth`.
- `login_record`: authenticate credentials and issue session-backed token payload.
- `logout_record`: invalidate server-side session for presented token.
- `refresh_token_record`: rotate token/session pair.
- `get_me_record`: fetch authenticated principal profile payload.

## Files
- `__init__.py`: public API boundary.
- `router.py`: thin transport orchestration.
- `service.py`: domain workflows.
- `repository.py`: persistence operations.
- `schemas.py`: schema re-exports for discoverability.
- `exceptions.py`: typed domain errors.
- `dependencies.py`: dependency wiring.

## Notes
- Shared auth/session dependency helpers live in `app/shared/dependencies/auth.py`.
- Legacy `app/api/routes/*` compatibility shims have been removed. Import directly from this module package.
