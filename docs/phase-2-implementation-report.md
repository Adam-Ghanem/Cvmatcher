# Phase 2 Implementation Report: Secure Identity and CV Intake

**Status:** Complete and verified locally
**Date:** 2026-08-26
**Scope:** Authentication, sessions, ownership-scoped CV documents, secure PDF/DOCX intake, responsive protected workspace, tests, migrations, CI, and documentation.

## Delivered capabilities

| Area | Implemented result |
|---|---|
| Accounts | Email/password registration and login using Argon2 password hashes in `password_credentials`. |
| Sessions | Opaque random sessions persisted as HMAC digests with expiry, revocation, and non-sensitive request metadata hashes. |
| Browser protection | httpOnly session cookie, same-site CSRF cookie/header validation, strict CORS, security headers, correlation IDs, and safe error envelopes. |
| Authorization | `CurrentPrincipal` derived from the server session; document retrieval and version operations scope by both document ID and user ID. |
| Document data model | `cv_documents` logical records plus immutable `cv_document_versions`; metadata includes filename, MIME type, byte size, checksum, timestamp, and hidden opaque object key. |
| Secure intake | 10 MiB streaming PDF/DOCX upload limit, filename normalization, signature/type agreement, DOCX ZIP container guards, private staging, restrictive permissions, atomic storage commit, and cleanup paths. |
| Storage | Server-only local private adapter for development/test. It has no public-serving capability and is rejected by production settings. |
| UI | Responsive registration/login routes, browser-level protected `/app` guard, CV workspace, loading/empty/error states, file selection, upload progress, and safe recovery messages. |
| Delivery | Alembic migration `20260826_0002`, PostgreSQL-backed integration fixtures, CI PostgreSQL service/migration setup, and updated architecture/API/security/README documentation. |

## Verification evidence

| Verification | Result |
|---|---|
| Backend lint | `ruff check .` passed. |
| Backend types | `mypy app` passed in strict mode. |
| Backend tests | `24 passed`; coverage includes sessions, CSRF failure, anonymous protection, logout revocation, upload validation, DOCX container acceptance, oversized upload rejection, IDOR resistance, versioning, migration schema, configuration, rate-limit and error baseline tests. |
| Frontend lint | ESLint passed. |
| Frontend types | `tsc --noEmit` passed. |
| Frontend tests | `3 passed`; covers landing proposition and typed credentialed API client behavior. |
| Frontend build | Next.js production build passed with routes `/`, `/auth/login`, `/auth/register`, and `/app`; Next.js proxy compiled. |
| Migration | `alembic upgrade head` applied `20260826_0002` to the isolated local development database; `alembic current` reported `20260826_0002 (head)`. |
| Live operational check | FastAPI `/api/v1/health` returned `{"status":"ok"}` and `/api/v1/ready` returned `{"status":"ready","database":"ready"}` against the migrated development database. |
| Visual check | The account creation screen rendered at desktop width with labelled inputs, clear primary/alternate actions, privacy messaging, and the shared CVMatcher visual language. The initial stale-preview 404 was diagnosed as a port conflict and corrected before verification. |
| Dependency checks | No frontend dependency was added. Backend added only `argon2-cffi` for password hashing and `python-multipart` for multipart intake. |

## Deliberate exclusions

Phase 2 has **not** implemented CV text extraction, PDF rendering, DOCX parsing, OCR, job description intake, matching/scoring, OpenAI, recommendations, document downloads, data deletion/retention workflows, billing, background jobs, distributed rate limiting, Redis, vector storage, or Ruflo.

## Known operational limits

The local private filesystem adapter is valid for development/test verification only. Production cannot start with it. A production deployment requires a managed private object-storage adapter, HTTPS, secret manager, managed PostgreSQL, backups, monitoring, and approved retention/deletion operations.

The in-memory rate limiter is intentionally process-local. It protects the Phase 2 local/runtime baseline but is not a cross-instance defense. A shared limiter is not introduced until deployment scale demonstrates the need.

The browser proxy checks for cookie presence to improve navigation; FastAPI remains the sole server-side authorization authority.

## Phase 3 recommendation

The next bounded implementation phase should add **safe CV text extraction** only. It should introduce an extraction job/data contract, parser-specific resource limits, malformed/hostile PDF and DOCX fixtures, checksum-based idempotency, extraction status/error modelling, user-visible document processing states, and retention/deletion design. It must not yet implement job matching, scores, OpenAI, or recommendations.
