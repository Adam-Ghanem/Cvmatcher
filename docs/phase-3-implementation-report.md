# Phase 3 Implementation Report: Bounded Private CV Text Extraction

**Status:** Complete and verified locally

**Date:** 2026-08-26
**Scope:** Owner-scoped PDF/DOCX text preparation, parser isolation and limits, extraction persistence/API contracts, accessible workspace controls, migrations, tests, and documentation.

## Delivered capabilities

| Area | Implemented result |
|---|---|
| Explicit preparation | A signed-in user can explicitly start private text preparation for one owned immutable CV version. The API also provides an owner-scoped status read without reparsing. |
| Authorization and idempotency | The service queries document/version ownership from the validated session, uses CSRF for the state-changing route, locks the immutable version during preparation, and enforces one extraction record per version. Inaccessible, missing, and not-yet-created records remain uniform `404` responses. |
| Parser isolation | The API delegates parsing from a worker thread to a short-lived spawned child process. The parent enforces an 8-second wall-clock limit and terminates an overdue worker. Linux workers apply `RLIMIT_CPU` at 4 seconds and `RLIMIT_AS` at 256 MiB. |
| PDF and DOCX bounds | PDF extraction uses `pypdf`, rejects encrypted PDFs, limits documents to 100 pages, and caps result text at 250,000 characters. DOCX extraction repeats archive validation, reads only `word/document.xml`, rejects DTD/entity markers, and uses the standard library for ZIP/XML processing. |
| Sensitive text boundary | `cv_extractions.extracted_text` is server-only. API schemas, browser types, logs by design, and workspace controls expose only safe status metadata, character count, timestamps, and a generic failure/recovery message. Raw CV text is never returned or displayed. |
| Persistence | Alembic migration `20260826_0003` adds `cv_extractions` with unique version ownership and database check constraints for lifecycle status, source type, and non-negative character count. |
| Workspace UX | Each saved CV has an explicit **Prepare CV text** action with server-only privacy explanation, in-progress state, safe success/failure states, and retry control. The interface is semantic, keyboard-operable, responsive, and uses the existing CVMatcher visual language. |
| Dependency rationale | Phase 3 adds `pypdf` as the only runtime parser dependency. It is a maintained pure-Python PDF reader; DOCX parsing reuses the existing archive safeguards and standard library, avoiding a full Office-processing dependency. |

## Verification evidence

| Verification | Result |
|---|---|
| Backend lint | `ruff check .` passed. |
| Backend types | `mypy app` passed with no issues across 43 source files. |
| Backend tests | `36 passed`; coverage includes success and safe failure paths, raw-text response exclusion, owner isolation, status retrieval, idempotent reuse, valid PDF/DOCX handling, encrypted PDFs, page/character ceilings, DOCX DTD rejection, archive entry revalidation, migrations, sessions, CSRF, upload rules, and security baseline behavior. |
| Frontend lint | `pnpm web:lint` passed. |
| Frontend types | `pnpm web:typecheck` passed. |
| Frontend tests | `pnpm web:test` passed with `5 passed`; coverage includes the typed extraction API client and explicit workspace preparation interaction. |
| Frontend build | `pnpm web:build` passed. The optimized Next.js build includes `/`, `/auth/login`, `/auth/register`, `/app`, and the proxy. |
| Migration | `alembic upgrade head` applied `20260826_0003` to the local development database and `alembic current` reported `20260826_0003 (head)`. The dedicated test database was rebuilt from `20260826_0002` to head before the final suite. |
| Live operational check | Restarted FastAPI successfully. `/api/v1/health` returned `{"status":"ok"}` and `/api/v1/ready` returned `{"status":"ready","database":"ready"}` against the migrated local database. |
| Dependency checks | `pnpm audit --audit-level high` found no known vulnerabilities. `pip3 check` reported compatible installed packages. |
| Change-set integrity | `git diff --check` passed before commit review. |
| Preview check | The current local preview redirected an unauthenticated `/app` request to the expected sign-in screen. The authenticated extraction control is exercised in its focused component interaction test; no raw CV text is rendered in its browser state. |

## Deliberate exclusions

Phase 3 has **not** added document rendering, OCR, job-description intake, matching or scoring, OpenAI, recommendations, document download, billing, queues, Redis, vector indexing, microservices, distributed rate limiting, or Ruflo. It does not claim that a CV score predicts an interview or employment outcome.

## Known operational limits

The parser child-process limits reduce parser denial-of-service risk, but they are not a malware guarantee or a complete production sandbox. `RLIMIT_CPU` and `RLIMIT_AS` are Linux-specific; the parent wall-clock deadline still applies on other supported platforms. A public production deployment requires deployment-sandbox review, least-privilege process permissions, managed private storage, malware-scanning policy, monitoring, capacity testing, and data retention/deletion operations.

The local private-storage adapter remains appropriate only for development and test. Production startup rejects it. Extracted CV text is now stored as sensitive data, so production also requires encryption-at-rest policy, verified deletion across primary storage and backups, managed PostgreSQL, a secret manager, HTTPS, operational monitoring, and approved retention controls.

## Phase 4 recommendation

The next bounded phase should introduce **secure target-role/job-description intake** only. It should use the same session-derived ownership, strict size/content validation, private persistence, UI empty/loading/error states, and API contract discipline. It must not yet perform matching, scoring, OpenAI calls, AI recommendations, billing, queueing, or vector indexing.
