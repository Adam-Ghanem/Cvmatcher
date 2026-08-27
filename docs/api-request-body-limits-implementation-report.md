# API Request-Body Limits Implementation Report

**Author:** Manus AI

**Scope:** Backend API hardening only

## Audit finding

The existing API already applied explicit CORS, safe error envelopes, request correlation, security response headers, authenticated-session controls, CSRF enforcement, and separate process-local rate limits for general and authentication traffic. The document-upload service also streamed individual PDF/DOCX files with a 10 MiB cap. However, no application-level boundary rejected oversized non-upload request bodies before they reached routing, and a chunked request without a trustworthy `Content-Length` could not be bounded by the earlier configuration alone.

The audit also identified unpaginated CV-document and target-role list endpoints. Correctly making those collections bounded requires a matching client pagination experience; the current product instruction explicitly prohibits frontend changes in this backend-only autonomous pass. That compatibility-sensitive work is deferred rather than silently truncating a user’s workspace data.

## Implemented boundary

The implementation adds a validated `max_request_body_bytes` setting with a 256 KiB default and a permitted range of 1 KiB to 5 MiB. This is sufficient for the existing bounded JSON contracts, including the maximum accepted job-description request, while preventing arbitrary-size generic request bodies.

A framework-level ASGI middleware applies the correct limit before application parsing. It rejects an oversized declared `Content-Length` immediately and wraps the ASGI `receive` callable to count every streamed request chunk. Once the cumulative byte count crosses the request-class limit, it raises the existing safe `ApiException` with a `413 REQUEST_TOO_LARGE` response. The existing request-context middleware converts the error into the standard redacted envelope, adds a request ID and security headers, and the unchanged outer CORS middleware supplies the configured allowed-origin response header.

| Request class | Bound | Enforcement |
|---|---:|---|
| JSON and other non-upload HTTP requests | 256 KiB default, configurable within 1 KiB–5 MiB | Early declared-size rejection and cumulative streamed-byte rejection. |
| Multipart document requests | Existing 10 MiB file cap plus the configured non-upload amount for the multipart envelope | Early declared-size rejection and cumulative streamed-byte rejection, followed by the existing private upload stream’s independent per-file cap. |

No score, extraction semantics, storage behavior, authorization rule, database schema, migration, external integration, frontend application code, dependency, or lockfile changed.

## Regression coverage

The focused regression tests prove that an oversized declared generic request is rejected before endpoint routing with the stable `413 REQUEST_TOO_LARGE` envelope, a correlation ID, required security headers, and an allowed-origin CORS header. A direct ASGI-level test proves a request that arrives over multiple chunks is rejected when its cumulative body exceeds the configured limit without relying on `Content-Length`. Configuration tests cover the generic limit’s lower bound and the multipart envelope derivation.

| Validation | Result |
|---|---|
| Red test: oversized declared request before routing | Failed as expected before the middleware: endpoint returned `405`. |
| Focused request-limit/configuration tests | Passed: 13 tests. |
| API lint | Passed. |
| API strict typecheck | Passed for 69 source files. |
| Full API regression suite | Passed: 81 tests, with one pre-existing Starlette/httpx deprecation warning. |

## Operational limits retained

Application middleware cannot prevent network bandwidth or reverse-proxy buffering before a request reaches the API process. Production ingress must therefore enforce matching body-size limits and request timeouts. The process-local rate limiter remains intentionally unchanged and is not a distributed abuse-control mechanism. The existing production requirements for managed private object storage, secret management, operational monitoring, malware scanning, and approval-gated privacy lifecycle controls remain unchanged.
