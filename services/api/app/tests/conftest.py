from __future__ import annotations

import os
from collections.abc import Iterator

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient

os.environ.setdefault("CV_MATCHER_DATABASE_URL", "postgresql://cvmatcher:cvmatcher@localhost:5432/cvmatcher")
os.environ.setdefault("CV_MATCHER_CORS_ALLOWED_ORIGINS", '["http://localhost:3000"]')
os.environ.setdefault("CV_MATCHER_APP_ENV", "test")

from app.core.config import Settings
from app.main import create_app


@pytest.fixture
def settings() -> Settings:
    return Settings(
        app_env="test",
        database_url="postgresql://cvmatcher:cvmatcher@localhost:5432/cvmatcher",
        cors_allowed_origins=["http://localhost:3000"],
        rate_limit_requests_per_minute=3,
    )


@pytest.fixture
def application(settings: Settings) -> FastAPI:
    return create_app(settings)


@pytest.fixture
def client(application: FastAPI) -> Iterator[TestClient]:
    with TestClient(application) as test_client:
        yield test_client
