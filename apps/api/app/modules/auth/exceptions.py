"""
MODULE: /apps/api/app/modules/auth/exceptions.py

FUNCTION:
    Defines typed domain exceptions for authentication workflows.

DEPENDENCIES:
    - /apps/api/app/modules/auth/router.py
    - /apps/api/app/modules/auth/service.py

IMPORTANCE:
    Typed exceptions keep auth failure semantics explicit while routes map them to
    stable HTTP contracts.
"""


class InvalidCredentialsError(Exception):
    """Raised when login credentials fail verification."""


class AuthenticationRequiredError(Exception):
    """Raised when an auth workflow requires a token but none is provided."""


class InvalidTokenError(Exception):
    """Raised when token decoding or token payload validation fails."""


class SessionExpiredError(Exception):
    """Raised when server-side session state is missing or expired."""


class AuthUserNotFoundError(Exception):
    """Raised when authenticated principal cannot be loaded from persistence."""

