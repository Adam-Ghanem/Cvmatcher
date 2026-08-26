from __future__ import annotations

from functools import lru_cache
from pathlib import Path
from typing import Literal

from pydantic import AnyHttpUrl, Field, PostgresDsn, field_validator
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
    log_level: Literal["DEBUG", "INFO", "WARNING", "ERROR"] = "INFO"

    @field_validator("cors_allowed_origins")
    @classmethod
    def validate_cors_origins(cls, origins: list[AnyHttpUrl]) -> list[AnyHttpUrl]:
        if not origins:
            raise ValueError("At least one explicit CORS origin is required.")
        if any(str(origin) == "*" for origin in origins):
            raise ValueError("Wildcard CORS origins are not permitted.")
        return origins

    @property
    def cors_origin_strings(self) -> list[str]:
        return [str(origin).rstrip("/") for origin in self.cors_allowed_origins]


@lru_cache
def get_settings() -> Settings:
    return Settings()
