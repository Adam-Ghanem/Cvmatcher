# Production Maturity Architecture Gap Assessment

**Author:** Manus AI
**Repository baseline:** `26ac0117020fd34895d99f77a41484ee192bf1be` on `main`
**Purpose:** Pre-implementation assessment for the multi-instance backend maturity program.

## Executive assessment

CVMatcher has a strong deterministic MVP security foundation. It has server-derived ownership, opaque cookie sessions, CSRF-protected mutations, bounded request and extraction work, owner-scoped persistence, private storage abstractions, deterministic scoring, audit events, safe error envelopes, redacted structured logging, and successful remote CI gates. The highest production-readiness risks are not the existing career-intelligence logic; they are operational boundaries that intentionally remain local or single-process.

The most immediate gap is rate limiting. The current `InMemoryRateLimiter` has an intentionally minimal `allow(key) -> bool` protocol, process-local deques, a per-process lock, and no result metadata, provider configuration, backend-health policy, or rate-limit headers. It protects only a single application process and would permit a client to receive a fresh budget through every API replica. A provider-ready contract and explicit production configuration gate can be added without adding Redis or claiming that distributed enforcement already exists.

## Architecture and trust boundaries

| Boundary | Current state | Production assessment |
|---|---|---|
| Browser to API | Cookie-authenticated API requests; CSRF on mutations; explicit CORS origins; shared safe error schema. | **Implemented.** A reverse proxy or gateway must still terminate HTTPS and set trusted forwarding behavior in production. |
| Authentication and authorization | Argon2 hashes, opaque HMAC-digested sessions, server-derived owners, uniform owned/unowned 404s, concurrent duplicate-registration recovery. | **Implemented.** Session persistence is database-backed and can span API replicas. |
| Request processing | Request IDs, security headers, safe framework errors, generic and auth-sensitive in-memory budgets, and streamed request-size enforcement. | **Partially implemented.** Rate limits are single-process and no proxy-trust policy is configured. |
| Database | PostgreSQL, Alembic, SQLAlchemy async sessions, `pool_pre_ping`, bounded local pool settings, owner filters, relevant uniqueness constraints and row locks. | **Partially implemented.** Pool values are hard-coded; no configurable statement timeout or explicit production database connection policy exists. |
| Private documents | Opaque object keys, safe filename/signature validation, atomic local staging/commit/delete, bounded DOCX container inspection, no public URL/download API. | **Implemented for development/test.** Local filesystem storage is correctly rejected for production; a managed adapter remains required. |
| Text extraction | Spawned constrained child process, time/CPU/address-space limits, safe status metadata, no parser diagnostics or raw text in API responses. | **Implemented.** No OCR, external network, or model processing is present. |
| Deterministic analysis | Versioned v2/v3 deterministic scorers, owner-scoped inputs, immutable persisted results, concurrency locks, requirement/action pagination. | **Implemented.** Scoring semantics must remain unchanged. |
| Audit and logs | Allowlisted non-content audit events, request correlation, normalized structured-field redaction. | **Implemented for internal records.** Centralized metrics, retention, access, and alerting are not deployed. |
| CI and supply chain | Frozen pnpm installation, narrow pnpm 11 build allowlist, audits, pip compatibility check, secret scanner, type/lint/test/build gates. | **Implemented.** Remote GitHub Actions succeeded at the audited baseline. |

## Classification of current maturity

| Area | Classification | Evidence and implication |
|---|---|---|
| Authentication, sessions, CSRF, owner scoping | **Production-ready application boundary** | The server derives identity/ownership, persists only session digests, protects browser mutations, and avoids account enumeration in normal and concurrent duplicate flows. |
| Error, request-ID, and non-disclosure behavior | **Production-ready application boundary** | Typed safe envelopes cover domain, validation, unexpected, 404, and 405 failures; storage paths, source text, tokens, and stack traces remain excluded. |
| CV upload and extraction security | **Production-ready application boundary** | Input/signature/archive checks, bounded private staging, child-process limits, and cleanup are tested. Malware scanning is not claimed. |
| Deterministic scoring and persisted actions | **Production-ready application boundary** | Existing v2/v3 semantics, row locks, uniqueness constraints, and safe evidence projections are preserved. |
| Database ownership/transaction correctness | **Strong MVP, partially production-configured** | PostgreSQL constraints and targeted locks exist, but fixed pool values and absent statement-timeout policy require configuration-boundary work. |
| Rate limiting | **MVP-only and unsafe for multi-instance deployment** | In-memory buckets are not shared between replicas and expose no retry/reset metadata. |
| Top-level CV and target listing | **MVP-only contract** | Results are owner-scoped and ordered but unbounded. A compatibility-preserving pagination migration must involve frontend/client contracts. |
| Private storage | **Development/test implementation only** | The storage protocol is a useful abstraction; only the local adapter is implemented. Production activation must stop pending provider and privacy decisions. |
| Observability | **Internal foundation only** | Request correlation, audit records, and redaction exist. Metrics, alerting, dashboarding, and log access/retention controls are absent. |
| Malware handling | **Missing runtime integration; design required** | Existing validation reduces parser risk but is not malware detection. No file may be labelled scanned without a real scanner. |
| Backup, restore, and retention operations | **Approval-gated and undeployed** | Existing privacy strategy correctly defers legal/policy decisions, backup deletion, holds, and data-subject workflows. |
| AI, billing, queues, Redis, OCR, semantic retrieval | **Explicitly deferred** | None is currently needed to preserve the deterministic scope; each expands infrastructure, privacy, cost, or product decisions. |

