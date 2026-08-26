# Deterministic Scoring v3 Implementation Report

**Status:** Implemented and locally verified

**Scope:** A new, pure `deterministic-v3` scorer that evaluates server-owned reviewed structured requirements against normalized private CV evidence.

**Compatibility:** `deterministic-v2` remains unchanged. Existing v2 analyses remain readable, retain their persisted result payloads, and continue to be reused by the default API path.

## Audit Findings

The scoring audit verified that v2 is a pure five-component scorer over private CV and target-description text. `match_analyses` persists a named `scoring_version`, bounded JSONB `result_payload`, overall score, and a uniqueness tuple over CV version, target, and version. Structured requirements were present but were not previously consumed by a scorer. There was no existing structured requirement-evidence model.

The new phase therefore adds a separate scorer module and a version-aware persistence identity rather than changing the v2 module or migrating v2 result payloads.

## V3 Calculation Design

The v3 scorer accepts only normalized CV terms and a tuple of server-loaded `ReviewedRequirement` values. It has no clock, random value, network request, prompt, model, parser, database access, or client-provided evidence input.

A requirement is calculation-eligible only when it has a normalized skill and a review state of `reviewed` or `user-confirmed`. Requirements without review are represented as `NOT_REVIEWED`; reviewed requirements without a normalized skill are `NOT_COMPARABLE`. Requirements that share a normalized skill are deduplicated deterministically: higher category base weight wins, then higher priority, then stable requirement UUID ordering.

| Category | Base weight | Effective requirement weight |
|---|---:|---|
| `must-have` | 60 | `60 × priority` |
| `should-have` | 30 | `30 × priority` |
| `nice-to-have` | 10 | `10 × priority` |

The overall score is `round(sum(matched effective weights) / sum(all effective weights) × 100)`. An exact normalized-skill hit produces `MATCHED` with `{ source: "CV_NORMALIZED_SKILL", term }`. A miss produces `NOT_FOUND_IN_PROVIDED_CV`, no evidence object, and the exact safe message **“Not found in the provided CV.”** This is evidence language only; it does not claim that a person lacks a qualification.

The response exposes only requirement UUID, normalized/controlled metadata, state, safe message, and bounded normalized term evidence. It never returns raw CV text, raw job description, raw requirement/source text, object keys, paths, or client-supplied evidence.

## Versioning and Persistence

Migration `20260826_0009` adds `match_analyses.input_fingerprint` and replaces the prior uniqueness tuple with `(cv_document_version_id, job_target_id, scoring_version, input_fingerprint)`. Existing rows are preserved with deterministic 64-character legacy fingerprints. The server computes a SHA-256 fingerprint over the v3 scoring version and the sorted server-owned requirement IDs, categories, normalized skills, priorities, review states, and normalization versions.

As a result, unchanged v3 inputs reuse the same persisted analysis, while a reviewed requirement mutation creates a separately versioned v3 analysis. V2 behavior remains intentionally stable: the default request still selects v2 and the service returns the existing v2 record for its CV version/target pair regardless of legacy fingerprint representation.

V3 calculations with no eligible reviewed requirement return `409 REQUIREMENTS_NOT_READY` and do not persist a meaningless score. Blocked CVs remain rejected with the existing `409 CV_TEXT_NOT_READY`; warning-ready CVs remain eligible.

## API Contract

`POST /api/v1/match-analyses` now accepts an optional strict `scoringVersion` of `deterministic-v2` or `deterministic-v3`; omission defaults to v2. The existing detail and history routes remain backward compatible. V3 results add optional `requirements` and `calculationMetadata` fields. Existing v2 result shapes remain valid because the additions are optional.

The API never accepts requirement IDs or evidence objects from a client for scoring. The server derives target ownership from the session, loads requirements by both owner and target IDs, validates readiness on server-stored extraction metadata, and derives evidence only from server-private extracted CV text.

## Security Review

This phase adds no AI/LLM, OCR, embeddings, queue, cache, external API, storage path, new secret, or privacy/retention workflow. Existing opaque sessions, CSRF on analysis creation, uniform owner-scoped `404` behavior, strict Pydantic unknown-field rejection, private extraction boundaries, and deterministic readiness gating are retained.

Focused tests cover same-input purity, explicit must/should/nice weighting, missing-evidence wording, duplicates, unreviewed/non-comparable requirements, zero eligible requirements, warning/blocked CV behavior, v2 historical readability, v3 repeat reuse, changed-requirement fingerprint reanalysis, cross-user v3 target access rejection, and rejection of client-supplied evidence fields.

## Verification

| Check | Result |
|---|---|
| Backend Ruff | Passed |
| Backend mypy | Passed with no issues in 61 source files |
| Backend pytest | 69 passed; one pre-existing Starlette/httpx deprecation warning |
| Focused scoring/analysis/migration suite | 17 passed |
| Focused v3 readiness/ownership suite | 5 passed |
| Frontend ESLint | Passed |
| Frontend TypeScript | Passed |
| Frontend Vitest | 12 passed across 3 test files |
| Frontend production build | Passed |
| Development Alembic state | `20260826_0009 (head)` |
| Isolated test Alembic state | `20260826_0009 (head)` |
| `pnpm audit --audit-level high` | No known vulnerabilities found |
| `pip3 check` | All installed packages compatible |
| Changed-file secret scan | No common private-key, AWS, OpenAI-style, or GitHub-token patterns found |
| Whitespace validation | Passed before final documentation updates; rechecked before commit |

## Next Safe Backend Work

The next bounded phase can add a dedicated action-priority and action-plan persistence model grounded exclusively in persisted v3 requirement/evidence states. It must remain separate from any AI recommendation phase and must preserve the existing private-data and deterministic scoring boundaries.
