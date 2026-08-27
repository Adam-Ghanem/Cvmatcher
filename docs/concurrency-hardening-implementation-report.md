# Concurrency Hardening Implementation Report

**Author:** Manus AI

**Scope:** Deterministic analysis creation and action-plan concurrency only

## Audit finding

The existing backend already used database-backed safeguards for several race-sensitive flows. CV version creation and CV deletion lock the owning document. Private extraction locks the immutable version and has a unique extraction row per version. Deterministic analysis persistence has a unique constraint covering CV version, target, scoring version, and input fingerprint. Action generation locks the analysis and has a unique constraint covering the analysis and its requirement-derived action.

The audit identified one concrete gap. Analysis creation locked the CV version but read the owner-scoped target role without a row lock. A concurrent target deletion could therefore remove the role while deterministic calculation was in progress. Although the foreign key would reject or cascade an inconsistent final state, this created avoidable retry/error behavior and an unclear transaction boundary.

## Implemented fix

`MatchAnalysisService.create_or_get` now locks the validated owner-scoped target row with `FOR UPDATE` immediately after locking the CV version. The lock is held by the existing request-scoped transaction until the request succeeds or rolls back. A target deletion already uses `FOR UPDATE` on the same row, so it now waits for the in-flight analysis to complete. The change does not alter deterministic-v2 or deterministic-v3 calculations, fingerprints, result payloads, scores, reuse rules, public routes, request schemas, response schemas, or database migrations.

| Operation | Existing database control | Verified behavior |
|---|---|---|
| V2/V3 analysis create-or-reuse | Unique `cv_document_version_id`, `job_target_id`, `scoring_version`, and `input_fingerprint` combination; CV version row lock | Two simultaneous authenticated V2 requests return the same persisted analysis ID. |
| Analysis versus target deletion | CV version lock plus the new target-row lock; target deletion locks the same owned row | Deletion waits while deterministic analysis is calculating, then completes after the analysis transaction finishes. |
| Action-plan generation | Analysis row lock and unique `analysis_id`/`requirement_id` combination | Two simultaneous requests return the same deterministic action plan without duplicate actions. |
| Extraction create-or-reuse | Existing immutable version row lock and unique extraction row per version | Existing behavior remains unchanged; the audit found no additional safe code change required. |

## Regression coverage and verification

The new tests use two independent authenticated test clients sharing the same valid session state. They exercise real PostgreSQL-backed application transactions rather than mocks. The target-deletion race deliberately pauses deterministic-v2 calculation after the owning rows are locked, confirms deletion cannot complete during that transaction, then releases calculation and confirms both operations succeed in a serializable order.

| Validation | Result |
|---|---|
| Concurrent V2 analysis create-or-reuse regression | Passed. |
| Concurrent action-plan generation regression | Passed. |
| Analysis creation versus target deletion regression | Passed after the target lock was added. |
| Focused analysis/action suites | Passed: 20 tests, with one pre-existing Starlette/httpx deprecation warning. |

## Boundaries retained

This phase intentionally does not introduce client idempotency keys, because the API does not advertise such a key and a partial implementation would create a misleading retry contract. User-authored target/requirement creation remains an ordinary create operation; collapsing intentionally repeated records would require explicit product semantics. The existing process-local rate limiter, approval-gated privacy lifecycle work, managed-object-storage requirement, and no-AI boundary remain unchanged.
