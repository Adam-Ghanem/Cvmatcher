# ADR 0001: CVMatcher Phase 1 Production Foundation

**Status:** Accepted for Phase 1
**Date:** 2026-08-26
**Decision owners:** CVMatcher Product and Engineering

## Context

CVMatcher is a greenfield, privacy-sensitive career intelligence SaaS. Phase 1 must establish an extensible, secure foundation only. It must not implement CV parsing, CV matching, AI analysis, billing, background workers, vector search, or multi-agent orchestration. The architecture must make later implementation safe without adding premature infrastructure.

## Decisions

| Area | Decision | Rationale and Phase 1 boundary |
|---|---|---|
| 1. Frontend architecture | Use a TypeScript-strict Next.js App Router application in `apps/web` with Tailwind CSS, server-rendered routes by default, and small client components only for interaction. | Next.js provides a coherent web foundation while retaining SEO-ready server rendering for public pages. Phase 1 establishes design tokens, a responsive application shell, accessible primitives, and a typed API-client boundary; it does not implement authenticated product flows. |
| 2. Backend architecture | Use a modular FastAPI application in `services/api`, with routers, Pydantic v2 schemas, domain services, and infrastructure adapters separated by package. | FastAPI and Pydantic meet the required stack while maintaining typed HTTP boundaries. A modular monolith is simpler to secure, test, deploy, and evolve than microservices. |
| 3. PostgreSQL data model | Use PostgreSQL through SQLAlchemy 2.x and Alembic. Phase 1 creates a `users` ownership anchor, an `audit_events` baseline, and a migration history. | User-owned CV, job, and analysis records will require a stable ownership relationship. Versioned migrations make later data evolution reviewable. Raw CV content is not stored in the database. |
| 4. Authentication and authorization | Define a pluggable `CurrentPrincipal` boundary and ownership-aware repository/service conventions. Do not implement a public sign-in provider in Phase 1. | Authentication-provider selection has data, UX, and commercial consequences. Phase 1 avoids a fake auth implementation while ensuring every future user-owned query is designed around server-derived identity rather than client-supplied owner IDs. OWASP recommends deny-by-default, least privilege, and authorization checks on every request.[1] |
| 5. Private CV storage | Define a `PrivateObjectStorage` protocol, with no public bucket, public URL, or browser credentials. Do not store CVs or implement uploads in Phase 1. | CV documents are sensitive and must later be stored with opaque keys and server-authorized access only. This preserves storage-provider choice without creating a fake storage integration. |
| 6. PDF/DOCX extraction | Reserve a document-processing domain boundary but add no parser dependency or extraction code in Phase 1. | PDF/DOCX parsing requires a dedicated threat model, size/resource limits, temporary-file handling, and malicious-document tests. OWASP recommends allowlisting required formats, content validation, generated filenames, private storage, and limits.[2] |
| 7. Deterministic matching engine | Reserve a pure `matching` domain with versioned input/output contracts; do not calculate a score in Phase 1. | Scores must later be reproducible, evidence-backed, and independent of an LLM. Starting with a contract prevents business logic from leaking into routes or UI. |
| 8. OpenAI integration | Define a server-only adapter boundary and explicit configuration placeholder; do not include an SDK, key, or API call in Phase 1. | An OpenAI integration is not required for the production foundation. Adding it without a constrained, evidence-backed use case would increase security and cost risk. Future requests must use strict structured output plus Pydantic/domain validation.[3] |
| 9. API contracts | Version HTTP routes under `/api/v1`; use Pydantic input/output schemas; return a single structured error envelope; propagate an `X-Request-ID` correlation identifier. | Stable, typed boundaries reduce frontend-backend coupling. Health endpoints are the only Phase 1 public API surface. |
| 10. Security boundaries | Treat browser input, HTTP headers, configuration, files, databases, and future model output as untrusted. Enforce typed settings, restricted CORS, security headers, path-safe storage conventions, redacted structured logs, and a pluggable rate-limit interface. | Security controls belong in the foundation, not a later hardening pass. In-memory rate limiting is suitable only for local/single-process Phase 1; the interface permits a production backing store when actual traffic architecture requires it. |
| 11. Testing architecture | Use pytest for backend unit/integration tests and Vitest with Testing Library for frontend tests. Keep tests local, deterministic, and behavior-focused; use an isolated PostgreSQL database when integration tests are enabled. | Phase 1 must prove configuration validation, health/readiness behavior, security headers/CORS behavior, error envelopes, API client behavior, and responsive component rendering. |
| 12. Deployment architecture | Use one repository with independently buildable web and API containers, a PostgreSQL development service in Compose, GitHub Actions CI, typed environment templates, and documented local commands. | Separate deployable processes fit the mandated stack without adding queues, Redis, Kafka, vector databases, or microservices. Production object storage, managed PostgreSQL, identity provider, and secret manager remain provider decisions rather than hardcoded infrastructure. |

## Project structure

```text
apps/web/                 Next.js frontend
services/api/             FastAPI backend
packages/contracts/       Versioned cross-boundary contract documentation
infra/                    Compose and container configuration
docs/adr/                 Architecture decisions
.github/workflows/        Continuous integration
```

## Consequences

Phase 1 deliberately uses interfaces where provider or policy decisions require later evidence. It will provide a real executable frontend, backend, database connection abstraction, migrations, health/readiness checks, error handling, security middleware, tests, CI, and documentation. It will not simulate completed CV analysis functionality.

The first architecture reassessment is required before implementing Phase 2 document ingestion because that phase introduces sensitive document data, a storage provider, parser dependencies, retention behavior, and potentially asynchronous processing requirements.

## References

[1]: https://cheatsheetseries.owasp.org/cheatsheets/Authorization_Cheat_Sheet.html "OWASP Authorization Cheat Sheet"
[2]: https://cheatsheetseries.owasp.org/cheatsheets/File_Upload_Cheat_Sheet.html "OWASP File Upload Cheat Sheet"
[3]: https://developers.openai.com/api/docs/guides/structured-outputs "OpenAI Structured model outputs"
