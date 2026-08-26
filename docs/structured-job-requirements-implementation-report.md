# Structured Job Requirements Implementation Report

**Status:** Implemented and locally verified

**Scope:** Manual, owner-scoped structured requirement management for existing private target roles.

**Out of scope:** Automatic job-description extraction, AI/LLM use, deterministic scoring changes, CV extraction/readiness changes, analysis-result mutation, queues, vectors, embeddings, storage redesign, and privacy-retention policy changes.

## Audit Findings

The repository was clean at `83497e9 feat: add private analysis history`. The implemented backend already provided Argon2-backed opaque sessions, CSRF validation, owner-scoped private CV/document storage, bounded PDF/DOCX extraction, deterministic document readiness, private target-job intake, deterministic analysis creation/detail/history, deletion controls, typed schemas, Alembic migrations, and database-backed tests.

The verified missing capability was a structured job-requirement domain. Existing `job_targets` persisted one private free-form job description and safe metadata only; no requirement model, migration, service, route, or test existed. Deterministic scoring was intentionally left unchanged and continues to use the existing `deterministic-v2` path.

## Implemented Capability

This phase adds manually curated requirements beneath an existing owned target role. A user can create, list, update, and delete requirements without exposing the private full job description. Each requirement records the following controlled fields.

| Field | Behavior |
|---|---|
| `requirement` | User-supplied reviewed requirement text, 2–1,000 characters. |
| `category` | Exactly `must-have`, `should-have`, or `nice-to-have`. |
| `normalizedSkill` | Optional server-normalized, lowercased whitespace-collapsed value. |
| `priority` | Explicit integer from 1 through 100. |
| `sourceReference` | Optional concise user-provided source reference, up to 500 characters. |
| `normalizationVersion` | Server-controlled `manual-v1`; the client cannot set it. |
| `reviewState` | Exactly `unreviewed`, `reviewed`, or `user-confirmed`. |

`GET /api/v1/job-targets/{target_id}/requirements` uses owner-scoped keyset pagination ordered by priority, creation time, and ID. `POST`, `PATCH`, and `DELETE` routes require the existing authenticated-session and CSRF boundary. The API uses strict Pydantic schemas, rejects unknown fields, and supports partial updates with an explicit non-empty update requirement.

## Data Model and Migration

Migration `20260826_0008` creates `job_requirements`. It has user and target foreign keys with cascade deletion, bounded string/text columns, database constraints for requirement text length, category, priority, and review state, plus a target/priority/creation/ID pagination index. This migration is additive and does not alter or delete existing documents, targets, analyses, or private source text.

The API service resolves the parent target through the authenticated user ID before every operation. Requirement reads and writes then filter by requirement ID, target ID, and user ID together. Missing and cross-user target/requirement references return the established safe `404 RESOURCE_NOT_FOUND` behavior.

## Security and Privacy Boundaries

The phase does not read, return, parse, or automatically derive data from `job_targets.job_description`. Requirement records are owner-scoped private structured data; their API projections do not include raw job-description text, CV text, storage keys, filesystem paths, parser state, source resource IDs, infrastructure details, or stack traces.

Existing CV extraction resource limits, document readiness derivation, deterministic scoring rules, session handling, CSRF validation, uniform owner-not-found responses, and private storage boundaries remain unchanged. No external service, AI model, prompt, network request, background worker, or new secret is introduced.

## Verification

| Check | Result |
|---|---|
| Backend Ruff | Passed |
| Backend mypy | Passed with no issues in 59 source files |
| Backend pytest | 62 passed; one pre-existing Starlette/httpx deprecation warning |
| Focused requirement/migration tests | 4 passed |
| Frontend ESLint | Passed |
| Frontend TypeScript | Passed |
| Frontend Vitest | 12 passed across 3 test files |
| Frontend production build | Passed |
| Development Alembic state | `20260826_0008 (head)` |
| Isolated test Alembic state | `20260826_0008 (head)` |
| `pnpm audit --audit-level high` | No known vulnerabilities found |
| `pip3 check` | All installed packages compatible |
| Changed-file secret scan | No common private-key, AWS, OpenAI-style, or GitHub-token patterns found |
| Whitespace validation | Passed |

Focused integration tests cover creation, normalization, newest-page traversal, update behavior, strict validation, CSRF enforcement, private-job-description absence, cross-user list/update/delete rejection, and schema/index migration presence.

## Remaining Backend Roadmap

The next bounded backend phase can make explicit how manually reviewed structured requirements participate in a new deterministic scoring version. That work must define evidence references, component weighting, reproducibility, and persisted scoring-version semantics without silently changing `deterministic-v2`. A subsequent phase can add action-plan persistence only after its evidence model and product policy are specified. AI-assisted extraction or recommendations remain deferred pending a separate safety and privacy review.
