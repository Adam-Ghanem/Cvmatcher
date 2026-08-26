# CVMatcher

CVMatcher is a career intelligence product designed to turn a CV and target role into transparent, evidence-backed priorities and actions. This repository implements **Phase 4: Secure Target-Role Intake** on top of the Phase 1 foundation, Phase 2 secure identity and CV intake, and Phase 3 bounded CV text extraction.

Phase 4 lets a signed-in user explicitly save a target role and pasted job description as private, untrusted application data. The API validates request size and fields, derives ownership only from the session, persists the raw description server-side, and returns safe role metadata only. The workspace provides responsive target-role creation, loading, empty, error, and saved-state experiences without analysing the description.

It intentionally does **not** render PDFs, perform OCR, parse job requirements, calculate match scores, call OpenAI, provide recommendations, serve document downloads, add billing, add background workers or queues, add Redis, add vector storage, or introduce Ruflo.

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
6. Define a target role and paste the job description. The target is private and retained only as future comparison evidence; it is not yet analysed.
7. The workspace reports preparation status, safe failure/retry guidance, and target metadata. It never receives a storage key, document-download link, extracted CV text, or pasted job-description text from list responses.

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

Phase 4 retains the Phase 1–3 controls and adds owner-scoped, CSRF-protected target-role creation with strict title/company/location/description validation. Pasted job descriptions are private untrusted text in `job_targets.job_description`; safe API and workspace projections expose role metadata and a character count only. Phase 3 extraction continues to use a short-lived child process with an 8-second wall-clock cap, Linux CPU/address-space limits, PDF/DOCX bounds, and metadata-only responses.

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
| [`docs/phase-4-implementation-report.md`](docs/phase-4-implementation-report.md) | Phase 4 implementation and verification record. |
| [`docs/adr/0001-phase-1-foundation.md`](docs/adr/0001-phase-1-foundation.md) | Initial foundation decisions. |
| [`docs/adr/0002-authentication-and-secure-cv-intake.md`](docs/adr/0002-authentication-and-secure-cv-intake.md) | Authentication and document-intake threat model. |
| [`packages/contracts/analysis-contract.md`](packages/contracts/analysis-contract.md) | Future deterministic analysis contract boundary. |

## Next phase

Phase 5 should introduce a deterministic, non-AI matching and scoring foundation only after the score model, evidence references, score explanations, and adversarial test cases are agreed. It must preserve the private CV/job text boundaries and must not call OpenAI, generate recommendations, add billing, queueing, or vector indexing.
