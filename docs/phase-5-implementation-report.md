# Phase 5 Implementation Report: Deterministic Evidence Matching

**Status:** Complete and locally verified
**Date:** 2026-08-26
**Scope:** Owner-scoped, deterministic CV-to-target-role evidence matching only. No AI or recommendation capability was added.

## Delivered capabilities

| Capability | Delivered behavior |
|---|---|
| Deterministic scorer | `deterministic-v2` combines five fixed-weight components: skills (35%), explicit experience evidence (20%), controlled keywords (25%), education evidence (10%), and ATS structural signals (10%). All rules are local, source-controlled, exact-normalized, and have no network/model dependency. |
| Controlled keyword evidence | Keyword gaps are restricted to a fixed source-controlled vocabulary. Arbitrary prose and punctuation-bearing tokens from target descriptions cannot become user-facing gaps. The material rule refinement was versioned from the working v1 draft to `deterministic-v2`. |
| Private persistence | Alembic revision `20260826_0005` adds `match_analyses`, including ownership, CV-version/target foreign keys, score validation, payload storage, indexes, and a unique CV-version/target/scoring-version tuple. |
| Protected API | `POST /api/v1/match-analyses` is authenticated and CSRF-protected. It creates or reuses one owner-scoped result. `GET /api/v1/match-analyses/{id}` returns only an owned result. |
| Evidence-safe output | Public responses contain score metadata, component explanations, bounded normalized evidence, and `NOT_FOUND_IN_PROVIDED_CV` gaps only. They omit raw CV text, raw job-description text, selected resource IDs, storage keys, and user IDs. |
| Accessible workspace | The protected workspace now lets users select a prepared CV and saved target, create an evidence match, inspect weighted component evidence, review priorities, and expand a “How we calculated this” disclosure. It includes loading, empty, error, disabled, keyboard-native form, focus, and responsive states. |
| Testing | Added deterministic unit coverage, database-backed API integration coverage, browser client contract coverage, and workspace interaction coverage. |

## Verification evidence

| Area | Verification | Result |
|---|---|---|
| Deterministic scorer | Focused regression for controlled keywords and punctuation normalization | `3 passed` |
| Analysis API | Authentication, CSRF, success, reuse, readiness, ownership, retrieval, and no-raw-text integration tests | `4 passed` |
| Backend quality | `ruff check . && mypy app && pytest` | `45 passed`; one pre-existing Starlette/httpx deprecation warning |
| Web quality | `pnpm web:lint && pnpm web:typecheck && pnpm web:test && pnpm web:build` | Lint/typecheck clean; `9 passed`; production build completed |
| Migration | `alembic upgrade head && alembic current` against development PostgreSQL | `20260826_0005 (head)` |
| Operational health | Restarted local API; checked `/api/v1/health` and `/api/v1/ready` | Both returned success with database ready |
| Authenticated live flow | Disposable local account uploaded a harmless DOCX fixture, prepared private text, saved a private target, and created a fresh `deterministic-v2` result | Rendered an 88% evidence match with only normalized evidence and two controlled keyword gaps; raw source text remained absent |
| Browser behavior | Authenticated workspace showed disabled guidance before preparation, target refresh behavior, native selects, result focus, and method disclosure | Verified on the local 3000 development origin |

## Security and privacy review

The analysis service derives ownership from the validated session and never accepts a client owner ID. It owner-scopes CV versions, target roles, and persisted analyses; inaccessible references return uniform `404 RESOURCE_NOT_FOUND` errors. Analysis creation requires CSRF validation and requires a successful existing private extraction, returning `409 CV_TEXT_NOT_READY` otherwise.

CV text and job-description text remain untrusted private data and are not rendered, logged intentionally, passed to a prompt, sent to a model, or included in public response payloads. The scorer operates entirely on local exact normalized data and source-controlled vocabularies. Output phrases missing evidence as **“Not found in the provided CV”** rather than making claims about a user’s actual qualifications.

## Deliberate exclusions

Phase 5 does not call OpenAI, use embeddings or vector search, infer qualifications, generate recommendations, edit CV text, parse semantic meaning beyond fixed exact matching, claim employment or interview likelihood, serve downloads, add billing, introduce queues/workers beyond the pre-existing bounded parser process, or add public sharing.

## Remaining operational limits

The current local filesystem private-storage adapter and in-memory rate limiter remain development/test controls. Production still requires managed private storage, HTTPS termination, secret management, monitoring, backup/restore operations, malware-scanning policy, retention configuration, and verified user-controlled deletion before public launch. Existing analyses created under an earlier named scoring version remain reproducible; a version change permits an intentional new analysis rather than rewriting historical results.

## Recommended next bounded phase

Phase 6 should add user-controlled data lifecycle operations for private CV documents, extractions, target roles, and analyses. The work should define retention semantics, owner-scoped deletion, safe cascade behavior, recovery messaging, audit events, and test coverage. AI recommendations remain out of scope until a later explicit design review covers consent, prompt injection, strict model schemas, cost/latency controls, and evidence grounding.
