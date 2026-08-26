from __future__ import annotations

from sqlalchemy import create_engine, inspect

from app.tests.conftest import sync_database_url


def test_phase_two_migration_creates_secure_identity_and_document_tables() -> None:
    engine = create_engine(sync_database_url())
    try:
        inspector = inspect(engine)
        tables = set(inspector.get_table_names())
        assert {
            "password_credentials",
            "user_sessions",
            "cv_documents",
            "cv_document_versions",
        }.issubset(tables)

        credential_columns = {
            column["name"] for column in inspector.get_columns("password_credentials")
        }
        session_columns = {column["name"] for column in inspector.get_columns("user_sessions")}
        version_columns = {
            column["name"] for column in inspector.get_columns("cv_document_versions")
        }

        assert "password_hash" in credential_columns
        assert "password" not in credential_columns
        assert {"token_digest", "csrf_token_digest", "expires_at", "revoked_at"}.issubset(
            session_columns
        )
        assert "private_object_key" in version_columns
        assert "original_filename" in version_columns
    finally:
        engine.dispose()