## Threat-focused gap analysis

| Risk | Current control | Remaining gap | Priority |
|---|---|---|---|
| Distributed request abuse | Separate general/auth in-memory limits. | Budget resets on another replica; no provider health policy or standard response metadata. | **Critical** |
| Database resource exhaustion | Pool pre-ping, small bounded pool, request-scoped sessions. | Pool and timeout settings cannot be tuned by environment; no application statement-timeout policy. | **High** |
| Unbounded private list response | Stable owner-scoped ordering for documents and targets. | No cursor/limit contract for top-level lists; silently truncating would break clients. | **High** |
| Storage deployment mismatch | Production rejects default local storage. | No managed private adapter/provider configuration or operational object lifecycle evidence. | **High, approval/configuration gated** |
| Malicious document payload | Size, MIME/signature, container, parser resource, and private-storage controls. | No malware-scanner integration boundary or quarantine lifecycle. | **Medium** |
| Operational blind spots | Redacted logs, request IDs, safe audit events. | No internal metrics interface or centralized monitoring configuration. | **Medium** |
| Restore inconsistency | Atomic local staging and database transaction cleanup reduce normal upload inconsistency. | No documented managed-storage/database restore reconciliation procedure. | **Medium, infrastructure gated** |

## Recommended implementation order

The next implementation phase should be a **provider-ready rate-limit contract**. It will add result metadata, separate policy identities, safe `Retry-After` response behavior, a local fallback that is explicitly non-production, and validated production configuration that refuses to pretend local memory is shared. It will not add a Redis dependency, external service credential, distributed store, or production activation.

The following phase should make database pool and timeout policy configurable and testable, using existing SQLAlchemy/PostgreSQL capabilities. Any index addition must follow a query plan or data-growth evidence; none should be created solely because it appears conventional.

Top-level list pagination should be designed as a coordinated typed API/client transition. Existing document and target consumers currently receive arrays; imposing a server-side maximum is not backward-compatible. No unilateral backend truncation is recommended.

The storage and malware items should proceed as interfaces and operational decision records only unless a managed provider or scanner is approved. The existing `PrivateObjectStorage` boundary already preserves opaque identifiers, private access, controlled deletion, and no-public-URL behavior; it should not be replaced.

## Approval and configuration gates

| Gate | Classification | Required before activation |
|---|---|---|
| Shared rate-limit backend | **Configuration required** | Select/provision a shared provider or enforced gateway policy; define availability and failure policy. |
| Managed object storage | **Configuration and approval required** | Provider, region, private bucket policy, encryption/KMS, credentials, replication/versioning, deletion evidence, and access audit decisions. |
| Malware scanner | **Configuration and approval required** | Scanner provider/runtime, quarantine ownership, timeout, unavailable-scanner policy, and operational response process. |
| Central monitoring | **Configuration required** | Monitoring destination, access controls, retention, alert thresholds, and privacy review. |
| Backup/restore lifecycle | **Approval required** | Backup inventory, RPO/RTO, restore runbook, object/database reconciliation, retention, legal hold, and privacy strategy approval. |
| AI or billing | **Product, privacy, and commercial approval required** | Explicit user value, provider/processors, consent/data handling, model/payment security, costs, and support operations. |

## Audit conclusion

The repository is ready for incremental operational hardening but is not yet a fully production-ready multi-instance SaaS deployment. The proposed sequence preserves that distinction: it adds explicit provider boundaries and configuration validation where safe, documents unavailable infrastructure honestly, and refuses to replace working deterministic product systems with speculative services.
