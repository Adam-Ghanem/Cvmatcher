# CVMatcher Security Baseline

## Implemented in Phase 1

| Control | Implementation |
|---|---|
| Configuration | `pydantic-settings` validates required database configuration, environment name, log level, CORS values, and rate limit bounds. `.env` is ignored; `.env.example` contains no secret. |
| Browser access | CORS permits only explicitly configured origins. Wildcard origins are rejected by settings validation. |
| HTTP hardening | The API applies `X-Content-Type-Options`, `X-Frame-Options`, `Referrer-Policy`, `Permissions-Policy`, a restrictive API CSP, and production-only HSTS. |
| Correlation | A valid UUID correlation ID is propagated or a server ID is generated. Untrusted header strings are not reflected. |
| Error handling | API errors use a safe typed envelope. Unhandled exceptions are logged internally and return a generic customer-facing message. |
| Logging | JSON logging carries correlation metadata and redacts known sensitive field names, including authorization, token, secret, password, and document-content keys. |
| Abuse control | An in-memory request limiter is applied to non-health routes. It is explicitly a single-process Phase 1 control, not a horizontal-scale solution. |
| Ownership preparation | `users` is the ownership anchor. `CurrentPrincipal` and `require_owner` make future access checks server-derived rather than client-supplied. |
| Dependency baseline | JavaScript audit and Python dependency consistency checks are part of verification; CI runs lint, typecheck, tests, and build. |

## Not implemented by design

Phase 1 does not accept or persist CVs, job descriptions, uploaded files, OpenAI prompts, or AI output. It also does not implement public authentication. Therefore, there is no claim that upload security, parser isolation, session security, data retention/deletion, or LLM prompt-injection mitigation is complete.

## Required before Phase 2 document ingestion

Document ingestion must introduce authenticated users, object-level authorization, private object storage, filename/path isolation, format/signature/size validation, temporary-file cleanup, parser resource ceilings, malware/active-content policy, retention/deletion behavior, and malicious-document test fixtures. The document body must be treated as untrusted data, never as application instructions.

## Required before Phase 5 AI features

OpenAI access must be server-side only. Inputs must be separated into system policy and explicitly labelled untrusted document data. Responses must use strict schemas, Pydantic validation, permitted evidence references, output escaping, token/cost limits, and adversarial prompt-injection tests. AI output must not become the source of truth for score calculation or candidate facts.
