# Privacy-Safe Internal Observability Implementation Report

**Author:** Manus AI

## Delivered change

The API now emits one structured `request completed` event for each completed request. It records only the HTTP method, FastAPI route template, response status code, integer duration in milliseconds, and the existing correlation request ID. The event is emitted while the request correlation context remains active, so it can be joined with other safe application events without persisting CV content or credentials.

The event intentionally does not contain the raw URL, query string, headers, request body, user identifier, document identifier, filename, storage key, job text, CV text, email address, or exception message. Unmatched paths are represented as the fixed `unmatched` value rather than the user-supplied request target.

| Boundary | Behavior |
|---|---|
| Completion event | Emits method, route template, status code, duration, and correlated request ID only. |
| Route representation | Uses framework route templates, not concrete resource URLs. |
| Request targets | `httpx`, `httpcore`, and Uvicorn access loggers are raised to `WARNING` because their INFO access messages may contain full request targets and query strings. |
| Existing application logs | Continue using JSON formatting, correlation IDs, recursive sensitive-field redaction, and allowlisted event metadata. |
| External monitoring | Not configured or claimed. |
| Logs, metrics, traces, alerting, retention, and access controls | Remain operational deployment decisions and are not implemented by this change. |

## Verification

A new regression test submits a private-looking query value and asserts that the completion event uses the safe route template and contains no raw query or raw path field. The complete backend gate passed: Ruff, mypy, and 103 pytest tests all passed. The only warning is the pre-existing Starlette TestClient/httpx deprecation warning.

## Deferred operational decisions

A production observability deployment still needs approved choices for log sink, metric/tracing provider, dashboard and alert definitions, retention, encryption, regional processing, access control, incident access, auditability, and costs. Those decisions must preserve the current redaction and data-minimization boundaries. This implementation does not send telemetry to an external provider and must not be represented as centralized monitoring.
