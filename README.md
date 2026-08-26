# CVMatcher

CVMatcher is a career intelligence product designed to turn a CV and target role into transparent, evidence-backed priorities and actions. This repository implements **Phase 2: Secure Identity and CV Intake** on top of the Phase 1 production foundation.

Phase 2 adds local account registration/login, opaque server-side sessions, CSRF protection, ownership-scoped CV document metadata, immutable document versions, private PDF/DOCX intake, PostgreSQL-backed integration tests, responsive account/CV workspace UX, and CI database migration verification.

It intentionally does **not** parse CV text, render PDFs, perform OCR, accept job descriptions, calculate match scores, call OpenAI, provide recommendations, serve document downloads, add billing, add background workers, add Redis, add vector storage, or introduce Ruflo.

## Prerequisites

| Tool | Supported version |
|---|---|
| Node.js | 22.x |
| pnpm | 11.21.0 |
| Python | 3.12.x |
| PostgreSQL | 16.x or later, or Docker Compose for local PostgreSQL |

## First-time setup

```bash
cp .env.example .env
pnpm install --frozen-lockfile
sudo pip3 install -e "./services/api[dev]"
```

The root `.env` file is read by the API. `NEXT_PUBLIC_API_BASE_URL` is intentionally the only browser-visible configuration value in the template. Do not put secrets in `NEXT_PUBLIC_*` variables.

`CV_MATCHER_SESSION_HMAC_SECRET` must be replaced with a production secret outside source control. Production configuration rejects the development example secret and local filesystem document storage.

### Start PostgreSQL

With Docker Compose installed:

```bash
docker compose up -d postgres
```

Alternatively, create a local PostgreSQL database matching `CV_MATCHER_DATABASE_URL` in `.env`.

### Apply migrations

```bash
cd services/api
alembic upgrade head
cd ../..
```

### Start the services

In one terminal:

```bash
pnpm web:dev
```

In another terminal:

```bash
cd services/api
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```

The frontend runs at `http://localhost:3000`. The API health endpoint is `http://localhost:8000/api/v1/health`; readiness is `http://localhost:8000/api/v1/ready` and reports ready only after PostgreSQL is reachable.

## Phase 2 user flow

1. Open `/auth/register` to create a local account, or `/auth/login` to sign in.
2. The API creates an Argon2 password credential and issues an opaque, revocable httpOnly session cookie.
3. Open `/app` to access the protected CV workspace.
4. Upload one PDF or DOCX CV, up to 10 MiB. The API streams it to private staging, verifies format agreement and safe DOCX markers, then records safe metadata under the signed-in account.
5. The workspace lists logical CV documents and latest immutable versions. It never receives a private storage key or document-download link.

## Quality checks

```bash
# Frontend
pnpm web:lint
pnpm web:typecheck
pnpm web:test
pnpm web:build

# Backend (requires the migrated local test database from the verification workflow)
cd services/api
ruff check .
mypy app
pytest
```

CI runs the equivalent web checks. Its API job provisions PostgreSQL, creates `cvmatcher_test`, applies `alembic upgrade head`, then runs lint, strict typechecking, and database-backed tests.

## Security baseline

Phase 2 uses explicit CORS origins, security headers, correlation IDs, safe error envelopes, redacted structured logs, Argon2 credential hashes, opaque server-side sessions, CSRF validation, owner-scoped queries, PDF/DOCX signature/container validation, a 10 MiB streaming limit, private opaque storage keys, and cleanup paths for failed document persistence.

The local storage adapter is for development/test only. Production requires HTTPS, a secret manager, managed PostgreSQL, a managed private object-storage implementation, observability, backups, and explicitly approved retention/deletion operations before public document intake is enabled.

No real secrets belong in the repository. Copy `.env.example` to `.env` locally and use a deployment secret manager in production.

## Documentation

| Document | Purpose |
|---|---|
| [`docs/architecture.md`](docs/architecture.md) | Actual Phase 2 component, trust-boundary, and data architecture. |
| [`docs/api.md`](docs/api.md) | Implemented versioned API surface and response contracts. |
| [`docs/security.md`](docs/security.md) | Implemented controls and deferred requirements. |
| [`docs/adr/0001-phase-1-foundation.md`](docs/adr/0001-phase-1-foundation.md) | Initial foundation decisions. |
| [`docs/adr/0002-authentication-and-secure-cv-intake.md`](docs/adr/0002-authentication-and-secure-cv-intake.md) | Authentication and document-intake threat model. |
| [`packages/contracts/analysis-contract.md`](packages/contracts/analysis-contract.md) | Future deterministic analysis contract boundary. |

## Next phase

Phase 3 may introduce safe CV PDF/DOCX text extraction only after parser isolation, resource ceilings, malicious-document fixtures, extraction contracts, and data retention/deletion policy are approved. It must preserve Phase 2 ownership, private storage, typed error, session, and document-version boundaries.
