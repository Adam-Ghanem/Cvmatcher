from __future__ import annotations

import pytest
from pydantic import ValidationError

from app.core.config import Settings


def test_settings_normalize_explicit_cors_origins() -> None:
    settings = Settings(
        database_url="postgresql://cvmatcher:cvmatcher@localhost:5432/cvmatcher",
        cors_allowed_origins=["http://localhost:3000/"],
    )

    assert settings.cors_origin_strings == ["http://localhost:3000"]


def test_production_settings_reject_local_private_storage() -> None:
    with pytest.raises(ValidationError, match="private object-storage backend"):
        Settings(
            app_env="production",
            database_url="postgresql://cvmatcher:cvmatcher@localhost:5432/cvmatcher",
            cors_allowed_origins=["https://app.cvmatcher.example"],
            session_hmac_secret="production-session-secret-that-is-at-least-thirty-two-bytes",
            private_storage_root=".local-storage",
        )


def test_settings_require_an_explicit_cors_origin() -> None:
    with pytest.raises(ValidationError, match="At least one explicit CORS origin"):
        Settings(
            database_url="postgresql://cvmatcher:cvmatcher@localhost:5432/cvmatcher",
            cors_allowed_origins=[],
        )


def test_settings_bound_non_upload_requests_and_derive_a_multipart_envelope() -> None:
    settings = Settings(
        database_url="postgresql://cvmatcher:cvmatcher@localhost:5432/cvmatcher",
        max_upload_bytes=1_024,
        max_request_body_bytes=2_048,
    )

    assert settings.max_request_body_bytes == 2_048
    assert settings.max_multipart_request_bytes == 3_072


def test_settings_reject_an_unreasonably_small_non_upload_request_limit() -> None:
    with pytest.raises(ValidationError):
        Settings(
            database_url="postgresql://cvmatcher:cvmatcher@localhost:5432/cvmatcher",
            max_request_body_bytes=1_023,
        )


@pytest.mark.parametrize("app_env", ["staging", "production"])
def test_deployment_settings_require_https_cors_origins(app_env: str) -> None:
    with pytest.raises(ValidationError, match="HTTPS CORS origins"):
        Settings(
            app_env=app_env,
            database_url="postgresql://cvmatcher:cvmatcher@localhost:5432/cvmatcher",
            cors_allowed_origins=["http://app.cvmatcher.example"],
            session_hmac_secret="production-session-secret-that-is-at-least-thirty-two-bytes",
            private_storage_root="/configured-private-storage",
            rate_limit_backend="shared",
        )


def test_staging_settings_reject_a_development_session_secret() -> None:
    with pytest.raises(ValidationError, match="non-development session secret"):
        Settings(
            app_env="staging",
            database_url="postgresql://cvmatcher:cvmatcher@localhost:5432/cvmatcher",
            cors_allowed_origins=["https://staging.cvmatcher.example"],
            session_hmac_secret="development-only-change-me-before-production-32-bytes",
        )


def test_production_settings_reject_the_local_storage_adapter_at_any_path() -> None:
    with pytest.raises(ValidationError, match="private object-storage backend"):
        Settings(
            app_env="production",
            database_url="postgresql://cvmatcher:cvmatcher@localhost:5432/cvmatcher",
            cors_allowed_origins=["https://app.cvmatcher.example"],
            session_hmac_secret="production-session-secret-that-is-at-least-thirty-two-bytes",
            private_storage_root="/configured-private-storage",
            private_storage_backend="local",
            rate_limit_backend="shared",
        )
