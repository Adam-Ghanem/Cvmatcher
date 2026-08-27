# Deferred Production Capability Gates

**Author:** Manus AI

**Status:** Architectural decision record for capabilities intentionally not implemented in the current deterministic product foundation.

## Purpose

CVMatcher currently operates as a synchronous, private, deterministic CV-to-target analysis product. The backend uses bounded document parsing, owner-scoped PostgreSQL persistence, private local development storage, and no external AI, billing, queue, cache, analytics, or object-storage service. This document records the concrete evidence and approval gates required before those boundaries change.

## Asynchronous processing

Document extraction is intentionally synchronous at the API layer but isolated in a child process with an eight-second wall-clock timeout, a four-second Linux CPU limit, and a 256 MiB address-space limit. The bounded work and lack of production throughput evidence do not currently justify queue infrastructure.

An asynchronous runner becomes appropriate only after production measurements show that synchronous extraction materially harms request reliability or capacity, such as sustained timeouts, unacceptable user-facing latency, repeated provider/storage retries, or a requirement for durable retry/recovery independent of an HTTP request. The selected design must retain owner scoping, idempotent extraction/analysis states, bounded payloads, no raw-document logging, job authorization, retry limits, failure visibility, and deletion/retention coverage. A queue, worker, or Redis instance must not be introduced only for anticipated scale.

## Distributed rate limiting

The current in-memory rate limiter is intentionally bounded to a single API process. It is adequate for local development and a single-instance deployment. Before running more than one API process or replica, rate limiting must move to an explicitly approved shared ingress or distributed enforcement layer. That decision must include trusted-client-IP handling, authentication versus general budgets, failure behavior, monitoring, and abuse-response ownership.

## Billing and entitlement

No billing provider, payment data, subscription state, or plan entitlement is implemented. Adding billing requires confirmed commercial packaging, a provider decision, product owner approval, webhook signature validation, replay/idempotency semantics, authorization boundaries, pricing/currency/tax decisions, secure customer-portal behavior, incident support process, and privacy/security review. Payment credentials and webhook secrets must remain outside source control and must never appear in logs or audit metadata.

## AI-assisted recommendations

No OpenAI or other model provider is currently called. The deterministic scorer remains the only source of match scores, and no extraction pipeline treats document text as instructions. AI work must remain deferred until an explicit product and privacy authorization defines the user value, data-scope consent, provider processing terms, retention, regional handling, cost/rate limits, output schema, abuse controls, and evaluation criteria.

Any future AI capability must preserve the existing rule that it never invents employment history, education, certifications, employers, achievements, or skills. Source document text and job descriptions remain untrusted data; they must be separated from system instructions, sent only when authorized, and never control tools, storage, requests, or scoring. Strict schema validation and deterministic scoring transparency remain mandatory.

## Privacy lifecycle and storage operations

The approved privacy strategy continues to defer account erasure, exports, legal holds, retention timers, backup deletion, restore guards, and managed storage implementation pending business, legal, security, and operations decisions. Existing resource deletes remain immediate live-system actions only; they must not be described as full account erasure or backup purge.

Before production launch, a managed private object-storage adapter, encryption/key-management model, backup inventory, deletion evidence, recovery/restore guard, centralized log-retention controls, operational monitoring, and a privacy approval process remain required. These requirements are product and deployment gates, not hidden implementation backlog.

## Decision summary

| Capability | Current decision | Required trigger or approval |
|---|---|---|
| Queue or worker | Deferred | Measured reliability/capacity need plus durable job design. |
| Redis or shared limiter | Deferred | Horizontal deployment or an approved shared-ingress policy. |
| Billing | Deferred | Commercial packaging, provider, security, legal, and support approval. |
| AI/model provider | Deferred | Explicit product scope and approved privacy/data-processing design. |
| Account deletion/export/retention | Deferred | Approved lifecycle, backup/restore, legal, and operations policy. |
| Managed object storage | Required before production launch | Provider, encryption, replication/versioning, and deletion-operation approval. |
