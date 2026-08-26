from __future__ import annotations

from sqlalchemy import create_engine, inspect

from app.tests.conftest import sync_database_url


def test_migrations_create_secure_identity_document_and_extraction_tables() -> None:
    engine = create_engine(sync_database_url())
    try:
        inspector = inspect(engine)
        tables = set(inspector.get_table_names())
        assert {
            "password_credentials",
            "user_sessions",
            "cv_documents",
            "cv_document_versions",
            "cv_extractions",
        }.issubset(tables)

        credential_columns = {
            column["name"] for column in inspector.get_columns("password_credentials")
        }
        session_columns = {column["name"] for column in inspector.get_columns("user_sessions")}
        version_columns = {
            column["name"] for column in inspector.get_columns("cv_document_versions")
        }
        extraction_columns = {
            column["name"] for column in inspector.get_columns("cv_extractions")
        }
        extraction_constraints = {
            constraint["name"] for constraint in inspector.get_check_constraints("cv_extractions")
        }

        assert "password_hash" in credential_columns
        assert "password" not in credential_columns
        assert {"token_digest", "csrf_token_digest", "expires_at", "revoked_at"}.issubset(
            session_columns
        )
        assert "private_object_key" in version_columns
        assert "original_filename" in version_columns
        assert {
            "document_version_id",
            "status",
            "source_type",
            "character_count",
            "extracted_text",
            "failure_message",
            "completed_at",
        }.issubset(extraction_columns)
        assert {
            "ck_cv_extraction_status",
            "ck_cv_extraction_source_type",
            "ck_cv_extraction_character_count_nonnegative",
        }.issubset(extraction_constraints)
    finally:
        engine.dispose()
