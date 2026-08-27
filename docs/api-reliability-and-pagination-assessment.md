# API Reliability and Pagination Assessment

**Author:** Manus AI

**Scope:** Bounded response behavior, pagination, ownership disclosure controls, and backward-compatible API evolution.

## Current state

CVMatcher’s private routes are versioned, typed, owner-scoped, and protected by safe correlated error envelopes. Request schemas reject unknown fields, private response projections omit source text and storage identifiers, and missing/cross-user identifiers share the same `404 RESOURCE_NOT_FOUND` response. The API already uses owner-scoped keyset pagination for structured job requirements, analysis history, and action plans. These contracts bound expensive derived collections and retain stable ordering.

The remaining response-bounding gap is limited to top-level CV documents, CV versions, and job targets. Each currently returns a typed `data` array ordered by a stable server-controlled order but without a limit or cursor. The web workspace and typed API client directly consume these full arrays. Adding a default server limit now would silently hide existing private resources from current users and violate the established API behavior.

## Classification

| Area | Classification | Evidence and conclusion |
|---|---|---|
| Error envelope | Implemented | Domain, validation, unexpected, 404, and 405 responses use product-safe correlated envelopes; 405 keeps `Allow`. |
| Ownership disclosure | Implemented | Private resource lookups derive owners from the session and return uniform not-found behavior for inaccessible IDs. |
| Request input bounds | Implemented | Strict Pydantic schemas plus generic/multipart request size guards bound browser input. |
| Private data projection | Implemented | Public document, extraction, target, requirement, analysis, and action responses omit raw source text, tokens, storage keys, and parser internals. |
| Requirement/history/action lists | Implemented | Existing keyset pagination bounds owner-scoped collection reads. |
| CV/target/version lists | Partially implemented | Stable ordering and ownership are present; the public array contract is unbounded. |
| Silent server-side truncation | Rejected | It would be backward-incompatible and could make users believe earlier CV versions or target roles no longer exist. |

## Required pagination transition

The appropriate change is a coordinated contract and workspace transition, not a backend-only query modification. A future phase must define a stable keyset cursor for each remaining list, bounded `limit` validation, an explicit `nextCursor` response field, typed client methods, initial/loading/error/empty states, keyboard-accessible “load more” or pagination controls, and regression coverage for order, cursor ownership, exhaustion, and mobile presentation.

The default behavior must be migrated deliberately. It may initially preserve legacy full-array behavior behind an explicit compatible version/feature transition, or it may introduce a bounded default only in the same release that updates every consuming client. The repository must not accept an arbitrary cursor from another owner, expose internal sort metadata, or treat an offset as a durable cursor.

## Decision

No API response behavior changes in this assessment phase. Existing bounded subresource pagination remains unchanged. The remaining top-level pagination work is **high priority** for growth but requires coordinated backend and frontend implementation; it is not safe to introduce as an isolated backend hardening patch.
