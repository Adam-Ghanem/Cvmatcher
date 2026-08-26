# CVMatcher

CVMatcher is a career intelligence product designed to turn a CV and target role into transparent, evidence-backed priorities and actions. This repository implements **Phase 3: Bounded Private CV Text Extraction** on top of the Phase 1 production foundation and Phase 2 secure identity and CV intake.

Phase 3 adds explicit, owner-scoped PDF/DOCX text preparation for one immutable CV version at a time. Parsing runs in a short-lived child process from a worker thread, with an 8-second wall-clock deadline and Linux CPU/address-space limits. The service applies PDF page, DOCX archive/XML, and extracted-character ceilings, persists only a private server-side working copy, and returns status metadata rather than CV text. The workspace makes preparation explicit, communicates safe retry states, and never displays extracted content.

It intentionally does **not** render PDFs, perform OCR, accept job descriptions, calculate match scores, call OpenAI, provide recommendations, serve document downloads, add billing, add background workers or queues, add Redis, add vector storage, or introduce Ruflo.

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

## Phase 3 user flow

1. Open `/auth/register` to create a local account, or `/auth/login` to sign in.
2. The API creates an Argon2 password credential and issues an opaque, revocable httpOnly session cookie.
3. Open `/app` to access the protected CV workspace.
4. Upload one PDF or DOCX CV, up to 10 MiB. The API streams it to private staging, verifies format agreement and safe DOCX markers, then records safe metadata under the signed-in account.
5. Choose **Prepare CV text** for one owned immutable version. The API parses only that stored document in a short-lived constrained child process and stores a server-only text working copy.
6. The workspace reports preparation status, safe failure/retry guidance, and character count indirectly through the API contract. It never receives a storage key, document-download link, or the extracted CV text.

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

Phase 3 retains the Phase 2 controls and adds server-only text persistence, owner-scoped extraction status reads, an explicit CSRF-protected start action, a one-record-per-document-version invariant, and constrained PDF/DOCX parsing. Extraction uses a short-lived child process with an 8-second wall-clock cap, Linux `RLIMIT_CPU` of 4 seconds, Linux `RLIMIT_AS` of 256 MiB, a 100-page PDF cap, existing DOCX archive validation, DTD/entity rejection, and a 250,000-character output cap. API responses and the workspace expose status and safe metadata only.

The local storage adapter is for development/test only. Production requires HTTPS, a secret manager, managed PostgreSQL, a managed private object-storage implementation, observability, backups, and explicitly approved retention/deletion operations before public document intake is enabled.

No real secrets belong in the repository. Copy `.env.example` to `.env` locally and use a deployment secret manager in production.

## Documentation

| Document | Purpose |
|---|---|
| [`docs/architecture.md`](docs/architecture.md) | Actual Phase 3 component, trust-boundary, and data architecture. |
| [`docs/api.md`](docs/api.md) | Implemented versioned API surface and response contracts. |
| [`docs/security.md`](docs/security.md) | Implemented controls and deferred requirements. |
| [`docs/adr/0003-safe-cv-text-extraction.md`](docs/adr/0003-safe-cv-text-extraction.md) | Text-extraction threat model and resource-boundary decision. |
| [`docs/phase-3-implementation-report.md`](docs/phase-3-implementation-report.md) | Phase 3 implementation and verification record. |
| [`docs/adr/0001-phase-1-foundation.md`](docs/adr/0001-phase-1-foundation.md) | Initial foundation decisions. |
| [`docs/adr/0002-authentication-and-secure-cv-intake.md`](docs/adr/0002-authentication-and-secure-cv-intake.md) | Authentication and document-intake threat model. |
| [`packages/contracts/analysis-contract.md`](packages/contracts/analysis-contract.md) | Future deterministic analysis contract boundary. |

## Next phase

Phase 4 should introduce a bounded target-role/job-description intake foundation with the same ownership, validation, privacy, and error-handling standards. It must not yet perform matching, scoring, OpenAI calls, recommendations, billing, queueing, or vector indexing.
