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
            "job_targets",
            "match_analyses",
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
        job_target_columns = {
            column["name"] for column in inspector.get_columns("job_targets")
        }
        job_target_constraints = {
            constraint["name"] for constraint in inspector.get_check_constraints("job_targets")
        }
        match_analysis_columns = {
            column["name"] for column in inspector.get_columns("match_analyses")
        }
        match_analysis_constraints = {
            constraint["name"] for constraint in inspector.get_check_constraints("match_analyses")
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
        assert {
            "user_id",
            "title",
            "job_description",
            "job_description_character_count",
        }.issubset(job_target_columns)
        assert "ck_job_target_description_character_count_nonnegative" in job_target_constraints
        assert {
            "user_id",
            "cv_document_version_id",
            "job_target_id",
            "scoring_version",
            "overall_score",
            "result_payload",
        }.issubset(match_analysis_columns)
        assert "ck_match_analysis_score_range" in match_analysis_constraints
    finally:
        engine.dispose()
