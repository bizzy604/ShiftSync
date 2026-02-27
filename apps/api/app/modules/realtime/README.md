# Realtime Module

## Purpose
The realtime module owns websocket authentication and connection orchestration for
live updates (`/api/v1/realtime/ws`).

## Public API
Import from `app.modules.realtime` only.

- `router`: FastAPI websocket router
- `websocket_endpoint`: websocket protocol handler
- `list_manager_location_ids`: repository helper for manager channel subscriptions

## Internal Structure
- `router.py`: Registers websocket path only.
- `service.py`: Session validation, token decoding, and ping/pong loop.
- `repository.py`: Persistence access for manager-location subscriptions.

## Runtime Dependencies
- Token decode: `app.core.security.decode_access_token`
- Session store: `app.state.session_store`
- Websocket manager: `app.state.ws_manager`

## Validation
- `python -m pytest -q`
- `python scripts/check_module_boundaries.py`
