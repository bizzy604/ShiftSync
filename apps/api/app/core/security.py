"""
MODULE: /apps/api/app/core/security.py

FUNCTION:
    Provides core infrastructure logic for `security` used across backend modules.

DEPENDENCIES:
    - /apps/api/app/api/deps.py
    - /apps/api/app/api/routes/auth.py
    - /apps/api/app/api/routes/realtime.py
    - /apps/api/app/api/routes/users.py

IMPORTANCE:
    This module is foundational infrastructure; regressions here can cascade across the
    backend.
"""

from datetime import datetime, timedelta, timezone
from uuid import uuid4

from jose import JWTError, jwt
from passlib.context import CryptContext

from app.core.config import get_settings


pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")


def hash_password(password: str) -> str:
    """Hash password.
    
    Args:
        password: Input parameter `password` used by this operation.
    
    Returns:
        Result typed as `str`.
    """
    return pwd_context.hash(password)


def verify_password(plain_password: str, hashed_password: str) -> bool:
    """Verify password.
    
    Args:
        plain_password: Input parameter `plain_password` used by this operation.
        hashed_password: Input parameter `hashed_password` used by this operation.
    
    Returns:
        True when the operation succeeds, otherwise False.
    """
    return pwd_context.verify(plain_password, hashed_password)


def create_access_token(
    user_id: str,
    role: str,
    location_ids: list[str],
    session_id: str | None = None,
    expires_delta: timedelta | None = None,
) -> tuple[str, str, datetime]:
    """Create access token.
    
    Args:
        user_id: Target user identifier.
        role: Input parameter `role` used by this operation.
        location_ids: Input parameter `location_ids` used by this operation.
        session_id: Identifier for the target resource.
        expires_delta: Input parameter `expires_delta` used by this operation.
    
    Returns:
        Result typed as `tuple[str, str, datetime]`.
    """
    settings = get_settings()
    now = datetime.now(tz=timezone.utc)
    ttl = expires_delta or timedelta(minutes=settings.access_token_expire_minutes)
    expires_at = now + ttl
    sid = session_id or str(uuid4())

    payload = {
        "sub": user_id,
        "role": role,
        "location_ids": location_ids,
        "sid": sid,
        "iat": int(now.timestamp()),
        "exp": int(expires_at.timestamp()),
    }
    signing_key = _get_signing_key()
    token = jwt.encode(payload, signing_key, algorithm=settings.jwt_algorithm)
    return token, sid, expires_at


def decode_access_token(token: str) -> dict:
    """Decode access token.
    
    Args:
        token: Encoded JWT access token.
    
    Returns:
        Structured dictionary result.
    """
    settings = get_settings()
    try:
        verification_key = _get_verification_key()
        return jwt.decode(token, verification_key, algorithms=[settings.jwt_algorithm])
    except JWTError as exc:
        raise ValueError("Invalid token") from exc


def _get_signing_key() -> str:
    settings = get_settings()
    if settings.jwt_algorithm.startswith("RS"):
        if not settings.jwt_private_key:
            raise RuntimeError("JWT_PRIVATE_KEY must be set when using RSA JWT algorithms.")
        return settings.jwt_private_key
    return settings.jwt_secret


def _get_verification_key() -> str:
    settings = get_settings()
    if settings.jwt_algorithm.startswith("RS"):
        if settings.jwt_public_key:
            return settings.jwt_public_key
        if settings.jwt_private_key:
            # Fallback for local development where only private key is provided.
            return settings.jwt_private_key
        raise RuntimeError("JWT_PUBLIC_KEY or JWT_PRIVATE_KEY must be set when using RSA JWT algorithms.")
    return settings.jwt_secret
