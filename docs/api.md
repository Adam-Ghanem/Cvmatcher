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

Successful account responses return only public identity fields. The browser receives an httpOnly `cvmatcher_session` cookie and a readable `cvmatcher_csrf` cookie. Every state-changing browser call sends the matching token in `X-CSRF-Token`. Raw session tokens, password hashes, session digests, CSRF digests, storage keys, and auth subjects never appear in API responses.

## CV document routes

All document routes require the validated opaque session cookie. Upload routes also require `X-CSRF-Token`. The API derives ownership solely from the server-side session.

| Method | Route | Purpose |
|---|---|---|
| `GET` | `/cv-documents` | Lists the authenticated user’s logical CV documents with their latest version. |
| `POST` | `/cv-documents` | Streams one PDF or DOCX into private storage and creates document version `1`. Multipart field: `file`. |
| `GET` | `/cv-documents/{document_id}` | Retrieves safe metadata for one owned document. |
| `GET` | `/cv-documents/{document_id}/versions` | Lists immutable safe metadata for all versions of one owned document. |
| `POST` | `/cv-documents/{document_id}/versions` | Streams another PDF or DOCX as the next immutable version. Multipart field: `file`. |
| `DELETE` | `/cv-documents/{document_id}` | CSRF-protected owner deletion of a CV document, all immutable versions, server-only extractions, derived analyses, and its private stored objects. |

Uploads are limited to **10 MiB**. The API accepts only a `.pdf` with `application/pdf` and the `%PDF-` signature, or a `.docx` with the canonical Office MIME type, ZIP signature, and safe Office container markers. Document responses expose safe metadata only, never raw bytes, storage keys, or download URLs. Missing and unowned documents share `404 RESOURCE_NOT_FOUND`.

## CV extraction routes

Extraction routes require the validated opaque session cookie. Starting extraction also requires `X-CSRF-Token`. The API derives ownership from the session and scopes the document/version lookup by both IDs and the authenticated principal.

| Method | Route | CSRF | Purpose |
|---|---|---:|---|
| `GET` | `/cv-documents/{document_id}/versions/{version_id}/extraction` | No | Returns safe metadata for an existing owned extraction record without parsing again. |
| `POST` | `/cv-documents/{document_id}/versions/{version_id}/extraction` | Yes | Explicitly creates or retries constrained private text preparation for an owned immutable version. A successful existing record is reused. |

Both routes return safe extraction metadata only:

```json
{
  "id": "uuid",
  "status": "succeeded",
  "sourceType": "pdf",
  "characterCount": 14218,
  "parserVersion": "bounded-text-v2",
  "quality": "usable",
  "warnings": [],
  "readiness": {
    "state": "ready",
    "explanation": "This document is ready for deterministic comparison.",
    "recoveryGuidance": null
  },
  "completedAt": "2026-08-26T00:00:00Z",
  "failureMessage": null
}
```

`status` is one of `pending`, `processing`, `succeeded`, or `failed`. `quality` is authoritative extraction metadata (`unknown`, `low`, `limited`, or `usable`); the nested `readiness` object is derived deterministically from that metadata and is never persisted separately. `readiness.state` is `ready`, `warning`, or `blocked`. Ready and warning records can be selected for deterministic comparison; warning records return concise recovery guidance because their readable content is limited. Blocked records cannot be analyzed. `warnings` contains only bounded, allowlisted identifiers; the current values are `NO_EXTRACTABLE_TEXT` and `LIMITED_EXTRACTABLE_TEXT`.

No response contains extracted text, a private storage key, raw document bytes, parser diagnostics, or an internal stack trace. A missing, unowned, or not-yet-created extraction uses the shared `404 RESOURCE_NOT_FOUND` envelope.

## Target-role routes

Target-role routes require the validated opaque session cookie. Creation also requires `X-CSRF-Token`. The API derives ownership exclusively from the authenticated session; browser clients never submit a user ID.

| Method | Route | CSRF | Purpose |
|---|---|---:|---|
| `GET` | `/job-targets` | No | Lists safe metadata for the signed-in user’s private target roles. |
| `POST` | `/job-targets` | Yes | Saves one private, untrusted target role and pasted job description. |
| `DELETE` | `/job-targets/{target_id}` | Yes | Deletes one owned private target role and dependent analyses. |

Creation accepts a strict JSON object with no unknown fields. `title` is 2–180 characters; optional `company` and `location` are at most 180 characters; `jobDescription` is 80–50,000 characters after whitespace trimming.

```json
{
  "title": "Staff platform engineer",
  "company": "Northstar Systems",
  "location": "Remote",
  "jobDescription": "Untrusted private pasted job-description text..."
}
```

Creation and listing return safe metadata including `jobDescriptionCharacterCount`; `jobDescription` is intentionally omitted from every public target response. Both delete routes return `204 No Content` only after an explicit authenticated owner action and valid CSRF token. A missing or another user’s document/target returns the same `404 RESOURCE_NOT_FOUND` response; the browser presents an irreversible-action confirmation before submitting the delete request.

## Deterministic match-analysis routes

Match-analysis routes require the validated opaque session cookie. Creating or reusing an analysis also requires `X-CSRF-Token`. The server derives ownership from the session, never from request data. CV and target references belonging to another user are indistinguishable from missing resources.

| Method | Route | CSRF | Purpose |
|---|---|---:|---|
| `POST` | `/match-analyses` | Yes | Creates or reuses the `deterministic-v2` analysis for one owned CV version and one owned target role. |
| `GET` | `/match-analyses/{analysis_id}` | No | Retrieves one owned persisted analysis result. |

Creation accepts exactly this strict JSON object. Unknown fields are rejected.

```json
{
  "cvDocumentVersionId": "uuid",
  "jobTargetId": "uuid"
}
```

A successful response returns metadata-only, bounded analysis evidence. It does not include either source text, resource IDs, storage keys, file URLs, or user IDs.

```json
{
  "id": "uuid",
  "scoringVersion": "deterministic-v2",
  "overallScore": 88,
  "components": [
    {
      "key": "skills",
      "label": "Skills match",
      "weight": 35,
      "score": 100,
      "state": "MATCHED",
      "matchedTerms": ["docker", "python"],
      "notFoundTerms": [],
      "explanation": "Uses exact normalized evidence terms from the provided CV and target description."
    }
  ],
  "gaps": [
    {
      "term": "automation",
      "state": "NOT_FOUND_IN_PROVIDED_CV",
      "component": "keywords"
    }
  ],
  "createdAt": "2026-08-26T00:00:00Z"
}
```

Component `state` is one of `MATCHED`, `PARTIAL`, `EVIDENCE_NOT_FOUND`, or `NOT_APPLICABLE`. Gap state is always `NOT_FOUND_IN_PROVIDED_CV`; it means evidence was not found in the submitted CV text, not that the person lacks the skill or credential. `overallScore` and every component score are integers in the inclusive `0`–`100` range. The score is an explainable planning aid, not a hiring or interview prediction.

`POST /match-analyses` returns `409 CV_TEXT_NOT_READY` when the selected owned version has no analysis-eligible private extraction, including a readiness state of `blocked`. It returns `404 RESOURCE_NOT_FOUND` for absent or inaccessible CV versions, targets, and analysis IDs. Repeating the same owned CV version, target role, and scoring version returns the existing persisted result rather than creating a duplicate.

## Deliberate boundaries

The implemented API does not call an LLM, use semantic retrieval, infer qualifications, generate recommendations, modify source CVs or target roles, serve document bytes, add billing, run a background queue, or expose raw private CV/job text. These are intentional security and product boundaries, not hidden behavior.
