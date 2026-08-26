# CVMatcher

CVMatcher is a career-intelligence product that turns a private CV and a private target role into transparent, evidence-backed priorities. This repository implements **Phase 5: Deterministic Evidence Matching** on top of the Phase 1 foundation, Phase 2 secure identity and CV intake, Phase 3 bounded CV text extraction, and Phase 4 secure target-role intake.

Phase 5 lets a signed-in user explicitly pair one prepared CV version with one saved target role. The API computes and persists an owner-scoped `deterministic-v2` result using fixed, source-controlled exact-match rules. The workspace presents a reproducible overall evidence match, five weighted components, bounded normalized evidence terms, and gaps labelled **“Not found in the provided CV.”** It is a planning aid, not an interview, employment, or hiring prediction.

The implementation intentionally does **not** render PDFs, perform OCR, call OpenAI, use embeddings or vector storage, infer experience or qualifications, generate recommendations, modify source documents, add billing, serve document downloads, add background workers or queues, add Redis, or introduce Ruflo.

## Prerequisites

| Tool | Supported version |
|---|---:|
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

## Phase 5 user flow

1. Open `/auth/register` to create a local account, or `/auth/login` to sign in.
2. Upload a PDF or DOCX CV, up to 10 MiB. The API stores safe metadata and private bytes under the signed-in account.
3. Choose **Prepare CV text** for one owned immutable version. Parsing is bounded and the extracted text remains server-only.
4. Define a target role and paste a job description. The raw description remains private and is never returned in target lists.
5. Under **Compare the evidence**, choose one prepared CV version and one saved target role, then choose **Create evidence match**.
6. Review the deterministic-v2 result: skills (35%), explicit experience evidence (20%), controlled keywords (25%), education (10%), and ATS-ready structural signals (10%). Use **How we calculated this** to inspect the fixed method.

The browser receives only safe document/target metadata, normalized comparison evidence, and bounded gap terms. It never receives raw CV text, raw job-description text, storage keys, document URLs, or private parser output.

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

# Dependency checks
cd ../..
pnpm audit --audit-level high
pip3 check
```

CI runs the equivalent web checks. Its API job provisions PostgreSQL, creates `cvmatcher_test`, applies `alembic upgrade head`, then runs lint, strict typechecking, and database-backed tests.

## Security baseline

Phase 5 retains the Phase 1–4 controls and adds a server-owned deterministic analysis boundary. Creating an analysis requires authentication and CSRF validation. The service owner-scopes the CV version and target role, requires a successful private extraction, uses only deterministic local rules, and persists only a private derived result. The API exposes no raw source text and returns uniform `404 RESOURCE_NOT_FOUND` responses for inaccessible CV versions, target roles, and analyses.

`deterministic-v2` uses only fixed source-controlled vocabularies and exact normalized terms. Target and CV text are untrusted document data, not instructions. The analysis response labels unmatched requirements as **“Not found in the provided CV”** and never makes a factual claim about the person behind the CV.

The local storage adapter is for development/test only. Production requires HTTPS, a secret manager, managed PostgreSQL, a managed private object-storage implementation, observability, backups, and explicitly approved retention/deletion operations before public document intake is enabled.

No real secrets belong in the repository. Copy `.env.example` to `.env` locally and use a deployment secret manager in production.

## Documentation

| Document | Purpose |
|---|---|
| [`docs/architecture.md`](docs/architecture.md) | Implemented Phase 5 component, trust-boundary, data, and persistence architecture. |
| [`docs/api.md`](docs/api.md) | Implemented versioned API surface, including match-analysis requests and metadata-only responses. |
| [`docs/security.md`](docs/security.md) | Implemented controls, Phase 5 analysis boundaries, and deferred requirements. |
| [`docs/adr/0004-deterministic-evidence-scoring.md`](docs/adr/0004-deterministic-evidence-scoring.md) | Deterministic-v2 scoring and trust-boundary decision. |
| [`docs/phase-5-implementation-report.md`](docs/phase-5-implementation-report.md) | Phase 5 implementation and verification record. |
| [`docs/phase-6-implementation-report.md`](docs/phase-6-implementation-report.md) | Phase 6 private-data deletion implementation and verification record. |
| [`docs/privacy-data-lifecycle-strategy.md`](docs/privacy-data-lifecycle-strategy.md) | Production Privacy Center, export, retention, backup, and deletion strategy requiring policy approval. |
| [`packages/contracts/analysis-contract.md`](packages/contracts/analysis-contract.md) | Implemented public deterministic analysis contract. |
| [`docs/adr/0001-phase-1-foundation.md`](docs/adr/0001-phase-1-foundation.md) | Initial foundation decisions. |
| [`docs/adr/0002-authentication-and-secure-cv-intake.md`](docs/adr/0002-authentication-and-secure-cv-intake.md) | Authentication and document-intake threat model. |
| [`docs/adr/0003-safe-cv-text-extraction.md`](docs/adr/0003-safe-cv-text-extraction.md) | Text-extraction threat model and resource-boundary decision. |

## Next phase

Phase 6 now provides authenticated, CSRF-protected user deletion for private CV documents and target roles, including dependent private lifecycle cleanup. The next bounded phase should define a privacy center and account-level deletion only after a production-grade retention, backup, and erasure design is approved. AI recommendations remain explicitly out of scope until that privacy foundation and a separate AI safety design review are complete.
