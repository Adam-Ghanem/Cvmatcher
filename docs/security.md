# CVMatcher Security Baseline

## Implemented through Phase 4

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
| Private extraction | A protected, CSRF-gated start route resolves the version by both owner and document ID before reading it server-side. One extraction record per immutable version is enforced by a unique database constraint and version-row lock. Status reads are owner-scoped and inaccessible/absent resources remain indistinguishable as `404`. |
| Parser isolation | PDF/DOCX parsing runs from a worker thread in a short-lived spawned child process. The parent uses an 8-second wall-clock limit and terminates nonresponsive workers. Linux workers apply 4-second CPU and 256 MiB address-space ceilings. |
| Parser input/output bounds | PDF parsing uses `pypdf` with a 100-page cap and rejects encrypted inputs. DOCX parsing repeats archive structure limits, reads only `word/document.xml`, rejects DTD/entity markers, and caps extracted text at 250,000 characters. |
| Sensitive text boundary | Extracted CV text is stored only in `cv_extractions.extracted_text`. API response schemas and workspace state expose status and safe metadata only; they never return, log intentionally, or display raw extracted CV text. Parsing failures persist a generic recovery message without deleting the original document. |
| Target-role intake | `POST /job-targets` derives the user from the validated session and requires CSRF. Its strict schema rejects unknown fields, bounds title/context fields and pasted job-description length, and persists the raw description only under the owner. List responses and the workspace intentionally omit the description. |
| Prompt-injection boundary | Pasted job descriptions are classified as untrusted private document content. Phase 4 does not parse requirements, invoke tools, render the full text in a list, or place it in an AI prompt. |
| Verification | CI provisions PostgreSQL, creates the isolated test database, applies Alembic migrations, then runs API lint, strict typecheck, and database-backed tests. The web job runs lint, strict typecheck, unit tests, and production build. |

## Security constraints and intentional Phase 4 limits

The local storage adapter remains a private development/test implementation, not production object storage. Production configuration fails rather than silently storing CVs on local disk. A managed private-storage adapter, production secret manager, HTTPS termination, database backups, operational monitoring, malware-scanning policy, and documented retention/deletion operations remain deployment prerequisites.

The parser process limits reduce denial-of-service risk; they are not a malware guarantee or a complete sandbox. The current `resource` CPU/address-space limits are Linux-specific. The parent wall-clock limit remains active on all supported platforms, but production deployment requires an operating-system/container sandbox review, least-privilege process permissions, malware-scanning policy, monitoring, and capacity testing before public launch.

Phase 3 and Phase 4 store sensitive private text only to support a later deterministic analysis step. Data-subject deletion, retention configuration, encryption-at-rest policy, production object-store erasure verification, and backup lifecycle controls remain required before launch. No API route downloads or publicly shares a CV, extracted text, or pasted job description. No endpoint parses job requirements, computes a match, uses OpenAI, or accepts AI output. These absences are intentional controls, not incomplete hidden behavior.

## Required before AI and matching features

OpenAI access must remain server-side only. CVs and job descriptions must be labelled and isolated as untrusted data from system instructions. Every model response must pass strict JSON-schema/Pydantic validation, use permitted evidence references, and remain separate from deterministic score calculation. The AI phase must add prompt-injection, output-validation, cost, latency, and adversarial-document tests before release.
