# CI Schema-Drift Gate Implementation Report

**Author:** Manus AI

## Delivered CI control

The API CI job now runs `alembic check` immediately after `alembic upgrade head`. This detects ORM metadata changes for which no matching migration exists before linting, type-checking, and API tests continue. The gate is local, deterministic, uses the same ephemeral PostgreSQL service already provisioned by CI, and adds no external dependency or production infrastructure.

The first local run exposed metadata drift rather than a missing production migration. Four models had declared a `unique=True, index=True` column, while the existing revisions created a separate unnamed unique constraint plus a non-unique lookup index. The database schema already enforces uniqueness. The model metadata has been aligned to that actual schema by declaring corresponding `UniqueConstraint` objects and retaining non-unique indexes. No revision was rewritten, no new revision was generated, and the deployed database schema remains unchanged.

| Affected model | Existing schema represented by migrations | Metadata alignment |
|---|---|---|
| `User` | Unique `auth_subject`/`email` constraints plus ordinary lookup indexes | Explicit table constraints with indexed columns |
| `PasswordCredential` | Unique `user_id` constraint plus ordinary lookup index | Explicit table constraint with indexed column |
| `UserSession` | Unique `token_digest` constraint plus ordinary lookup index | Explicit table constraint with indexed column |
| `CvExtraction` | Unique `document_version_id` constraint plus ordinary lookup index | Explicit table constraint with indexed column |

## Verification

The initial `alembic check` correctly failed and identified only the four model/migration representations above. After alignment, it reported `No new upgrade operations detected.` The full backend gate passed afterward: Ruff, mypy, and 106 pytest tests. Existing database migration tests remain in place.

## Scope and non-goals

This gate does not replace review of a proposed migration, production migration backups, rollback planning, or restore testing. It does not run automatically generated revisions, alter historical migrations, add speculative database indexes, or claim that a production database is fully operational. CI continues to run the existing migration upgrade before this check, which verifies the repository’s current head revision against its ephemeral PostgreSQL service.
