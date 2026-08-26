# ADR 0004: Deterministic Evidence-Based Matching and Scoring

**Status:** Accepted and implemented in Phase 5
**Date:** 2026-08-26

## Context

Phase 3 provides private extracted CV text for an immutable document version. Phase 4 provides private target-role and job-description text. Phase 5 introduces a user-triggered deterministic comparison of exactly one owned CV version and one owned target role.

The score is a planning aid, not a hiring prediction. It must be reproducible from stored inputs and a named scoring version. No LLM, semantic service, external API, learned model, or user-provided instruction influences the result.

## Inputs and trust boundaries

| Input | Trust classification | Phase 5 treatment |
|---|---|---|
| Extracted CV text | Sensitive, untrusted user document content | Read server-side only after an owner-scoped check and successful extraction status. It is tokenized as data, never instructions. |
| Target-role job description | Sensitive, untrusted user document content | Read server-side only after an owner-scoped check. It is tokenized as data, never instructions. |
| Fixed skill, keyword, and degree vocabularies | Application-controlled configuration | Versioned in source, exact-normalized, deterministic, and covered by tests. |
| Analysis output | Sensitive user-owned derived data | Persisted owner-scoped; API returns bounded score/evidence summaries, never raw CV or job-description text. |

## Scoring version `deterministic-v2`

The overall score is a weighted sum of five independently explainable components. Every component includes its weight, matched normalized terms, unmatched requirement terms, state, and a plain-language explanation.

| Component | Weight | Deterministic method | Missing-evidence behavior |
|---|---:|---|---|
| Skills match | 35% | Exact normalized matches of a fixed technical-skill vocabulary appearing in both target and CV text. | A target skill absent from CV evidence is reported as `NOT_FOUND_IN_PROVIDED_CV`. |
| Experience match | 20% | Compares explicit whole-year requirements such as `5+ years` in target text with explicit whole-year CV evidence. | If a target years requirement exists but no qualifying CV evidence is found, report `NOT_FOUND_IN_PROVIDED_CV`; no claim is made about actual experience. |
| Keyword match | 25% | Exact normalized matches from a fixed source-controlled vocabulary of technical and bounded role evidence terms. Arbitrary job-description prose is never converted into a gap. | An unmatched controlled term is labelled as not found in the provided CV. |
| Education match | 10% | Exact degree-category comparison using an ordered fixed vocabulary. | A target degree category absent from CV evidence is reported as `NOT_FOUND_IN_PROVIDED_CV`. |
| ATS readiness | 10% | CV-only structural checks for email/contact presence and common `experience`, `education`, and `skills` markers. | A missing signal is phrased as not found in the provided CV, not as a statement of the candidate’s background. |

The deterministic service calculates each score in the closed range `0`–`100`; overall score uses standard rounding after applying the documented weights. Components with no target signal remain `NOT_APPLICABLE`, contribute their full neutral score of `100`, and state that no corresponding requirement was found in the provided target description. This avoids silently changing weights between analyses.

`deterministic-v2` supersedes the earlier Phase 5 working `deterministic-v1` rule draft because v2 restricts keyword evidence to a controlled vocabulary and removes punctuation-bearing/arbitrary prose from user-facing gaps. Persisted analyses are keyed by scoring version so a material correction does not silently rewrite or mislabel existing results.

## Persistence and API decisions

Each analysis references an immutable CV version and one target role, stores the scoring version and private derived result, and is created only through an explicit authenticated/CSRF-protected request. The database enforces one analysis per `(cv_document_version_id, job_target_id, scoring_version)` tuple. The response provides score metadata, bounded normalized evidence terms, and action-neutral gaps; it does not return raw source text, source resource IDs, or storage details.

## Explicit exclusions

Phase 5 does not use OpenAI, infer experience, recommend CV edits, parse semantic meaning beyond fixed exact-match rules, claim interview likelihood, modify source CVs or targets, accept uploaded analysis artifacts, add billing, introduce queues, use vector retrieval, or create public share links.
