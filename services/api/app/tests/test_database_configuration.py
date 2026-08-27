from __future__ import annotations

from typing import Any

import pytest
from pydantic import ValidationError
from sqlalchemy import text

from app.core.config import Settings
from app.db.session import (
    create_database_engine,
    database_connect_args,
    database_engine_options,
)
from app.tests.conftest import TEST_DATABASE_URL


def configured_settings(**overrides: Any) -> Settings:
    return Settings(
        database_url=overrides.pop("database_url", TEST_DATABASE_URL),
        **overrides,
    )


def test_database_pool_and_timeout_settings_are_explicit_and_bounded() -> None:
    settings = configured_settings(
        database_pool_size=7,
        database_max_overflow=3,
        database_pool_timeout_seconds=12,
        database_statement_timeout_ms=4_000,
        database_idle_transaction_timeout_ms=5_000,
    )

    assert settings.database_pool_size == 7
    assert settings.database_max_overflow == 3
    assert settings.database_pool_timeout_seconds == 12
    assert settings.database_statement_timeout_ms == 4_000
    assert settings.database_idle_transaction_timeout_ms == 5_000


def test_database_settings_reject_unbounded_or_invalid_pool_values() -> None:
    with pytest.raises(ValidationError):
        configured_settings(database_pool_size=0)
    with pytest.raises(ValidationError):
        configured_settings(database_pool_timeout_seconds=0)
    with pytest.raises(ValidationError):
        configured_settings(database_statement_timeout_ms=0)


def test_database_connection_settings_set_postgresql_resource_timeouts() -> None:
    settings = configured_settings(
        database_statement_timeout_ms=4_000,
        database_idle_transaction_timeout_ms=5_000,
    )

    assert database_connect_args(settings) == {
        "server_settings": {
            "statement_timeout": "4000",
            "idle_in_transaction_session_timeout": "5000",
        }
    }


async def test_database_engine_applies_server_timeouts_to_connections() -> None:
    settings = configured_settings(
        database_statement_timeout_ms=4_000,
        database_idle_transaction_timeout_ms=5_000,
    )
    engine = create_database_engine(settings)
    try:
        async with engine.connect() as connection:
            statement_timeout = await connection.scalar(text("SHOW statement_timeout"))
            idle_transaction_timeout = await connection.scalar(
                text("SHOW idle_in_transaction_session_timeout")
            )
    finally:
        await engine.dispose()

    assert statement_timeout == "4s"
    assert idle_transaction_timeout == "5s"


def test_database_engine_uses_the_configured_pool_limits() -> None:
    settings = configured_settings(
        database_pool_size=7,
        database_max_overflow=3,
        database_pool_timeout_seconds=12,
    )

    assert database_engine_options(settings) == {
        "pool_pre_ping": True,
        "pool_size": 7,
        "max_overflow": 3,
        "pool_timeout": 12,
        "connect_args": database_connect_args(settings),
    }
