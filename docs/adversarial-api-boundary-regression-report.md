# Adversarial API Boundary Regression Report

**Author:** Manus AI

## Delivered browser-throttling boundary

The API already emits `RateLimit-Limit`, `RateLimit-Remaining`, `RateLimit-Reset`, and, when applicable, `Retry-After` on rate-limited request paths. This phase closes a browser interoperability gap: those response headers are now exposed to explicitly allowed CORS origins alongside `X-Request-ID`. A browser client can therefore display a safe retry state and honor a backoff period without inferring limits from response text.

The CORS allowlist remains explicit, credentials remain enabled only for those configured origins, and request headers remain restricted to the existing safe list. No wildcard origin, client-controlled limiter key, authentication bypass, or new network dependency was introduced.

| Adversarial condition | Verified behavior |
|---|---|
| Allowed cross-origin browser request | Can read the request ID and rate-limit/retry response headers. |
| Unauthorized request | Remains a safe `401` while retaining its policy-specific rate-limit headers. |
| Rate-limit service failure | Existing fail-closed `503 RATE_LIMIT_UNAVAILABLE` behavior remains unchanged. |
| Raw CV/job/query content | Not added to CORS headers, logs, or error contracts. |
| Untrusted forwarding headers | No trust policy was introduced; limiter identity remains the deployment-provided request client address. |

## Explicit limits

This regression addition does not make local rate limiting distributed and does not configure trusted proxy forwarding rules. A real deployment must choose its shared provider and a strict trusted-proxy/client-IP policy before operating multiple instances. It also does not add malware scanning, managed object storage, central telemetry, backups, retention lifecycle jobs, AI, OCR, or pagination changes.
