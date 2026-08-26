# CVMatcher

CVMatcher is a career intelligence product designed to turn a CV and target role into transparent, evidence-backed priorities and actions. This repository currently implements **Phase 1: Production Foundation only**.

Phase 1 includes a Next.js frontend foundation, FastAPI service foundation, PostgreSQL ownership and audit schema, Alembic migrations, health/readiness checks, typed configuration, structured safe errors, correlation IDs, security headers, strict CORS, a local rate-limit boundary, tests, CI, and development container configuration.

It intentionally does **not** include CV upload/parsing, PDF/DOCX processing, scoring/matching, OpenAI calls, billing, background workers, Redis, Kafka, vector databases, or Ruflo.

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

The root `.env` file is read by the API. `NEXT_PUBLIC_API_BASE_URL` is intentionally the only browser-visible configuration value in the template; do not put secrets in variables prefixed with `NEXT_PUBLIC_`.

### Start PostgreSQL

With Docker Compose installed:

```bash
docker compose up -d postgres
```

Alternatively, create a local PostgreSQL database matching `CV_MATCHER_DATABASE_URL` in `.env`.

### Run the migration

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

## Quality checks

```bash
# Frontend
pnpm web:lint
pnpm web:typecheck
pnpm web:test
pnpm web:build

# Backend
cd services/api
ruff check .
mypy app
pytest
```

CI runs the equivalent checks on pull requests and pushes to `main`.

## Security baseline

The foundation uses a server-only API boundary, strict environment validation, allowlisted CORS origins, security headers, correlation IDs, safe error envelopes, redacted structured logs, a bounded in-memory development rate limiter, and ownership-aware database/service conventions. It does not accept document uploads yet.

No real secrets belong in the repository. Copy `.env.example` to `.env` locally and use a deployment secret manager in production.

## Architecture

The accepted Phase 1 decisions are in [`docs/adr/0001-phase-1-foundation.md`](docs/adr/0001-phase-1-foundation.md). The future deterministic-analysis boundary is documented in [`packages/contracts/analysis-contract.md`](packages/contracts/analysis-contract.md).

## Next phase

Phase 2 should introduce secure CV/job ingestion only after a dedicated storage, document-processing, retention, and threat-model review. It must not bypass the ownership, object-storage, typed-error, and migration boundaries established here.
