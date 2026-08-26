from __future__ import annotations

from functools import lru_cache
from pathlib import Path
from typing import Literal

from pydantic import AnyHttpUrl, Field, PostgresDsn, SecretStr, field_validator, model_validator
from pydantic_settings import BaseSettings, SettingsConfigDict

REPOSITORY_ROOT = Path(__file__).resolve().parents[4]


class Settings(BaseSettings):
    """Validated runtime configuration for the API service."""

    model_config = SettingsConfigDict(
        env_file=REPOSITORY_ROOT / ".env",
        env_file_encoding="utf-8",
        env_prefix="CV_MATCHER_",
        extra="ignore",
    )

    app_env: Literal["development", "test", "staging", "production"] = "development"
    app_name: str = "CVMatcher API"
    api_v1_prefix: str = "/api/v1"
    database_url: PostgresDsn
    cors_allowed_origins: list[AnyHttpUrl] = Field(
        default_factory=lambda: [AnyHttpUrl("http://localhost:3000")]
    )
    rate_limit_requests_per_minute: int = Field(default=120, ge=1, le=10_000)
    auth_rate_limit_requests_per_minute: int = Field(default=20, ge=1, le=1_000)
    session_hmac_secret: SecretStr = Field(min_length=32)
    session_ttl_hours: int = Field(default=168, ge=1, le=24 * 31)
    max_upload_bytes: int = Field(default=10 * 1024 * 1024, ge=1_024, le=50 * 1024 * 1024)
    private_storage_root: Path = Path(".local-storage")
    log_level: Literal["DEBUG", "INFO", "WARNING", "ERROR"] = "INFO"

    @field_validator("cors_allowed_origins")
    @classmethod
    def validate_cors_origins(cls, origins: list[AnyHttpUrl]) -> list[AnyHttpUrl]:
        if not origins:
            raise ValueError("At least one explicit CORS origin is required.")
        if any(str(origin) == "*" for origin in origins):
            raise ValueError("Wildcard CORS origins are not permitted.")
        return origins

    @model_validator(mode="after")
    def validate_production_requirements(self) -> Settings:
        secret = self.session_hmac_secret.get_secret_value()
        if self.app_env == "production":
            if secret.startswith("development-only-"):
                raise ValueError("A non-development session secret is required in production.")
            if not self.secure_cookies:
                raise ValueError("Secure cookies are required in production.")
            if self.resolved_private_storage_root == (REPOSITORY_ROOT / ".local-storage").resolve():
                raise ValueError(
                    "Production requires a configured private object-storage adapter, "
                    "not local storage."
                )
        return self

    @property
    def cors_origin_strings(self) -> list[str]:
        return [str(origin).rstrip("/") for origin in self.cors_allowed_origins]

    @property
    def secure_cookies(self) -> bool:
        return self.app_env in {"staging", "production"}

    @property
    def resolved_private_storage_root(self) -> Path:
        if self.private_storage_root.is_absolute():
            return self.private_storage_root
        return (REPOSITORY_ROOT / self.private_storage_root).resolve()


@lru_cache
def get_settings() -> Settings:
    return Settings()
