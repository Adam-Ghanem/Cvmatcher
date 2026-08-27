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
            "job_requirements",
            "match_analyses",
            "analysis_actions",
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
        job_requirement_columns = {
            column["name"] for column in inspector.get_columns("job_requirements")
        }
        job_requirement_constraints = {
            constraint["name"] for constraint in inspector.get_check_constraints("job_requirements")
        }
        job_requirement_indexes = {
            index["name"] for index in inspector.get_indexes("job_requirements")
        }
        analysis_action_columns = {
            column["name"] for column in inspector.get_columns("analysis_actions")
        }
        analysis_action_constraints = {
            constraint["name"] for constraint in inspector.get_check_constraints("analysis_actions")
        }
        analysis_action_indexes = {
            index["name"] for index in inspector.get_indexes("analysis_actions")
        }
        analysis_action_unique_constraints = {
            constraint["name"]
            for constraint in inspector.get_unique_constraints("analysis_actions")
        }
        analysis_action_foreign_keys = inspector.get_foreign_keys("analysis_actions")
        match_analysis_columns = {
            column["name"] for column in inspector.get_columns("match_analyses")
        }
        match_analysis_constraints = {
            constraint["name"] for constraint in inspector.get_check_constraints("match_analyses")
        }
        match_analysis_unique_constraints = {
            constraint["name"] for constraint in inspector.get_unique_constraints("match_analyses")
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
            "parser_version",
            "quality",
            "warnings",
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
            "job_target_id",
            "requirement_text",
            "category",
            "priority",
            "normalization_version",
            "review_state",
        }.issubset(job_requirement_columns)
        assert {
            "ck_job_requirement_text_length",
            "ck_job_requirement_category",
            "ck_job_requirement_priority_range",
            "ck_job_requirement_review_state",
        }.issubset(job_requirement_constraints)
        assert "ix_job_requirements_target_priority_created_id" in job_requirement_indexes
        assert {
            "user_id",
            "analysis_id",
            "requirement_id",
            "title",
            "description",
            "priority",
            "category",
            "evidence_state",
            "status",
            "position",
        }.issubset(analysis_action_columns)
        assert {
            "ck_analysis_action_category",
            "ck_analysis_action_priority_range",
            "ck_analysis_action_position_positive",
            "ck_analysis_action_status",
        }.issubset(analysis_action_constraints)
        assert "uq_analysis_action_analysis_requirement" in analysis_action_unique_constraints
        assert "ix_analysis_actions_analysis_position_id" in analysis_action_indexes
        assert any(
            foreign_key["referred_table"] == "match_analyses"
            and foreign_key["options"].get("ondelete") == "CASCADE"
            for foreign_key in analysis_action_foreign_keys
        )
        assert {
            "user_id",
            "cv_document_version_id",
            "job_target_id",
            "scoring_version",
            "input_fingerprint",
            "overall_score",
            "result_payload",
        }.issubset(match_analysis_columns)
        assert "ck_match_analysis_score_range" in match_analysis_constraints
        assert "uq_match_analysis_input_fingerprint" in match_analysis_unique_constraints
    finally:
        engine.dispose()
