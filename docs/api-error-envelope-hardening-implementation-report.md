# API Error Envelope Hardening Implementation Report

**Author:** Manus AI

**Scope:** Safe, consistent responses for framework-generated API errors

## Audit finding

The application already returned structured, correlated error envelopes for domain exceptions, request-validation failures, request-size enforcement, and unexpected internal errors. However, FastAPI/Starlette generated its default `{"detail": ...}` response body for unmatched API paths and unsupported methods. Those responses did not use the product’s documented error schema, despite still receiving security headers and a request ID from middleware.

## Implemented control

The API now has a central handler for framework HTTP exceptions. It maps unknown resources to `RESOURCE_NOT_FOUND` with HTTP 404 and unsupported methods to `METHOD_NOT_ALLOWED` with HTTP 405. Other framework HTTP status errors receive the generic `REQUEST_ERROR` code with the original HTTP status. Each response is generated through the existing error-envelope helper and therefore contains the standard `error.code`, safe `error.message`, and request correlation ID.

The handler preserves protocol-required framework headers. In particular, a 405 response continues to include `Allow`, enabling a client to recover without exposing framework-specific response bodies. It does not echo exception detail text, request values, internal paths, storage references, credentials, or stack traces.

| Response category | HTTP status | Safe code | Correlation and security headers |
|---|---:|---|---|
| Unknown API path | 404 | `RESOURCE_NOT_FOUND` | Preserved by existing middleware. |
| Unsupported API method | 405 | `METHOD_NOT_ALLOWED` | Preserved, including the `Allow` protocol header. |
| Other framework HTTP exception | Original status | `REQUEST_ERROR` | Preserved by existing middleware. |
| Domain/API exception | Existing status | Existing explicit code | Unchanged. |
| Validation failure | 422 | `VALIDATION_ERROR` | Unchanged. |
| Unexpected failure | 500 | `INTERNAL_ERROR` | Unchanged; only exception class is logged. |

## Regression coverage and verification

New regressions verify that both 404 and 405 responses use the safe envelope rather than `detail`, include the correlation ID and security headers, and retain the 405 `Allow` header. The complete backend quality gate passed: Ruff lint, strict mypy for 69 source files, and 88 tests. The suite continues to emit one pre-existing Starlette/httpx deprecation warning.

## Deliberate boundaries

This phase does not convert non-API browser/static hosting failures, introduce content negotiation, change status-code semantics, expose debugging detail, or add an external error-tracking service. Operational alerting, distributed rate limiting, and managed production observability remain separate deployment decisions.
