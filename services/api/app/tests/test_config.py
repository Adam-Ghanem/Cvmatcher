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
    with pytest.raises(ValidationError, match="private object-storage adapter"):
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
