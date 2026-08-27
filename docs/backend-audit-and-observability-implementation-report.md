# Backend Audit and Safe Observability Implementation Report

**Status:** Backend audit completed; bounded production observability phase implemented and locally verified.

**Audited baseline:** `241a0eb feat: add deterministic action plans`.

**Implemented phase:** Privacy-safe, request-correlated audit events for core authentication, extraction, analysis, and action-plan lifecycle operations.

## Full Backend Audit

The repository remains a deliberately simple FastAPI/PostgreSQL service with typed Pydantic contracts, async SQLAlchemy, Alembic migrations, a private object-storage abstraction, and no external AI, queue, Redis, vector, embedding, or worker infrastructure. The browser application was not modified during this backend-only phase.

| Capability | Audit classification | Evidence and conclusion |
|---|---|---|
| Authentication and sessions | Implemented | Argon2 password hashes, opaque HMAC-digested sessions, expiry/revocation, secure cookie enforcement in staging/production, and server-derived principals are present. |
| Authorization and IDOR defense | Implemented | Private services query each resource through the authenticated owner. Inaccessible references use uniform safe `404` errors. |
| CSRF | Implemented | A readable CSRF cookie, submitted header, and server-side digest are validated for state-changing authenticated operations. |
| Request/response validation | Implemented | Pydantic request schemas bound values, reject unknown fields, and response models constrain public projections. |
| Safe errors, request IDs, security headers | Implemented | Generic envelopes carry a generated/validated UUID request ID; security headers and restrictive CORS origins are configured. |
| Upload and extraction safety | Implemented | Private streamed PDF/DOCX intake, MIME/magic validation, 10 MiB limit, constrained child-process parsing, page/character/archive bounds, no network traversal, and metadata-only output remain in place. |
| Readiness | Implemented | `ready`, `warning`, and `blocked` are derived deterministically from authoritative extraction metadata. |
| Deterministic scoring | Implemented | Historical `deterministic-v2` is preserved; versioned `deterministic-v3` uses server-owned reviewed requirements and safe evidence states. |
| Structured requirements | Implemented | Owner-scoped CRUD, bounded categories/priorities/review states, normalization version, and pagination are present. |
| Analysis history and action plans | Implemented | Owner-scoped keyset history and persisted deterministic v3 action plans are present with cascade integrity. |
| Durable domain/security event observability | Missing at audit baseline; implemented in this phase | An `audit_events` table existed but no route/service wrote events. |
| Rate limiting | Partial | Single-process in-memory per-client buckets are implemented. Distributed multi-instance enforcement needs an approved shared infrastructure decision and is intentionally not added. |
| CI security automation | Partial | CI runs migrations, Ruff, mypy, pytest, and web checks, but does not yet automate dependency audit or secret scanning. |
| Production deployment operations | Partial / production-blocking | The non-root API image and production local-storage rejection exist; production still requires managed private object storage, secret management, TLS termination, monitoring/alerting, backups, retention decisions, and operational runbooks. |
| Privacy lifecycle / export / retention | Approval-gated | The approved lifecycle strategy deliberately defers retention timers, backup erasure, account deletion workflows, and export policy. No changes were made. |
| Billing and AI | Missing by design | Neither is required or approved for this bounded backend phase. |

## Safe Audit-Event Design

The existing `audit_events` table is now used through `app.services.audit_events.record_audit_event`. This service only accepts a closed allowlist of event names and exact allowlisted metadata keys. It rejects unknown events, unexpected keys, nested values, collections, and overlong strings before persistence.

| Event | Exact permitted metadata | Trigger |
|---|---|---|
| `auth.account_created` | `authentication_method` | Successful local account creation. |
| `auth.session_issued` | `authentication_method` | Successful session issuance after registration or login. |
| `auth.session_revoked` | None | Successful logout/session revocation. |
| `cv.extraction_succeeded` | `source_type`, `quality` | Bounded extraction completes. |
| `cv.extraction_failed` | `source_type` | Bounded extraction reaches the existing safe failure path. |
| `analysis.created` | `scoring_version` | A new deterministic result is persisted, never an idempotent reuse. |
| `action_plan.generated` | `created_count` | A deterministic action-plan generation request completes. |
| `action.status_updated` | `status` | An owner changes an action state. |

Each event includes the authenticated user UUID in the existing owner column and the current validated request correlation UUID. The metadata contains only scalar values; it never contains CV content, extracted text, job descriptions, requirement/source-reference text, credentials, cookies, IP/user-agent hashes, storage keys, filesystem paths, parser output, model/prompt data, or stack traces. Audit events remain private server-side data: no new public audit API exists.

No migration was required because `audit_events` was already an established and migration-managed model. No retention, export, account-deletion, backup, or legal-hold behavior was changed. Audit-event retention remains an explicit approval-gated policy decision.

## Files Changed

| Path | Change |
|---|---|
| `services/api/app/services/audit_events.py` | New allowlisted, scalar-only, request-correlated audit-event service. |
| `services/api/app/services/authentication.py` | Records fixed account/session lifecycle events. |
| `services/api/app/services/cv_extraction.py` | Records safe extraction success/failure categories after existing parsing completes. |
| `services/api/app/services/match_analyses.py` | Records only newly persisted deterministic analyses. |
| `services/api/app/services/analysis_actions.py` | Records action-plan generation and bounded status updates. |
| `services/api/app/tests/test_audit_events.py` | Adds allowlist, scalar-boundary, lifecycle coverage, and private-content absence assertions. |
| `docs/backend-audit-and-observability-implementation-report.md` | This audit and implementation record. |

## Verification

| Command | Actual result |
|---|---|
| `cd services/api && pytest app/tests/test_audit_events.py` | 3 passed; known upstream Starlette/httpx deprecation warning only. |
| `cd services/api && ruff check . && mypy app && pytest` | Ruff passed; mypy passed for 67 source files; 77 tests passed; same known warning only. |
| `cd /home/ubuntu/cvmatcher && pnpm audit --audit-level high` | No known vulnerabilities found. |
| `pip3 check` | All 116 installed packages are compatible. |
| `cd services/api && alembic current` | `20260827_0010 (head)`; no migration added or required. |
| Scoped changed-file secret scan | No common private-key, AWS, OpenAI-style, or GitHub-token patterns found. |
| `git diff --check` | Passed before documentation updates; repeated before commit. |

## Limitations and Next Safe Work

This phase establishes durable private event categories and correlation, not a monitoring platform. It deliberately does not add log shipping, dashboards, alerting, traces, metrics infrastructure, telemetry vendors, distributed rate limiting, queues, or background workers.

The next highest-value safe backend improvement is to add CI enforcement for the already-run dependency audit and secret scan, provided workflow changes are treated as a separate focused phase. Distributed rate limiting, managed private object storage, backups/retention, export, account erasure, billing, and AI need separate explicit architecture and policy decisions.
