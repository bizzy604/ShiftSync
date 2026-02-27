# Schema Layer (`app/schemas`)

Pydantic models used at API boundaries.

## Purpose
- Validate incoming request payloads.
- Shape response payloads returned by route handlers.
- Keep transport contracts explicit and typed.

## Conventions
- Use one schema file per domain (`user.py`, `shift.py`, `swap.py`, etc.).
- Keep schema classes serialization-focused; avoid business logic.
- Add field-level constraints where they protect API correctness.
- Document any custom validators with clear behavior notes.

## Testing Guidance
- Validate complex serializer/validator behavior in integration tests.
- Add unit tests for non-trivial validators when introduced.
