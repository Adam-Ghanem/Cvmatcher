# Provider-Ready Private Storage Implementation Report

**Author:** Manus AI

## Delivered startup boundary

The private-storage integration now has an explicit `private_storage_backend` setting with `local` and `managed` selections. The local selection remains the development/test default. Production rejects it regardless of the configured filesystem path, closing the gap where an arbitrary local path could previously satisfy the production settings check while application startup still constructed the local adapter.

Application composition now uses a typed private-storage factory alongside the existing rate-limit factory. The default factory creates `LocalPrivateObjectStorage` only when the `local` backend is explicitly selected. A `managed` selection requires a supplied factory and fails startup with a clear operator-facing error if none is configured. Tests prove both the fail-safe absence case and a test-only injected implementation case.

| Configuration state | Startup behavior |
|---|---|
| Development/test + `local` | Creates the existing local private adapter. |
| Staging + `managed` with no factory | Fails startup; no local fallback occurs. |
| Production + `local` | Settings validation rejects configuration before application startup. |
| Production + `managed` with no factory | Settings accepts the intended provider selection; startup fails until a provider factory is supplied. |
| Any environment + `managed` with injected factory | Uses only the injected implementation. |

## Security and operational limits

This is an integration boundary, not a managed storage implementation. It does not add a cloud provider, credentials, public object URL, download route, encryption/KMS setup, replication/versioning rule, malware scanner, quarantine, backup process, deletion lifecycle, or restore guard. Document storage remains private and server-only. Existing signature/archive validation, extraction limits, ownership checks, and raw-content non-disclosure behavior are unchanged.

A production deployment must still approve and implement a provider adapter that preserves opaque object keys, private storage, bounded reads, explicit delete semantics, cleanup/compensation behavior, encryption/key management, regional/data-processing controls, and privacy-lifecycle requirements. The operator must supply that adapter through application composition; no provider name or secret is encoded in the repository.

## Verification

The new tests initially failed against the previous silent-local-fallback behavior, then passed after the explicit selection and factory boundary were implemented. The complete backend gate passed with Ruff, mypy, Alembic schema-drift checking, and 110 pytest tests. The remaining warning is the pre-existing Starlette TestClient/httpx deprecation notice.
