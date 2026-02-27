from functools import lru_cache
from pathlib import Path

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict
from dotenv import load_dotenv


ROOT_DIR = Path(__file__).resolve().parents[4]
load_dotenv(ROOT_DIR / ".env", override=False)
load_dotenv(ROOT_DIR / ".env.local", override=True)


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=(ROOT_DIR / ".env.local", ROOT_DIR / ".env"),
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

    frontend_url: str = Field(default="http://localhost:5173", alias="FRONTEND_URL")
    simulated_email_log_path: str = Field(
        default=str(ROOT_DIR / "simulated_emails.log"),
        alias="SIMULATED_EMAIL_LOG_PATH",
    )


@lru_cache
def get_settings() -> Settings:
    return Settings()
