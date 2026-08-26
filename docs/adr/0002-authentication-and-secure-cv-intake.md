# ADR 0002: Authentication and Secure CV Intake

**Status:** Accepted for Phase 2
**Date:** 2026-08-26
**Decision owners:** CVMatcher Product and Engineering

## Context

Phase 2 introduces the first externally supplied credentials and sensitive CV files. It therefore creates authentication, session, data-ownership, upload, storage, and browser trust boundaries. CV text extraction, OCR, job matching, AI, billing, queues, and public document delivery remain out of scope.

## Threat model

| Boundary | Assets at risk | Primary abuse cases | Required controls |
|---|---|---|---|
| Browser → API | Accounts, sessions, CV metadata, documents | Credential stuffing, session theft, CSRF, replay, malformed input | Argon2 password hashing, opaque httpOnly sessions, explicit CORS, same-site cookies, CSRF double-submit token, bounded auth rate limit, typed schemas. |
| Authenticated user → document API | Other users’ document metadata and files | IDOR through UUID guessing or altered route IDs | Server-derived principal, ownership-scoped queries, uniform `404` for inaccessible documents, no client-supplied owner IDs. |
| Upload stream → server | API availability, temporary filesystem, private storage | Oversized multipart bodies, type spoofing, ZIP misuse, path traversal, filename attacks | ASGI byte cap, streaming multipart parser, extension + signature agreement, DOCX container checks, opaque keys, mode-restricted staging, atomic persistence, cleanup on failure. |
| Storage → document API | Confidentiality and retention | Public links, raw path access, leaked filenames, orphaned files | Server-only storage protocol, no public URL methods, opaque IDs, private local implementation for development/test only, deletion on DB-write failure. |
| Database → application | Password credentials, sessions, ownership metadata | Token reuse, user enumeration, cross-tenant joins | Token digests, expiration/revocation, unique constraints, parameterized ORM queries, explicit owner scope. |
| Logging → operations | CV content, tokens, credentials, PII | Sensitive-data disclosure through logs | Event metadata only, field redaction, no file bytes, no credential values, no raw multipart logging. |

## Decisions

| Area | Decision | Rationale |
|---|---|---|
| Authentication | Implement local email/password registration and login with Argon2 password hashes in a dedicated `password_credentials` table. | A local workflow is required for a functioning Phase 2 and needs no third-party credentials. Keeping credentials out of `users` preserves the identity-provider boundary for a later provider addition. |
| User identity | Retain `users` as the canonical ownership anchor and use a server-generated `local:<uuid>` auth subject for local credentials. | The browser never submits a user ID or auth subject for authorization. |
| Sessions | Use high-entropy opaque random tokens, store only keyed digests in PostgreSQL, and issue an httpOnly cookie. | Opaque server-side sessions allow revocation, expiry, and auditability without exposing bearer tokens to browser JavaScript. |
| CSRF | Use a same-site, readable CSRF cookie plus matching `X-CSRF-Token` header for every state-changing endpoint. Rotate the token when a session is issued. | Cookie authentication requires explicit cross-site request protection in addition to restricted CORS. |
| Authorization | Resolve `CurrentPrincipal` from the validated server-side session, then query every document resource by both resource ID and principal user ID. | This prevents IDOR and prevents client body/query values from selecting ownership. |
| CV document model | Model a logical `cv_documents` record and immutable `cv_document_versions` records. Each version has opaque storage key, checksum, MIME type, byte count, source filename metadata, and ordered version number. | A logical document can have safe, observable versions without overwriting prior candidate documents. |
| Upload policy | Limit multipart request bodies to 10 MiB and stream the file to a private staging file. Permit only `.pdf` / `application/pdf` with `%PDF-` and `.docx` / Office MIME type with a valid Office ZIP container. | Client MIME and extensions are advisory; byte signatures and container structure are the server evidence accepted in Phase 2. No document content is interpreted or executed. |
| Storage | Implement the existing `PrivateObjectStorage` protocol with a private local filesystem adapter for development and test. Reject local storage in production configuration until a managed private object-store adapter is configured. | It provides a real, testable upload path without pretending local sandbox storage is a production object-storage solution. |
| Temporary files | Use a private staging directory, random system-created filenames, restrictive permissions, atomic moves, and best-effort cleanup on every reject/failure path. | Original filenames never become paths, and partial files cannot become visible documents. |
| API surface | Add `/auth/csrf`, `/auth/register`, `/auth/login`, `/auth/logout`, `/auth/me`, `/cv-documents`, `/cv-documents/{id}`, and `/cv-documents/{id}/versions` below `/api/v1`. | The routes are additive, typed, versioned, and keep resource operations separate from authentication. |
| Frontend access | Use native Next/React primitives and browser `XMLHttpRequest` for upload progress. Add a cookie-presence route guard plus server-authoritative `/auth/me` check. | No frontend auth, upload, form, or state library is required for the Phase 2 user flows. |

## Consequences

Phase 2 intentionally does not parse or inspect CV semantics. PDF/DOCX validation stops at allowed extension, declared MIME, byte signature, and safe DOCX container markers. Phase 3 must add parser-specific limits, isolated extraction, and extraction-result contracts before any text enters storage or later matching/AI systems.

Authentication and local private storage are production-grade foundation mechanisms, but a production deployment still requires a secret manager, HTTPS, managed PostgreSQL, and a private object-storage provider. These provider credentials are not committed or simulated in this repository.

## References

[1]: https://cheatsheetseries.owasp.org/cheatsheets/Authentication_Cheat_Sheet.html "OWASP Authentication Cheat Sheet"
[2]: https://cheatsheetseries.owasp.org/cheatsheets/File_Upload_Cheat_Sheet.html "OWASP File Upload Cheat Sheet"
[3]: https://cheatsheetseries.owasp.org/cheatsheets/Authorization_Cheat_Sheet.html "OWASP Authorization Cheat Sheet"
