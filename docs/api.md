# CVMatcher API

All implemented routes are versioned under `/api/v1`. Success and error payloads use JSON. Errors use the shared envelope below and include a correlation identifier in both the body and `X-Request-ID` response header.

```json
{
  "error": {
    "code": "AUTHENTICATION_REQUIRED",
    "message": "Sign in to continue.",
    "requestId": "uuid"
  }
}
```

## Operational routes

| Method | Route | Authentication | Purpose |
|---|---|---:|---|
| `GET` | `/health` | No | Process health response. |
| `GET` | `/ready` | No | PostgreSQL readiness response; returns `503` when unavailable. |

## Account and session routes

| Method | Route | CSRF | Purpose |
|---|---|---:|---|
| `GET` | `/auth/csrf` | No | Issues or rotates the browser CSRF token. When a valid session cookie exists, the API rotates its server-side CSRF digest too. |
| `POST` | `/auth/register` | Yes | Creates a local account with an Argon2 password hash and starts an opaque session. |
| `POST` | `/auth/login` | Yes | Verifies a local account credential and starts an opaque session. |
| `GET` | `/auth/me` | Session | Returns the safe public user projection. |
| `POST` | `/auth/logout` | Session + CSRF | Revokes the server-side session and clears browser cookies. |

`POST /auth/register` and `POST /auth/login` accept this strict JSON object. Unknown fields are rejected.

```json
{
  "email": "candidate@example.com",
  "password": "at-least-twelve-characters"
}
```

Successful account responses return only public identity fields:

```json
{
  "user": {
    "id": "uuid",
    "email": "candidate@example.com",
    "createdAt": "2026-08-26T00:00:00Z"
  }
}
```

The browser receives an httpOnly `cvmatcher_session` cookie and a readable `cvmatcher_csrf` cookie. Every state-changing browser call sends the matching token in `X-CSRF-Token`. Raw session tokens, password hashes, session digests, CSRF digests, storage keys, and auth subjects never appear in API responses.

## CV document routes

All document routes require the validated opaque session cookie. Upload routes also require `X-CSRF-Token`. The API derives ownership solely from the server-side session.

| Method | Route | Purpose |
|---|---|---|
| `GET` | `/cv-documents` | Lists the authenticated user’s logical CV documents with their latest version. |
| `POST` | `/cv-documents` | Streams one PDF or DOCX into private storage and creates document version `1`. Multipart field: `file`. |
| `GET` | `/cv-documents/{document_id}` | Retrieves safe metadata for one owned document. |
| `GET` | `/cv-documents/{document_id}/versions` | Lists immutable safe metadata for all versions of one owned document. |
| `POST` | `/cv-documents/{document_id}/versions` | Streams another PDF or DOCX as the next immutable version. Multipart field: `file`. |

Uploads are limited to **10 MiB**. Phase 2 accepts only a `.pdf` with `application/pdf` and the `%PDF-` byte signature, or a `.docx` with the canonical Office MIME type, ZIP signature, and safe Office container markers. Phase 2 does not parse document text or offer document downloads.

A document response exposes safe metadata only:

```json
{
  "id": "uuid",
  "title": "candidate-cv",
  "createdAt": "2026-08-26T00:00:00Z",
  "updatedAt": "2026-08-26T00:00:00Z",
  "latestVersion": {
    "id": "uuid",
    "versionNumber": 1,
    "originalFilename": "candidate-cv.pdf",
    "contentType": "application/pdf",
    "byteSize": 183204,
    "uploadedAt": "2026-08-26T00:00:00Z"
  }
}
```

For a missing or unowned document, the API returns the same `404 RESOURCE_NOT_FOUND` envelope. This avoids cross-user document-existence disclosure.

## Phase boundary

No current API endpoint parses a CV, accepts a job description, computes a match, sends data to an LLM, generates recommendations, serves uploaded file bytes, supports billing, or runs background work. Those boundaries remain deferred to later approved phases.
