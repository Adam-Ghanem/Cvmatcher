# Analysis History Implementation Report

**Status:** Implemented and locally verified

**Scope:** Owner-scoped, cursor-paginated retrieval of existing deterministic analysis summaries.

**Out of scope:** CV extraction changes, readiness changes, deterministic scoring changes, OCR, AI/LLM features, queues, Redis, embeddings, storage changes, and privacy-retention policy changes.

## Product Capability

Returning users can now retrieve a bounded history of their prior deterministic CV-to-target comparisons. This closes the product gap where an analysis could be created and retrieved by a known ID but could not be safely rediscovered after leaving the workspace.

The new `GET /api/v1/match-analyses` endpoint returns newest-first summary cards suitable for a future history interface. The first release intentionally remains backend/API-only; it does not add a new workspace view or modify the existing analysis creation flow.

| Contract element | Behavior |
|---|---|
| Authentication | Requires the existing validated opaque session. |
| CSRF | Not required because the endpoint is read-only. |
| Pagination | Keyset pagination using `limit` from 1 to 50 (default 20) and an optional `cursor`. |
| Ordering | Descending `createdAt`, then descending analysis ID, for a stable keyset order. |
| Response | Safe analysis ID, scoring version, overall score, document title/version, target title, creation timestamp, and `nextCursor`. |
| Source privacy | No CV text, job-description text, source resource IDs, storage data, parser data, or complete analysis payload is returned. |

## Backend Design

`MatchAnalysisService.list_history` resolves a cursor only within the authenticated owner scope. A nonexistent or foreign cursor returns the established uniform `404 RESOURCE_NOT_FOUND` response. The page query joins the analysis record with the document version, document, and target role in one query and verifies the owner boundary on all three resources. It obtains one extra row to decide whether to return a `nextCursor`, avoiding a separate count query.

The query does not invoke extraction, readiness derivation, matching, or scoring. It reads only existing persisted deterministic results and metadata. The existing private detail endpoint remains unchanged and continues to be the only way to retrieve full bounded evidence for a known owned analysis.

## Persistence and Migration

Migration `20260826_0007` adds `ix_match_analyses_user_created_id` over `(user_id, created_at, id)`. This supports the owner-filtered newest-first keyset query without altering or deleting existing user data. The development database was upgraded successfully to `20260826_0007 (head)`.

## Security Review

The feature adds no new sensitive data category, upload path, authentication mechanism, external integration, or background process. Authorization is server-derived from the session and never from a user-supplied account identifier. Cursor validation is owner-scoped, preventing a user from using another account’s analysis UUID as a pagination anchor. Error behavior stays uniform for missing and inaccessible cursors.

All summary fields are explicit allowlisted projections. Source CV text, private target text, persistent input resource IDs, stored object references, and internal extraction data are excluded by both the schema and the service response builder.

## Test Coverage and Verification

The tests cover multi-page traversal without duplication, safe projection/no private source text, owner isolation, foreign cursor rejection, unauthenticated access, and malformed or oversized pagination parameters. The full verification set passed:

| Check | Result |
|---|---|
| Backend Ruff | Passed |
| Backend mypy | Passed with no issues in 55 source files |
| Backend pytest | 59 passed; one pre-existing Starlette/httpx deprecation warning |
| Frontend ESLint | Passed |
| Frontend TypeScript | Passed |
| Frontend Vitest | 12 passed across 3 test files |
| Frontend production build | Passed |
| Alembic current | `20260826_0007 (head)` |
| `pnpm audit --audit-level high` | No known vulnerabilities found |
| `pip3 check` | All installed packages compatible |
| Diff whitespace check | Passed |

## Next Safe Step

The next product increment can add a compact, accessible analysis-history UI that uses this paginated metadata-only API and reopens a selected owned analysis through the existing detail endpoint. It should remain separate from any future target-editing work, because target updates require an explicit policy for persisted deterministic-result invalidation.
