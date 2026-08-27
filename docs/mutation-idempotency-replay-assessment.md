# Mutation Idempotency and Replay Assessment

**Author:** Manus AI

**Scope:** Current authenticated mutation safety; no new public idempotency-key contract.

## Audit result

CVMatcher already has targeted idempotency where a repeated server operation would create a costly or contradictory derived result. The deterministic analysis service reuses an existing persisted analysis for the same owned immutable inputs and scoring version; v3 additionally uses a server-computed input fingerprint. Action generation locks the owned analysis and uses a unique analysis/requirement pair, preserving existing statuses when generation is repeated. Concurrent registration has a database uniqueness constraint and returns the existing safe conflict response.

The remaining create routes intentionally do not accept an `Idempotency-Key`. Adding one would be a public contract and requires a durable owner-scoped record, request fingerprinting, an in-flight response policy, replay response storage, and a retention window that outlives each client/provider retry path. No approved retention policy currently exists for that new personal-data-adjacent record. Adding an incomplete header or a process-local cache would create a false retry guarantee and is therefore not safe.

## Current mutation behavior

| Operation | Existing retry/duplicate protection | Assessment |
|---|---|---|
| Register account | Unique email constraint; concurrent loser rolls back and returns `409 ACCOUNT_UNAVAILABLE`. | Safe duplicate-account prevention. |
| Login | A retry can issue another valid opaque session. | Intentional session behavior; no irreversible external effect. |
| Logout | Revocation is safe in the original request; a retry after cookie clearing may receive the existing authentication response. | No duplicate destructive effect. |
| Create CV document/version | Every successful upload is an explicit immutable version/document, and storage/database failures clean up staged/committed objects. | A response-lost retry may create another intended upload/version; durable idempotency requires an approved retention contract. |
| Start extraction | Existing successful extraction is reused under the immutable version constraint/lock. | Idempotent. |
| Create target role | A repeated browser request creates another user-owned target. | Distinct creates are currently valid product actions; no safe deduplication key exists. |
| Create/update/delete requirement | Target/owner scoped; update sets a declared state and delete is non-duplicating at the database level. | No expensive derived duplicate effect; a public retry contract would need per-operation semantics. |
| Create match analysis | Owner-scoped locks and uniqueness/reuse preserve one deterministic derived result. | Idempotent. |
| Generate action plan | Analysis lock plus unique action pair preserves one plan and user-managed statuses. | Idempotent. |
| Update action status | Repeating a declared status is state-idempotent. | Idempotent state transition. |
| Audit events | Events record individual lifecycle attempts/outcomes under a fixed allowlist. | Event repetition is an operational fact, not a user-visible duplicated resource. |

## Decision

No new idempotency system is introduced in this phase. The existing targeted controls are sufficient for deterministic analysis/extraction/action generation and the registration uniqueness race. Durable generic idempotency remains **approval-gated** until a product decision defines which user-visible creates must be safely retried, how in-flight attempts respond, and how long replay records may be retained.

Any future implementation must use an atomic owner-scoped unique claim, compare a server-computed request fingerprint, reject mismatched payload reuse, return a deliberate in-flight result, never use a client key as authorization, and record no raw CV/job text in the fingerprint or response cache. It must also align deletion and data-export behavior with the approved privacy lifecycle strategy.
