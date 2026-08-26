from __future__ import annotations

import os
from collections.abc import Iterator
from pathlib import Path

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient
from sqlalchemy import create_engine, text

TEST_DATABASE_URL = "postgresql://cvmatcher:cvmatcher@localhost:5432/cvmatcher_test"
TEST_SESSION_SECRET = "test-only-session-secret-that-is-at-least-thirty-two-bytes"

os.environ.setdefault("CV_MATCHER_DATABASE_URL", TEST_DATABASE_URL)
os.environ.setdefault("CV_MATCHER_CORS_ALLOWED_ORIGINS", '["http://localhost:3000"]')
os.environ.setdefault("CV_MATCHER_APP_ENV", "test")
os.environ.setdefault("CV_MATCHER_SESSION_HMAC_SECRET", TEST_SESSION_SECRET)
os.environ.setdefault("CV_MATCHER_PRIVATE_STORAGE_ROOT", ".local-storage-test")

from app.core.config import Settings  # noqa: E402
from app.main import create_app  # noqa: E402


def sync_database_url() -> str:
    return TEST_DATABASE_URL.replace("postgresql://", "postgresql+psycopg://", 1)


@pytest.fixture
def settings(tmp_path: Path) -> Settings:
    return Settings(
        app_env="test",
        database_url=TEST_DATABASE_URL,
        cors_allowed_origins=["http://localhost:3000"],
        rate_limit_requests_per_minute=100,
        auth_rate_limit_requests_per_minute=100,
        session_hmac_secret=TEST_SESSION_SECRET,
        private_storage_root=tmp_path / "private-storage",
    )


@pytest.fixture(autouse=True)
def reset_database() -> Iterator[None]:
    engine = create_engine(sync_database_url())
    truncate_statement = text(
        "TRUNCATE TABLE cv_extractions, cv_document_versions, cv_documents, user_sessions, "
        "password_credentials, "
        "audit_events, users RESTART IDENTITY CASCADE"
    )
    with engine.begin() as connection:
        connection.execute(truncate_statement)
    try:
        yield
    finally:
        with engine.begin() as connection:
            connection.execute(truncate_statement)
        engine.dispose()


@pytest.fixture
def application(settings: Settings) -> FastAPI:
    return create_app(settings)


@pytest.fixture
def second_application(settings: Settings) -> FastAPI:
    return create_app(settings)


@pytest.fixture
def client(application: FastAPI) -> Iterator[TestClient]:
    with TestClient(application) as test_client:
        yield test_client


@pytest.fixture
def second_client(second_application: FastAPI) -> Iterator[TestClient]:
    with TestClient(second_application) as test_client:
        yield test_client
