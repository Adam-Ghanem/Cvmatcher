# CVMatcher Security Baseline

## Implemented through Phase 2

| Control | Implementation and scope |
|---|---|
| Configuration | `pydantic-settings` validates environment name, PostgreSQL configuration, explicit CORS origins, session secret length, rate-limit bounds, upload limit, and storage root. `.env` is ignored; `.env.example` contains development-only values. Production startup rejects both a development session secret and the local filesystem storage adapter. |
| Browser access | CORS permits only explicitly configured origins. Wildcard origins are rejected. Browser credential requests use `allow_credentials`; the browser client always sends credentials intentionally rather than relying on implicit defaults. |
| HTTP hardening | The API applies `X-Content-Type-Options`, `X-Frame-Options`, `Referrer-Policy`, `Permissions-Policy`, a restrictive API CSP, and production-only HSTS. |
| Authentication | Local accounts persist Argon2 password hashes in `password_credentials`; no plaintext password is persisted or intentionally logged. Account failures return safe user-facing messages. |
| Sessions | Successful login/register flows issue random opaque session cookies. PostgreSQL stores only HMAC session digests with expiry and revocation metadata. The session cookie is httpOnly, same-site, and secure outside development/test. |
| CSRF | State-changing browser routes require a readable `cvmatcher_csrf` cookie, matching `X-CSRF-Token`, and—when authenticated—a matching server-side CSRF digest. |
| Authorization | The API derives the principal from the server-side session and scopes every CV document query by both resource ID and owner ID. Clients never submit owner IDs. Unowned and absent documents share `404 RESOURCE_NOT_FOUND`. |
| Upload validation | The private-storage adapter streams file bytes to a restrictive staging file, enforces a 10 MiB maximum, normalizes client filenames, checks PDF/DOCX extension, declared MIME, and byte signature agreement, and validates DOCX container markers without extracting document text. |
| Private storage | Local development/test objects use random opaque keys, restrictive directory/file permissions, atomic moves, cleanup on failures, and no public URL or download method. Storage keys are omitted from API contracts. |
| Logging and errors | JSON logging carries correlation metadata and redacts known sensitive fields. Error envelopes remain generic and avoid storage paths, database URLs, credentials, raw CV bytes, and internal exception messages. |
| Abuse control | General and authentication route groups have bounded in-memory rate limiters. This is suitable for a single process only; distributed enforcement is explicitly deferred until horizontal scale is required. |
| Verification | CI provisions PostgreSQL, creates the isolated test database, applies Alembic migrations, then runs API lint, strict typecheck, and database-backed tests. The web job runs lint, strict typecheck, unit tests, and production build. |

## Security constraints and intentional Phase 2 limits

The Phase 2 storage adapter is a real private local development/test implementation, not production object storage. Production configuration fails rather than silently storing CVs on local disk. A managed private-storage adapter, production secret manager, HTTPS termination, database backups, operational monitoring, malware-scanning policy, and documented retention/deletion operations remain deployment prerequisites.

Phase 2 validates document structure only enough to accept safe PDF/DOCX containers; it does **not** parse, render, OCR, inspect, or execute CV content. Parser-specific resource ceilings, sandboxing, antivirus integration, and content extraction belong to the explicitly approved CV processing phase.

No API route presently downloads or publicly shares a CV. No endpoint processes job descriptions, computes a match, uses OpenAI, or accepts AI output. These absences are intentional controls, not incomplete hidden behavior.

## Required before AI and matching features

OpenAI access must remain server-side only. CVs and job descriptions must be labelled and isolated as untrusted data from system instructions. Every model response must pass strict JSON-schema/Pydantic validation, use permitted evidence references, and remain separate from deterministic score calculation. The AI phase must add prompt-injection, output-validation, cost, latency, and adversarial-document tests before release.
