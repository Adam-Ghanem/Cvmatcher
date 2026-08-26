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


def test_settings_require_an_explicit_cors_origin() -> None:
    with pytest.raises(ValidationError, match="At least one explicit CORS origin"):
        Settings(
            database_url="postgresql://cvmatcher:cvmatcher@localhost:5432/cvmatcher",
            cors_allowed_origins=[],
        )
