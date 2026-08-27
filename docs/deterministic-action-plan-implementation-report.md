# Deterministic Action Plan Implementation Report

**Status:** Implemented and locally verified

**Scope:** Persistent, owner-scoped action plans derived exclusively from one persisted deterministic analysis and its stored v3 requirement-evidence entries.

**Out of scope:** AI/LLM recommendations, OpenAI, OCR, automatic job parsing, embeddings, vector search, Redis, queues, background work, external APIs, frontend changes, extraction redesign, scoring changes, and privacy/retention changes.

## Audit Findings

`match_analyses` is the existing immutable, owner-scoped analysis snapshot. It stores the named scoring version, server-computed input fingerprint, overall score, and bounded result payload. The v3 payload already records safe requirement UUIDs, normalized skills, categories, stored priorities, review metadata, and evidence states. No persistent action-plan model or analysis action route existed.

Both analyses and structured requirements have existing database cascades from their upstream CV/target resources. The chosen action table therefore attaches to `match_analyses` with `ON DELETE CASCADE`, preventing orphaned plans when an analysis disappears due to CV or target deletion. Its optional reference to `job_requirements` uses `ON DELETE SET NULL`, preserving the safe immutable action snapshot even when the current editable requirement is removed.

## Domain and Deterministic Generation

`analysis_actions` is a private persistent subresource owned by the same user as its analysis. It stores only the durable action snapshot fields needed to reproduce the plan: analysis/requirement references, template title and description, computed priority, category, evidence state, user-managed status, deterministic position, and timestamps.

Actions are created only from persisted `deterministic-v3` entries whose state is `NOT_FOUND_IN_PROVIDED_CV`. Matched, unreviewed, non-comparable, and duplicate-superseded requirements do not generate unnecessary actions. V2 analyses safely yield an empty action plan and do not change v2 code, result shape, or score.

| Category | Action priority | Ordering |
|---|---:|---|
| `must-have` | `200 + stored requirement priority` | First among otherwise comparable actions |
| `should-have` | `100 + stored requirement priority` | After must-have actions |
| `nice-to-have` | `stored requirement priority` | After should-have actions |

The fixed category bases are an explainable action ordering policy; they do not alter deterministic-v3 matching or compete with its scoring formula. Ties are resolved by requirement UUID. Titles and descriptions are fixed server templates using only the normalized skill and state: they direct users to add **truthful, verifiable evidence if applicable** and say only that evidence was **not found in the provided CV**.

## API and Idempotency

Three owner-scoped routes were added under the existing analysis resource:

| Method | Path | Contract |
|---|---|---|
| `GET` | `/api/v1/match-analyses/{analysisId}/actions` | Cursor-paginated metadata-only actions. |
| `POST` | `/api/v1/match-analyses/{analysisId}/actions` | CSRF-protected deterministic generation. The only valid body is `{}`. |
| `PATCH` | `/api/v1/match-analyses/{analysisId}/actions/{actionId}` | CSRF-protected status-only update. |

The generation route locks the owned analysis before determining and inserting missing actions. `(analysis_id, requirement_id)` is unique at the database layer, making repeat generation idempotent and preventing duplicate actions for one persisted requirement evidence entry. Generation never trusts client evidence, priorities, requirement IDs, or action content. It derives all values from the persisted analysis snapshot.

## Security and Privacy

Every action route requires the current authenticated session. Writes also validate the existing CSRF boundary. The action service owner-scopes its analysis, cursor, and action queries; absent and cross-user resources use the established uniform `404 RESOURCE_NOT_FOUND` response. Strict Pydantic schemas reject unknown generation fields and status-update fields other than the three bounded statuses.

Responses exclude raw CV text, raw target description, raw requirement/source-reference text, private storage keys, paths, parser data, stack traces, and secrets. No new external service, prompt, model, background process, or private-document processing path was introduced. Existing extraction/readiness and deterministic-v2/v3 behavior are unchanged.

## Database Migration

Migration `20260827_0010_analysis_actions.py` creates the additive `analysis_actions` table with these integrity controls.

| Control | Purpose |
|---|---|
| `analysis_id → match_analyses.id ON DELETE CASCADE` | Removes actions when their analysis is removed through a CV/target cascade. |
| `requirement_id → job_requirements.id ON DELETE SET NULL` | Keeps the historical safe snapshot if the current editable requirement is deleted. |
| `user_id → users.id ON DELETE CASCADE` | Retains tenant ownership and account-resource cleanup semantics. |
| Unique `(analysis_id, requirement_id)` | Enforces action-plan idempotency. |
| Checks for category, priority, position, and status | Prevents invalid persisted values. |
| `(analysis_id, position, id)` index | Supports action-plan keyset pagination. |

The migration is additive. It changes no existing analysis, score, requirement, CV, target, or privacy-lifecycle data.

## Verification

| Check | Result |
|---|---|
| Focused action-plan integration and migration tests | 6 passed |
| Backend Ruff | Passed |
| Backend mypy | Passed with no issues in 65 source files |
| Backend pytest | 74 passed; one pre-existing Starlette/httpx deprecation warning |
| Frontend ESLint | Passed |
| Frontend TypeScript | Passed |
| Frontend Vitest | 12 passed across 3 test files |
| Frontend production build | Passed |
| Development Alembic state | `20260827_0010 (head)` |
| Isolated test Alembic state | `20260827_0010 (head)` |
| `pnpm audit --audit-level high` | No known vulnerabilities found |
| `pip3 check` | All installed packages compatible |
| Changed-file secret scan | No common private-key, AWS, OpenAI-style, or GitHub-token patterns found |
| Whitespace validation | Passed before documentation updates; rechecked before commit |

## Limitations and Next Safe Work

This phase deliberately contains no AI recommendations and no automatic job requirement extraction. It adds no OCR, LLM, OpenAI, vector, embedding, queue, Redis, or external API functionality.

A future bounded phase can add an accessible frontend action-plan experience using these metadata-only contracts. It should not calculate priority or scores in the browser. Any AI-assisted recommendation capability remains a separate, approval-gated design and security effort.
