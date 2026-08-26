# CVMatcher Architecture

## Implemented Phase 2 architecture

CVMatcher is a modular monorepo with a Next.js frontend and a FastAPI backend. The services are independently buildable, but the product remains a deliberately simple single-application architecture: one browser client, one API, one PostgreSQL database, and one private-storage adapter boundary. It does not use microservices, queues, Redis, vector storage, billing infrastructure, or AI orchestration.

```mermaid
flowchart LR
  Browser[Browser] -->|HTTPS / cookie session| Web[apps/web: Next.js]
  Browser -->|HTTPS / JSON and multipart| API[services/api: FastAPI]
  Web -->|UX route guard only| Browser
  API -->|typed SQLAlchemy queries| DB[(PostgreSQL)]
  API -->|server-only opaque keys| Storage[Private object storage adapter]
  API --> Logs[Redacted structured logs]
  API -. future server-only adapter .-> OpenAI[OpenAI]
```

## Repository layout

| Path | Responsibility |
|---|---|
| `apps/web` | TypeScript-strict Next.js App Router frontend, Tailwind tokens, cookie-aware typed API client, accessible account and CV intake experiences, browser tests. |
| `services/api` | FastAPI application, Pydantic settings/schemas, SQLAlchemy models, Alembic migrations, ownership-scoped API services, and API/security integration tests. |
| `packages/contracts` | Versioned product-contract documentation for future deterministic analysis results. |
| `docs/adr` | Recorded architecture and security decisions. |
| `compose.yaml` | Development PostgreSQL configuration. |

## Identity and session boundary

The browser submits credentials only to the API. The API hashes passwords with Argon2 and persists only `password_credentials.password_hash`; plaintext credentials are neither persisted nor logged. Local identity remains attached to the existing `users` ownership anchor through a server-generated `local:<uuid>` subject.

A successful registration or login issues a high-entropy opaque session cookie. PostgreSQL stores an HMAC digest of that token, its expiration, revocation timestamp, and hashed request metadata. Browser JavaScript cannot read the session cookie. A readable CSRF cookie is paired with an `X-CSRF-Token` header and a server-side token digest for state-changing authenticated routes.

The Next.js `proxy.ts` provides a browser-level route guard for `/app`, but it is intentionally not the authorization authority. Every protected FastAPI route resolves the session on the server and derives the principal from the validated session.

## Document intake boundary

Phase 2 persists only document bytes and safe metadata. It does **not** parse CV text, run OCR, extract skills, perform matching, send content to OpenAI, or serve document downloads.

| Layer | Implemented responsibility |
|---|---|
| Browser | Selects a PDF or DOCX, reports byte-upload progress, and presents typed recoverable errors. |
| API route | Requires a server-derived session and valid CSRF token. It never accepts client-provided ownership IDs. |
| Intake adapter | Streams uploads into private staging files, enforces a 10 MiB file limit, normalizes filenames, verifies extension/declaration/signature agreement, and validates DOCX container markers without extracting content. |
| Private storage | Uses a local development/test adapter with restrictive staging/object permissions and server-generated opaque keys. It exposes no public URL or download route. |
| PostgreSQL | Stores user-owned logical documents and immutable versions, metadata, checksums, and opaque storage keys. API projections omit the key. |

## Database model

| Table | Role |
|---|---|
| `users` | Canonical user ownership anchor. |
| `password_credentials` | One local Argon2 credential hash per user. |
| `user_sessions` | Revocable opaque session and CSRF token digests with expiration. |
| `cv_documents` | Logical user-owned CV record. |
| `cv_document_versions` | Immutable uploaded version metadata and opaque object key. |
| `audit_events` | Existing non-content security-event metadata foundation. |

All document queries include both the document identifier and the authenticated user ID. A resource that is absent or belongs to another account returns the same `404` response, so document existence is not disclosed across tenants.

## Deployment boundary

The web and API services each have a container definition. Development PostgreSQL is provided through Compose. CI provisions PostgreSQL, applies Alembic migrations, and runs database-backed integration tests. The local filesystem storage adapter is accepted only for development/test; production configuration rejects it and must receive a managed private object-storage implementation before document intake is enabled.

Production still requires HTTPS termination, a managed PostgreSQL service, production secret management, a private object-storage adapter, operational monitoring, and backup/retention decisions. These provider credentials and decisions are not encoded in this repository.
