"""
MODULE: /apps/api/app/core/config.py

FUNCTION:
    Provides core infrastructure logic for `config` used across backend modules.

DEPENDENCIES:
    - /apps/api/alembic/env.py
    - /apps/api/app/api/deps.py
    - /apps/api/app/api/routes/auth.py
    - /apps/api/app/api/routes/realtime.py
    - /apps/api/app/core/database.py
    - /apps/api/app/core/security.py
    - /apps/api/app/main.py
    - /apps/api/app/services/email_simulator.py

IMPORTANCE:
    This module is foundational infrastructure; regressions here can cascade across the
    backend.
"""

from functools import lru_cache
import os
from pathlib import Path
from typing import Literal

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict
from dotenv import load_dotenv


ROOT_DIR = Path(__file__).resolve().parents[4]


def _resolve_active_env_file() -> Path:
    explicit = os.getenv("ENV_FILE")
    if explicit:
        env_path = Path(explicit)
        if not env_path.is_absolute():
            env_path = ROOT_DIR / env_path
        return env_path

    app_env = os.getenv("APP_ENV", "development").strip().lower()
    if app_env in {"production", "prod"}:
        return ROOT_DIR / ".env.production"
    return ROOT_DIR / ".env.local"


ACTIVE_ENV_FILE = _resolve_active_env_file()
load_dotenv(ROOT_DIR / ".env", override=False)
load_dotenv(ACTIVE_ENV_FILE, override=True)


def _parse_origins(value: str | None) -> list[str]:
    if not value:
        return []
    parsed: list[str] = []
    for item in value.split(","):
        origin = item.strip().rstrip("/")
        if origin:
            parsed.append(origin)
    return parsed


class Settings(BaseSettings):
    """Settings type."""
    model_config = SettingsConfigDict(
        env_file=(ACTIVE_ENV_FILE, ROOT_DIR / ".env"),
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore",
    )

    app_name: str = "ShiftSync API"
    app_version: str = "0.1.0"
    app_env: str = "development"

    database_url: str = Field(alias="DATABASE_URL")
    redis_url: str = Field(default="redis://localhost:6379/0", alias="REDIS_URL")

    jwt_secret: str = Field(default="change-me-in-production", alias="JWT_SECRET")
    jwt_algorithm: str = Field(default="HS256", alias="JWT_ALGORITHM")
    jwt_private_key: str | None = Field(default=None, alias="JWT_PRIVATE_KEY")
    jwt_public_key: str | None = Field(default=None, alias="JWT_PUBLIC_KEY")
    access_token_expire_minutes: int = Field(default=480, alias="ACCESS_TOKEN_EXPIRE_MINUTES")
    token_cookie_name: str = Field(default="shiftsync_token", alias="TOKEN_COOKIE_NAME")
    cookie_secure: bool = Field(default=False, alias="COOKIE_SECURE")
    cookie_samesite: Literal["lax", "strict", "none"] = Field(default="lax", alias="COOKIE_SAMESITE")

    frontend_url: str = Field(default="http://localhost:5173", alias="FRONTEND_URL")
    frontend_urls: str | None = Field(default=None, alias="FRONTEND_URLS")
    cors_allowed_origins: str | None = Field(default=None, alias="CORS_ALLOWED_ORIGINS")
    simulated_email_log_path: str = Field(
        default=str(ROOT_DIR / "simulated_emails.log"),
        alias="SIMULATED_EMAIL_LOG_PATH",
    )

    @property
    def cors_origins(self) -> list[str]:
        """Cors origins.
        
        Returns:
            List of resulting items.
        """
        origins: list[str] = []
        origins.extend(_parse_origins(self.frontend_url))
        origins.extend(_parse_origins(self.frontend_urls))
        origins.extend(_parse_origins(self.cors_allowed_origins))
        deduped: list[str] = []
        for origin in origins:
            if origin not in deduped:
                deduped.append(origin)
        return deduped


@lru_cache
def get_settings() -> Settings:
    """Get settings.
    
    Returns:
        Result typed as `Settings`.
    """
    return Settings()
